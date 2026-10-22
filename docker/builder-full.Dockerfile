# Hermetic build environment for red_env source builds.
#
# The base image is pinned by digest so a rebuild cannot silently pick up a new
# python:3.11-slim-bookworm. Bump the digest deliberately, together with the
# toolchain versions below.
#
# Build:
#   docker build -f docker/builder-full.Dockerfile -t red-env-builder:full docker/
#
# Use:
#   python -m red_env build --profile core --arch x86_64 --in-docker
ARG BASE_IMAGE=python:3.11-slim-bookworm@sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf
FROM ${BASE_IMAGE}

# Toolchain pins. Rust and Go must match [toolchains] in manifests/manifest.toml;
# cargo-zigbuild and Zig are build-environment details owned by this image.
ARG RUST_VERSION=1.99.1
ARG CARGO_ZIGBUILD_VERSION=0.24.0
ARG ZIG_VERSION=0.16.0
ARG GO_VERSION=1.27.3

# Populated by buildx for multi-arch builds ("amd64" / "arm64").
ARG TARGETARCH

ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:/opt/zig:/usr/local/go/bin:${PATH} \
    CARGO_TERM_COLOR=always

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        tar \
        xz-utils \
        gcc \
        libc6-dev \
        make \
        pkg-config \
        cmake \
        clang \
        libclang-dev \
    && rm -rf /var/lib/apt/lists/*

# Some crates (ouch's bundled bzip3, for example) run bindgen at build time,
# which dlopen()s libclang instead of linking it. Debian keeps it under
# /usr/lib/llvm-*/, outside the default loader path, so expose it there.
RUN set -eux; \
    for lib in /usr/lib/llvm-*/lib/libclang.so /usr/lib/llvm-*/lib/libclang.so.*; do \
        [ -e "${lib}" ] || continue; \
        ln -sf "${lib}" "/usr/lib/$(uname -m)-linux-gnu/$(basename "${lib}")"; \
    done; \
    ldconfig; \
    ls -l /usr/lib/$(uname -m)-linux-gnu/libclang.so*

# Rust at the pinned version, with the musl targets cargo-zigbuild links against.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
        | sh -s -- -y --profile minimal --default-toolchain "${RUST_VERSION}" \
    && rustup target add --toolchain "${RUST_VERSION}" \
        x86_64-unknown-linux-musl \
        aarch64-unknown-linux-musl \
    && rustc --version

RUN cargo install cargo-zigbuild --version "${CARGO_ZIGBUILD_VERSION}" --locked \
    && cargo zigbuild --help > /dev/null

# Zig, downloaded per target architecture and verified against a pinned checksum.
RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
        amd64) zig_arch="x86_64";  zig_sha="70e49664a74374b48b51e6f3fdfbf437f6395d42509050588bd49abe52ba3d00" ;; \
        arm64) zig_arch="aarch64"; zig_sha="ea4b09bfb22ec6f6c6ceac57ab63efb6b46e17ab08d21f69f3a48b38e1534f17" ;; \
        *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 "https://ziglang.org/download/${ZIG_VERSION}/zig-${zig_arch}-linux-${ZIG_VERSION}.tar.xz" -o /tmp/zig.tar.xz; \
    echo "${zig_sha}  /tmp/zig.tar.xz" | sha256sum -c -; \
    mkdir -p /opt/zig; \
    tar -xJf /tmp/zig.tar.xz -C /opt/zig --strip-components=1; \
    rm -f /tmp/zig.tar.xz; \
    zig version

# Go at the pinned version, verified against a pinned checksum.
RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
        amd64) go_arch="amd64"; go_sha="65efbc80fdc1fa2cd2631cad5b481777a68e8725f34e89f50fc6ac714e379b40" ;; \
        arm64) go_arch="arm64"; go_sha="a06e99309dbcbdca1a8ccd2282c3ee146e55930886e26b4f1193269587165f49" ;; \
        *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    go_tarball="go${GO_VERSION}.linux-${go_arch}.tar.gz"; \
    for base in \
        "https://go.dev/dl" \
        "https://mirrors.aliyun.com/golang" \
        "https://golang.google.cn/dl" \
    ; do \
        if curl -fsSL --retry 3 --retry-delay 2 --connect-timeout 15 "${base}/${go_tarball}" -o /tmp/go.tar.gz; then \
            if echo "${go_sha}  /tmp/go.tar.gz" | sha256sum -c -; then \
                break; \
            fi; \
            echo "checksum mismatch for ${go_tarball} from ${base}" >&2; \
        else \
            echo "download failed from ${base}" >&2; \
        fi; \
        rm -f /tmp/go.tar.gz; \
    done; \
    test -f /tmp/go.tar.gz; \
    tar -xzf /tmp/go.tar.gz -C /usr/local; \
    rm -f /tmp/go.tar.gz; \
    go version

LABEL org.opencontainers.image.title="red-env builder" \
      org.opencontainers.image.description="Pinned Rust/Zig/Go toolchain for red_env source builds"

WORKDIR /workspace
