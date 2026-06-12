# AGENTS.md

## Project Map

- Main CLI: `docker_context_guard.py`
- Tests: `tests/test_docker_context_guard.py`
- Release gate: `scripts/prepublish_gate.py`
- Product rationale: `docs/product-brief.md`
- Validation evidence: `docs/validation-report.md`

## Commands

- `python -m unittest discover -s tests`
- `python -m py_compile docker_context_guard.py scripts/prepublish_gate.py`
- `python docker_context_guard.py examples/risky-node --fail-on none`
- `python scripts/prepublish_gate.py`

## Agent Rules

- Keep the project zero-dependency at runtime.
- Do not claim exact Docker parity; this tool is a conservative preflight guard.
- Keep tests synthetic and local.
- Do not add real secrets to examples or tests.
- Update `docs/release-manifest.md` when adding release files.
