#!/usr/bin/env bash
set -euo pipefail

print_help() {
  cat <<'USAGE'
Usage: download_soar.sh <owner/repo> --dest <dir> [--arch <x86_64|arm64>]

Downloads a linux-musl tar archive (x86_64 or arm64) from GitHub Releases via `soar`/`soar-dl`,
extracts it, and copies the extracted files into the specified destination directory.

Positional:
  owner/repo       GitHub repository (e.g. Gaurav-Gosain/tuios)

Options:
  --dest DIR       Destination directory to copy extracted files into (required)
  --arch ARCH      Target architecture: x86_64 or arm64 (optional; auto-detected if omitted)
  -h, --help       Show this help and exit

Behavior:
  - Prefer GitHub release assets matching a tar archive for the selected arch (only .tar.gz/.tar.xz).
  - Use `-y` (non-interactive) and `--extract --extract-dir` so that the archive is automatically extracted.
  - If no matching GitHub release asset is found, fallback to pkgforge/soar.
  - All extracted files are copied into the destination dir; ELF files get executable bit set.

Examples:
  ./scripts/download_soar.sh Gaurav-Gosain/tuios --dest ./bin
USAGE
}

die() { echo "ERROR: $*" >&2; exit 1; }

# Parse arguments
if [ $# -eq 0 ]; then print_help; exit 1; fi

REPO=""
ARCH=""
DEST=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dest)
      DEST="$2"; shift 2;;
    --arch)
      ARCH="$2"; shift 2;;
    -h|--help)
      print_help; exit 0;;
    --*)
      die "Unknown option: $1";;
    *)
      if [ -z "$REPO" ]; then REPO="$1"; shift; else die "Unexpected arg: $1"; fi;;
  esac
done

[ -n "$REPO" ] || die "missing owner/repo (first positional argument)"
[ -n "$DEST" ] || die "--dest <dir> is required"

# Validate repo format
if ! echo "$REPO" | grep -q '/'; then die "repo must be in owner/repo format"; fi

# Detect arch if not provided
if [ -z "$ARCH" ]; then
  uname_m=$(uname -m || true)
  case "$uname_m" in
    x86_64|amd64) ARCH="x86_64";;
    aarch64|arm64) ARCH="arm64";;
    *) die "Unable to detect architecture from uname -m ($uname_m). Please pass --arch <x86_64|arm64>.";;
  esac
else
  case "$ARCH" in
    x86_64|amd64) ARCH="x86_64";;
    arm64|aarch64) ARCH="arm64";;
    *) die "Unsupported --arch: $ARCH. Use x86_64 or arm64.";;
  esac
fi

# Prepare regex for tar archives only (tar.gz or tar.xz)
if [ "$ARCH" = "x86_64" ]; then
  REGEX='(?i).*(?:x86[_-]?64|amd64).*(?:unknown[-_.]linux[-_.]musl|linux[-_.]musl).*(?:\.tar\.gz|\.tar\.xz)$'
else
  REGEX='(?i).*(?:aarch64|arm64).*(?:unknown[-_.]linux[-_.]musl|linux[-_.]musl).*(?:\.tar\.gz|\.tar\.xz)$'
fi

# Find downloader (require `soar` with 'dl' subcommand)
if command -v soar >/dev/null 2>&1; then
  DL_CMD="soar"
else
  die "the 'soar' CLI (with 'dl' subcommand) is required but not found in PATH. Please install it."
fi

mkdir -p "$DEST" || die "failed to create dest dir: $DEST"

# Function to download from GitHub with --github flag and filter by arch/musl regex
attempt_download_github() {
  local repo="$1"; shift
  local tmpd; tmpd=$(mktemp -d)
  
  # Use --github flag with --regex to filter tar musl archives for the specified arch
  "$DL_CMD" dl -y --regex "$REGEX" --github "$repo" --extract --extract-dir "$DEST" -o "$tmpd" >&2 || true

  # if extracted files exist, return path via echo and status 0
  if [ -n "$(ls -A "$tmpd" 2>/dev/null | head -n1 || true)" ]; then
    rm -rf "$tmpd" 2>/dev/null || true
    return 0
  else
    rm -rf "$tmpd" 2>/dev/null || true
    return 1
  fi
}

# Function to download from Soar repository (without --github, no arch filtering)
attempt_download_soar() {
  local pkg="$1"; shift
  local out
  # Ensure we are in the dest dir so any downloaded/extracted files end up there
  cd "$DEST" || return 1

  # Capture both stdout and stderr to inspect for error lines.
  out=$("$DL_CMD" dl "$pkg" -y 2>&1) || {
    # If the command exits non-zero, print its output and fail.
    printf '%s\n' "$out" >&2
    return 1
  }

  # Some versions of 'soar dl' may print an [ERROR] line but still exit 0.
  # Detect such a line (or other known failure messages) and treat it as a failure.
  if printf '%s\n' "$out" | grep -q -E '\[ERROR\]|Invalid download resource'; then
    printf '%s\n' "$out" >&2
    return 1
  fi

  # On success, print any output (to stderr to be consistent with other messages)
  printf '%s\n' "$out" >&2
  return 0
}

# Try primary repo from GitHub, fallback to Soar repository
echo "Trying GitHub repo: $REPO (arch: $ARCH)"
from_github=true
tmpd=$(attempt_download_github "$REPO") || {
  echo "Trying Soar repository package: $REPO"
  from_github=false
  tmpd=$(attempt_download_soar "$REPO") || die "All attempts failed."
}
echo "Downloaded and extracted into: $tmpd"


echo "Install complete. Files to: $DEST"
exit 0
