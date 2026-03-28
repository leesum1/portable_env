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
