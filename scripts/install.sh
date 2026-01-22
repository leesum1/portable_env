#!/bin/bash
# =============================================================================
#                   Red Environment - 离线安装脚本
# =============================================================================
# 在目标机器上运行此脚本以安装终端环境
# 无需网络连接，无需 root 权限
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 安装目录（统一放置，避免与系统目录冲突）
RED_ENV_HOME="${HOME}/.red_env"
# INSTALL_DIR 可通过命令行选项覆盖（见 parse_args）
INSTALL_DIR="$RED_ENV_HOME"

# 通过函数在解析参数后更新以下路径，以便支持自定义安装目录
BIN_DIR="${INSTALL_DIR}/bin"
SHARE_DIR="${INSTALL_DIR}/share"
CONFIG_DIR="${INSTALL_DIR}/configs"
ZIM_HOME="${INSTALL_DIR}/zim"
RED_ENV_CACHE="${INSTALL_DIR}/cache"
FZF_HOME="${INSTALL_DIR}/fzf"
FONT_DIR="${INSTALL_DIR}/fonts"

# 选项
AUTO_YES=false
INSTALL_FONTS=true
BACKUP_EXISTING=true
VIMRC_PROFILE="minimal"

# 函数：打印带颜色的消息
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# 函数：打印帮助信息
print_help() {
    cat << EOF
Red Environment - 离线安装脚本

用法: ./install.sh [选项]

选项:
    -y, --yes           自动确认所有提示
    --no-fonts          不安装 Nerd Fonts 字体
    --no-backup         不备份现有配置
    --install-dir <dir> 指定安装目录（例如: /opt/red_env 或 ~/myenv）
    --vimrc <profile>   Vim 配置可选: awesome|minimal (默认 minimal)
    -h, --help          显示此帮助信息

示例:
    ./install.sh              # 交互式安装
    ./install.sh -y           # 自动安装
    ./install.sh --no-fonts   # 不安装字体
    ./install.sh --install-dir ~/myenv  # 指定安装目录
    ./install.sh --vimrc minimal  # 使用最小 Vim 配置
EOF
}

# 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -y|--yes)
                AUTO_YES=true
                shift
                ;;
            --no-fonts)
                INSTALL_FONTS=false
                shift
                ;;
            --no-backup)
                BACKUP_EXISTING=false
                shift
                ;;
            --vimrc)
                shift
                if [ -z "$1" ]; then
                    log_error "--vimrc 需要指定配置: awesome|minimal"
                    exit 1
                fi
                VIMRC_PROFILE="$1"
                shift
                ;;
            --vimrc=*)
                VIMRC_PROFILE="${1#*=}"
                shift
                ;;
            --install-dir)
                shift
                if [ -z "$1" ]; then
                    log_error "--install-dir 需要指定路径"
                    exit 1
                fi
                INSTALL_DIR="$1"
                shift
                ;;
            --install-dir=*)
                INSTALL_DIR="${1#*=}"
                shift
                ;;
            -d)
                shift
                if [ -z "$1" ]; then
                    log_error "-d 需要指定路径"
                    exit 1
                fi
                INSTALL_DIR="$1"
                shift
                ;;
            -h|--help)
                print_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                print_help
                exit 1
                ;;
        esac
    done

    if [ "$VIMRC_PROFILE" != "awesome" ] && [ "$VIMRC_PROFILE" != "minimal" ]; then
        log_error "不支持的 Vim 配置: $VIMRC_PROFILE (仅支持 awesome|minimal)"
        exit 1
    fi
}

# 在解析参数后更新基于 INSTALL_DIR 的路径
update_install_paths() {
    # 将 RED_ENV_HOME 与 INSTALL_DIR 对齐（保留兼容旧变量名）
    RED_ENV_HOME="$INSTALL_DIR"
    BIN_DIR="${INSTALL_DIR}/bin"
    SHARE_DIR="${INSTALL_DIR}/share"
    CONFIG_DIR="${INSTALL_DIR}/configs"
    ZIM_HOME="${INSTALL_DIR}/zim"
    RED_ENV_CACHE="${INSTALL_DIR}/cache"
    FZF_HOME="${INSTALL_DIR}/fzf"
    FONT_DIR="${INSTALL_DIR}/fonts"
}

