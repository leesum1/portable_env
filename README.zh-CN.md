# Red Environment - 现代化 Linux 终端离线环境

一个**配置即代码**的离线部署现代化 Linux 终端环境解决方案。支持多架构构建、验证与发布自动化。

## 🌟 项目特点

- 🔧 **配置即代码** - 工具与配置统一版本化管理
- 📦 **多架构离线包** - 一键生成 x86_64 与 arm64 离线安装包
- 🚀 **自动化构建与验证** - GitHub Actions 负责构建与发布
- 🐳 **容器化构建** - 使用 Docker 保证构建一致性
- 🐚 **现代化 Shell** - Zsh + Zimfw + 常用插件
- 🔐 **完整验证** - 包完整性与工具可用性自动检查
- 💻 **离线可用** - 安装与使用均无需网络

## 📋 项目结构

```
red_env/
├── .github/
│   └── workflows/
│       └── build-release.yml    # GitHub Actions 构建发布流程
├── configs/                      # 工具配置文件
│   ├── zsh/                     # Zsh 配置
│   │   ├── zshrc               # .zshrc 配置
│   │   └── zimrc               # .zimrc 配置
│   ├── vim/                     # Vim 配置
│   ├── tmux/                    # Tmux 配置
│   └── git/                     # Git 配置
├── docker/                       # Docker 构建与验证文件
│   ├── Dockerfile.base         # 基础层 Dockerfile
│   ├── Dockerfile.build        # 构建环境 Dockerfile
│   └── Dockerfile.verify       # 验证环境 Dockerfile
├── scripts/                      # 构建与安装脚本
│   ├── build.sh               # 本地构建脚本
│   ├── install.sh             # 离线安装脚本
│   ├── csource                # CSH 脚本兼容层 (zsh function)
│   └── verify_tools.sh        # 工具验证脚本
├── Makefile                      # 本地构建任务
├── output/                       # 构建输出 (构建后生成)
├── dist/                         # 最终产物 (构建后生成)
└── README.md
```

## 🚀 快速开始

### 本地构建

#### 构建所有架构
```bash
make build-all      # 构建 x86_64 和 arm64
make verify-all     # 验证所有架构
make all            # 构建并验证所有架构（默认）
```

#### 构建特定架构
```bash
make build-x86_64   # 构建 x86_64 包
make build-arm64    # 构建 arm64 包
make verify-x86_64  # 验证 x86_64 包
make verify-arm64   # 验证 arm64 包
```

#### 清理
```bash
make clean          # 清理构建产物
make clean-all      # 深度清理（包括 Docker 缓存）
```

### GitHub Actions 自动构建

#### 触发方式

| 事件 | 触发条件 | 构建产物 |
|------|----------|----------|
| Push | main/master | 临时 artifacts (7天) |
| Tag | tag v* | GitHub Release |
| PR | Pull Request | 临时 artifacts (7天) |
| Manual | workflow_dispatch | 临时 artifacts (7天) |

#### 发布新版本
```bash
git tag v1.0.0
git push origin v1.0.0
```

完成后，GitHub Actions 会自动：
1. 在 ubuntu-latest 构建 x86_64 包
2. 在 ubuntu-latest-arm64 构建 arm64 包
3. 验证两个架构的包完整性
4. 将产物上传到 GitHub Release

### 离线安装

下载发布版本的离线包后：

```bash
# 解压
 tar -xzf red_env_offline_<arch>.tar.gz -C ~/red_env_offline

# 安装
cd ~/red_env_offline
./install.sh

# 验证
source ~/.zshrc
zsh --version
```

## 📦 包含的软件（核心）

| 软件 | 版本 | 说明 |
|------|------|------|
| **Zsh** | Latest | 现代化 Shell |
| **Zimfw** | Latest | Zsh 框架 |
| **fzf** | Latest | 模糊搜索 |
| **bat** | Latest | 增强版 cat |
| **eza** | Latest | 增强版 ls |
| **ripgrep** | Latest | 高速搜索 |
| **fd** | Latest | 增强版 find |
| **delta** | Latest | Git diff 视图 |
| **tmux** | Latest | 终端复用器 |
| **Vim** | Latest | 静态编译编辑器 |

## ⚙️ 系统要求

### 构建环境（本地或 CI/CD）
- **Docker** 20.10+ 或 Docker Desktop
- **网络连接**（用于下载软件源）
- **磁盘空间** 5GB+

### 目标环境（安装后）
- **操作系统** Linux (x86_64 或 arm64)
- **网络** ✗ 无需网络连接
- **权限** 无需 root 权限（安装到用户目录）
- **磁盘空间** 500MB+

## 🛠️ 工具说明

### csource - CSH 脚本兼容层

在 Zsh 中直接 source CSH 脚本：

```bash
# 在 .zshrc 中添加
source /path/to/red_env/scripts/csource

# 使用
csource /path/to/script.csh
csource /path/to/script.csh arg1 arg2
```

**工作原理：**
- 比较脚本执行前后的环境变量
- 只导入新增或修改的变量到当前 Zsh 环境
- 无需额外前缀

## 📊 构建流程

```
git push/tag
    ↓
[Build x86_64]        [Build arm64]
(ubuntu-latest)   (ubuntu-latest-arm64)
    ↓                   ↓
[Verify x86_64]   [Verify arm64]
    ↓                   ↓
[Release] (仅 tag 时)
    ↓
GitHub Release
```

## 🔍 自定义配置

编辑 configs 目录下的配置文件来自定义环境：

```
configs/
├── zsh/zimrc          # 修改 Zsh 插件
├── zsh/zshrc          # 修改 Shell 配置
├── vim/vimrc          # 修改 Vim 配置
├── tmux/tmux.conf     # 修改 Tmux 配置
└── git/gitconfig      # 修改 Git 配置
```

修改后，重新构建即可：
```bash
make clean
make build-all
```

## 📝 License

MIT License
