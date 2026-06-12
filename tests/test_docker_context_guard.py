import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "docker_context_guard.py"


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class DockerContextGuardTest(unittest.TestCase):
    def run_cli(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), str(project), *args],
            text=True,
            capture_output=True,
        )

    def test_missing_dockerignore_reports_node_modules_and_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / "Dockerfile", "FROM node:22-alpine\nCOPY . .\n")
            write(project / "app.js", "console.log('ok')\n")
            write(project / "node_modules" / "left-pad" / "index.js", "module.exports = 1\n")
            write(project / ".env.local", "TOKEN=not-real\n")

            result = self.run_cli(project)

            self.assertEqual(result.returncode, 1)
            self.assertIn("DCG001", result.stdout)
            self.assertIn("DCG002", result.stdout)
            self.assertIn("DCG003", result.stdout)
            self.assertIn("DCG005", result.stdout)
            self.assertIn("node_modules/", result.stdout)
            self.assertIn(".env*", result.stdout)

    def test_dockerignore_excludes_risky_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / "Dockerfile", "FROM python:3.12-slim\nCOPY . /app\n")
            write(project / ".dockerignore", "node_modules/\n.env*\n.git/\n")
            write(project / "node_modules" / "pkg" / "index.js")
            write(project / ".env", "SECRET=not-real\n")
            write(project / ".git" / "config", "[core]\n")
            write(project / "app.py", "print('ok')\n")

            result = self.run_cli(project)

            self.assertEqual(result.returncode, 0)
            self.assertIn("No risky build-context findings", result.stdout)

    def test_negation_can_reinclude_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / ".dockerignore", "*.md\n!README.md\n")
            write(project / "README.md", "# Keep\n")
            write(project / "notes.md", "# Ignore\n")

            result = self.run_cli(project, "--format", "json", "--fail-on", "none")
            data = json.loads(result.stdout)
            paths = {item["path"] for item in data["top_files"]}

            self.assertEqual(result.returncode, 0)
            self.assertIn("README.md", paths)
            self.assertNotIn("notes.md", paths)

    def test_json_output_has_findings_and_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / "Dockerfile", "FROM scratch\nCOPY . .\n")
            write(project / "secrets" / "private_key.pem", "not-real\n")

            result = self.run_cli(project, "--format", "json")
            data = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            self.assertEqual(data["findings"][0]["severity"], "high")
            self.assertIn("*.pem", data["suggested_dockerignore"])

    def test_env_suffix_suggestion_matches_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / "local.env", "TOKEN=not-real\n")

            result = self.run_cli(project, "--format", "json", "--fail-on", "none")
            data = json.loads(result.stdout)

            self.assertEqual(result.returncode, 0)
            self.assertIn("*.env", data["suggested_dockerignore"])

    def test_size_limit_finding_can_fail_on_medium(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / ".dockerignore", "")
            write(project / "big.bin", "x" * 4096)

            result = self.run_cli(project, "--max-size-mb", "0.001", "--fail-on", "medium")

            self.assertEqual(result.returncode, 1)
            self.assertIn("DCG004", result.stdout)

    def test_dockerfile_specific_ignore_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            write(project / ".dockerignore", "")
            write(project / "docker" / "prod.Dockerfile", "FROM scratch\nCOPY . .\n")
            write(project / "docker" / "prod.Dockerfile.dockerignore", "node_modules/\n.env*\n")
            write(project / "node_modules" / "pkg" / "index.js")
            write(project / ".env.production", "SECRET=not-real\n")
            write(project / "main.py", "print('ok')\n")

            result = self.run_cli(project, "--dockerfile", str(project / "docker" / "prod.Dockerfile"))

            self.assertEqual(result.returncode, 0)
            self.assertIn("prod.Dockerfile.dockerignore", result.stdout)
            self.assertIn("No risky build-context findings", result.stdout)

    def test_invalid_context_exits_two(self) -> None:
        result = self.run_cli(Path("/path/that/does/not/exist"))

        self.assertEqual(result.returncode, 2)
        self.assertIn("context directory not found", result.stderr)

    def test_invalid_positive_integer_argument(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = self.run_cli(project, "--top", "0")

            self.assertEqual(result.returncode, 2)
            self.assertIn("must be a positive integer", result.stderr)


if __name__ == "__main__":
    unittest.main()
