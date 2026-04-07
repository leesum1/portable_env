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


def download_package_asset(package: PackageSpec, arch: str, destination: Path) -> Path:
    try:
        asset_match = package.strategy.match[arch]
    except KeyError as exc:
        raise ValueError(f"unsupported architecture: {arch}") from exc

    api_url = f"https://api.github.com/repos/{package.source.repo}/releases/latest"
    release_payload = _fetch_json(api_url)
    asset_url = select_asset_url(release_payload, asset_match)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _download_to_path(asset_url, destination)
    return destination


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
