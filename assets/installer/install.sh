#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="${SCRIPT_DIR}/../bundle"
INSTALL_DIR="${HOME}/.red_env"

copy_contents() {
  src="$1"
  dest="$2"
  if [ -d "$src" ]; then
    mkdir -p "$dest"
    cp -R "$src/." "$dest"
  fi
}

mkdir -p "${INSTALL_DIR}"
copy_contents "${SCRIPT_DIR}/../configs" "${INSTALL_DIR}/configs"
copy_contents "${BUNDLE_DIR}/bin" "${INSTALL_DIR}/bin"
copy_contents "${BUNDLE_DIR}/share" "${INSTALL_DIR}/share"

echo "Installed red_env into ${INSTALL_DIR}"
