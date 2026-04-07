# Red Environment

基于 TOML manifest 的 Linux 终端工具离线打包器。

## 快速开始

```bash
python -m pip install -e .[dev]
python -m red_env manifest lint
python -m red_env profile show core
python -m red_env build --profile core --arch x86_64
python -m red_env verify --artifact dist/red_env_core_x86_64.tar.gz --arch x86_64
```

## GitHub 访问

`red_env build` 会从 GitHub 拉取 release 资产。为了避免匿名 API 限流，本地构建前请先设置 `GH_TOKEN`；同时也兼容 `GITHUB_TOKEN`。

```bash
export GH_TOKEN=ghp_your_token
python -m red_env build --profile core --arch x86_64
```
