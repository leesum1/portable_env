FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    file \
    gzip \
    coreutils \
    python3 \
    tar \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /verify
ARG PACKAGE_FILE
COPY ${PACKAGE_FILE} /verify/package.tar.gz

RUN mkdir -p /verify/unpacked \
    && tar -xzf /verify/package.tar.gz -C /verify/unpacked \
    && test -d /verify/unpacked/red_env_offline/bundle/bin \
    && test -d /verify/unpacked/red_env_offline/configs \
    && test -d /verify/unpacked/red_env_offline/installer \
    && test -f /verify/unpacked/red_env_offline/bundle/bundle-manifest.json \
    && test -f /verify/unpacked/red_env_offline/installer/install.sh \
    && chmod +x /verify/unpacked/red_env_offline/installer/install.sh \
    && chmod +x /verify/unpacked/red_env_offline/installer/uninstall.sh \
    && HOME=/root sh /verify/unpacked/red_env_offline/installer/install.sh \
    && test -d /root/.red_env/bin \
    && test -d /root/.red_env/configs \
    && python3 -c "import json, os, pathlib; \
manifest = json.loads(pathlib.Path('/verify/unpacked/red_env_offline/bundle/bundle-manifest.json').read_text(encoding='utf-8')); \
packages = manifest.get('packages', []); \
assert packages, 'bundle-manifest has no packages'; \
bin_dir = pathlib.Path('/root/.red_env/bin'); \
assert bin_dir.is_dir(), 'installed bin directory missing'; \
installed = [pkg for pkg in packages if (bin_dir / pkg).exists()]; \
assert installed, f'no installed package binaries found for metadata packages: {packages}'; \
assert all(os.access(bin_dir / pkg, os.X_OK) for pkg in installed), f'non-executable binaries in: {installed}'"
