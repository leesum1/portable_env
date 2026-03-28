FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    file \
    gzip \
    coreutils \
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
    && test -f /verify/unpacked/red_env_offline/installer/install.sh \
    && chmod +x /verify/unpacked/red_env_offline/installer/install.sh \
    && chmod +x /verify/unpacked/red_env_offline/installer/uninstall.sh \
    && HOME=/root sh /verify/unpacked/red_env_offline/installer/install.sh \
    && test -d /root/.red_env/bin \
    && test -d /root/.red_env/configs \
    && test -x /root/.red_env/bin/fzf
