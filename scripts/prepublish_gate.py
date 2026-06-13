#!/usr/bin/env python3
"""Run release checks before publishing Docker Context Guard."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

PUBLIC_FILES = {
    ".github/workflows/ci.yml",
    ".gitignore",
    ".pre-commit-hooks.yaml",
    "AGENTS.md",
    "LICENSE.md",
    "MANIFEST.in",
    "README.md",
    "action.yml",
    "docker_context_guard.py",
    "docs/launch-drafts.md",
    "docs/launch-plan.md",
    "docs/product-brief.md",
    "docs/release-manifest.md",
    "docs/release-notes-v0.1.0.md",
    "docs/validation-report.md",
    "examples/risky-node/Dockerfile",
    "examples/risky-node/build/bundle.js",
    "examples/risky-node/local.env",
    "examples/risky-node/node_modules/demo/index.js",
    "examples/risky-node/package.json",
    "examples/risky-node/server.js",
    "pyproject.toml",
    "scripts/prepublish_gate.py",
    "tests/test_docker_context_guard.py",
}

FORBIDDEN_TEXT = (
    "/home/" + "wloe",
    "/mnt/" + "hgfs",
    "agent" + "-market-lab",
    "Agent " + "Brief",
)

IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", ".release-venv"}


def run(args: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args))
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def clean_generated() -> None:
    for path in (ROOT / "dist", ROOT / "build"):
        if path.exists():
            shutil.rmtree(path)
    for egg_info in ROOT.glob("*.egg-info"):
        shutil.rmtree(egg_info)
    for pycache in ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)


def check_docs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required = [
        "not a vulnerability scanner",
        "zero-dependency Python CLI",
        "Dockerfile-specific ignore",
        "Hadolint",
        "Trivy",
        "Dockle",
        "dive",
        "--fail-on",
        "GitHub Action",
        "pre-commit",
        "v0.1.0",
        "actions/checkout@v6",
        "actions/setup-python@v6",
    ]
    missing = [item for item in required if item not in readme]
    if missing:
        raise SystemExit(f"README is missing required release terms: {missing}")

    manifest = (ROOT / "docs" / "release-manifest.md").read_text(encoding="utf-8")
    for file_name in sorted(PUBLIC_FILES):
        if file_name not in manifest:
            raise SystemExit(f"release manifest is missing {file_name}")

    package_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    for expected in ("include action.yml", "include .pre-commit-hooks.yaml"):
        if expected not in package_manifest:
            raise SystemExit(f"MANIFEST.in is missing {expected}")

    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    for expected in ("using: composite", "docker-context-guard", "github.action_path", "actions/setup-python@v6"):
        if expected not in action:
            raise SystemExit(f"action.yml is missing {expected}")
    for lineno, line in enumerate(action.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("description: ") and not stripped.removeprefix("description: ").startswith('"'):
            raise SystemExit(f"action.yml description must be quoted on line {lineno}")

    pre_commit = (ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    for expected in ("id: docker-context-guard", "pass_filenames: false", "language: python"):
        if expected not in pre_commit:
            raise SystemExit(f".pre-commit-hooks.yaml is missing {expected}")


def check_sample_outputs() -> None:
    text_result = run([PYTHON, "docker_context_guard.py", "examples/risky-node", "--fail-on", "none"])
    for expected in ("DCG001", "DCG002", "DCG003", "DCG005", "*.env", "build/", "node_modules/"):
        if expected not in text_result.stdout:
            raise SystemExit(f"text sample output missing {expected}")

    json_result = run([PYTHON, "docker_context_guard.py", "examples/risky-node", "--format", "json", "--fail-on", "none"])
    data = json.loads(json_result.stdout)
    suggestions = set(data["suggested_dockerignore"])
    if not {"*.env", "build/", "node_modules/"}.issubset(suggestions):
        raise SystemExit(f"json sample suggestions are incomplete: {suggestions}")
    if not any(item["path"] == "node_modules" for item in data["findings"]):
        raise SystemExit("json sample missing node_modules finding")


def release_files() -> set[str]:
    files: set[str] = set()
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        parts = set(rel.split("/"))
        if rel.startswith(("build/", "dist/")):
            continue
        if rel.split("/", 1)[0].endswith(".egg-info"):
            continue
        if parts & IGNORED_PARTS:
            continue
        if rel.endswith(".pyc"):
            continue
        files.add(rel)
    return files


def check_release_allowlist() -> None:
    actual = release_files()
    extra = sorted(actual - PUBLIC_FILES)
    missing = sorted(PUBLIC_FILES - actual)
    if extra or missing:
        raise SystemExit(f"release file mismatch\nextra={extra}\nmissing={missing}")


def check_public_text_hygiene() -> None:
    for rel in sorted(PUBLIC_FILES):
        path = ROOT / rel
        if path.suffix.lower() not in {".md", ".py", ".toml", ".yml", ".yaml", ".txt", ".js", ".json", ""}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN_TEXT:
            if marker in text:
                raise SystemExit(f"forbidden marker {marker!r} found in {rel}")


def check_package_build() -> None:
    run([PYTHON, "-m", "build"])
    run([PYTHON, "-m", "twine", "check", "dist/*"])
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    if not wheels:
        raise SystemExit("wheel was not built")

    with tempfile.TemporaryDirectory() as temp:
        venv = Path(temp) / "venv"
        run([PYTHON, "-m", "venv", str(venv)])
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = venv / ("Scripts/docker-context-guard.exe" if os.name == "nt" else "bin/docker-context-guard")
        run([str(python), "-m", "pip", "install", "--quiet", str(wheels[-1])])
        installed = run([str(cli), "examples/risky-node", "--fail-on", "none"])
        if "Docker Context Guard Report" not in installed.stdout:
            raise SystemExit("installed console script did not produce expected report")


def check_manifest_format() -> None:
    manifest = ROOT / "docs" / "release-manifest.md"
    listed = set(re.findall(r"^([A-Za-z0-9_./-]+)$", manifest.read_text(encoding="utf-8"), flags=re.MULTILINE))
    missing = PUBLIC_FILES - listed
    if missing:
        raise SystemExit(f"manifest code block missing files: {sorted(missing)}")


def main() -> int:
    clean_generated()
    check_docs()
    check_manifest_format()
    run([PYTHON, "-m", "unittest", "discover", "-s", "tests"])
    run([PYTHON, "-m", "py_compile", "docker_context_guard.py", "scripts/prepublish_gate.py"])
    check_sample_outputs()
    check_release_allowlist()
    check_public_text_hygiene()
    check_package_build()
    print("prepublish gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
