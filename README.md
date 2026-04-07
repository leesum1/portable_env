# Red Environment

Manifest-driven offline package builder for Linux terminal tooling.

## Quick Start

```bash
python -m pip install -e .[dev]
python -m red_env manifest lint
python -m red_env profile show core
python -m red_env build --profile core --arch x86_64
python -m red_env verify --artifact dist/red_env_core_x86_64.tar.gz --arch x86_64
```

## GitHub Access

`red_env build` fetches release assets from GitHub. Set `GH_TOKEN` locally before running build commands to avoid anonymous API rate limits. `GITHUB_TOKEN` is also supported.

```bash
export GH_TOKEN=ghp_your_token
python -m red_env build --profile core --arch x86_64
```
