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

## Profiles

`core` is the bundle most users want: the shells (zsh and fish), the everyday CLI tools, and a complete zsh experience — `oh-my-zsh` plus the `z`, `zsh-autosuggestions` and `zsh-syntax-highlighting` plugins that `assets/configs/zsh/zshrc` enables. When a hand-built bundle lacks oh-my-zsh, the startup file prints a warning instead of silently dropping the theme and plugins.

`extended` adds the optional extras (eza, lazygit, yazi, glow, jq, uv, …) on top of `core`.

### Exposing a plugin under a different name

Some upstream repositories do not name their entry point after the plugin. `zsh-z` ships `zsh-z.plugin.zsh`, but oh-my-zsh only sources `<plugin>/<plugin>.plugin.zsh`, so the manifest declares a symlink:

```toml
[strategy.extract]
target_dir = "cache/oh-my-zsh/custom/plugins/z"
strip_components = 1
links = { "z.plugin.zsh" = "zsh-z.plugin.zsh" }
```

`links` is supported by the `archive_tree` strategy and the build fails when a link target does not exist in the extracted tree.

## GitHub Access

`red_env build` fetches release assets from GitHub. Anonymous requests are limited to 60 per hour, which is not enough for a full build, so the token is resolved in this order:

1. `GH_TOKEN`
2. `GITHUB_TOKEN`
3. `gh auth token` — the credential the GitHub CLI already stored

The third step means an authenticated `gh` is enough; no environment variable is required:

```bash
gh auth login          # once
python -m red_env build --profile core --arch x86_64
```

To inject a token explicitly (CI, or a machine without `gh`), keep using the environment:

```bash
export GH_TOKEN=ghp_your_token
python -m red_env build --profile core --arch x86_64
```

`--in-docker` forwards the resolved token into the builder container by name, so the secret never appears on the `docker run` command line.

## Reproducible source builds

Eighteen packages compile from a source archive (`zig_build` for Rust, `go_build` for Go). To keep those builds reproducible the toolchain versions are pinned in the manifest rather than resolved from the host:

```toml
# manifests/manifest.toml
[toolchains]
rust = "1.99.1"
go = "1.27.3"
```

Every `zig_build` package gets `rust_version` and every `go_build` package gets `go_version` injected from that table; a package can override the default by setting `rust_version` or `go_version` in its own `[strategy.extract]`. `manifest lint` fails when a source-build package has no pin, when it is backed by a binary-only source type, or when `locked` is not a boolean.

Builds are locked and cached:

* `zig_build` runs `cargo zigbuild --target <triple> --release --locked` and `go_build` runs `go build -mod=readonly`. Both require the upstream lock file (`Cargo.lock` / `go.sum`); set `locked = false` in `[strategy.extract]` to opt a package out.
* `GOTOOLCHAIN` is pinned to the manifest version so the Go toolchain downloads the exact release even when the host has another one.
* Downloaded registries live under `build/cache` (outside the work tree that is wiped on every build), so repeated builds reuse `CARGO_HOME`, `CARGO_ZIGBUILD_CACHE_DIR`, `GOCACHE` and `GOMODCACHE`. Override the location with `--cache-root` to share one cache across checkouts.

### Hermetic builds in Docker

`docker/builder-full.Dockerfile` pins every toolchain and its base image by digest. Build the image once, then let the CLI drive it:

```bash
python -m red_env build --profile core --arch x86_64 --in-docker
```

`--in-docker` bind-mounts the repository at `/workspace`, runs the same `red_env build` inside the image (with `RED_ENV_IN_DOCKER=1` preventing recursion), and hands the produced files back to your user id. Related flags: `--builder-image` to use a prebuilt image, `--builder-dockerfile` to point at a different recipe, and `--rebuild-builder` to force a rebuild.

The image installs Rust 1.99.1, cargo-zigbuild 0.24.0, Zig 0.16.0 and Go 1.27.3, verifying each download against a published SHA-256. Rebuild it with:

```bash
docker build --file docker/builder-full.Dockerfile --tag red-env-builder:full docker/
```

### Docker networking

`--in-docker` and `verify` run containers with `--network host` by default. Bridge networking requires the daemon to create `veth` pairs, which fails on restricted sandboxes and on hosts whose running kernel has no module tree:

```
failed to create endpoint ... on network bridge:
failed to add the host (veth…) <=> sandbox (veth…) pair interfaces: operation not supported
```

Host networking needs no `veth`, so builds and verification keep working. Pass `--docker-network bridge` when you want container isolation and your daemon supports it.

If you want bridge networking back, check whether the module for the *running* kernel actually exists:

```bash
uname -r
ls /lib/modules/$(uname -r)/kernel/drivers/net/veth.ko*   # missing?
modinfo veth                                              # "Module veth not found"?
```

On Arch, a missing directory usually means the kernel was upgraded and the old package removed without a reboot — the running kernel is no longer installed. Reboot into an installed kernel (`pacman -Q | grep '^linux'`) to restore `veth`.
