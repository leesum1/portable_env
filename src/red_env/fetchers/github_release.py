from __future__ import annotations

import json
import re
import shutil
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
    with urllib.request.urlopen(url, timeout=_NETWORK_TIMEOUT) as response:
        return json.load(response)


def _download_to_path(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=_NETWORK_TIMEOUT) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)
