from __future__ import annotations

from pathlib import Path
from typing import Protocol

from red_env.manifest.models import PackageSpec


class StrategyHandler(Protocol):
    def __call__(self, package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
        ...
