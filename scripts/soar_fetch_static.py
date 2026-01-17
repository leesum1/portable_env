#!/usr/bin/env python3
"""
Reimplementation of scripts/soar_fetch_static.sh in Python.

Usage: soar_fetch_static.py <owner/repo> --dest <dir> [--arch <x86_64|arm64>]

This script relies on the `soar` CLI (with `dl` subcommand) installed and in PATH.
It prefers GitHub release tar.xz/.tar.gz artifacts matching musl + arch; falls back to `soar` repository package.
"""

from __future__ import annotations
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def detect_arch(provided: str | None) -> str:
    if provided:
        a = provided.lower()
        if a in ("x86_64", "amd64"):
            return "x86_64"
        if a in ("arm64", "aarch64"):
            return "arm64"
        die(f"Unsupported --arch: {provided}. Use x86_64 or arm64.")
    uname = os.uname().machine
    if uname in ("x86_64", "amd64"):
        return "x86_64"
    if uname in ("aarch64", "arm64"):
        return "arm64"
    die(f"Unable to detect architecture from uname -m ({uname}). Please pass --arch <x86_64|arm64>.")


def build_regex(arch: str) -> str:
    if arch == "x86_64":
        return r'(?i).*(?:x86[_-]?64|amd64).*(?:unknown[-_.]linux[-_.]musl|linux[-_.]musl).*(?:\.tar\.gz|\.tar\.xz)$'
    return r'(?i).*(?:aarch64|arm64).*(?:unknown[-_.]linux[-_.]musl|linux[-_.]musl).*(?:\.tar\.gz|\.tar\.xz)$'


def find_extracted_files(dirpath: Path) -> list[Path]:
    paths = []
    for p in dirpath.rglob("*"):
        if p.is_file():
            paths.append(p)
    return paths


def is_elf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            header = f.read(4)
        return header.startswith(b"\x7fELF")
    except Exception:
        return False


def has_shebang(path: Path) -> bool:
    try:
        with path.open("r", errors="ignore") as f:
            first = f.readline()
        return first.startswith("#!")
    except Exception:
        return False


def attempt_download_github(repo: str, regex: str, dest: Path, dl_cmd: str) -> bool:
    tmpd = Path(tempfile.mkdtemp(prefix="soar_dl_"))
    try:
        print(f"[soar_fetch] attempting GitHub download for {repo} with regex {regex}", file=sys.stderr)
        cmd = [dl_cmd, "dl", "-y", "--regex", regex, "--github", repo, "--extract", "--extract-dir", str(tmpd), "-o", str(tmpd)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            return False
        # Check extracted files
        files = find_extracted_files(tmpd)
        if not files:
            return False
        # Copy files into dest (preserve name layout by flattening top-level contents)
        for f in files:
            rel = f.relative_to(tmpd)
            target = dest.joinpath(rel.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(f, target)
            except Exception:
                try:
                    shutil.copy(f, target)
                except Exception:
                    pass
            # Ensure executability for ELF or shebang
            try:
                if is_elf(target) or has_shebang(target):
                    target.chmod(target.stat().st_mode | 0o111)
            except Exception:
                pass
        print(f"[soar_fetch] GitHub download placed {len(files)} file(s) into {dest}", file=sys.stderr)
        return True
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


def attempt_download_soar(pkg: str, dest: Path, dl_cmd: str) -> bool:
    print(f"[soar_fetch] attempting Soar repository download for {pkg}", file=sys.stderr)
    try:
        proc = subprocess.run([dl_cmd, "dl", pkg, "-y"], cwd=str(dest), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError:
        die("the 'soar' CLI is required but not found in PATH. Please install it.")
    out = proc.stdout or ""
    if proc.returncode != 0:
        print(out, file=sys.stderr)
        return False
    # Some versions print an [ERROR] line but exit 0
    if re.search(r"\[ERROR\]|Invalid download resource", out):
        print(out, file=sys.stderr)
        return False
    # Mark extracted/copied files as executable if ELF/shebang
    for p in dest.iterdir():
        if p.is_file():
            try:
                if is_elf(p) or has_shebang(p):
                    p.chmod(p.stat().st_mode | 0o111)
            except Exception:
                pass
    print(out, file=sys.stderr)
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download musl static tar releases using soar (Python port)")
    p.add_argument("repo", help="owner/repo")
    p.add_argument("--dest", required=True, help="Destination directory to copy extracted files into")
    p.add_argument("--arch", required=False, help="Target architecture: x86_64 or arm64")
    args = p.parse_args(argv)

    repo = args.repo
    if "/" not in repo:
        die("repo must be in owner/repo format")
    dest = Path(args.dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    arch = detect_arch(args.arch)
    regex = build_regex(arch)

    dl_cmd = shutil.which("soar")
    if not dl_cmd:
        die("the 'soar' CLI (with 'dl' subcommand) is required but not found in PATH. Please install it.")

    print(f"Trying GitHub repo: {repo} (arch: {arch})", file=sys.stderr)
    ok = attempt_download_github(repo, regex, dest, dl_cmd)
    if not ok:
        print(f"Trying Soar repository package: {repo}", file=sys.stderr)
        ok = attempt_download_soar(repo, dest, dl_cmd)
        if not ok:
            die("All attempts failed.")
    print(f"Downloaded and extracted into: {dest}")
    print(f"Install complete. Files to: {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