# 函数：确认继续
confirm() {
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi

    local prompt="${1:-是否继续?}"
    read -p "$prompt [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# 函数：备份文件
backup_file() {
    local file="$1"
    if [ -e "$file" ] && [ "$BACKUP_EXISTING" = true ]; then
        local backup="${file}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "备份 $file -> $backup"
        mv "$file" "$backup"
    fi
}

# 函数：创建目录
create_directories() {
    log_step "创建安装目录..."

    mkdir -p "$BIN_DIR"
    mkdir -p "$SHARE_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$ZIM_HOME"
    mkdir -p "$RED_ENV_CACHE"
    mkdir -p "$FZF_HOME"
    mkdir -p "$FONT_DIR"

    log_success "目录创建完成"
}

# 函数：安装二进制文件
install_binaries() {
    log_step "安装 CLI 工具..."

    # 复制二进制文件
    if [ -d "${SCRIPT_DIR}/bin" ]; then
        # 逐个处理，目录用 -r，文件复制后设置可执行权限
        for src in "${SCRIPT_DIR}/bin/"*; do
            if [ -d "$src" ]; then
                cp -r "$src" "$BIN_DIR/" || true
            else
                cp -f "$src" "$BIN_DIR/" || true
                chmod +x "$BIN_DIR/$(basename "$src")" || true
            fi
        done
        log_success "CLI 工具安装完成"
    else
        log_warn "未找到 bin 目录，跳过 CLI 工具安装"
    fi

    # Copy recorded dynamic exceptions (if any) into install dir for auditing
    if [ -f "${SCRIPT_DIR}/DYNAMIC_EXCEPTIONS.txt" ]; then
        cp "${SCRIPT_DIR}/DYNAMIC_EXCEPTIONS.txt" "${INSTALL_DIR}/DYNAMIC_EXCEPTIONS.txt"
        log_info "Copied DYNAMIC_EXCEPTIONS.txt to ${INSTALL_DIR}/DYNAMIC_EXCEPTIONS.txt"
    fi

    # 安装 zsh share 目录 (函数补全等)
    if [ -d "${SCRIPT_DIR}/share/zsh" ]; then
        log_info "安装 zsh share 目录..."
        rm -rf "${SHARE_DIR}/zsh"
        cp -r "${SCRIPT_DIR}/share/zsh" "${SHARE_DIR}/"
        log_success "zsh share 目录安装完成"
    fi

    # 安装 terminfo（提升终端显示与颜色兼容性）
    if [ -d "${SCRIPT_DIR}/share/terminfo" ]; then
        log_info "安装 terminfo..."
        rm -rf "${SHARE_DIR}/terminfo"
        cp -r "${SCRIPT_DIR}/share/terminfo" "${SHARE_DIR}/"
        log_success "terminfo 安装完成"
    fi

    # 安装 Vim - 已禁用（仅保留 runtime/plugin 支持）
    if [ -d "${SCRIPT_DIR}/vim" ]; then
        log_info "已省略安装捆绑的 Vim 二进制（仅保留 runtime / 插件配置）"
        log_warn "跳过将捆绑的 Vim 二进制复制到 ${INSTALL_DIR}/vim，并且不创建 vim/vi 符号链接"
    else
        log_warn "未找到 vim 目录（或已省略），跳过 Vim 二进制安装"
    fi
}

# 函数：安装 Zim
install_zim() {
    log_step "安装 Zimfw..."

    # 复制 zimfw
    if [ -f "${SCRIPT_DIR}/cache/zim/zimfw.zsh" ]; then
        cp "${SCRIPT_DIR}/cache/zim/zimfw.zsh" "$ZIM_HOME/"
        log_success "zimfw.zsh 安装完成"
    fi

    # 复制 zimfw 模块
    if [ -d "${SCRIPT_DIR}/cache/zim/modules" ]; then
        log_info "安装 Zim 模块..."
        mkdir -p "$ZIM_HOME/modules"
        cp -r "${SCRIPT_DIR}/cache/zim/modules/"* "$ZIM_HOME/modules/"
        log_success "Zim 模块安装完成"
    fi

    # 复制缓存到 red_env 目录供 zshrc 使用
    mkdir -p "$RED_ENV_CACHE"
    cp -r "${SCRIPT_DIR}/cache/"* "$RED_ENV_CACHE/"
}

# 函数：安装 fzf shell 集成
install_fzf_integration() {
    log_step "安装 fzf shell 集成..."

    if [ -d "${SCRIPT_DIR}/cache/fzf/shell" ]; then
        mkdir -p "$FZF_HOME"
        cp -r "${SCRIPT_DIR}/cache/fzf/shell" "$FZF_HOME/"
        log_success "fzf shell 集成安装完成"
    fi
}

# 函数：安装配置文件
install_configs() {
    log_step "安装配置文件..."

    # 统一复制配置到安装目录
    mkdir -p "${CONFIG_DIR}/zsh" "${CONFIG_DIR}/tmux" "${CONFIG_DIR}/git" "${CONFIG_DIR}/vim"

    if [ -f "${SCRIPT_DIR}/configs/zsh/zshrc" ]; then
        cp "${SCRIPT_DIR}/configs/zsh/zshrc" "${CONFIG_DIR}/zsh/zshrc"
    fi

    if [ -f "${SCRIPT_DIR}/configs/zsh/zimrc" ]; then
        cp "${SCRIPT_DIR}/configs/zsh/zimrc" "${CONFIG_DIR}/zsh/zimrc"
    fi

    if [ -f "${SCRIPT_DIR}/configs/tmux/tmux.conf" ]; then
        cp "${SCRIPT_DIR}/configs/tmux/tmux.conf" "${CONFIG_DIR}/tmux/tmux.conf"
    fi

    if [ -f "${SCRIPT_DIR}/configs/git/gitconfig" ]; then
        cp "${SCRIPT_DIR}/configs/git/gitconfig" "${CONFIG_DIR}/git/gitconfig"
    fi

    local vimrc_installed=false
    if [ "$VIMRC_PROFILE" = "awesome" ]; then
        if [ -d "${SCRIPT_DIR}/vim_runtime" ]; then
            log_info "安装 The Awesome vimrc (amix/vimrc)..."
            if [ -d "${HOME}/.vim_runtime" ]; then
                backup_file "${HOME}/.vim_runtime"
                rm -rf "${HOME}/.vim_runtime"
            fi
            cp -r "${SCRIPT_DIR}/vim_runtime" "${HOME}/.vim_runtime"
            chmod +x "${HOME}/.vim_runtime/install_awesome_vimrc.sh"
            sh "${HOME}/.vim_runtime/install_awesome_vimrc.sh"
                        local vim_runtime_dir=""
                        # 优先使用包含完整 Vim 的 runtime（如果存在），否则回退到我们刚复制到 ${HOME}/.vim_runtime 的打包 runtime
                        if [ -d "${INSTALL_DIR}/vim/share/vim" ]; then
                                vim_runtime_dir="$(ls -d "${INSTALL_DIR}/vim/share/vim"/vim* 2>/dev/null | sort -V | tail -n 1 || true)"
                        fi
                        if [ -z "$vim_runtime_dir" ] && [ -d "${HOME}/.vim_runtime" ]; then
                                vim_runtime_dir="$(ls -d "${HOME}/.vim_runtime"/* 2>/dev/null | sort -V | tail -n 1 || true)"
                        fi
                        if [ -n "$vim_runtime_dir" ]; then
                                cat > "${HOME}/.vim_runtime/my_configs.vim" << EOF
" Red Environment runtime fix
if !exists('g:RED_ENV_VIMRUNTIME')
    let g:RED_ENV_VIMRUNTIME = '$vim_runtime_dir'
endif
if empty(\$VIMRUNTIME) || \$VIMRUNTIME =~# '/build/output/vim/share/vim'
    let \$VIMRUNTIME = g:RED_ENV_VIMRUNTIME
endif
if isdirectory(\$VIMRUNTIME)
    execute 'set runtimepath^=' . \$VIMRUNTIME
    execute 'set runtimepath+=' . \$VIMRUNTIME
    let &packpath = &runtimepath
endif
EOF
                        else
                                log_warn "未找到 Vim runtime 目录（已尝试安装包与 ${HOME}/.vim_runtime），跳过 Awesome vimrc runtime 修复"
                        fi
            vimrc_installed=true
            log_success "Awesome vimrc 安装完成"
        else
            log_warn "未找到 vim_runtime，回退到内置配置"
        fi
    fi

    if [ "$vimrc_installed" = false ]; then
        local vimrc_source="${SCRIPT_DIR}/configs/vim/vimrc"
        if [ "$VIMRC_PROFILE" = "minimal" ]; then
            vimrc_source="${SCRIPT_DIR}/configs/vim/vimrc_minimal"
        fi

        if [ -f "$vimrc_source" ]; then
            cp "$vimrc_source" "${CONFIG_DIR}/vim/vimrc"
            log_info "使用 Vim 配置: $VIMRC_PROFILE"
        else
            log_warn "未找到 Vim 配置: $vimrc_source"
        fi
    fi

    # 生成用户侧入口配置（stub）
    if [ -f "${CONFIG_DIR}/zsh/zshrc" ]; then
        backup_file "${HOME}/.zshrc"
        cat > "${HOME}/.zshrc" << EOF
# Red Environment shim
if [ -f "${CONFIG_DIR}/zsh/zshrc" ]; then
  source "${CONFIG_DIR}/zsh/zshrc"
fi
EOF
        log_success ".zshrc 安装完成"
    fi

    if [ -f "${CONFIG_DIR}/zsh/zimrc" ]; then
        backup_file "${HOME}/.zimrc"
        ln -sf "${CONFIG_DIR}/zsh/zimrc" "${HOME}/.zimrc"
        log_success ".zimrc 安装完成"
    fi

    if [ -f "${CONFIG_DIR}/tmux/tmux.conf" ]; then
        backup_file "${HOME}/.tmux.conf"
        cat > "${HOME}/.tmux.conf" << EOF
# Red Environment shim
if-shell 'test -f "${CONFIG_DIR}/tmux/tmux.conf"' "source-file ${CONFIG_DIR}/tmux/tmux.conf"
EOF
        log_success ".tmux.conf 安装完成"
    fi

    if [ -f "${CONFIG_DIR}/git/gitconfig" ]; then
        backup_file "${HOME}/.gitconfig"
        cat > "${HOME}/.gitconfig" << EOF
[include]
    path = ${CONFIG_DIR}/git/gitconfig
EOF
        log_success ".gitconfig 安装完成"
    fi

    if [ "$vimrc_installed" = false ] && [ -f "${CONFIG_DIR}/vim/vimrc" ]; then
        backup_file "${HOME}/.vimrc"
        cat > "${HOME}/.vimrc" << EOF
" Red Environment shim
if filereadable("${CONFIG_DIR}/vim/vimrc")
  source ${CONFIG_DIR}/vim/vimrc
endif
EOF
        log_success "vim/vimrc 安装完成"
    fi
}

# 函数：安装字体
install_fonts() {
    if [ "$INSTALL_FONTS" = false ]; then
        log_info "跳过字体安装"
        return
    fi

    log_step "安装 Nerd Fonts..."

    mkdir -p "$FONT_DIR"

    # 检查是否有 ttf 文件（精简版）或 tar.xz 文件（完整版）
    if ls "${SCRIPT_DIR}/fonts/"*.ttf &>/dev/null; then
        cp "${SCRIPT_DIR}/fonts/"*.ttf "$FONT_DIR/"

        # 更新字体缓存
        if command -v fc-cache &> /dev/null; then
            fc-cache -f "$FONT_DIR"
        fi

        log_success "JetBrainsMono Nerd Font 安装完成"
    elif [ -f "${SCRIPT_DIR}/fonts/JetBrainsMono.tar.xz" ]; then
        tar -xJf "${SCRIPT_DIR}/fonts/JetBrainsMono.tar.xz" -C "$FONT_DIR"

        # 更新字体缓存
        if command -v fc-cache &> /dev/null; then
            fc-cache -f "$FONT_DIR"
        fi

        log_success "JetBrainsMono Nerd Font 安装完成"
    else
        log_warn "未找到字体文件，跳过字体安装"
    fi
}

# 函数：初始化 Zim
initialize_zim() {
    log_step "初始化 Zimfw..."

    # 使用 zimfw build 生成 init.zsh
    if [ -f "$ZIM_HOME/zimfw.zsh" ]; then
        local zsh_bin="${BIN_DIR}/zsh"
        local zsh_functions_dir=""
        if [ ! -x "$zsh_bin" ]; then
            zsh_bin="$(command -v zsh || true)"
        fi

        for dir in "${SHARE_DIR}"/zsh/*/functions; do
            if [ -d "$dir" ]; then
                zsh_functions_dir="$dir"
                break
            fi
        done

        if [ -n "$zsh_bin" ] && [ -x "$zsh_bin" ]; then
            FPATH="${zsh_functions_dir}${FPATH:+:${FPATH}}" \
                ZIM_HOME="$ZIM_HOME" ZIM_CONFIG_FILE="${CONFIG_DIR}/zsh/zimrc" \
                "$zsh_bin" -c 'source "$ZIM_HOME/zimfw.zsh" build' || \
                log_warn "zimfw build 失败，请手动执行: zimfw build"
            log_success "Zimfw 初始化完成"
        else
            log_warn "未找到 zsh，跳过 zimfw build"
        fi
    fi
}

# 函数：配置 PATH
configure_path() {
    log_step "配置 PATH..."

    # 创建 zshenv 添加 PATH 和 FPATH
    cat > "${HOME}/.zshenv" << EOF
# Red Environment - 环境变量配置
export RED_ENV_HOME="${RED_ENV_HOME}"
export PATH="${RED_ENV_HOME}/bin:${RED_ENV_HOME}/vim/bin:${PATH}"

# Prefer bundled terminfo (if present) for consistent display/keys
if [[ -d "${RED_ENV_HOME}/share/terminfo" ]]; then
    export TERMINFO_DIRS="${RED_ENV_HOME}/share/terminfo${TERMINFO_DIRS:+:${TERMINFO_DIRS}}"
fi

# zsh 函数路径 (静态编译版本)
if [[ -d "${RED_ENV_HOME}/share/zsh" ]]; then
    _red_env_zsh_share="$(ls -d "${RED_ENV_HOME}/share/zsh"/* 2>/dev/null | head -n 1)"
    if [[ -n "${_red_env_zsh_share}" ]] && [[ -d "${_red_env_zsh_share}/functions" ]]; then
        export FPATH="${_red_env_zsh_share}/functions:${FPATH}"
    fi
    unset _red_env_zsh_share
fi

# Ensure portable Vim/gVim locate their runtime files
if [[ -d "${RED_ENV_HOME}/vim/share/vim" ]]; then
    _red_env_vimruntime="$(ls -d "${RED_ENV_HOME}/vim/share/vim"/vim* 2>/dev/null | head -n 1)"
    if [[ -n "${_red_env_vimruntime}" ]]; then
        export VIMRUNTIME="${_red_env_vimruntime}"
    fi
    unset _red_env_vimruntime
fi
EOF

    log_success "PATH 配置完成"
}

# 函数：验证安装
verify_installation() {
    log_step "验证安装..."

    echo ""
    echo "已安装的工具:"
    echo "=============================================="

    # 直接从 bin 目录获取工具列表
    if [ -d "$BIN_DIR" ]; then
        for tool in "$BIN_DIR"/*; do
            if [ -x "$tool" ]; then
                tool_name=$(basename "$tool")
                # 跳过某些非工具文件（如果需要）
                if [ "$tool_name" != "zsh" ] && [ "$tool_name" != "vim" ] && [ "$tool_name" != "vi" ]; then
                    if [ "$tool_name" = "iStyle" ]; then
                        version=$("$tool" --help 2>/dev/null | head -1 || echo "OK")
                    else
                        version=$("$tool" --version 2>/dev/null | head -1 || echo "OK")
                    fi
                    echo -e "  ${GREEN}✓${NC} $tool_name: $version"
                fi
            fi
        done

        # 特殊处理 zsh
        if [ -x "$BIN_DIR/zsh" ]; then
            version=$("$BIN_DIR/zsh" --version 2>/dev/null | head -1 || echo "OK")
            echo -e "  ${GREEN}✓${NC} zsh: $version"
        fi

        # 特殊处理 vim
        if [ -x "$BIN_DIR/vim" ]; then
            version=$("$BIN_DIR/vim" --version 2>/dev/null | head -1 || echo "OK")
            echo -e "  ${GREEN}✓${NC} vim: $version"
        else
            echo -e "  ${RED}✗${NC} vim: 未安装"
        fi
    else
        echo -e "  ${RED}✗${NC} bin 目录不存在"
    fi

    echo "=============================================="
    echo ""
}

# 函数：打印完成信息
print_completion() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo "  安装完成！"
    echo "==============================================${NC}"
    echo ""
    echo "后续步骤:"
    echo ""
    echo "  1. 使用静态编译的 Zsh (无需 root 权限):"
    echo "     ${RED_ENV_HOME}/bin/zsh"
    echo ""
    echo "  2. 或将其设为默认 Shell (需要管理员权限):"
    echo "     sudo sh -c 'echo ${RED_ENV_HOME}/bin/zsh >> /etc/shells'"
    echo "     chsh -s ${RED_ENV_HOME}/bin/zsh"
    echo ""
    echo "  3. 配置 Git 用户信息:"
    echo "     git config --global user.name \"Your Name\""
    echo "     git config --global user.email \"your.email@example.com\""
    echo ""
    echo "  4. 如果使用的是终端模拟器，请将字体设置为:"
    echo "     JetBrainsMono Nerd Font"
    echo ""
    echo "需要添加到 PATH 的路径:"
    echo "  ${RED_ENV_HOME}/bin"
    echo "  ${RED_ENV_HOME}/vim/bin"
    echo ""
    echo "可添加示例:"
    echo "  export PATH=\"${RED_ENV_HOME}/bin:${RED_ENV_HOME}/vim/bin:\$PATH\""
    echo ""
    echo "享受你的新终端环境！🚀"
    echo ""
}

# 主函数
main() {
    parse_args "$@"
    # 根据可能的 --install-dir 参数更新内部路径
    update_install_paths

    echo ""
    echo "=============================================="
    echo "  Red Environment - 离线安装"
    echo "=============================================="
    echo ""
    echo "安装目录: $INSTALL_DIR"
    echo "配置目录: $CONFIG_DIR"
    echo ""

    if ! confirm "是否开始安装?"; then
        log_info "安装已取消"
        exit 0
    fi

    echo ""

    create_directories
    install_binaries
    install_zim
    install_fzf_integration
    install_configs
    install_fonts
    initialize_zim
    configure_path
    verify_installation
    print_completion
}

# 运行主函数
main "$@"
