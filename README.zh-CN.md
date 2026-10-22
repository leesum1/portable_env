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

`red_env build` 会从 GitHub 拉取 release 资产。匿名请求每小时只有 60 次，跑不完一次完整构建，因此 token 按以下顺序解析：

1. `GH_TOKEN`
2. `GITHUB_TOKEN`
3. `gh auth token` —— GitHub CLI 已经保存的凭据

第三步意味着只要 `gh` 登录过就够了，不需要设置任何环境变量：

```bash
gh auth login          # 只需一次
python -m red_env build --profile core --arch x86_64
```

如果要在 CI 或没有 `gh` 的机器上显式注入 token，仍然用环境变量：

```bash
export GH_TOKEN=ghp_your_token
python -m red_env build --profile core --arch x86_64
```

`--in-docker` 会按变量名把解析到的 token 透传给构建容器，因此密钥不会出现在 `docker run` 的命令行里。

## 可复现的源码构建

有 18 个包从源码压缩包编译（Rust 用 `zig_build`，Go 用 `go_build`）。为了让这些构建可复现，工具链版本固定在 manifest 里，而不是从宿主机上碰运气：

```toml
# manifests/manifest.toml
[toolchains]
rust = "1.99.1"
go = "1.27.3"
```

加载 manifest 时，所有 `zig_build` 包会被注入 `rust_version`，所有 `go_build` 包会被注入 `go_version`；单个包可以在自己的 `[strategy.extract]` 里写 `rust_version` / `go_version` 覆盖默认值。`manifest lint` 会在以下情况报错：源码构建包缺少版本 pin、使用了不提供源码包的 source 类型、`locked` 不是布尔值。

构建过程加锁并复用缓存：

* `zig_build` 执行 `cargo zigbuild --target <triple> --release --locked`，`go_build` 执行 `go build -mod=readonly`。两者都要求上游提供锁文件（`Cargo.lock` / `go.sum`）；确实没有锁文件的包可在 `[strategy.extract]` 里写 `locked = false` 显式退出。
* `GOTOOLCHAIN` 固定为 manifest 中的版本，即使宿主机装的是别的 Go 版本，也会下载并使用指定的那个。
* 下载的依赖仓库统一放在 `build/cache`（在每次构建都会被清空的 work 目录之外），因此重复构建会复用 `CARGO_HOME`、`CARGO_ZIGBUILD_CACHE_DIR`、`GOCACHE` 和 `GOMODCACHE`。用 `--cache-root` 可以把缓存指到别处，在多个 checkout 之间共享。

### 在 Docker 中做 hermetic 构建

`docker/builder-full.Dockerfile` 固定了所有工具链版本，基础镜像按 digest 固定。构建一次镜像，之后交给 CLI 驱动：

```bash
python -m red_env build --profile core --arch x86_64 --in-docker
```

`--in-docker` 会把仓库挂载到 `/workspace`，在镜像里执行同样的 `red_env build`（通过 `RED_ENV_IN_DOCKER=1` 防止递归），结束后把产物交还给当前用户。相关参数：`--builder-image` 使用已有的镜像、`--builder-dockerfile` 指定别的构建文件、`--rebuild-builder` 强制重建镜像。

镜像内安装 Rust 1.99.1、cargo-zigbuild 0.24.0、Zig 0.16.0 和 Go 1.27.3，每个下载都用官方 SHA-256 校验。重建镜像：

```bash
docker build --file docker/builder-full.Dockerfile --tag red-env-builder:full docker/
```

### Docker 网络

`--in-docker` 和 `verify` 默认以 `--network host` 运行容器。bridge 网络需要 daemon 创建 `veth` 网卡对，在受限沙箱里、以及运行内核没有对应模块目录的机器上会失败：

```
failed to create endpoint ... on network bridge:
failed to add the host (veth…) <=> sandbox (veth…) pair interfaces: operation not supported
```

host 网络不需要 `veth`，因此构建和验证可以照常工作。如果你需要容器网络隔离且 daemon 支持，可以传 `--docker-network bridge`。

想恢复 bridge 网络，先确认**当前运行内核**的模块是否存在：

```bash
uname -r
ls /lib/modules/$(uname -r)/kernel/drivers/net/veth.ko*   # 不存在？
modinfo veth                                              # 报 "Module veth not found"？
```

在 Arch 上，目录缺失通常意味着内核升级后旧内核包已被删除但机器没重启 —— 运行中的内核已经不是已安装的内核了。重启进入已安装的内核（`pacman -Q | grep '^linux'`）即可恢复 `veth`。
