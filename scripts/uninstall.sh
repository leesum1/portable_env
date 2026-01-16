#!/bin/bash
# =============================================================================
#                   Red Environment - 卸载脚本
# =============================================================================
# 移除 ~/.red_env 安装目录及其关联的用户配置入口文件
# =============================================================================

set -e

RED_ENV_HOME="${HOME}/.red_env"
CONFIG_DIR="${RED_ENV_HOME}/configs"

AUTO_YES=false

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_help() {
    cat << EOF
Red Environment - 卸载脚本

用法: ./uninstall.sh [选项]

选项:
    -y, --yes           自动确认所有提示
    -h, --help          显示此帮助信息
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -y|--yes)
                AUTO_YES=true
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
}

confirm() {
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi

    local prompt="${1:-是否继续?}"
    read -p "$prompt [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

is_red_env_stub() {
    local file="$1"

    if [ -L "$file" ]; then
        local target
        target="$(readlink -f "$file")"
        if [[ "$target" == "$CONFIG_DIR"/* ]]; then
            return 0
        fi
    fi

    if [ -f "$file" ] && grep -q "Red Environment" "$file"; then
        return 0
    fi

    return 1
}

remove_stub() {
    local file="$1"

    if [ ! -e "$file" ]; then
        return 0
    fi

    if is_red_env_stub "$file"; then
        rm -f "$file"
        log_info "已移除 $file"
    else
        log_warn "$file 非 Red Environment 生成的文件，跳过"
    fi
}

main() {
    parse_args "$@"

    echo ""
    echo "=============================================="
    echo "  Red Environment - 卸载"
    echo "=============================================="
    echo ""
    echo "安装目录: $RED_ENV_HOME"
    echo ""

    if ! confirm "确认卸载并删除 ${RED_ENV_HOME}?"; then
        log_info "卸载已取消"
        exit 0
    fi

    remove_stub "${HOME}/.zshrc"
    remove_stub "${HOME}/.zshenv"
    remove_stub "${HOME}/.tmux.conf"
    remove_stub "${HOME}/.gitconfig"
    remove_stub "${HOME}/.vimrc"

    if [ -L "${HOME}/.zimrc" ] && [ "$(readlink -f "${HOME}/.zimrc")" = "${CONFIG_DIR}/zsh/zimrc" ]; then
        rm -f "${HOME}/.zimrc"
        log_info "已移除 ${HOME}/.zimrc"
    fi

    if [ -d "$RED_ENV_HOME" ]; then
        rm -rf "$RED_ENV_HOME"
        log_info "已删除安装目录 $RED_ENV_HOME"
    fi

    echo ""
    log_info "卸载完成"
    echo "如需恢复配置，请手动从 *.backup.* 文件中恢复"
}

main "$@"
