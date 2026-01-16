#!/usr/bin/env bash
set -euo pipefail

RED_ENV_HOME="${RED_ENV_HOME:-$HOME/.red_env}"
BIN_DIR="${RED_ENV_HOME}/bin"
VIM_BIN_DIR="${RED_ENV_HOME}/vim/bin"

echo "=== Verifying Installation ==="

echo "Tools (dynamic scan):"
if [ -d "$BIN_DIR" ]; then
    for tool in "$BIN_DIR"/*; do
        if [ -x "$tool" ]; then
            tool_name=$(basename "$tool")
            case "$tool_name" in
                zsh|vim|vi)
                    continue
                    ;;
            esac
            if [ "$tool_name" = "iStyle" ]; then
                version=$("$tool" --help 2>/dev/null | head -1 || echo "OK")
            else
                version=$("$tool" --version 2>/dev/null | head -1 || echo "OK")
            fi
            echo "${tool_name}: ${version}"
        fi
    done
else
    echo "bin dir not found: ${BIN_DIR}" >&2
    exit 1
fi

if [ -x "${BIN_DIR}/zsh" ]; then
    echo "zsh: $("${BIN_DIR}/zsh" --version 2>/dev/null | head -1 || echo "OK")"
else
    echo "zsh: NOT FOUND" >&2
    exit 1
fi

if [ -x "${VIM_BIN_DIR}/vim" ]; then
    echo "vim: $("${VIM_BIN_DIR}/vim" --version 2>/dev/null | head -1 || echo "OK")"
elif [ -x "${BIN_DIR}/vim" ]; then
    echo "vim: $("${BIN_DIR}/vim" --version 2>/dev/null | head -1 || echo "OK")"
else
    echo "vim: NOT FOUND" >&2
    exit 1
fi

echo "=== Installation Verified ==="
