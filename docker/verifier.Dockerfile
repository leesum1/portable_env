FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    file \
    gzip \
    coreutils \
    python3 \
    tar \
    vim \
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
    && test -f /root/.red_env/cache/zim/zimfw.zsh \
    && python3 -c "import json, os, pathlib; \
manifest = json.loads(pathlib.Path('/verify/unpacked/red_env_offline/bundle/bundle-manifest.json').read_text(encoding='utf-8')); \
installed_files = manifest.get('installed_files', []); \
assert installed_files, 'bundle-manifest has no installed_files'; \
install_root = pathlib.Path('/root/.red_env'); \
assert install_root.is_dir(), 'install root missing'; \
missing = [relative for relative in installed_files if not (install_root / relative).exists()]; \
assert not missing, f'missing installed files: {missing}'; \
non_executable = [relative for relative in installed_files if (install_root / relative).is_file() and not os.access(install_root / relative, os.X_OK)]; \
assert not non_executable, f'non-executable installed files: {non_executable}'" \
    && if [ -x /root/.red_env/bin/zsh ]; then HOME=/root ZDOTDIR=/root/.red_env/configs/zsh /root/.red_env/bin/zsh -i -c 'test -f /root/.red_env/zim/zimfw.zsh && test -f /root/.red_env/zim/init.zsh'; fi
