from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from red_env.manifest.models import PackageSpec


def select_asset_url(release_payload: dict, regex: str) -> str:
    pattern = re.compile(regex)
    for asset in release_payload.get("assets", []):
        if pattern.match(asset["name"]):
            return asset["browser_download_url"]
    raise ValueError(f"no asset matched regex: {regex}")


def download_package_asset(package: PackageSpec, arch: str, destination: Path) -> Path:
    api_url = f"https://api.github.com/repos/{package.source.repo}/releases/latest"
    with urllib.request.urlopen(api_url) as response:
        release_payload = json.load(response)
    asset_url = select_asset_url(release_payload, package.strategy.match[arch])
    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(asset_url, destination)
    return destination
