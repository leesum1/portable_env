#!/usr/bin/env python3
"""
Batch fetch multiple packages using soar_fetch_static.py and organize them.

This script:
1. Maps TARGETARCH to soar_fetch_static.py arch values (x86_64|arm64)
2. Downloads multiple packages in parallel or sequentially
3. Detects ELF binaries and shebang scripts
4. Organizes files into the output directory
5. Sets executable permissions
6. Tracks and reports failures
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple


def die(msg: str):
    """Print error message and exit with code 1."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def map_arch(target_arch: str) -> str:
    """Map TARGETARCH to soar_fetch_static.py compatible arch."""
    if target_arch == "arm64":
        return "arm64"
    else:
        return "x86_64"


def is_elf_binary(file_path: Path) -> bool:
    """Check if a file is an ELF binary using file command."""
    try:
        result = subprocess.run(
            ["file", "-L", str(file_path)],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "ELF" in result.stdout
    except Exception:
        return False


def is_shebang_script(file_path: Path) -> bool:
    """Check if a file is a shebang script."""
    try:
        with open(file_path, "rb") as f:
            first_bytes = f.read(2)
            return first_bytes == b"#!"
    except Exception:
        return False


def fetch_package(
    repo: str,
    arch: str,
    temp_dir: Path,
    soar_script: Path,
) -> Tuple[bool, Path]:
    """
    Fetch a single package using soar_fetch_static.py.
    
    Returns:
        Tuple of (success: bool, temp_directory: Path)
    """
    temp_fetch_dir = temp_dir / f"fetch_{repo.replace('/', '_')}"
    temp_fetch_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        str(soar_script),
        repo,
        "--arch", arch,
        "--dest", str(temp_fetch_dir),
    ]
    
    print(f"[soar_fetch] Running: {' '.join(cmd)}", file=sys.stderr)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        # Always print stdout/stderr
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        
        if result.returncode == 0:
            print(f"[soar_fetch] {repo} downloaded to {temp_fetch_dir}")
            file_count = sum(1 for _ in temp_fetch_dir.rglob("*") if _.is_file())
            print(f"[soar_fetch] {repo} file count: {file_count}")
            return True, temp_fetch_dir
        else:
            print(f"[soar_fetch] {repo} failed with exit code {result.returncode}")
            return False, temp_fetch_dir
    except subprocess.TimeoutExpired:
        print(f"[soar_fetch] {repo} timed out (300s)")
        return False, temp_fetch_dir
    except Exception as e:
        print(f"[soar_fetch] {repo} error: {e}")
        return False, temp_fetch_dir


def process_downloaded_files(
    base_temp_dir: Path,
    output_bin_dir: Path,
) -> List[str]:
    """
    Process all downloaded files:
    - Detect ELF binaries and shebang scripts
    - Copy/move them to output_bin_dir
    - Set executable permissions
    
    Returns:
        List of filenames that were processed
    """
    processed = []
    
    # Find all files in temp directory
    for file_path in base_temp_dir.rglob("*"):
        if not file_path.is_file():
            continue
        
        base_name = file_path.name
        dest_path = output_bin_dir / base_name
        
        # Skip if file already exists in destination
        if dest_path.exists():
            print(f"[soar_fetch] skip existing {base_name}")
            continue
        
        # Check if it's an ELF binary
        if is_elf_binary(file_path):
            try:
                shutil.copy2(str(file_path), str(dest_path))
                print(f"[soar_fetch] copied binary {base_name}")
                processed.append(base_name)
                continue
            except Exception:
                pass
        
        # Check if it's a shebang script
        if is_shebang_script(file_path):
            try:
                shutil.copy2(str(file_path), str(dest_path))
                print(f"[soar_fetch] copied script {base_name}")
                processed.append(base_name)
                continue
            except Exception:
                pass
        
        print(f"[soar_fetch] ignored {base_name}")
    
    return processed


def set_executable_permissions(bin_dir: Path):
    """Set executable permissions on all files in the bin directory."""
    try:
        for file_path in bin_dir.rglob("*"):
            if file_path.is_file():
                # Add executable permission for user, group, and others
                current_mode = file_path.stat().st_mode
                new_mode = current_mode | 0o111  # Add a+x
                file_path.chmod(new_mode)
    except Exception as e:
        print(f"[soar_fetch] warning: failed to set executable permissions: {e}", file=sys.stderr)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="batch_soar_fetch.py",
        description="Batch fetch multiple packages using soar_fetch_static.py",
    )
    
    parser.add_argument(
        "packages",
        nargs="?",
        help="Space-separated list of packages, file path with packages (one per line), or JSON file with packages array",
    )
    parser.add_argument(
        "--target-arch",
        default="x86_64",
        help="Target architecture: x86_64 or arm64 (default: x86_64)",
    )
    parser.add_argument(
        "--output-dir",
        default="/build/output",
        help="Output directory for binaries (default: /build/output)",
    )
    parser.add_argument(
        "--soar-script",
        help="Path to soar_fetch_static.py (auto-detected if omitted)",
    )
    
    args = parser.parse_args()
    
    if not args.packages:
        die("packages argument is required")
    
    return args


