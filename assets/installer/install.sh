#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.red_env"

mkdir -p "${INSTALL_DIR}"
cp -R "${SCRIPT_DIR}/../configs" "${INSTALL_DIR}/configs"
cp -R "${SCRIPT_DIR}/../bundle/bin" "${INSTALL_DIR}/bin"
if [ -d "${SCRIPT_DIR}/../bundle/share" ]; then
  cp -R "${SCRIPT_DIR}/../bundle/share" "${INSTALL_DIR}/share"
fi

echo "Installed red_env into ${INSTALL_DIR}"
