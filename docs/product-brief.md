# Product Brief: Docker Context Guard

## Problem

Docker build context mistakes are easy to miss because the dangerous state is local and boring: `node_modules`, `.git`, virtualenvs, build outputs, caches, and local env files sit next to application code. A broad build context and `COPY . .` can upload those files to a local or remote builder.

Public demand signals:

- Docker docs describe `.dockerignore` as the mechanism that removes files from the build context before it is sent to the builder: <https://docs.docker.com/build/concepts/context/>
- A Fly.io community thread shows confusion around `.dockerignore`, `node_modules`, and a deploy that appeared hundreds of MB larger than expected: <https://community.fly.io/t/dockerignore-being-ignored/4342>
- A Flyctl issue reports context size being sent to a builder as GBs instead of MBs: <https://github.com/superfly/flyctl/issues/456>
- A Moby issue asks for build context speedups around `node_modules`: <https://github.com/moby/moby/issues/7213>
- Stack Overflow answers around very large Docker build context remain highly referenced: <https://stackoverflow.com/questions/26600769/build-context-for-docker-image-very-large>

## Target Users

| User | Pain | Entry Point | Why They Might Star |
|---|---|---|---|
| Solo app developer | Slow deploys and confusing Docker context uploads | CLI before deploy | Immediate explanation plus copyable `.dockerignore` suggestions |
| AI-native builder | Many generated projects and inconsistent scaffolds | Local preflight step | Catches common generated-project clutter before shipping |
| Small team | PRs accidentally include build outputs or local env files in build context | CI step | Cheap guardrail without adopting a large platform |
| OSS maintainer | Contributors submit Docker fixes without knowing context rules | README/CI badge later | Small, understandable contributor check |
| DevOps/security consultant | Needs a quick triage artifact during Docker cleanup | JSON/text report | Produces a concise evidence report before deeper tooling |

## Product Shape

MVP:

- single-file Python CLI
- zero runtime dependencies
- text and JSON output
- fail threshold for CI
- local synthetic fixtures and unit tests
- release gate that checks docs, tests, package build, install, and public-file hygiene

Non-goals:

- full Docker engine implementation
- deep secret scanning
- image vulnerability scanning
- Dockerfile best-practice linting beyond broad context copy warnings

## Competitive Map

| Tool | Covers | Gap Left For This Project |
|---|---|---|
| Hadolint | Dockerfile instruction linting | Does not focus on what local files are about to enter the build context |
| Trivy | Vulnerabilities, secrets, IaC, images, filesystem | Broader security scanner; heavier mental model for a pre-build context check |
| Dockle | Built image security and best practices | Runs after an image exists |
| dive | Built image layers and image size | Useful after build, not before context upload |
| Docker/BuildKit output | Shows context transfer during build | Feedback arrives after the developer already started the build |

The wedge is narrow by design: "tell me what Docker is about to upload from this folder before I build."

## Star Path Hypothesis

To have a shot at 150 GitHub stars, the repo needs to be easy to understand in under 30 seconds:

1. Name and README promise must be concrete: "audit Docker build context before upload."
2. Demo must show an instantly recognizable failure: `node_modules`, `build`, and `local.env`.
3. Install must be one Python command from source, then later `pipx` or PyPI.
4. Launch copy should compare against known tools without attacking them.
5. First distribution should target Docker/Fly.io/Render/Railway/devops channels where slow deploy pain is already discussed.

## Open Questions

- Is exact `.dockerignore` parity important enough to justify using Docker's patternmatcher semantics later?
- Should the next release include SARIF output for GitHub code scanning?
- Should there be a dedicated GitHub Action wrapper, or is a Python CLI step enough for the first release?
- Would examples for Node, Python, Rust, and monorepos improve credibility enough to justify extra fixtures?
