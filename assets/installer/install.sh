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
for path in "${BUNDLE_DIR}"/*; do
  if [ -e "$path" ]; then
    name="$(basename "$path")"
    copy_contents "$path" "${INSTALL_DIR}/${name}"
  fi
done

echo "Installed red_env into ${INSTALL_DIR}"
