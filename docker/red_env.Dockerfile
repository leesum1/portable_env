# ============================================================
# Red Environment — 基于 Ubuntu latest + Go/Zig/Rust/Cargo + core profile
# 包含: bat, fzf, rg, fd, delta (预编译二进制) + zsh (oh-my-zsh)
# 附带: Go + Zig(0.16.0) + Rust(Cargo+musl targets)（用于 zig_build/go_build）
# ============================================================

FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    TERM=xterm-256color

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash ca-certificates file gzip coreutils python3 tar vim xz-utils locales \
    ncurses-term git wget curl gcc libc6-dev musl-dev python3-pip > /dev/null 2>&1 \
    && sed -i 's/^# *en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Go（用于未来 go_build）+ musl-dev（编译目标依赖）
RUN wget -qO go.tar.gz https://go.dev/dl/go1.23.6.linux-amd64.tar.gz \
    && tar Cxz --strip-components=1 -f go.tar.gz -C /usr/local > /dev/null 2>&1 \
    && rm go.tar.gz

# 安装 Zig（用于未来 zig_build）—— 使用 Ubuntu apt 包
RUN apt-get update > /dev/null 2>&1 && apt-get install -y --no-install-recommends zig > /dev/null 2>&1 || echo "zig not in apt"

# 安装 Rust + musl targets（用于未来 zig_build）—— Zig 编译目标需要 Rust/Cargo
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y > /dev/null 2>&1 \
    && . "$HOME/.cargo/env" && rustup target add x86_64-unknown-linux-musl aarch64-unknown-linux-musl > /dev/null 2>&1

# 安装 cargo-zigbuild（用于 zig_build 策略的 Rust Cargo 编译目标）
RUN . "$HOME/.cargo/env" && cargo install cargo-zigbuild --quiet > /dev/null 2>&1

ENV PATH="/root/.cargo/bin:/usr/local/go/bin:/usr/local/bin:$PATH"

WORKDIR /workspace
COPY dist/red_env_core_x86_64.tar.gz .

# 解压 bundle + oh-my-zsh + configs，安装到 /root/.red_env，复制 bin 到全局 PATH
RUN tar -xzf red_env_core_x86_64.tar.gz && \
    mkdir -p /root/.red_env/bundle/bin /root/.red_env/configs/zsh /root/.red_env/installer && \
    cp -r red_env_offline/bundle/* /root/.red_env/bundle/ 2>/dev/null || true && \
    cp -r red_env_offline/configs/* /root/.red_env/configs/ 2>/dev/null || true && \
    cp -r red_env_offline/installer/* /root/.red_env/installer/ 2>/dev/null || true && \
    # oh-my-zsh: 从 bundle/zsh-bin/ 安装（如果有）
    if [ -d /workspace/red_env_offline/bundle/zsh-bin ]; then \
        mkdir -p /root/.red_env/bin && \
        tar xzf /workspace/red_env_offline/bundle/zsh-bin/zsh-5.8-linux.tar.gz -C /root/.red_env 2>/dev/null; \
        chmod +x /root/.red_env/bin/zsh; fi && \
    # oh-my-zsh: 从 bundle/cache/oh-my-zsh 复制（如果有）
    if [ -d /workspace/red_env_offline/bundle/cache ]; then \
        mkdir -p /root/.red_env/cache/oh-my-zsh; cp -r /workspace/red_env_offline/bundle/cache/* /root/.red_env/cache/; fi && \
    # 运行安装脚本（备份用户配置 + 创建符号链接）
    HOME=/root bash red_env_offline/installer/install.sh > /dev/null 2>&1 || true && \
    # 确保 bundle/bin 下的所有二进制都在 PATH (/bin) 中可用，zsh 特殊处理
    for f in /workspace/red_env_offline/bundle/bin/*; do \
        if [ -f "$f" ] && command -v "$(basename "$f")" >/dev/null 2>&1; then \
            echo "SKIP $(basename "$f"): already exists"; \
        else \
            cp "$f" /bin/; \
        fi; \
    done && \
    # zsh: bundle/bin/zsh 不存在，但从 bundle/zsh-bin/ 复制（如果已解压）
    if [ -x /root/.red_env/bin/zsh ] && ! command -v zsh >/dev/null 2>&1; then \
        cp /root/.red_env/bin/zsh /bin/zsh; fi

VOLUME ["/workspace"]
CMD ["bash", "-i", "-l"]