# Docker Context Guard v0.1.0

Initial public release.

Docker Context Guard is a zero-runtime-dependency Python CLI that audits a Docker build context before `docker build` uploads it. It is meant as a fast preflight check, not a vulnerability scanner.

## Highlights

- Detects missing `.dockerignore` files when risky or bulky paths are present.
- Flags included `node_modules`, `.git`, virtualenvs, build outputs, caches, coverage folders, and secret-looking files.
- Warns when broad `COPY . .` / `ADD . ...` instructions are used while risky paths are still included.
- Supports Dockerfile-specific ignore files such as `docker/prod.Dockerfile.dockerignore`.
- Provides text and JSON output with a configurable `--fail-on` threshold for CI.
- Includes a GitHub Action wrapper and a pre-commit hook entry.

## Quick Try

```bash
git clone https://github.com/wc1905605162-sketch/docker-context-guard.git
cd docker-context-guard
python docker_context_guard.py examples/risky-node --fail-on none
```

Or use it in GitHub Actions:

```yaml
- uses: wc1905605162-sketch/docker-context-guard@v0.1.0
  with:
    fail-on: high
```

## Boundaries

- This is a conservative triage tool, not a security audit.
- `.dockerignore` matching is intentionally small and local; verify with Docker or BuildKit when exact parity matters.
- Secret detection is filename-based and can miss real secrets or flag harmless fixtures.
