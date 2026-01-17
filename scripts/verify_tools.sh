#!/usr/bin/env bash
set -euo pipefail

RED_ENV_HOME="${RED_ENV_HOME:-$HOME/.red_env}"
BIN_DIR="${RED_ENV_HOME}/bin"
VIM_BIN_DIR="${RED_ENV_HOME}/vim/bin"
EXCEPTIONS_FILE="${RED_ENV_HOME}/DYNAMIC_EXCEPTIONS.txt"
SKIP_BIN=()
# Load documented dynamic exceptions (format: <binary>:<version>:GNU_DYNAMIC)
if [ -f "${EXCEPTIONS_FILE}" ]; then
    while IFS= read -r line; do
        bn=$(echo "${line}" | cut -d: -f1)
        bn=$(basename "${bn}")
        SKIP_BIN+=("${bn}")
    done < "${EXCEPTIONS_FILE}"
fi

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
    # If vim is documented as a missing static exception, treat as documented and continue
    if [ -f "${EXCEPTIONS_FILE}" ] && grep -qE '^vim:.*:MISSING_STATIC' "${EXCEPTIONS_FILE}"; then
        echo "vim: MISSING_STATIC (documented)"
    else
        echo "vim: NOT FOUND" >&2
        exit 1
    fi
fi

echo "=== Installation Verified ==="

# -----------------------------------------------------------------------------
# Static linking checks
# -----------------------------------------------------------------------------
NON_STATIC=()
check_static() {
    bin_path="$1"
    if [ ! -f "$bin_path" ]; then
        return 0
    fi
    bn=$(basename "$bin_path")
    # If documented dynamic exception, skip static check
    for skip in "${SKIP_BIN[@]}"; do
        if [ "$skip" = "$bn" ]; then
            echo "Note: $bn is a documented GNU-dynamic exception, skipping static check" >&2
            return 0
        fi
    done

    # Use file and ldd to detect dynamic linking
    if ! command -v file >/dev/null 2>&1 || ! command -v ldd >/dev/null 2>&1; then
        echo "⚠️  'file' or 'ldd' not available; cannot perform static check" >&2
        return 0
    fi
    file_out=$(file -b "$bin_path" || true)
    if echo "$file_out" | grep -qiE "statically linked|statically-linked|statically linked"; then
        return 0
    fi
    ldd_out=$(ldd "$bin_path" 2>&1 || true)
    if echo "$ldd_out" | grep -qi "not a dynamic executable"; then
        return 0
    fi
    # If ldd prints library dependencies, it's dynamic
    if echo "$ldd_out" | grep -qi "=>"; then
        NON_STATIC+=("$bin_path")
    fi
}

# List of binaries to check (common culprits)
CANDIDATES=("$BIN_DIR/jq" "$BIN_DIR/yq" "$BIN_DIR/shfmt" "$BIN_DIR/glow" "$BIN_DIR/duf" "$VIM_BIN_DIR/vim" "$BIN_DIR/vim")
for b in "${CANDIDATES[@]}"; do
    check_static "$b"
done

if [ ${#NON_STATIC[@]} -ne 0 ]; then
    echo "\n⚠️  Non-static binaries detected:" >&2
    for nb in "${NON_STATIC[@]}"; do
        echo " - $nb" >&2
        file "$nb" || true
        ldd "$nb" || true
    done
    echo "\nPlease replace them with statically linked alternatives or adjust the build." >&2
    exit 2
else
    echo "\n✅ All inspected binaries appear to be statically linked (or checks not applicable)."
fi

# Print documented dynamic exceptions for auditing
if [ -f "${EXCEPTIONS_FILE}" ]; then
    echo "\n⚠️ Documented GNU-dynamic exceptions (from ${EXCEPTIONS_FILE}):"
    cat "${EXCEPTIONS_FILE}"
fi
