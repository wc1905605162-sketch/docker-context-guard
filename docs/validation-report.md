# Validation Report

Date: 2026-06-12

## What Was Tested

Local unit tests cover:

- missing `.dockerignore` with `node_modules`, env file, and broad `COPY`
- ignored risky paths producing no findings
- `.dockerignore` negation re-including a file
- JSON output and suggested patterns
- `*.env` suggestion for `local.env`
- context size threshold failures
- Dockerfile-specific `.dockerignore` precedence
- invalid context exit code
- invalid positive integer argument handling

Manual sample checks cover:

```bash
python docker_context_guard.py examples/risky-node --fail-on none
python docker_context_guard.py examples/risky-node --format json --fail-on none
```

The risky Node fixture intentionally includes:

- `node_modules/demo/index.js`
- `build/bundle.js`
- `local.env`
- broad `COPY . .`
- no `.dockerignore`

Release documentation checks cover:

- bilingual English/Chinese README
- public product brief
- launch plan
- release manifest
- prepublish gate documentation

## Iteration Notes

First unit run failed three tests. Root cause: relative path normalization used `lstrip("./")`, which stripped meaningful leading dots from `.env.local` and `.git`. Fix: only remove a literal leading `./`.

Second manual review found a more realistic issue: `local.env` was detected but suggested `.env*`, which would not ignore `local.env`. Fix: suggest `*.env` for suffix-style env files, `.env*` for dot-env files, and `*.env.*` for infix env files.

## Current Result

Unit tests:

```text
Ran 9 tests
OK
```

Sample findings:

```text
DCG002 node_modules
DCG003 local.env
DCG001 .dockerignore
DCG002 build
DCG005 Dockerfile:3
```

Suggested ignore additions:

```dockerignore
*.env
build/
node_modules/
```

## Remaining Risk

- `.dockerignore` pattern matching is intentionally simplified and should not be described as Docker-equivalent.
- Broad `COPY` detection is line-oriented and does not cover every Dockerfile form.
- Filename-based secret detection is a triage signal, not proof.
