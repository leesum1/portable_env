FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    tar \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
