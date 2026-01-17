#!/usr/bin/env python3
"""
Download a linux-musl tar archive (x86_64 or arm64) from GitHub Releases via soar,
extract it, and copy the extracted files into the specified destination directory.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from platform import machine


def print_help():
    """Print help message."""
    help_text = """Usage: soar_fetch_static.py <owner/repo> --dest <dir> [--arch <x86_64|arm64>]

Downloads a tar archive (x86_64 or arm64) from GitHub Releases via `soar`/`soar-dl`,
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
  - Fallback 1: Try pkgforge/soar repository (no filtering).
  - Fallback 2: Generic download from GitHub (any arch-matching binary, no musl requirement).
  - All extracted files are copied into the destination dir; ELF files get executable bit set.

Examples:
  ./scripts/soar_fetch_static.py Gaurav-Gosain/tuios --dest ./bin"""
    print(help_text)


def die(msg: str):
    """Print error message and exit with code 1."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def detect_arch() -> str:
    """Auto-detect architecture from uname -m."""
    machine_type = machine()
    if machine_type in ("x86_64", "amd64"):
        return "x86_64"
    elif machine_type in ("aarch64", "arm64"):
        return "arm64"
    else:
        die(f"Unable to detect architecture from uname -m ({machine_type}). "
            f"Please pass --arch <x86_64|arm64>.")


def validate_arch(arch: str) -> str:
    """Validate and normalize architecture."""
    if arch in ("x86_64", "amd64"):
        return "x86_64"
    elif arch in ("arm64", "aarch64"):
        return "arm64"
    else:
        die(f"Unsupported --arch: {arch}. Use x86_64 or arm64.")


def get_regex_list(arch: str) -> list:
    """Get list of regex patterns to try for tar archives (musl variants).
    Tries multiple patterns from most specific to more general.
    """
    if arch == "x86_64":
        return [
            # Exact patterns
            r"(?i).*x86[_-]?64.*musl.*\.tar\.(?:gz|xz)$",
            r"(?i).*amd64.*musl.*\.tar\.(?:gz|xz)$",
            # Variations
            r"(?i).*x86.*musl.*\.tar\.(?:gz|xz)$",
            r"(?i).*64.*musl.*\.tar\.(?:gz|xz)$",
            r"(?i).*musl.*x86.*\.tar\.(?:gz|xz)$",
        ]
    else:
        return [
            # Exact patterns
            r"(?i).*aarch64.*musl.*\.tar\.(?:gz|xz)$",
            r"(?i).*arm64.*musl.*\.tar\.(?:gz|xz)$",
            # Variations
            r"(?i).*arm.*musl.*\.tar\.(?:gz|xz)$",
            r"(?i).*aarch.*musl.*\.tar\.(?:gz|xz)$",
            r"(?i).*musl.*arm.*\.tar\.(?:gz|xz)$",
        ]


def get_generic_regex_list(arch: str) -> list:
    """Get list of regex patterns to try for tar archives (any linux variant).
    Tries multiple patterns from most specific to more general.
    """
    if arch == "x86_64":
        return [
            # Most specific: x86_64/amd64 with linux
            r"(?i).*x86[_-]?64.*linux.*\.tar\.(?:gz|xz)$",
            r"(?i).*amd64.*linux.*\.tar\.(?:gz|xz)$",
            # Variations
            r"(?i).*x86.*linux.*\.tar\.(?:gz|xz)$",
            r"(?i).*linux.*x86[_-]?64.*\.tar\.(?:gz|xz)$",
            r"(?i).*linux.*amd64.*\.tar\.(?:gz|xz)$",
            # Very general: any x86_64 archive
            r"(?i).*x86[_-]?64.*\.tar\.(?:gz|xz)$",
            r"(?i).*amd64.*\.tar\.(?:gz|xz)$",
        ]
    else:
        return [
            # Most specific: arm64/aarch64 with linux
            r"(?i).*aarch64.*linux.*\.tar\.(?:gz|xz)$",
            r"(?i).*arm64.*linux.*\.tar\.(?:gz|xz)$",
            # Variations
            r"(?i).*arm.*linux.*\.tar\.(?:gz|xz)$",
            r"(?i).*aarch.*linux.*\.tar\.(?:gz|xz)$",
            r"(?i).*linux.*aarch64.*\.tar\.(?:gz|xz)$",
            r"(?i).*linux.*arm64.*\.tar\.(?:gz|xz)$",
            # Very general: any arm archive
            r"(?i).*aarch64.*\.tar\.(?:gz|xz)$",
            r"(?i).*arm64.*\.tar\.(?:gz|xz)$",
        ]


def get_regex(arch: str) -> str:
    """Get primary regex pattern for tar archives based on architecture (musl only)."""
    return get_regex_list(arch)[0]


def get_generic_regex(arch: str) -> str:
    """Get primary regex pattern for tar archives based on architecture (any linux variant)."""
    return get_generic_regex_list(arch)[0]


def check_soar_installed() -> str:
    """Check if soar is installed and return the path."""
    result = shutil.which("soar")
    if not result:
        die("the 'soar' CLI (with 'dl' subcommand) is required but not found in PATH. Please install it.")
    return result