def get_soar_script() -> Path:
    """Find soar_fetch_static.py."""
    # Try in the same directory as this script
    script_dir = Path(__file__).parent
    soar_script = script_dir / "soar_fetch_static.py"
    
    if soar_script.exists():
        return soar_script
    
    # Try common locations
    common_paths = [
        Path("/usr/local/bin/soar_fetch_static.py"),
        Path("./scripts/soar_fetch_static.py"),
    ]
    
    for path in common_paths:
        if path.exists():
            return path
    
    die("soar_fetch_static.py not found. Please provide --soar-script argument.")


def parse_packages(packages_arg: str) -> List[str]:
    """Parse packages from command line argument, text file, or JSON file.
    
    Supports:
    - Space-separated string: "pkg1 pkg2 pkg3"
    - Text file (one package per line)
    - JSON file with packages array: {"packages": ["pkg1", "pkg2"]}
    """
    packages_path = Path(packages_arg)
    
    # Check if it's a file
    if packages_path.exists() and packages_path.is_file():
        with open(packages_path, "r") as f:
            content = f.read().strip()
        
        # Try to parse as JSON first
        if content.startswith("{") or content.startswith("["):
            try:
                import json
                data = json.loads(content)
                # Support both {"packages": [...]} and [...] formats
                if isinstance(data, dict):
                    packages = data.get("packages", [])
                elif isinstance(data, list):
                    packages = data
                else:
                    die(f"Invalid JSON format in {packages_arg}")
                return [str(p).strip() for p in packages if p]
            except json.JSONDecodeError as e:
                die(f"Failed to parse JSON in {packages_arg}: {e}")
        
        # Otherwise treat as text file (one per line)
        packages = [line.strip() for line in content.split("\n") if line.strip()]
        return packages
    
    # Otherwise treat as space-separated string
    return packages_arg.split()


def main():
    """Main function."""
    args = parse_args()
    
    # Validate and get paths
    soar_script = Path(args.soar_script) if args.soar_script else get_soar_script()
    if not soar_script.exists():
        die(f"soar_fetch_static.py not found at {soar_script}")
    
    output_dir = Path(args.output_dir)
    output_bin_dir = output_dir / "bin"
    
    # Create output directories
    try:
        output_bin_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        die(f"failed to create output dir: {output_bin_dir} ({e})")
    
    # Map architecture
    arch = map_arch(args.target_arch)
    print(f"[soar_fetch] target arch: {args.target_arch} -> {arch}")
    
    # Parse packages
    packages = parse_packages(args.packages)
    if not packages:
        die("no packages specified")
    
    print(f"[soar_fetch] fetching {len(packages)} packages")
    print(f"[soar_fetch] packages: {', '.join(packages[:5])}" + 
          (f" ... and {len(packages) - 5} more" if len(packages) > 5 else ""))
    print(f"[soar_fetch] arch: {arch}", file=sys.stderr)
    print(f"[soar_fetch] output-dir: {output_bin_dir}", file=sys.stderr)
    print(f"[soar_fetch] soar-script: {soar_script}", file=sys.stderr)
    
    # Create temporary directory for all downloads
    with tempfile.TemporaryDirectory() as base_temp:
        base_temp_path = Path(base_temp)
        
        failures = []
        
        # Fetch each package
        for repo in packages:
            print(f"[soar_fetch] fetching {repo} for arch={arch}")
            success, temp_dir = fetch_package(repo, arch, base_temp_path, soar_script)
            if not success:
                failures.append(repo)
        
        # Print total downloaded files
        total_files = sum(1 for _ in base_temp_path.rglob("*") if _.is_file())
        print(f"[soar_fetch] total downloaded files: {total_files}")
        
        # Process downloaded files
        processed = process_downloaded_files(base_temp_path, output_bin_dir)
        print(f"[soar_fetch] processed {len(processed)} files")
        
        # Set executable permissions
        set_executable_permissions(output_bin_dir)
    
    # Write failure log if any
    if failures:
        failed_log = output_dir / "FAILED_FETCHES.txt"
        with open(failed_log, "w") as f:
            f.write("FAILED_FETCHES:" + ",".join(failures) + "\n")
        print("=== FAILED_FETCHES ===")
        print(",".join(failures))
        print(f"[soar_fetch] {len(failures)} package(s) failed to download, but continuing anyway")
    
    # List output directory
    print("=== output bin contents ===")
    if output_bin_dir.exists():
        print(f"Contents of {output_bin_dir}:")
        for item in sorted(output_bin_dir.iterdir()):
            stat_info = item.stat()
            mode = oct(stat_info.st_mode)[-3:]
            size = stat_info.st_size
            print(f"  {mode} {size:10d}  {item.name}")
    
    # Always exit successfully (failures are logged but don't fail the build)
    sys.exit(0)


if __name__ == "__main__":
    main()
