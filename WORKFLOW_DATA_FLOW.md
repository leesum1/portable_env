# GitHub Actions Workflow 数据流完整分析

## 📊 完整数据传递链路

### 第一阶段：构建 (Build)

#### build-x86_64 job
```
创建目录: mkdir -p logs dist
    ↓
Dockerfile.base 构建基础镜像: red_env_build_base:x86_64 (--load 加载到本地)
    ↓
Dockerfile.build 构建离线包
    ├─ 输入: BASE_IMAGE=red_env_build_base:x86_64
    ├─ 输出: docker buildx --output type=local,dest=./output_x86_64
    ├─ 生成文件:
    │   ├─ output_x86_64/red_env_offline_x86_64.tar.gz
    │   └─ output_x86_64/red_env_offline_x86_64.tar.gz.sha256
    ↓
cp output_x86_64/*.tar.gz* dist/
    ├─ dist/red_env_offline_x86_64.tar.gz
    └─ dist/red_env_offline_x86_64.tar.gz.sha256
    ↓
ls -lh dist/ (列出验证)
    ↓
Upload Artifacts: dist/ → red_env_offline_x86_64 (retention-days: 7)
```

#### build-arm64 job
```
同上，但 --platform linux/arm64
生成:
    ├─ output_arm64/red_env_offline_arm64.tar.gz
    ├─ output_arm64/red_env_offline_arm64.tar.gz.sha256
    └─ 上传为 red_env_offline_arm64
```

---

### 第二阶段：验证 (Verify)

#### verify-x86_64 job
```
需要: build-x86_64 ✓

检出代码: Checkout code (获取 docker/Dockerfile.verify, configs/, scripts/)
    ↓
设置 Docker Buildx
    ↓
下载 artifacts: red_env_offline_x86_64 → dist/
    ├─ dist/red_env_offline_x86_64.tar.gz
    └─ dist/red_env_offline_x86_64.tar.gz.sha256
    ↓
创建目录: mkdir -p logs
    ↓
验证包完整性:
    ├─ 方法1: sha256sum -c 直接验证
    ├─ 方法2 (备选): 手动比较哈希值
    └─ 结果: ✓ Package integrity verified for x86_64!
    ↓
[文件检查] test -f dist/red_env_offline_x86_64.tar.gz
    ↓
构建验证镜像:
    ├─ 构建上下文: . (项目根目录)
    ├─ Dockerfile: docker/Dockerfile.verify
    ├─ ARG PACKAGE_FILE=red_env_offline_x86_64.tar.gz
    ├─ COPY dist/${PACKAGE_FILE} → /home/testuser/
    │   ├─ COPY dist/red_env_offline_x86_64.tar.gz
    │   ├─ COPY configs/ → /home/testuser/configs/
    │   └─ COPY scripts/verify_tools.sh → /home/testuser/
    ├─ RUN tar -xzf /home/testuser/red_env_offline_x86_64.tar.gz
    ├─ RUN cd /home/testuser/red_env_offline && ./install.sh --yes
    ├─ RUN /home/testuser/verify_tools.sh (构建时运行验证)
    └─ 镜像: red_env_verify:x86_64 (--load 加载到本地)
    ↓
完成标记: ✓ Verification passed for x86_64!
```

#### verify-arm64 job
```
同上，但:
    ├─ --platform linux/arm64
    ├─ PACKAGE_FILE=red_env_offline_arm64.tar.gz
    └─ 镜像: red_env_verify:arm64
```

---

### 第三阶段：发布 (Release)

#### release job
```
需要: [verify-x86_64, verify-arm64] ✓
条件: if: startsWith(github.ref, 'refs/tags/v') (仅在标签推送时运行)

检出代码
    ↓
下载所有 artifacts:
    ├─ red_env_offline_x86_64/
    │   ├─ red_env_offline_x86_64.tar.gz
    │   └─ red_env_offline_x86_64.tar.gz.sha256
    └─ red_env_offline_arm64/
        ├─ red_env_offline_arm64.tar.gz
        └─ red_env_offline_arm64.tar.gz.sha256
    ↓
    → release_artifacts/
    ↓
准备发布文件:
    ├─ mkdir -p release_files
    ├─ find release_artifacts -name "*.tar.gz" -o -name "*.sha256"
    └─ cp 到 release_files/
    ↓
    release_files/
    ├─ red_env_offline_x86_64.tar.gz
    ├─ red_env_offline_x86_64.tar.gz.sha256
    ├─ red_env_offline_arm64.tar.gz
    └─ red_env_offline_arm64.tar.gz.sha256
    ↓
创建 GitHub Release:
    └─ 上传文件 + 发布说明
```

---

## ✅ 数据流完整性检查清单

### Build 阶段
- [x] 目录结构正确
- [x] docker buildx 输出路径正确
- [x] 文件复制到 dist/ 正确
- [x] artifacts 上传正确

### Verify 阶段
- [x] artifacts 下载到正确位置 (dist/)
- [x] checksum 验证算法改进 (双重检查)
- [x] **NEW**: 文件存在性检查
- [x] **NEW**: 详细的调试日志输出
- [x] Docker 构建上下文包含所需文件
- [x] Dockerfile.verify 文件访问路径正确

### Release 阶段
- [x] artifacts 递归查找正确
- [x] **NEW**: 详细的文件列表输出
- [x] **NEW**: 文件存在性检查（防止空发布）
- [x] 文件名一致性

---

## 🔍 关键改进点

### 1. Checksum 验证改进
**问题**: checksum 文件中的绝对路径 `/output/...` 与实际文件位置不匹配
**方案**: 添加备选的手动哈希比对方法

### 2. 文件检查改进
**新增**: 
```bash
test -f dist/red_env_offline_x86_64.tar.gz || {
  echo "ERROR: File not found!"
  exit 1
}
```

### 3. 调试日志改进
**新增**: 每个关键步骤都有详细的日志输出
- Build output 列表
- 文件查找结果
- 最终文件验证

---

## ⚠️ 已知限制

1. **Artifact 保留时间**: 仅 7 天，部署时需要尽快下载
2. **并行构建**: x86_64 和 ARM64 可并行构建，加快流程
3. **Release 条件**: 仅在 `v*` 标签推送时创建发布

