# Red Environment - Modern Offline Linux Terminal Environment

A **configuration-as-code** solution for building and shipping a modern Linux terminal environment offline. Supports multi-arch build, verification, and release automation.

## 🌟 Highlights

- 🔧 **Configuration as code** - tools and configs are versioned together
- 📦 **Multi-arch offline packages** - one command for x86_64 and arm64
- 🚀 **Automated build & verify** - GitHub Actions handles build and release
- 🐳 **Containerized build** - Docker ensures reproducible environments
- 🐚 **Modern shell stack** - Zsh + Zimfw + curated plugins
- 🔐 **Verification pipeline** - integrity and tool checks are automated
- 💻 **Offline-ready** - install and use without network access

## 📋 Project Structure

```
red_env/
├── .github/
│   └── workflows/
│       └── build-release.yml    # GitHub Actions 构建发布流程
├── configs/                      # Tool configurations
│   ├── zsh/                     # Zsh 配置
│   │   ├── zshrc               # .zshrc 配置
│   │   └── zimrc               # .zimrc 配置
│   ├── vim/                     # Vim 配置
│   ├── tmux/                    # Tmux 配置
│   └── git/                     # Git 配置
├── docker/                       # Docker build & verify files
│   ├── Dockerfile.base         # 基础层 Dockerfile
│   ├── Dockerfile.build        # 构建环境 Dockerfile
│   └── Dockerfile.verify       # 验证环境 Dockerfile
├── scripts/                      # Build & install scripts
│   ├── build.sh               # 本地构建脚本
│   ├── install.sh             # 离线安装脚本
│   ├── csource                # CSH 脚本兼容层 (zsh function)
│   └── verify_tools.sh        # 工具验证脚本
├── Makefile                      # Local build targets
├── output/                       # Build output (generated)
├── dist/                         # Release artifacts (generated)
└── README.md
```

## 🚀 Quick Start

### Local Build

#### Build All Architectures
```bash
make build-all      # 构建 x86_64 和 ARM64
make verify-all     # 验证所有架构
make all            # 构建并验证所有架构（默认）
```

#### Build Specific Architecture
```bash
make build-x86_64   # 构建 x86_64 包
make build-arm64    # 构建 ARM64 包
make verify-x86_64  # 验证 x86_64 包
make verify-arm64   # 验证 ARM64 包
```

#### Clean
```bash
make clean          # 清理构建产物
make clean-all      # 深度清理（包括 Docker 缓存）
```

### GitHub Actions

#### Triggers

| Event | Condition | Artifacts |
|------|-----------|-----------|
| Push | main/master | Temporary artifacts (7 days) |
| Tag | tag v* | GitHub Release |
| PR | Pull Request | Temporary artifacts (7 days) |
| Manual | workflow_dispatch | Temporary artifacts (7 days) |

#### Release a New Version
```bash
git tag v1.0.0
git push origin v1.0.0
```

After tagging, GitHub Actions will:
1. Build x86_64 on ubuntu-latest
2. Build arm64 on ubuntu-latest-arm64
3. Verify both packages
4. Publish assets to GitHub Release

### Offline Install

下载发布版本的离线包后：

```bash
# Unpack
tar -xzf red_env_offline_<arch>.tar.gz -C ~/red_env_offline

# Install
cd ~/red_env_offline
./install.sh

# Verify
source ~/.zshrc
zsh --version
```

## 📦 Included Tools (Core)

| Tool | Version | Notes |
|------|---------|-------|
| **Zsh** | Latest | Modern shell |
| **Zimfw** | Latest | Zsh framework |
| **fzf** | Latest | Fuzzy finder |
| **bat** | Latest | Better cat |
| **eza** | Latest | Better ls |
| **ripgrep** | Latest | Fast search |
| **fd** | Latest | Better find |
| **delta** | Latest | Git diff viewer |
| **tmux** | Latest | Terminal multiplexer |
| **Vim** | Latest | Statically built editor |

## ⚙️ Requirements

### Build Environment (Local or CI)
- **Docker** 20.10+ or Docker Desktop
- **Network access** (for downloads during build)
- **Disk** 5GB+ (cache)

### Target Environment (Runtime)
- **OS** Linux (x86_64 or arm64)
- **Network** not required
- **Permissions** no root required (user-local install)
- **Disk** 500MB+

## 🛠️ Tools

### csource - CSH Compatibility

Source CSH scripts in Zsh:

```bash
# Add to .zshrc
source /path/to/red_env/scripts/csource

# Use
csource /path/to/script.csh
csource /path/to/script.csh arg1 arg2
```

**How it works:**
- Diffs env vars before and after running the script
- Imports only new or changed variables into Zsh
- No extra prefix needed

## 📊 Build Flow

```
git push/tag
    ↓
[Build x86_64]        [Build ARM64]
(ubuntu-latest)   (ubuntu-latest-arm64)
    ↓                   ↓
[Verify x86_64]   [Verify ARM64]
    ↓                   ↓
[Release] (tags only)
    ↓
GitHub Release
```

## 🔍 Customization

Edit configs under configs to customize the environment:

```bash
configs/
├── zsh/zimrc          # 修改 Zsh 插件
├── zsh/zshrc          # 修改 Shell 配置
├── vim/vimrc          # 修改 Vim 配置
├── tmux/tmux.conf     # 修改 Tmux 配置
└── git/gitconfig      # 修改 Git 配置
```

Rebuild after changes:
```bash
make clean
make build-all
```

## 📝 License

MIT License
