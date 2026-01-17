# =============================================================================
#                   Red Environment - Build Makefile
# =============================================================================
# 用于构建和验证离线终端环境包
#
# 使用方法:
#   make build-x86_64      # 构建 x86_64 包
#   make build-arm64       # 构建 ARM64 包
#   make build-all         # 构建所有架构
#   make verify-x86_64     # 验证 x86_64 包
#   make verify-arm64      # 验证 ARM64 包
#   make verify-all        # 验证所有架构
#   make all               # 构建并验证所有架构
#   make clean             # 清理构建产物
# =============================================================================

.PHONY: all build-all build-x86_64 build-arm64 build-base build-base-x86_64 build-base-arm64 verify-all verify-x86_64 verify-arm64 verify-shell-x86_64 verify-shell-arm64 clean help




# 目录定义
DIST_DIR := dist
LOGS_DIR := logs
OUTPUT_X86_64 := output_x86_64
OUTPUT_ARM64 := output_arm64
BASE_IMAGE_X86_64 := red_env_build_base:x86_64
BASE_IMAGE_ARM64 := red_env_build_base:arm64

# Docker buildx 构建参数
# 使用 default builder (docker driver) 以获得 --network host 支持
DOCKER_BUILDX_FLAGS := --builder default --network host
# Docker secret flags are disabled by default (opt-in behavior)
DOCKER_SECRET_FLAGS :=

# 默认目标

# 默认目标
all: build-all verify-all

# =============================================================================
# 构建目标
# =============================================================================

build-all: build-x86_64 build-arm64

build-base: build-base-x86_64 build-base-arm64

## 构建 x86_64 基础镜像
build-base-x86_64: $(LOGS_DIR)
	@echo "=== 构建 x86_64 基础构建镜像 ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/amd64 \
		$(DOCKER_SECRET_FLAGS) \
		-f docker/Dockerfile.base \
		-t $(BASE_IMAGE_X86_64) \
		--load \
		. 2>&1 | tee $(LOGS_DIR)/build_base_x86_64.log

## 构建 ARM64 基础镜像
build-base-arm64: $(LOGS_DIR)
	@echo "=== 构建 ARM64 基础构建镜像 ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/arm64 \
		$(DOCKER_SECRET_FLAGS) \
		-f docker/Dockerfile.base \
		-t $(BASE_IMAGE_ARM64) \
		--load \
		. 2>&1 | tee $(LOGS_DIR)/build_base_arm64.log

