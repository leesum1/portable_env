#!/bin/bash
# =============================================================================
#                   Red Environment - 构建脚本
# =============================================================================
# 使用 Docker 构建离线安装包
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="${PROJECT_DIR}/output"

# Docker 镜像名称
BUILD_IMAGE="red_env_builder"

# 函数：打印带颜色的消息
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 函数：检查 Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker 守护进程未运行或权限不足"
        exit 1
    fi

    log_success "Docker 检查通过"
}

# 函数：清理旧的构建
clean_old_build() {
    log_info "清理旧的构建文件..."
    rm -rf "${OUTPUT_DIR}"
    mkdir -p "${OUTPUT_DIR}"
}

# 函数：构建 Docker 镜像
build_docker_image() {
    log_info "构建 Docker 构建镜像..."

    # 检测架构
    ARCH=$(uname -m)
    case $ARCH in
        x86_64)
            PLATFORM="linux/amd64"
            ;;
        aarch64|arm64)
            PLATFORM="linux/arm64"
            ;;
        *)
            log_error "不支持的架构: $ARCH"
            exit 1
            ;;
    esac

    log_info "目标架构: $PLATFORM"

    docker build \
        --platform "$PLATFORM" \
        -t "$BUILD_IMAGE" \
        -f "${PROJECT_DIR}/docker/Dockerfile.build" \
        "${PROJECT_DIR}"

    log_success "Docker 镜像构建完成"
}

# 函数：运行容器并生成离线包
generate_offline_package() {
    log_info "生成离线安装包..."

    # 创建临时目录用于构建最终包
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT

    # 从 Docker 容器中提取文件
    docker create --name red_env_temp "$BUILD_IMAGE" &>/dev/null
    docker cp red_env_temp:/build/output/. "${TEMP_DIR}/"
    docker rm red_env_temp &>/dev/null

    # 复制配置文件
    log_info "复制配置文件..."
    cp -r "${PROJECT_DIR}/configs" "${TEMP_DIR}/"

    # 复制安装脚本
    log_info "复制安装脚本..."
    cp "${PROJECT_DIR}/scripts/install.sh" "${TEMP_DIR}/"
    chmod +x "${TEMP_DIR}/install.sh"

    # 创建版本信息
    cat > "${TEMP_DIR}/version.txt" << EOF
Red Environment Offline Package
Build Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Build Host: $(hostname)
Architecture: $(uname -m)
EOF

    # 创建压缩包
    log_info "创建压缩包..."
    tar -czvf "${OUTPUT_DIR}/red_env_offline.tar.gz" -C "${TEMP_DIR}" .

    # 计算校验和
    log_info "计算校验和..."
    cd "${OUTPUT_DIR}"
    sha256sum red_env_offline.tar.gz > red_env_offline.tar.gz.sha256

    log_success "离线安装包创建完成: ${OUTPUT_DIR}/red_env_offline.tar.gz"
}

# 函数：显示构建结果
show_result() {
    echo ""
    echo "=============================================="
    echo -e "${GREEN}构建完成！${NC}"
    echo "=============================================="
    echo ""
    echo "输出文件:"
    ls -lh "${OUTPUT_DIR}/"
    echo ""
    echo "使用方法:"
    echo "  1. 将 red_env_offline.tar.gz 复制到目标机器"
    echo "  2. 解压: tar -xzf red_env_offline.tar.gz -C ~/red_env_offline"
    echo "  3. 安装: cd ~/red_env_offline && ./install.sh"
    echo ""
    echo "验证安装:"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "=============================================="
    echo "  Red Environment - 离线包构建工具"
    echo "=============================================="
    echo ""

    check_docker
    clean_old_build
    build_docker_image
    generate_offline_package
    show_result
}

# 运行主函数
main "$@"