def attempt_download_github(repo: str, regex: str, dest_dir: str) -> bool:
    """
    Attempt to download from GitHub with --github flag and filter by the provided regex.
    Returns True if successful, False otherwise.
    """
    soar_cmd = check_soar_installed()
    
    with tempfile.TemporaryDirectory() as tmpd:
        cmd = [
            soar_cmd, "dl",
            "-y",
            "--regex", regex,
            "--github", repo,
            "--extract",
            "--extract-dir", dest_dir,
            "-o", tmpd
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.stdout:
                print(result.stdout, file=sys.stderr, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            
            # Check if any files were extracted
            tmp_path = Path(tmpd)
            if any(tmp_path.iterdir()):
                return True
            else:
                print(f"[GitHub] No files extracted for {repo}", file=sys.stderr)
        except Exception as e:
            print(f"[GitHub] Exception: {e}", file=sys.stderr)
    
    return False


def attempt_download_github_multi(repo: str, regexes: list, dest_dir: str) -> bool:
    """
    Attempt to download from GitHub using multiple regex patterns.
    Tries each regex in order until one succeeds.
    Returns True if any attempt succeeds, False if all fail.
    """
    for i, regex in enumerate(regexes, 1):
        print(f"[GitHub] Attempt {i}/{len(regexes)} with regex: {regex}", file=sys.stderr)
        if attempt_download_github(repo, regex, dest_dir):
            return True
    return False


def attempt_download_soar(pkg: str, dest_dir: str) -> bool:
    """
    Attempt to download from Soar repository (without --github, no arch filtering).
    Returns True if successful, False otherwise.
    """
    soar_cmd = check_soar_installed()
    
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(dest_dir)
        
        cmd = [soar_cmd, "dl", pkg, "-y"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print output to stderr
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="")
        
        # Check for error indicators
        output = result.stdout + result.stderr
        if result.returncode != 0 or "[ERROR]" in output or "Invalid download resource" in output:
            return False
        
        return True
    except Exception as e:
        print(f"Exception during download: {e}", file=sys.stderr)
        return False
    finally:
        import os
        os.chdir(original_cwd)


def attempt_download_generic(repo: str, regex: str, dest_dir: str) -> bool:
    """
    Attempt generic download from GitHub (any arch-matching binary, no musl requirement).
    Returns True if successful, False otherwise.
    """
    soar_cmd = check_soar_installed()
    
    with tempfile.TemporaryDirectory() as tmpd:
        cmd = [
            soar_cmd, "dl",
            "-y",
            "--regex", regex,
            "--github", repo,
            "--extract",
            "--extract-dir", dest_dir,
            "-o", tmpd
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.stdout:
                print(result.stdout, file=sys.stderr, end="")
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="")
            
            # Check if any files were extracted
            tmp_path = Path(tmpd)
            if any(tmp_path.iterdir()):
                return True
            else:
                print(f"[Generic] No files extracted for {repo}", file=sys.stderr)
        except Exception as e:
            print(f"[Generic] Exception: {e}", file=sys.stderr)
    
    return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="soar_fetch_static.py",
        description="Download and extract a linux-musl tar archive from GitHub Releases via soar",
        add_help=False  # We'll handle help manually to match the bash version
    )
    
    parser.add_argument("repo", nargs="?", help="GitHub repository (e.g. Gaurav-Gosain/tuios)")
    parser.add_argument("--dest", required=False, help="Destination directory to copy extracted files into")
    parser.add_argument("--arch", required=False, help="Target architecture: x86_64 or arm64")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help and exit")
    
    args = parser.parse_args()
    
    if args.help or not args.repo:
        print_help()
        sys.exit(0 if args.help else 1)
    
    if not args.dest:
        die("--dest <dir> is required")
    
    # Validate repo format
    if "/" not in args.repo:
        die("repo must be in owner/repo format")
    
    return args


def main():
    """Main function."""
    args = parse_args()
    
    repo = args.repo
    dest = args.dest
    arch = args.arch if args.arch else detect_arch()
    arch = validate_arch(arch)
    
    # Create destination directory
    dest_path = Path(dest)
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        die(f"failed to create dest dir: {dest} ({e})")
    
    # Try GitHub first (musl only)
    print(f"Trying GitHub repo: {repo} (arch: {arch}, musl)")
    regexes = get_regex_list(arch)
    if attempt_download_github_multi(repo, regexes, dest):
        print(f"Install complete. Files to: {dest}")
        sys.exit(0)
    
    # Fallback 1: Try Soar repository
    print(f"Trying Soar repository package: {repo}")
    if attempt_download_soar(repo, dest):
        print(f"Install complete. Files to: {dest}")
        sys.exit(0)
    
    # Fallback 2: Generic GitHub download (any arch-matching binary)
    print(f"Trying generic GitHub download: {repo} (arch: {arch}, any linux)")
    generic_regexes = get_generic_regex_list(arch)
    if attempt_download_github_multi(repo, generic_regexes, dest):
        print(f"Install complete. Files to: {dest}")
        sys.exit(0)
    
    die("All attempts failed.")


if __name__ == "__main__":
    main()