## 构建 x86_64 包
build-x86_64: build-base-x86_64 $(DIST_DIR) $(LOGS_DIR)
	@echo "=== 构建 x86_64 离线包 ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/amd64 \
		$(DOCKER_SECRET_FLAGS) \
		--build-arg BASE_IMAGE=$(BASE_IMAGE_X86_64) \
		-f docker/Dockerfile.build \
		-t red_env_builder:x86_64 \
		--output type=local,dest=./$(OUTPUT_X86_64) \
		. 2>&1 | tee $(LOGS_DIR)/build_x86_64.log
	@cp $(OUTPUT_X86_64)/*.tar.gz* $(DIST_DIR)/
	@echo "=== x86_64 构建完成 ==="
	@ls -lh $(DIST_DIR)/red_env_offline_x86_64.tar.gz

## 构建 ARM64 包
build-arm64: build-base-arm64 $(DIST_DIR) $(LOGS_DIR)
	@echo "=== 构建 ARM64 离线包 ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/arm64 \
		$(DOCKER_SECRET_FLAGS) \
		--build-arg BASE_IMAGE=$(BASE_IMAGE_ARM64) \
		-f docker/Dockerfile.build \
		-t red_env_builder:arm64 \
		--output type=local,dest=./$(OUTPUT_ARM64) \
		. 2>&1 | tee $(LOGS_DIR)/build_arm64.log
	@cp $(OUTPUT_ARM64)/*.tar.gz* $(DIST_DIR)/
	@echo "=== ARM64 构建完成 ==="
	@ls -lh $(DIST_DIR)/red_env_offline_arm64.tar.gz

# =============================================================================
# 验证目标
# =============================================================================

verify-all: verify-x86_64 verify-arm64

## 验证 x86_64 包
verify-x86_64: $(DIST_DIR)/red_env_offline_x86_64.tar.gz
	@echo "=== 验证 x86_64 离线包 ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/amd64 \
		-f docker/Dockerfile.verify \
		-t red_env_verify:x86_64 \
		--build-arg PACKAGE_FILE=red_env_offline_x86_64.tar.gz \
		--load \
		. 2>&1 | tee $(LOGS_DIR)/verify_x86_64.log
	@echo "=== 运行 x86_64 验证测试 ==="
	@docker run --rm red_env_verify:x86_64 /home/testuser/verify_tools.sh
	@echo "=== x86_64 验证通过 ==="

## 进入 x86_64 验证镜像进行交互
verify-shell-x86_64: $(DIST_DIR)/red_env_offline_x86_64.tar.gz
	@echo "=== 构建 x86_64 验证镜像（供交互） ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/amd64 \
		-f docker/Dockerfile.verify \
		-t red_env_verify:x86_64 \
		--build-arg PACKAGE_FILE=red_env_offline_x86_64.tar.gz \
		--load \
		. 2>&1 | tee $(LOGS_DIR)/verify_x86_64_build_only.log
	@echo "=== 进入 x86_64 验证容器 ==="
	@docker run --rm -it red_env_verify:x86_64 zsh

## 验证 ARM64 包（需要 QEMU 模拟或在 ARM64 机器上运行）
verify-arm64: $(DIST_DIR)/red_env_offline_arm64.tar.gz
	@echo "=== 验证 ARM64 离线包 ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/arm64 \
		-f docker/Dockerfile.verify \
		-t red_env_verify:arm64 \
		--build-arg PACKAGE_FILE=red_env_offline_arm64.tar.gz \
		--load \
		. 2>&1 | tee $(LOGS_DIR)/verify_arm64.log
	@echo "=== 运行 ARM64 验证测试 ==="
	@docker run --rm --platform linux/arm64 red_env_verify:arm64 /home/testuser/verify_tools.sh
	@echo "=== ARM64 验证通过 ==="

## 进入 ARM64 验证镜像进行交互（需要 QEMU 或 ARM64 机器）
verify-shell-arm64: $(DIST_DIR)/red_env_offline_arm64.tar.gz
	@echo "=== 构建 ARM64 验证镜像（供交互） ==="
	docker buildx build $(DOCKER_BUILDX_FLAGS) \
		--platform linux/arm64 \
		-f docker/Dockerfile.verify \
		-t red_env_verify:arm64 \
		--build-arg PACKAGE_FILE=red_env_offline_arm64.tar.gz \
		--load \
		. 2>&1 | tee $(LOGS_DIR)/verify_arm64_build_only.log
	@echo "=== 进入 ARM64 验证容器 ==="
	@docker run --rm -it --platform linux/arm64 red_env_verify:arm64 zsh

# =============================================================================
# 辅助目标
# =============================================================================

## 创建目录
$(DIST_DIR):
	@mkdir -p $(DIST_DIR)

$(LOGS_DIR):
	@mkdir -p $(LOGS_DIR)

## 清理构建产物
clean:
	@echo "=== 清理构建产物 ==="
	rm -rf $(OUTPUT_X86_64) $(OUTPUT_ARM64)
	rm -f $(DIST_DIR)/*.tar.gz $(DIST_DIR)/*.sha256
	rm -f $(LOGS_DIR)/*.log
	-docker rmi red_env_builder:x86_64 red_env_builder:arm64 2>/dev/null
	-docker rmi $(BASE_IMAGE_X86_64) $(BASE_IMAGE_ARM64) 2>/dev/null
	-docker rmi red_env_verify:x86_64 red_env_verify:arm64 2>/dev/null
	@echo "=== 清理完成 ==="

## 深度清理（包括 Docker 缓存）
clean-all: clean
	@echo "=== 清理 Docker 构建缓存 ==="
	docker builder prune -f
	@echo "=== 深度清理完成 ==="

## 显示帮助信息
help:
	@echo "Red Environment 构建系统"
	@echo ""
	@echo "使用方法: make [目标]"
	@echo ""
	@echo "构建目标:"
	@echo "  build-x86_64    构建 x86_64 架构离线包"
	@echo "  build-arm64     构建 ARM64 架构离线包"
	@echo "  build-all       构建所有架构离线包"
	@echo "  build-base      构建基础构建镜像（加速后续构建）"
	@echo ""
	@echo "验证目标:"
	@echo "  verify-x86_64   验证 x86_64 离线包"
	@echo "  verify-arm64    验证 ARM64 离线包"
	@echo "  verify-all      验证所有架构离线包"
	@echo ""
	@echo "其他目标:"
	@echo "  all             构建并验证所有架构 (默认)"
	@echo "  clean           清理构建产物"
	@echo "  clean-all       深度清理（包括 Docker 缓存）"
	@echo "  verify-shell-x86_64  进入 x86_64 验证镜像进行交互"
	@echo "  verify-shell-arm64   进入 ARM64 验证镜像进行交互"
	@echo "  help            显示此帮助信息"
	@echo ""
	@echo "示例:"
	@echo "  make build-x86_64 verify-x86_64  # 构建并验证 x86_64"
	@echo "  make all                         # 构建并验证所有架构"
