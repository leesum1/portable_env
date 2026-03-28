#!/usr/bin/env sh
set -eu

INSTALL_DIR="${HOME}/.red_env"
if [ -d "${INSTALL_DIR}" ]; then
  rm -rf "${INSTALL_DIR}"
  echo "Removed ${INSTALL_DIR}"
else
  echo "${INSTALL_DIR} does not exist"
fi
