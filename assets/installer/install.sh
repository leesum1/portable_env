#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="${SCRIPT_DIR}/../bundle"
INSTALL_DIR="${HOME}/.red_env"
COMPRESS="${RED_ENV_COMPRESS:-}"

# Parse command line arguments
while [ $# -gt 0 ]; do
  case "$1" in
    --compress) COMPRESS=1; shift ;;
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --help)
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --compress       Compress ELF binaries with UPX after installation"
      echo "  --install-dir DIR  Install to DIR (default: ~/.red_env)"
      echo "  --help             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Use --help for usage information" >&2
      exit 1
      ;;
  esac
done

copy_contents() {
  src="$1"
  dest="$2"
  if [ -d "$src" ]; then
    mkdir -p "$dest"
    cp -R "$src/." "$dest"
  fi
}

# Compress ELF binaries with UPX
compress_binaries() {
  bin_dir="$1"
  if [ ! -d "$bin_dir" ]; then
    return
  fi

  # Check if upx is available
  if ! command -v upx >/dev/null 2>&1; then
    echo "Warning: UPX not found, skipping binary compression" >&2
    return
  fi

  echo "Compressing binaries with UPX..."
  compressed=0
  skipped=0
  for binary in "$bin_dir"/*; do
    if [ ! -f "$binary" ]; then
      continue
    fi
    # Check if it's an ELF binary
    if file "$binary" 2>/dev/null | grep -q "ELF"; then
      original_size=$(wc -c < "$binary")
      if upx -9 -q "$binary" 2>/dev/null; then
        compressed_size=$(wc -c < "$binary")
        savings=$(( (original_size - compressed_size) * 100 / original_size ))
        echo "  $(basename "$binary"): ${original_size} -> ${compressed_size} (-${savings}%)"
        compressed=$((compressed + 1))
      else
        echo "  $(basename "$binary"): compression failed, skipping" >&2
        skipped=$((skipped + 1))
      fi
    fi
  done
  echo "Compressed ${compressed} binaries (${skipped} skipped)"
}

mkdir -p "${INSTALL_DIR}"

# -----------------------------------------------------------------------------
# Install zsh using romkatv/zsh-bin install script
# The zsh-bin tarball is extracted to bundle/zsh-bin/ by the build process
# -----------------------------------------------------------------------------
detect_arch() {
  arch="$(uname -m)"
  case "$arch" in
    x86_64|amd64)  echo "x86_64" ;;
    aarch64|arm64) echo "aarch64" ;;
    *)
      echo "Unsupported architecture: $arch" >&2
      exit 1
      ;;
  esac
}

ARCH="$(detect_arch)"
ZSH_ARCHIVE="${BUNDLE_DIR}/zsh-bin/zsh-5.8-linux.tar.gz"
ZSH_INSTALL_SCRIPT="${BUNDLE_DIR}/zsh-bin/install"

if [ -f "$ZSH_ARCHIVE" ] && [ -f "$ZSH_INSTALL_SCRIPT" ]; then
  echo "Installing zsh 5.8 from romkatv/zsh-bin..."

  # The romkatv/zsh-bin install script needs the tarball and will extract it properly
  # with the relocate script included in the archive
  sh "$ZSH_INSTALL_SCRIPT" -q -d "$INSTALL_DIR" -f "$ZSH_ARCHIVE" -e no

  echo "zsh installed to ${INSTALL_DIR}/bin/zsh"
else
  echo "Warning: zsh-bin archive or install script not found, skipping zsh installation" >&2
  echo "  Expected archive: $ZSH_ARCHIVE" >&2
  echo "  Expected script: $ZSH_INSTALL_SCRIPT" >&2
fi

# -----------------------------------------------------------------------------
# Install user fonts from bundle
# -----------------------------------------------------------------------------
BUNDLE_FONTS="${BUNDLE_DIR}/fonts"

if [ -d "$BUNDLE_FONTS" ]; then
  # Use standard user fonts directory
  USER_FONTS="${HOME}/.local/share/fonts/red_env"
  mkdir -p "$USER_FONTS"

  font_count=0
  for font in "$BUNDLE_FONTS"/*; do
    if [ -f "$font" ]; then
      cp "$font" "$USER_FONTS/"
      font_count=$((font_count + 1))
    fi
  done

  if [ "$font_count" -gt 0 ]; then
    echo "Installed ${font_count} font(s) to ${USER_FONTS}"
    # Update font cache if fc-cache is available
    if command -v fc-cache >/dev/null 2>&1; then
      fc-cache -f "$USER_FONTS" >/dev/null 2>&1 || true
    fi
  fi
fi

# -----------------------------------------------------------------------------
# Install ForceTerm AppImage
# -----------------------------------------------------------------------------
BUNDLE_FORCETERM="${BUNDLE_DIR}/forceterm/forceterm.AppImage"

if [ -f "$BUNDLE_FORCETERM" ]; then
  FORCETERM_DIR="${INSTALL_DIR}/forceterm"
  mkdir -p "$FORCETERM_DIR"
  cp "$BUNDLE_FORCETERM" "$FORCETERM_DIR/forceterm.AppImage"
  chmod +x "$FORCETERM_DIR/forceterm.AppImage"

  # Create symlink in bin for easy access
  mkdir -p "${INSTALL_DIR}/bin"
  ln -sf "$FORCETERM_DIR/forceterm.AppImage" "${INSTALL_DIR}/bin/forceterm"

  echo "Installed ForceTerm AppImage to ${FORCETERM_DIR}"
fi

# -----------------------------------------------------------------------------
# Copy remaining bundle contents (configs, oh-my-zsh, plugins, etc.)
# -----------------------------------------------------------------------------
copy_contents "${SCRIPT_DIR}/../configs" "${INSTALL_DIR}/configs"
for path in "${BUNDLE_DIR}"/*; do
  if [ -e "$path" ]; then
    name="$(basename "$path")"
    # Skip zsh-bin as it was handled above
    if [ "$name" = "zsh-bin" ]; then
      continue
    fi
    copy_contents "$path" "${INSTALL_DIR}/${name}"
  fi
done

# -----------------------------------------------------------------------------
# Optional: compress binaries with UPX
# -----------------------------------------------------------------------------
if [ -n "$COMPRESS" ]; then
  compress_binaries "${INSTALL_DIR}/bin"
fi

echo "Installed red_env into ${INSTALL_DIR}"
