#!/usr/bin/env python3
"""Audit Docker build contexts before Docker has to upload them."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


DEFAULT_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".turbo",
    "__pycache__",
}

RISKY_DIRS: dict[str, tuple[str, str, str]] = {
    ".git": ("high", ".git", "Git history is included in the build context."),
    "node_modules": ("high", "node_modules", "Local dependencies are included in the build context."),
    ".venv": ("high", ".venv", "A Python virtualenv is included in the build context."),
    "venv": ("high", "venv", "A Python virtualenv is included in the build context."),
    "env": ("medium", "env", "A local environment directory is included in the build context."),
    "dist": ("medium", "dist", "Build output is included in the build context."),
    "build": ("medium", "build", "Build output is included in the build context."),
    "target": ("medium", "target", "Rust/Java build output is included in the build context."),
    "coverage": ("medium", "coverage", "Coverage output is included in the build context."),
    ".pytest_cache": ("low", ".pytest_cache", "Python test cache is included in the build context."),
    ".mypy_cache": ("low", ".mypy_cache", "Python type-check cache is included in the build context."),
    ".ruff_cache": ("low", ".ruff_cache", "Ruff cache is included in the build context."),
    ".next": ("medium", ".next", "Next.js build/cache output is included in the build context."),
    ".turbo": ("medium", ".turbo", "Turborepo cache is included in the build context."),
    "__pycache__": ("low", "__pycache__", "Python bytecode cache is included in the build context."),
}

SENSITIVE_NAME_RE = re.compile(
    r"(^|[._-])("
    r"env|secret|secrets|token|tokens|credential|credentials|password|passwd"
    r")([._-]|$)"
    r"|(^|[._-])(api|access|private|ssh)[._-]?key([._-]|$)"
    r"|^(id_rsa|id_dsa|id_ecdsa|id_ed25519)$"
    r"|\.(pem|key|p12|pfx)$",
    re.IGNORECASE,
)

BROAD_COPY_RE = re.compile(r"^\s*(COPY|ADD)\s+(?:--[^\s]+\s+)*(\.|(?:\./))\s+", re.IGNORECASE)
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class IgnoreRule:
    raw: str
    pattern: str
    negated: bool
    directory_only: bool
    line: int


@dataclass(frozen=True)
class FileEntry:
    path: str
    size: int


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    path: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class AuditReport:
    context: str
    dockerfile: str | None
    ignore_file: str | None
    included_files: int
    included_bytes: int
    total_files_seen: int
    findings: list[Finding]
    top_files: list[FileEntry]
    top_dirs: list[FileEntry]
    suggested_dockerignore: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Docker build context size, secrets, and .dockerignore gaps before running docker build."
    )
    parser.add_argument("context", nargs="?", default=".", type=Path, help="Docker build context directory. Default: current directory.")
    parser.add_argument("--dockerfile", type=Path, default=None, help="Dockerfile path. Default: CONTEXT/Dockerfile when present.")
    parser.add_argument("--max-size-mb", type=float, default=100.0, help="Warn when included context exceeds this size. Default: 100")
    parser.add_argument("--top", type=positive_int, default=8, help="Number of largest files/directories to show. Default: 8")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format. Default: text")
    parser.add_argument(
        "--fail-on",
        choices=("none", "low", "medium", "high"),
        default="high",
        help="Exit 1 when findings at or above this severity exist. Default: high",
    )
    return parser.parse_args(argv)


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def normalize_rel(path: Path) -> str:
    rel = path.as_posix()
    return rel[2:] if rel.startswith("./") else rel


def read_ignore_rules(ignore_file: Path | None) -> list[IgnoreRule]:
    if ignore_file is None or not ignore_file.is_file():
        return []
    rules: list[IgnoreRule] = []
    for line_no, line in enumerate(ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        negated = stripped.startswith("!")
        if negated:
            stripped = stripped[1:].strip()
        if not stripped or stripped == ".":
            continue
        directory_only = stripped.endswith("/")
        pattern = stripped.strip("/")
        if pattern:
            rules.append(IgnoreRule(raw=line.strip(), pattern=pattern, negated=negated, directory_only=directory_only, line=line_no))
    return rules


def find_ignore_file(context: Path, dockerfile: Path | None) -> Path | None:
    if dockerfile is not None:
        specific = dockerfile.with_name(dockerfile.name + ".dockerignore")
        if specific.is_file():
            return specific
    root_ignore = context / ".dockerignore"
    return root_ignore if root_ignore.is_file() else None


def rule_matches(rule: IgnoreRule, rel_path: str, is_dir: bool) -> bool:
    rel = rel_path.strip("/")
    if not rel:
        return False
    parts = rel.split("/")
    pattern = rule.pattern
    if rule.directory_only and not (is_dir or any(fnmatch.fnmatch(part, pattern) for part in parts[:-1])):
        return False
    if "/" not in pattern:
        if any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
        return fnmatch.fnmatch(PurePosixPath(rel).name, pattern)
    if fnmatch.fnmatch(rel, pattern) or PurePosixPath(rel).match(pattern):
        return True
    return rel.startswith(pattern.rstrip("/") + "/")


def is_ignored(rel_path: str, is_dir: bool, rules: list[IgnoreRule]) -> bool:
    ignored = False
    for rule in rules:
        if rule_matches(rule, rel_path, is_dir):
            ignored = not rule.negated
    return ignored


def iter_context_files(context: Path, rules: list[IgnoreRule]) -> tuple[list[FileEntry], int]:
    included: list[FileEntry] = []
    total_seen = 0
    for current, dirs, names in os.walk(context):
        current_path = Path(current)
        rel_dir = current_path.relative_to(context)
        kept_dirs = []
        for directory in sorted(dirs):
            rel = normalize_rel(rel_dir / directory)
            if not is_ignored(rel, True, rules):
                kept_dirs.append(directory)
        dirs[:] = kept_dirs
        for name in sorted(names):
            path = current_path / name
            rel = normalize_rel(path.relative_to(context))
            total_seen += 1
            if is_ignored(rel, False, rules):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            included.append(FileEntry(path=rel, size=size))
    return included, total_seen


def dir_totals(files: list[FileEntry]) -> list[FileEntry]:
    totals: dict[str, int] = {}
    for entry in files:
        parts = PurePosixPath(entry.path).parts
        if len(parts) == 1:
            totals["."] = totals.get(".", 0) + entry.size
        else:
            totals[parts[0]] = totals.get(parts[0], 0) + entry.size
    return [FileEntry(path=path, size=size) for path, size in totals.items()]


def collect_risky_dirs(files: list[FileEntry]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for entry in files:
        for part in PurePosixPath(entry.path).parts[:-1]:
            if part in RISKY_DIRS and part not in seen:
                severity, suggestion, message = RISKY_DIRS[part]
                findings.append(Finding("DCG002", severity, part, message, f"Add `{suggestion}/` to .dockerignore."))
                seen.add(part)
    return findings


def collect_sensitive_files(files: list[FileEntry]) -> list[Finding]:
    findings: list[Finding] = []
    for entry in files:
        name = PurePosixPath(entry.path).name
        if SENSITIVE_NAME_RE.search(name):
            findings.append(
                Finding(
                    "DCG003",
                    "high",
                    entry.path,
                    "Sensitive-looking file is included in the Docker build context.",
                    f"Add `{suggest_ignore_pattern(entry.path)}` to .dockerignore or move the file outside the context.",
                )
            )
    return findings


def collect_size_finding(files: list[FileEntry], max_size_mb: float) -> list[Finding]:
    included_bytes = sum(entry.size for entry in files)
    limit = max_size_mb * 1024 * 1024
    if included_bytes <= limit:
        return []
    return [
        Finding(
            "DCG004",
            "medium",
            ".",
            f"Included context is {human_size(included_bytes)}, above the {max_size_mb:g} MB limit.",
            "Ignore generated, dependency, cache, and local artifact directories.",
        )
    ]


def collect_broad_copy_finding(dockerfile: Path | None, risky_findings: list[Finding]) -> list[Finding]:
    if dockerfile is None or not dockerfile.is_file() or not risky_findings:
        return []
    findings: list[Finding] = []
    for line_no, line in enumerate(dockerfile.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if BROAD_COPY_RE.search(line):
            findings.append(
                Finding(
                    "DCG005",
                    "medium",
                    f"{dockerfile.name}:{line_no}",
                    "Dockerfile copies the whole context while risky files or directories are included.",
                    "Tighten .dockerignore or copy dependency manifests before copying the rest of the source.",
                )
            )
    return findings


def collect_missing_ignore_finding(context: Path, ignore_file: Path | None, findings: list[Finding]) -> list[Finding]:
    if ignore_file is not None or not findings:
        return []
    return [
        Finding(
            "DCG001",
            "medium",
            ".dockerignore",
            "No .dockerignore file was found, but the context contains risky or bulky paths.",
            "Create .dockerignore with the suggested patterns.",
        )
    ]


def suggest_ignore_pattern(path: str) -> str:
    parts = PurePosixPath(path).parts
    for part in parts:
        if part in RISKY_DIRS:
            return part + "/"
    name = PurePosixPath(path).name
    lowered = name.lower()
    if lowered.startswith(".env"):
        return ".env*"
    if lowered.endswith(".env"):
        return "*.env"
    if ".env." in lowered:
        return "*.env.*"
    if name.endswith((".pem", ".key", ".p12", ".pfx")):
        return "*" + PurePosixPath(name).suffix
    return path


def suggested_patterns(findings: list[Finding]) -> list[str]:
    suggestions: list[str] = []
    for finding in findings:
        match = re.search(r"`([^`]+)`", finding.suggestion)
        if match:
            suggestions.append(match.group(1))
    defaults = [".git/", "node_modules/", ".env*", "*.pem", "*.key", "dist/", "build/", "coverage/"]
    for item in defaults:
        if any(finding.path.startswith(item.strip("/")) for finding in findings):
            suggestions.append(item)
    return sorted(dict.fromkeys(suggestions))


def audit(context: Path, dockerfile_arg: Path | None, max_size_mb: float, top: int) -> AuditReport:
    context = context.expanduser().resolve()
    if not context.is_dir():
        raise ValueError(f"context directory not found: {context}")
    dockerfile = None
    if dockerfile_arg is not None:
        candidate = dockerfile_arg.expanduser()
        dockerfile = candidate.resolve() if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
    elif (context / "Dockerfile").is_file():
        dockerfile = context / "Dockerfile"
    ignore_file = find_ignore_file(context, dockerfile)
    rules = read_ignore_rules(ignore_file)
    files, total_seen = iter_context_files(context, rules)
    included_bytes = sum(entry.size for entry in files)
    top_files = sorted(files, key=lambda item: item.size, reverse=True)[:top]
    top_dirs = sorted(dir_totals(files), key=lambda item: item.size, reverse=True)[:top]

    findings: list[Finding] = []
    risky = collect_risky_dirs(files)
    sensitive = collect_sensitive_files(files)
    findings.extend(risky)
    findings.extend(sensitive)
    findings.extend(collect_missing_ignore_finding(context, ignore_file, [*risky, *sensitive]))
    findings.extend(collect_size_finding(files, max_size_mb))
    findings.extend(collect_broad_copy_finding(dockerfile, [*risky, *sensitive]))
    findings = sorted(findings, key=lambda item: (-SEVERITY_ORDER[item.severity], item.rule, item.path))

    return AuditReport(
        context=str(context),
        dockerfile=str(dockerfile) if dockerfile else None,
        ignore_file=str(ignore_file) if ignore_file else None,
        included_files=len(files),
        included_bytes=included_bytes,
        total_files_seen=total_seen,
        findings=findings,
        top_files=top_files,
        top_dirs=top_dirs,
        suggested_dockerignore=suggested_patterns(findings),
    )


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def report_to_dict(report: AuditReport) -> dict[str, Any]:
    data = asdict(report)
    data["included_human"] = human_size(report.included_bytes)
    return data


def render_text(report: AuditReport) -> str:
    lines = [
        "# Docker Context Guard Report",
        "",
        f"Context: `{report.context}`",
        f"Dockerfile: `{report.dockerfile or 'not found'}`",
        f"Ignore file: `{report.ignore_file or 'not found'}`",
        f"Included files: {report.included_files} / {report.total_files_seen}",
        f"Included size: {human_size(report.included_bytes)}",
        "",
        "## Findings",
        "",
    ]
    if report.findings:
        for finding in report.findings:
            lines.append(f"- [{finding.severity.upper()}] {finding.rule} `{finding.path}`: {finding.message}")
            lines.append(f"  Suggestion: {finding.suggestion}")
    else:
        lines.append("- No risky build-context findings.")

    lines.extend(["", "## Largest Included Directories", ""])
    for entry in report.top_dirs:
        lines.append(f"- `{entry.path}`: {human_size(entry.size)}")
    if not report.top_dirs:
        lines.append("- None.")

    lines.extend(["", "## Largest Included Files", ""])
    for entry in report.top_files:
        lines.append(f"- `{entry.path}`: {human_size(entry.size)}")
    if not report.top_files:
        lines.append("- None.")

    lines.extend(["", "## Suggested .dockerignore Additions", ""])
    if report.suggested_dockerignore:
        lines.extend(f"- `{item}`" for item in report.suggested_dockerignore)
    else:
        lines.append("- No additions suggested.")
    return "\n".join(lines) + "\n"


def should_fail(report: AuditReport, threshold: str) -> bool:
    if threshold == "none":
        return False
    minimum = SEVERITY_ORDER[threshold]
    return any(SEVERITY_ORDER[finding.severity] >= minimum for finding in report.findings)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = audit(args.context, args.dockerfile, args.max_size_mb, args.top)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report_to_dict(report), indent=2, ensure_ascii=False))
    else:
        print(render_text(report), end="")
    return 1 if should_fail(report, args.fail_on) else 0


if __name__ == "__main__":
    raise SystemExit(main())
