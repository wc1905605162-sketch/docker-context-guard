# Launch Plan

Goal: publish a small open-source utility with a credible path to 150 GitHub stars.

## Positioning

One-liner:

> Docker Context Guard audits the files Docker is about to send to the builder, before a slow build or accidental secret copy surprises you.

Short post:

> I built a tiny zero-dependency Python CLI for a Docker problem I keep seeing in public threads: huge build contexts, missing `.dockerignore`, `node_modules`, local env files, build output, and broad `COPY . .`. It is not a replacement for Hadolint, Trivy, Dockle, or dive. It checks the pre-build context, then prints a small report and suggested `.dockerignore` additions.

## Low-Risk Channels

Do not post until the human owner approves.

| Channel | Draft Angle | Success Signal |
|---|---|---|
| GitHub repository | Clear README, topics, CI badge after first push | Organic stars, issues, forks |
| Hacker News "Show HN" | "Show HN: Audit Docker build contexts before upload" | Comments with real edge cases |
| Reddit r/docker | "I made a tiny preflight check for missing .dockerignore and oversized contexts" | Practical feedback, not only upvotes |
| dev.to | Tutorial around fixing a slow Node Docker build | Bookmarks and comments |
| Fly.io/Render/Railway communities | Remote builders make context upload pain visible | Maintainer/user feedback |
| GitHub Action Marketplace | Root `action.yml` lets users run `uses: wc1905605162-sketch/docker-context-guard@v0.1.0` | Workflow usage, issues asking for CI features |
| pre-commit | `.pre-commit-hooks.yaml` supports local guardrails before PRs | Stars from teams that already use pre-commit |

## GitHub Topics

`docker`, `dockerignore`, `build-context`, `devops`, `ci`, `python`, `containers`, `static-analysis`

## Release Checklist

- [x] Repository is public.
- [x] README renders cleanly on GitHub.
- [x] `python scripts/prepublish_gate.py` passes from a fresh checkout.
- [x] GitHub Action wrapper is present.
- [x] pre-commit hook entry is present.
- [ ] First issue templates are optional, not required.
- [ ] No internal paths, lab notes, or unpublished user identity in public files.
- [ ] Create one demo GIF or screenshot.
- [ ] Draft launch posts remain unsent until human approval.

## Star Strategy

The first 150 stars likely come from usefulness plus clarity, not feature volume.

High-leverage improvements after launch:

1. Add SARIF output for GitHub code scanning.
2. Add Marketplace-oriented examples for the GitHub Action wrapper.
3. Add more fixtures: Node, Python, Rust, monorepo, nested Dockerfile.
4. Add a `--print-dockerignore-patch` mode.
5. Document false positives and parity gaps in public issues.

## Blocked Until Authorization

- Posting launch threads.
- Replying in public issue/discussion threads.
- Submitting to newsletters or directories.
