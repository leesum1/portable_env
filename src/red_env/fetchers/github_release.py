from __future__ import annotations

import json
import os
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from red_env.manifest.models import PackageSpec

_NETWORK_TIMEOUT = 30


def select_asset_url(release_payload: dict, regex: str) -> str:
    pattern = re.compile(regex)
    for asset in release_payload.get("assets", []):
        if pattern.search(asset["name"]):
            return asset["browser_download_url"]
    raise ValueError(f"no asset matched regex: {regex}")


def download_package_asset(package: PackageSpec, arch: str, destination: Path, manifest_root: Path | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if package.source.type == "local_file":
        if not package.source.file_path:
            raise ValueError(f"local_file source requires file_path, missing in package {package.id}")
        file_path_template = package.source.file_path
        # Normalize architecture for local file names
        arch_mapping = {"arm64": "aarch64", "x86_64": "x86_64"}
        resolved_arch = arch_mapping.get(arch, arch)
        file_path = file_path_template.replace("${ARCH}", resolved_arch)
        local_path = manifest_root / file_path if manifest_root else Path(file_path)
        if not local_path.exists():
            raise FileNotFoundError(f"local file not found: {local_path}")
        # Copy to destination, renaming to include arch for clarity
        dest_name = destination.name.replace("${ARCH}", arch)
        final_dest = destination.parent / dest_name
        shutil.copy2(local_path, final_dest)
        return final_dest

    if package.source.type == "github_release":
        # archive_tree strategy doesn't need asset URL matching - just find the right asset
        if package.strategy.type == "archive_tree":
            api_url = f"https://api.github.com/repos/{package.source.repo}/releases/latest"
            release_payload = _fetch_json(api_url)
            pkg_id = package.id.lower()
            # Find the asset that starts with "pkgid-<arch>..." pattern
            arch_variants = ["x86_64", "amd64"] if arch == "x86_64" else ["aarch64", "arm64"]
            for asset in release_payload.get("assets", []):
                name = asset["name"].lower()
                if not name.endswith((".tar.gz", ".tgz", ".zip")):
                    continue
                if "linux" not in name:
                    continue
                # Check if name starts with "pkgid-" followed by arch
                for variant in arch_variants:
                    prefix = f"{pkg_id}-{variant}"
                    if name.startswith(prefix):
                        _download_to_path(asset["browser_download_url"], destination)
                        return destination
            # Fallback: find any asset with arch + linux in the name
            for asset in release_payload.get("assets", []):
                name = asset["name"].lower()
                if not name.endswith((".tar.gz", ".tgz", ".zip")):
                    continue
                if "linux" not in name:
                    continue
                if any(v in name for v in arch_variants):
                    _download_to_path(asset["browser_download_url"], destination)
                    return destination
            raise ValueError(f"no suitable asset found for {package.id} on {arch}")

        try:
            asset_match = package.strategy.match[arch]
        except KeyError as exc:
            raise ValueError(f"unsupported architecture: {arch}") from exc

        api_url = f"https://api.github.com/repos/{package.source.repo}/releases/latest"
        release_payload = _fetch_json(api_url)
        asset_url = select_asset_url(release_payload, asset_match)
        _download_to_path(asset_url, destination)
        return destination

    if package.source.type == "github_archive":
        ref = package.source.ref or "master"
        _download_github_archive(package.source.repo, ref, destination)
        return destination

    raise ValueError(f"unsupported source type: {package.source.type}")


def _download_github_archive(repo: str, ref: str, destination: Path) -> None:
    if ref.startswith("refs/"):
        archive_urls = [f"https://github.com/{repo}/archive/{ref}.tar.gz"]
    else:
        archive_urls = [
            f"https://github.com/{repo}/archive/refs/heads/{ref}.tar.gz",
            f"https://github.com/{repo}/archive/refs/tags/{ref}.tar.gz",
        ]

    last_not_found: urllib.error.HTTPError | None = None
    for archive_url in archive_urls:
        try:
            _download_to_path(archive_url, destination)
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
            last_not_found = exc

    if last_not_found is not None:
        raise last_not_found


def _fetch_json(url: str) -> dict:
    request = _github_request(url)
    try:
        with urllib.request.urlopen(request, timeout=_NETWORK_TIMEOUT) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if _is_rate_limited(exc):
            remaining = _header_value(exc, "X-RateLimit-Remaining")
            reset = _header_value(exc, "X-RateLimit-Reset")
            token_used = "yes" if _github_token() else "no"
            raise RuntimeError(
                "GitHub API rate limit exceeded while requesting "
                f"{url} (status={exc.code}, remaining={remaining}, reset={reset}, auth_token={token_used})"
            ) from exc
        raise


def _download_to_path(url: str, destination: Path) -> None:
    request = _github_request(url)
    with urllib.request.urlopen(request, timeout=_NETWORK_TIMEOUT) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _github_request(url: str) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "red-env/0.1.0",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _github_token() -> str | None:
    return os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")


def _header_value(error: urllib.error.HTTPError, header: str) -> str:
    if error.headers is None:
        return "unknown"
    return str(error.headers.get(header, "unknown"))


def _is_rate_limited(error: urllib.error.HTTPError) -> bool:
    if error.code == 429:
        return True
    if error.code != 403:
        return False
    if _header_value(error, "X-RateLimit-Remaining") == "0":
        return True
    return "rate limit" in str(error).lower()
