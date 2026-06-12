# Release Manifest

This file is the public release allowlist used by `scripts/prepublish_gate.py`.

## Included

```text
.github/workflows/ci.yml
.gitignore
AGENTS.md
LICENSE.md
MANIFEST.in
README.md
docker_context_guard.py
docs/launch-plan.md
docs/product-brief.md
docs/release-manifest.md
docs/validation-report.md
examples/risky-node/Dockerfile
examples/risky-node/build/bundle.js
examples/risky-node/local.env
examples/risky-node/node_modules/demo/index.js
examples/risky-node/package.json
examples/risky-node/server.js
pyproject.toml
scripts/prepublish_gate.py
tests/test_docker_context_guard.py
```

## Excluded

Generated artifacts are not part of the source release tree:

```text
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
build/
dist/
*.egg-info/
```
