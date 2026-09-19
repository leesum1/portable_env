FROM python:3.11-slim

# Install build dependencies (Rust + Zig + Go toolchain)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    tar \
    xz-utils \
    wget \
    gcc \
    libc6-dev \
    musl-dev \
    llvm-19-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust + musl targets (for zig_build) — use bash for source
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y > /dev/null 2>&1 \
    && . "$HOME/.cargo/env" \
    && rustup target add x86_64-unknown-linux-musl aarch64-unknown-linux-musl > /dev/null 2>&1

# Install Zig (for zig_build) — use 0.13 which has stable GitHub release
RUN wget -qO zig.tar.xz https://github.com/ziglang/zig/releases/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz \
    && tar xf zig.tar.xz -C /usr/local --strip-components=1 > /dev/null 2>&1 \
    && rm zig.tar.xz

# Install Go (for go_build) — use GitHub release as fallback
RUN wget -qO go.tar.gz https://go.dev/dl/go1.23.6.linux-amd64.tar.gz \
    && tar Cxz --strip-components=1 -f go.tar.gz -C /usr/local > /dev/null 2>&1 \
    && rm go.tar.gz

ENV PATH="/root/.cargo/bin:/usr/local/bin:$PATH"

WORKDIR /workspace