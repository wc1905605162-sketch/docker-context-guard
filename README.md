# Docker Context Guard

[![CI](https://github.com/wc1905605162-sketch/docker-context-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/wc1905605162-sketch/docker-context-guard/actions/workflows/ci.yml)

Audit a Docker build context before `docker build` uploads it.

在 `docker build` 上传构建上下文之前，先检查本地目录里会被送进 builder 的文件。

Docker Context Guard is a zero-dependency Python CLI that finds the boring mistakes that make Docker builds slow, expensive, leaky, or confusing:

- missing `.dockerignore`
- included `node_modules`, `.git`, virtualenvs, build outputs, caches, and coverage folders
- secret-looking files such as `.env*`, `*.env`, `*.pem`, `*.key`, and SSH keys
- contexts larger than your threshold
- broad `COPY . .` / `ADD . ...` instructions when risky paths are still included
- Dockerfile-specific ignore files such as `docker/prod.Dockerfile.dockerignore`

Docker Context Guard 是一个零运行依赖的 Python CLI，用来发现那些很普通但很容易拖慢、搞乱或暴露 Docker 构建的错误：

- 缺失 `.dockerignore`
- `node_modules`、`.git`、虚拟环境、构建产物、缓存、coverage 目录进入 build context
- `.env*`、`*.env`、`*.pem`、`*.key`、SSH key 等看起来像 secret 的文件进入 build context
- build context 超过你设置的大小阈值
- Dockerfile 在风险文件仍被包含时使用 broad `COPY . .` / `ADD . ...`
- 支持 `docker/prod.Dockerfile.dockerignore` 这类 Dockerfile-specific ignore file

It is not a vulnerability scanner and it does not claim byte-for-byte Docker parity. It is a fast preflight guard for the common build-context problems that humans notice only after a slow deploy, a failed CI run, or an accidental copy.

它不是漏洞扫描器，也不声称逐字节复刻 Docker 行为。它是一个快速 preflight guard：在慢 deploy、失败 CI 或误复制发生前，先把常见 build-context 问题指出来。

## Quick Start / 快速开始

Try the included risky fixture:

试一下仓库里的风险 fixture：

```bash
git clone https://github.com/wc1905605162-sketch/docker-context-guard.git
cd docker-context-guard
python docker_context_guard.py examples/risky-node --fail-on none
```

Run from source:

从源码运行：

```bash
python docker_context_guard.py .
```

Install from a checkout:

从本地 checkout 安装：

```bash
python -m pip install .
docker-context-guard .
```

Use JSON in CI:

在 CI 中使用 JSON 输出：

```bash
docker-context-guard . --format json --fail-on high
```

Use as a GitHub Action:

作为 GitHub Action 使用：

```yaml
name: docker-context-guard

on: [pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: wc1905605162-sketch/docker-context-guard@v0.1.0
        with:
          fail-on: high
```

Use as a pre-commit hook:

作为 pre-commit hook 使用：

```yaml
repos:
  - repo: https://github.com/wc1905605162-sketch/docker-context-guard
    rev: v0.1.0
    hooks:
      - id: docker-context-guard
```

Scan a custom Dockerfile and size budget:

扫描指定 Dockerfile，并设置上下文大小预算：

```bash
docker-context-guard . --dockerfile docker/prod.Dockerfile --max-size-mb 25
```

## Example / 示例

The fixture in `examples/risky-node` intentionally contains `node_modules`, `build`, and `local.env`.

`examples/risky-node` 这个 fixture 故意包含 `node_modules`、`build` 和 `local.env`。

```bash
python docker_context_guard.py examples/risky-node --fail-on none
```

Expected findings:

预期会看到：

```text
- [HIGH] DCG002 `node_modules`: Local dependencies are included in the build context.
- [HIGH] DCG003 `local.env`: Sensitive-looking file is included in the Docker build context.
- [MEDIUM] DCG001 `.dockerignore`: No .dockerignore file was found, but the context contains risky or bulky paths.
- [MEDIUM] DCG002 `build`: Build output is included in the build context.
- [MEDIUM] DCG005 `Dockerfile:3`: Dockerfile copies the whole context while risky files or directories are included.
```

Suggested `.dockerignore` additions:

建议加入 `.dockerignore`：

```dockerignore
*.env
build/
node_modules/
```

## Why This Exists / 为什么需要它

Docker sends a build context to the builder. Docker's own documentation says `.dockerignore` removes matching files and directories from that context before it is sent, and Dockerfile-specific ignore files can override the root `.dockerignore`.

Docker 会把 build context 发送给 builder。Docker 官方文档说明，`.dockerignore` 会在 context 被发送前移除匹配的文件和目录；Dockerfile-specific ignore file 还可以覆盖根目录 `.dockerignore`。

That small rule creates a recurring failure mode: local folders and secrets look harmless in a repository, then get swept into a remote build because the context is too broad or the ignore file is missing. Public reports include huge build contexts, `node_modules` confusion, and remote-builder deploys where the uploaded context is much larger than the app.

这个小规则带来一种反复出现的失败模式：本地文件夹和 secret 在仓库里看起来没什么，结果因为 context 太宽或 ignore 文件缺失，被一起扫进远程构建。公开讨论中反复出现 huge build context、`node_modules` 困惑，以及远程 builder 上传上下文明显大于应用本身的问题。

Docker Context Guard focuses on that pre-build moment. It complements tools such as Hadolint, Trivy, Dockle, and dive rather than replacing them:

Docker Context Guard 只关注 build 前这一刻。它不是替代 Hadolint、Trivy、Dockle 或 dive，而是补上它们之前的一层检查：

- Hadolint checks Dockerfile instructions.
- Trivy scans vulnerabilities, secrets, IaC, and artifacts.
- Dockle checks built container images against security best practices.
- dive explores built image layers and image size.
- Docker Context Guard checks the local files about to be sent as the build context.

- Hadolint 检查 Dockerfile 指令。
- Trivy 扫描漏洞、secret、IaC 和 artifact。
- Dockle 检查已经构建出的镜像是否符合安全最佳实践。
- dive 查看已经构建出的镜像层和镜像大小。
- Docker Context Guard 检查即将作为 build context 发送的本地文件。

## Rules / 规则

| Rule | Severity | Meaning |
|---|---:|---|
| `DCG001` | medium | Missing `.dockerignore` while risky or bulky paths are present |
| `DCG002` | low-high | Risky local directory is included |
| `DCG003` | high | Secret-looking file is included |
| `DCG004` | medium | Included context exceeds `--max-size-mb` |
| `DCG005` | medium | Broad `COPY`/`ADD` while risky paths are included |

| 规则 | 严重度 | 含义 |
|---|---:|---|
| `DCG001` | medium | 有风险或大体积路径时缺失 `.dockerignore` |
| `DCG002` | low-high | 风险本地目录被包含 |
| `DCG003` | high | 看起来像 secret 的文件被包含 |
| `DCG004` | medium | 被包含的 context 超过 `--max-size-mb` |
| `DCG005` | medium | 风险路径仍存在时使用 broad `COPY`/`ADD` |

## Options / 参数

```text
usage: docker-context-guard [context] [--dockerfile PATH]
                            [--max-size-mb MB] [--top N]
                            [--format text|json]
                            [--fail-on none|low|medium|high]
```

Defaults:

默认值：

- `context`: current directory
- `--max-size-mb`: `100`
- `--top`: `8`
- `--format`: `text`
- `--fail-on`: `high`

- `context`：当前目录
- `--max-size-mb`：`100`
- `--top`：`8`
- `--format`：`text`
- `--fail-on`：`high`

Exit codes:

退出码：

- `0`: no findings at or above `--fail-on`
- `1`: findings met the fail threshold
- `2`: invalid input or usage

- `0`：没有达到 `--fail-on` 阈值的 finding
- `1`：finding 达到失败阈值
- `2`：输入或参数错误

## GitHub Actions

Recommended:

推荐：

```yaml
- uses: wc1905605162-sketch/docker-context-guard@v0.1.0
  with:
    context: .
    fail-on: high
```

If you prefer a plain Python CLI step:

如果你更想用普通 Python CLI step：

```yaml
name: docker-context-guard

on: [pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: python -m pip install .
      - run: docker-context-guard . --fail-on high
```

## Limitations / 限制

- This is a conservative triage tool, not a security audit.
- `.dockerignore` matching is intentionally small and local. If exact Docker engine parity matters, verify with Docker or BuildKit.
- Secret detection is filename-based. It can miss secrets and it can flag harmless fixture files.
- Dockerfile parsing is line-oriented and only catches common broad `COPY`/`ADD` forms.
- It does not send files anywhere.

- 这是保守的 triage 工具，不是安全审计。
- `.dockerignore` 匹配实现刻意保持小而本地化；如果需要精确 Docker 行为，请用 Docker 或 BuildKit 复核。
- secret 检测基于文件名，可能漏报，也可能标记无害 fixture。
- Dockerfile 解析是按行处理，只覆盖常见 broad `COPY`/`ADD` 形式。
- 工具不会把文件发送到任何地方。

## Development / 开发

```bash
python -m unittest discover -s tests
python -m py_compile docker_context_guard.py scripts/prepublish_gate.py
python -m pip install build twine
python scripts/prepublish_gate.py
```

## License / 许可证

MIT
