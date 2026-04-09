from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceSpec:
    type: str
    repo: str
    ref: str | None = None
    file_path: str | None = None


@dataclass(frozen=True)
class StrategySpec:
    type: str
    match: dict[str, str] = field(default_factory=dict)
    extract: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PackageSpec:
    id: str
    description: str
    profiles: list[str]
    architectures: list[str]
    source: SourceSpec
    strategy: StrategySpec


@dataclass(frozen=True)
class ProfileSpec:
    name: str
    packages: list[str]
    extends: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BundleSpec:
    layout: dict[str, str]


@dataclass(frozen=True)
class ManifestSpec:
    manifest_version: int
    bundle: BundleSpec
    profiles: dict[str, ProfileSpec]
    packages: dict[str, PackageSpec]
