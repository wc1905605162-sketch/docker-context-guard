# Launch Drafts

These are prepared copy blocks. Do not post them from an automated account. Use them after a human owner reviews the wording and chooses a channel.

## GitHub Short Description

Audit Docker build contexts before `docker build` uploads local junk, secrets, or huge folders.

## Show HN Draft

Title:

```text
Show HN: Docker Context Guard - audit build contexts before Docker uploads them
```

Body:

```text
I made a small zero-dependency Python CLI for a boring Docker failure mode: the build context contains files you did not mean to send.

It checks for missing .dockerignore files, included node_modules/.git/build/cache directories, secret-looking filenames, large contexts, and broad COPY . . instructions while risky paths are still included.

It is not a vulnerability scanner and it does not replace Hadolint, Trivy, Dockle, or dive. It sits one step earlier: before docker build uploads the local context.

Repo:
https://github.com/wc1905605162-sketch/docker-context-guard

The first release also includes a GitHub Action and pre-commit hook. Feedback I am most interested in: false positives, Dockerfile-specific ignore edge cases, and whether SARIF output would make this more useful in CI.
```

## Reddit r/docker Draft

Title:

```text
Tiny preflight tool for missing .dockerignore, huge contexts, and accidental local files
```

Body:

```text
I published a small Python CLI called Docker Context Guard:
https://github.com/wc1905605162-sketch/docker-context-guard

The narrow goal is to catch build-context mistakes before running docker build:

- missing .dockerignore
- node_modules, .git, build outputs, caches, virtualenvs
- .env / .pem / .key-looking filenames
- broad COPY . . while risky files are still included
- context size over a configured threshold

It does not try to be a full Dockerfile linter or image scanner. It is more of a quick preflight report plus suggested .dockerignore additions.

I would appreciate feedback on which false positives would make this annoying in real projects.
```

## dev.to Draft

Title:

```text
Before docker build: catch accidental build-context bloat
```

Outline:

```text
1. The hidden cost of Docker build context upload
2. Reproduce the failure with node_modules, build/, and local.env
3. Run Docker Context Guard
4. Apply the suggested .dockerignore entries
5. Add it to GitHub Actions or pre-commit
6. Where this tool stops: not vulnerability scanning, not exact Docker parity
```

## First Outreach Targets

- GitHub repo release page: safe, already owned surface.
- Hacker News Show HN: broad but high variance.
- Reddit r/docker: best fit for practical false-positive feedback.
- dev.to tutorial: slower but useful for search and onboarding.
- Fly.io, Render, Railway communities: only after a real user story or example is prepared.
