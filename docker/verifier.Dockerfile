FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    file \
    git \
    tar \
    xz-utils \
    zsh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /verify
ARG PACKAGE_FILE
COPY ${PACKAGE_FILE} /verify/package.tar.gz
