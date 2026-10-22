from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildLayout:
    root: Path
    profile: str
    arch: str

    @property
    def work_dir(self) -> Path:
        return self.root / "work" / self.profile / self.arch

    @property
    def downloads_dir(self) -> Path:
        return self.work_dir / "downloads"

    @property
    def bundle_dir(self) -> Path:
        return self.work_dir / "bundle"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs" / self.profile / self.arch

    @property
    def cache_dir(self) -> Path:
        """Shared toolchain cache.

        Deliberately outside ``work_dir``: the work tree is wiped before every
        build, while this directory must survive to make rebuilds cheap.
        """
        return self.root / "cache"
