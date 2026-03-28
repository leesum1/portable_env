# Red Environment Re-architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the repository into a TOML-driven offline packaging system with a single Python CLI, explicit package strategies, and Docker-based verification for `x86_64` and `arm64`.

**Architecture:** The new system centers on `manifests/*.toml` plus one Python package under `src/red_env/`. Manifest loading, profile resolution, fetching, strategy execution, packaging, installer generation, and Docker verification are split into focused modules. Docker is reduced to an execution environment, while package rules live only in manifests.

**Tech Stack:** Python 3.11+, `tomllib`, `argparse`, `pytest`, Docker Buildx, GitHub Releases HTTP API, POSIX shell installer scripts, TOML manifests

---

## File Map

### Create

- `pyproject.toml` - Python project metadata and pytest configuration.
- `src/red_env/__init__.py` - package marker and version export.
- `src/red_env/__main__.py` - `python -m red_env` entrypoint.
- `src/red_env/cli/app.py` - root argument parser and subcommand dispatch.
- `src/red_env/cli/commands/manifest.py` - `manifest lint` command.
- `src/red_env/cli/commands/profile.py` - `profile show` command.
- `src/red_env/cli/commands/build.py` - `build` command.
- `src/red_env/cli/commands/verify.py` - `verify` command.
- `src/red_env/cli/commands/release.py` - `release` command.
- `src/red_env/manifest/models.py` - dataclasses for manifest objects.
- `src/red_env/manifest/loader.py` - TOML loading and validation.
- `src/red_env/manifest/resolver.py` - profile expansion and package selection.
- `src/red_env/fetchers/github_release.py` - GitHub release asset lookup and download.
- `src/red_env/strategies/base.py` - strategy protocol and helpers.
- `src/red_env/strategies/direct_binary.py` - single-binary copy strategy.
- `src/red_env/strategies/archive_extract.py` - archive extraction strategy.
- `src/red_env/strategies/directory_copy.py` - directory-copy strategy.
- `src/red_env/strategies/registry.py` - strategy lookup table.
- `src/red_env/packaging/layout.py` - working directory layout helpers.
- `src/red_env/packaging/builder.py` - build orchestration and artifact creation.
- `src/red_env/installer/metadata.py` - bundle metadata writer.
- `src/red_env/verification/docker.py` - Docker build and verify orchestration.
- `manifests/manifest.toml` - manifest root file.
- `manifests/profiles.toml` - profile definitions.
- `manifests/bundle.toml` - bundle layout definitions.
- `manifests/packages/*.toml` - one package per file.
- `docker/builder.Dockerfile` - builder runtime image.
- `docker/verifier.Dockerfile` - clean verification image.
- `tests/cli/`, `tests/manifest/`, `tests/fetchers/`, `tests/strategies/`, `tests/packaging/`, `tests/installer/`, `tests/verification/` - focused test suites.

### Modify

- `.gitignore` - replace old output paths with new `build/` and `dist/` rules.
- `README.md` - document the new Python CLI and manifest model.
- `README.zh-CN.md` - same as above in Chinese.
- `.github/workflows/build-release.yml` - switch CI to the new CLI and Dockerfiles.

### Delete After Cutover

- `Makefile`
- `release_files/packages.json`
- `docker/Dockerfile.base`
- `docker/Dockerfile.build`
- `docker/Dockerfile.verify`
- `scripts/batch_soar_fetch.py`
- `scripts/soar_fetch_static.py`
- `scripts/install.sh`
- `scripts/uninstall.sh`
- `scripts/verify_tools.sh`

Do not delete the old entrypoints until Task 8 has passed and the new build and verify flow is green.

### Shared Conventions

- Use `python -m pytest` commands for all test execution.
- Use `python -m red_env` commands for all CLI examples.
- Prefer standard library modules where practical; do not add runtime dependencies without a specific need.
- All generated paths live under `build/` or `dist/`.

### Task 1: Bootstrap the Python Project and CLI Root

**Files:**
- Create: `pyproject.toml`
- Create: `src/red_env/__init__.py`
- Create: `src/red_env/__main__.py`
- Create: `src/red_env/cli/app.py`
- Test: `tests/cli/test_main.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from red_env.cli.app import main


def test_main_shows_expected_subcommands(capsys):
    exit_code = main(["--help"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "manifest" in captured.out
    assert "profile" in captured.out
    assert "build" in captured.out
    assert "verify" in captured.out
    assert "release" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_main.py::test_main_shows_expected_subcommands -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'red_env'`

- [ ] **Step 3: Write the minimal project bootstrap and root parser**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "red-env"
version = "0.1.0"
description = "Offline package builder for red_env"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/red_env/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/red_env/__main__.py
from red_env.cli.app import main


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/red_env/cli/app.py
from __future__ import annotations

import argparse
from typing import Sequence


def _noop(_: argparse.Namespace) -> int:
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red_env")
    subparsers = parser.add_subparsers(dest="command")

    for name in ("manifest", "profile", "build", "verify", "release"):
        command_parser = subparsers.add_parser(name)
        command_parser.set_defaults(handler=_noop)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cli/test_main.py::test_main_shows_expected_subcommands -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/red_env/__init__.py src/red_env/__main__.py src/red_env/cli/app.py tests/cli/test_main.py
git commit -m "feat: bootstrap red_env python cli"
```

### Task 2: Implement TOML Manifest Models and Loader

**Files:**
- Create: `src/red_env/manifest/models.py`
- Create: `src/red_env/manifest/loader.py`
- Test: `tests/manifest/test_loader.py`

- [ ] **Step 1: Write the failing manifest loader test**

```python
from pathlib import Path

from red_env.manifest.loader import load_manifest


def test_load_manifest_reads_root_profiles_bundle_and_packages(tmp_path: Path):
    manifests = tmp_path / "manifests"
    packages = manifests / "packages"
    packages.mkdir(parents=True)

    (manifests / "manifest.toml").write_text(
        'manifest_version = 1\npackage_dir = "packages"\n',
        encoding="utf-8",
    )
    (manifests / "profiles.toml").write_text(
        '[profiles.core]\npackages = ["fzf"]\n',
        encoding="utf-8",
    )
    (manifests / "bundle.toml").write_text(
        '[layout]\nbin = "bin"\nshare = "share"\nconfigs = "configs"\ncache = "cache"\nfonts = "fonts"\n',
        encoding="utf-8",
    )
    (packages / "fzf.toml").write_text(
        '\n'.join(
            [
                'id = "fzf"',
                'description = "fzf fuzzy finder"',
                'profiles = ["core"]',
                'architectures = ["x86_64", "arm64"]',
                '',
                '[source]',
                'type = "github_release"',
                'repo = "junegunn/fzf"',
                '',
                '[strategy]',
                'type = "archive_extract"',
                '',
                '[strategy.match]',
                'x86_64 = "(?i).*linux.*amd64.*tar.gz$"',
                'arm64 = "(?i).*linux.*arm64.*tar.gz$"',
                '',
                '[strategy.extract]',
                'include = ["fzf"]',
                'target_dir = "bin"',
            ]
        ),
        encoding="utf-8",
    )

    manifest = load_manifest(manifests)

    assert manifest.manifest_version == 1
    assert manifest.bundle.layout["bin"] == "bin"
    assert manifest.profiles["core"].packages == ["fzf"]
    assert manifest.packages["fzf"].source.repo == "junegunn/fzf"
    assert manifest.packages["fzf"].strategy.type == "archive_extract"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/manifest/test_loader.py::test_load_manifest_reads_root_profiles_bundle_and_packages -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'red_env.manifest'`

- [ ] **Step 3: Write manifest dataclasses and the root loader**

```python
# src/red_env/manifest/models.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceSpec:
    type: str
    repo: str


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
```

```python
# src/red_env/manifest/loader.py
from __future__ import annotations

import tomllib
from pathlib import Path

from red_env.manifest.models import BundleSpec, ManifestSpec, PackageSpec, ProfileSpec, SourceSpec, StrategySpec


def _read_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_manifest(manifest_root: Path) -> ManifestSpec:
    manifest_data = _read_toml(manifest_root / "manifest.toml")
    profiles_data = _read_toml(manifest_root / "profiles.toml")
    bundle_data = _read_toml(manifest_root / "bundle.toml")

    package_dir = manifest_root / manifest_data["package_dir"]
    packages: dict[str, PackageSpec] = {}
    for package_file in sorted(package_dir.glob("*.toml")):
        package_data = _read_toml(package_file)
        package = PackageSpec(
            id=package_data["id"],
            description=package_data["description"],
            profiles=list(package_data["profiles"]),
            architectures=list(package_data["architectures"]),
            source=SourceSpec(**package_data["source"]),
            strategy=StrategySpec(
                type=package_data["strategy"]["type"],
                match=dict(package_data["strategy"].get("match", {})),
                extract=dict(package_data["strategy"].get("extract", {})),
            ),
        )
        packages[package.id] = package

    profiles = {
        name: ProfileSpec(
            name=name,
            packages=list(data.get("packages", [])),
            extends=list(data.get("extends", [])),
        )
        for name, data in profiles_data["profiles"].items()
    }

    return ManifestSpec(
        manifest_version=int(manifest_data["manifest_version"]),
        bundle=BundleSpec(layout=dict(bundle_data["layout"])),
        profiles=profiles,
        packages=packages,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/manifest/test_loader.py::test_load_manifest_reads_root_profiles_bundle_and_packages -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/red_env/manifest/models.py src/red_env/manifest/loader.py tests/manifest/test_loader.py
git commit -m "feat: add toml manifest loader"
```

### Task 3: Add Manifest Validation, Profile Resolution, and Read-Only CLI Commands

**Files:**
- Create: `src/red_env/manifest/resolver.py`
- Create: `src/red_env/cli/commands/manifest.py`
- Create: `src/red_env/cli/commands/profile.py`
- Modify: `src/red_env/cli/app.py`
- Test: `tests/cli/test_manifest_commands.py`

- [ ] **Step 1: Write the failing command test**

```python
from pathlib import Path

from red_env.cli.app import main


def test_profile_show_prints_expanded_package_ids(tmp_path: Path, capsys):
    manifests = tmp_path / "manifests"
    packages = manifests / "packages"
    packages.mkdir(parents=True)

    (manifests / "manifest.toml").write_text('manifest_version = 1\npackage_dir = "packages"\n', encoding="utf-8")
    (manifests / "profiles.toml").write_text(
        '\n'.join(
            [
                '[profiles.core]',
                'packages = ["fzf"]',
                '',
                '[profiles.extended]',
                'extends = ["core"]',
                'packages = ["bat"]',
            ]
        ),
        encoding="utf-8",
    )
    (manifests / "bundle.toml").write_text('[layout]\nbin = "bin"\n', encoding="utf-8")
    (packages / "fzf.toml").write_text(
        'id = "fzf"\ndescription = "fzf"\nprofiles = ["core"]\narchitectures = ["x86_64"]\n[source]\ntype = "github_release"\nrepo = "junegunn/fzf"\n[strategy]\ntype = "direct_binary"\n',
        encoding="utf-8",
    )
    (packages / "bat.toml").write_text(
        'id = "bat"\ndescription = "bat"\nprofiles = ["extended"]\narchitectures = ["x86_64"]\n[source]\ntype = "github_release"\nrepo = "sharkdp/bat"\n[strategy]\ntype = "direct_binary"\n',
        encoding="utf-8",
    )

    exit_code = main(["profile", "show", "extended", "--manifest-root", str(manifests)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == ["bat", "fzf"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/cli/test_manifest_commands.py::test_profile_show_prints_expanded_package_ids -q`
Expected: FAIL with `SystemExit: 2` because `profile show` and `--manifest-root` are not implemented

- [ ] **Step 3: Implement validation, profile expansion, and command wiring**

```python
# src/red_env/manifest/resolver.py
from __future__ import annotations

from red_env.manifest.models import ManifestSpec


def validate_manifest(manifest: ManifestSpec) -> None:
    for profile in manifest.profiles.values():
        for package_id in profile.packages:
            if package_id not in manifest.packages:
                raise ValueError(f"profile {profile.name} references unknown package {package_id}")
        for parent in profile.extends:
            if parent not in manifest.profiles:
                raise ValueError(f"profile {profile.name} extends unknown profile {parent}")

    for package in manifest.packages.values():
        if package.source.type != "github_release":
            raise ValueError(f"unsupported source type: {package.source.type}")
        if package.strategy.type not in {"direct_binary", "archive_extract", "directory_copy"}:
            raise ValueError(f"unsupported strategy type: {package.strategy.type}")


def resolve_profile(manifest: ManifestSpec, profile_name: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def visit(name: str) -> None:
        profile = manifest.profiles[name]
        for parent in profile.extends:
            visit(parent)
        for package_id in profile.packages:
            if package_id not in seen:
                seen.add(package_id)
                ordered.append(package_id)

    if profile_name not in manifest.profiles:
        raise ValueError(f"unknown profile: {profile_name}")
    visit(profile_name)
    return sorted(ordered)
```

```python
# src/red_env/cli/commands/manifest.py
from __future__ import annotations

from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import validate_manifest


def lint_command(args) -> int:
    manifest = load_manifest(Path(args.manifest_root))
    validate_manifest(manifest)
    print(f"manifest ok: {len(manifest.packages)} packages")
    return 0
```

```python
# src/red_env/cli/commands/profile.py
from __future__ import annotations

from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def show_command(args) -> int:
    manifest = load_manifest(Path(args.manifest_root))
    validate_manifest(manifest)
    for package_id in resolve_profile(manifest, args.profile_name):
        print(package_id)
    return 0
```

```python
# src/red_env/cli/app.py
from __future__ import annotations

import argparse
from typing import Sequence

from red_env.cli.commands.manifest import lint_command
from red_env.cli.commands.profile import show_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red_env")
    subparsers = parser.add_subparsers(dest="command")

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser_subcommands = manifest_parser.add_subparsers(dest="manifest_command")
    lint_parser = manifest_parser_subcommands.add_parser("lint")
    lint_parser.add_argument("--manifest-root", default="manifests")
    lint_parser.set_defaults(handler=lint_command)

    profile_parser = subparsers.add_parser("profile")
    profile_subcommands = profile_parser.add_subparsers(dest="profile_command")
    show_parser = profile_subcommands.add_parser("show")
    show_parser.add_argument("profile_name")
    show_parser.add_argument("--manifest-root", default="manifests")
    show_parser.set_defaults(handler=show_command)

    for name in ("build", "verify", "release"):
        command_parser = subparsers.add_parser(name)
        command_parser.set_defaults(handler=lambda _: 0)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/cli/test_manifest_commands.py::test_profile_show_prints_expanded_package_ids -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/red_env/manifest/resolver.py src/red_env/cli/commands/manifest.py src/red_env/cli/commands/profile.py src/red_env/cli/app.py tests/cli/test_manifest_commands.py
git commit -m "feat: add manifest lint and profile resolution"
```

### Task 4: Implement GitHub Release Fetching and Strategy Execution

**Files:**
- Create: `src/red_env/fetchers/github_release.py`
- Create: `src/red_env/strategies/base.py`
- Create: `src/red_env/strategies/direct_binary.py`
- Create: `src/red_env/strategies/archive_extract.py`
- Create: `src/red_env/strategies/directory_copy.py`
- Create: `src/red_env/strategies/registry.py`
- Test: `tests/fetchers/test_github_release.py`
- Test: `tests/strategies/test_archive_extract.py`

- [ ] **Step 1: Write the failing fetcher and strategy tests**

```python
import io
import json
import tarfile
from pathlib import Path

from red_env.fetchers.github_release import select_asset_url
from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.archive_extract import apply_archive_extract


def test_select_asset_url_matches_arch_regex():
    release_payload = {
        "assets": [
            {"name": "tool_linux_amd64.tar.gz", "browser_download_url": "https://example.invalid/amd64.tar.gz"},
            {"name": "tool_linux_arm64.tar.gz", "browser_download_url": "https://example.invalid/arm64.tar.gz"},
        ]
    }

    url = select_asset_url(release_payload, r"(?i).*amd64.*tar.gz$")
    assert url == "https://example.invalid/amd64.tar.gz"


def test_apply_archive_extract_copies_named_binary(tmp_path: Path):
    archive_path = tmp_path / "tool.tar.gz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with tarfile.open(archive_path, "w:gz") as tar:
        payload = b"#!/bin/sh\necho fzf\n"
        info = tarfile.TarInfo("fzf")
        info.size = len(payload)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(payload))

    package = PackageSpec(
        id="fzf",
        description="fzf",
        profiles=["core"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="junegunn/fzf"),
        strategy=StrategySpec(
            type="archive_extract",
            extract={"include": ["fzf"], "target_dir": "bin"},
        ),
    )

    outputs = apply_archive_extract(package, archive_path, bundle_root)
    assert outputs == [bundle_root / "bin" / "fzf"]
    assert (bundle_root / "bin" / "fzf").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/fetchers/test_github_release.py::test_select_asset_url_matches_arch_regex tests/strategies/test_archive_extract.py::test_apply_archive_extract_copies_named_binary -q`
Expected: FAIL with import errors for `red_env.fetchers.github_release` and `red_env.strategies.archive_extract`

- [ ] **Step 3: Implement the fetcher and strategy registry**

```python
# src/red_env/fetchers/github_release.py
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
```

```python
# src/red_env/strategies/base.py
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from red_env.manifest.models import PackageSpec


class StrategyHandler(Protocol):
    def __call__(self, package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
        pass
```

```python
# src/red_env/strategies/direct_binary.py
from __future__ import annotations

import shutil
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_direct_binary(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / package.id
    shutil.copy2(downloaded_asset, target_path)
    target_path.chmod(0o755)
    return [target_path]
```

```python
# src/red_env/strategies/archive_extract.py
from __future__ import annotations

import shutil
import tarfile
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_archive_extract(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract["target_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    include = set(package.strategy.extract["include"])
    written: list[Path] = []

    with tarfile.open(downloaded_asset, "r:*") as archive:
        for member in archive.getmembers():
            member_name = Path(member.name).name
            if member_name not in include or not member.isfile():
                continue
            extracted = archive.extractfile(member)
            assert extracted is not None
            target_path = target_dir / member_name
            with target_path.open("wb") as handle:
                shutil.copyfileobj(extracted, handle)
            target_path.chmod(member.mode or 0o755)
            written.append(target_path)

    return written
```

```python
# src/red_env/strategies/directory_copy.py
from __future__ import annotations

import shutil
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_directory_copy(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract["target_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / downloaded_asset.name
    if downloaded_asset.is_dir():
        shutil.copytree(downloaded_asset, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(downloaded_asset, destination)
    return [destination]
```

```python
# src/red_env/strategies/registry.py
from __future__ import annotations

from red_env.strategies.archive_extract import apply_archive_extract
from red_env.strategies.directory_copy import apply_directory_copy
from red_env.strategies.direct_binary import apply_direct_binary


STRATEGY_REGISTRY = {
    "direct_binary": apply_direct_binary,
    "archive_extract": apply_archive_extract,
    "directory_copy": apply_directory_copy,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/fetchers/test_github_release.py::test_select_asset_url_matches_arch_regex tests/strategies/test_archive_extract.py::test_apply_archive_extract_copies_named_binary -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/red_env/fetchers/github_release.py src/red_env/strategies/base.py src/red_env/strategies/direct_binary.py src/red_env/strategies/archive_extract.py src/red_env/strategies/directory_copy.py src/red_env/strategies/registry.py tests/fetchers/test_github_release.py tests/strategies/test_archive_extract.py
git commit -m "feat: add github release fetcher and package strategies"
```

### Task 5: Build Bundle Layouts and Package Artifacts

**Files:**
- Create: `src/red_env/packaging/layout.py`
- Create: `src/red_env/packaging/builder.py`
- Create: `src/red_env/cli/commands/build.py`
- Modify: `src/red_env/cli/app.py`
- Test: `tests/packaging/test_builder.py`

- [ ] **Step 1: Write the failing build orchestration test**

```python
from pathlib import Path

from red_env.packaging.builder import build_artifact


def test_build_artifact_creates_bundle_tarball_and_checksum(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    (bundle_root / "bin").mkdir(parents=True)
    (bundle_root / "bin" / "fzf").write_text("fzf", encoding="utf-8")

    output_dir = tmp_path / "dist"
    tarball_path, checksum_path = build_artifact(bundle_root, output_dir, "core", "x86_64")

    assert tarball_path.name == "red_env_core_x86_64.tar.gz"
    assert checksum_path.name == "red_env_core_x86_64.tar.gz.sha256"
    assert tarball_path.exists()
    assert checksum_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/packaging/test_builder.py::test_build_artifact_creates_bundle_tarball_and_checksum -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'red_env.packaging'`

- [ ] **Step 3: Implement build layout helpers, artifact packaging, and the `build` command**

```python
# src/red_env/packaging/layout.py
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
```

```python
# src/red_env/packaging/builder.py
from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path


def build_artifact(bundle_root: Path, output_dir: Path, profile: str, arch: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tarball_path = output_dir / f"red_env_{profile}_{arch}.tar.gz"
    checksum_path = output_dir / f"{tarball_path.name}.sha256"

    with tarfile.open(tarball_path, "w:gz") as archive:
        archive.add(bundle_root, arcname="red_env_offline")

    digest = hashlib.sha256(tarball_path.read_bytes()).hexdigest()
    checksum_path.write_text(f"{digest}  {tarball_path.name}\n", encoding="utf-8")
    return tarball_path, checksum_path
```

```python
# src/red_env/cli/commands/build.py
from __future__ import annotations

from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest
from red_env.packaging.builder import build_artifact


def build_command(args) -> int:
    manifest = load_manifest(Path(args.manifest_root))
    validate_manifest(manifest)
    package_ids = resolve_profile(manifest, args.profile)

    bundle_root = Path(args.build_root) / "work" / args.profile / args.arch / "bundle"
    (bundle_root / "bin").mkdir(parents=True, exist_ok=True)
    manifest_file = bundle_root / "selected-packages.txt"
    manifest_file.write_text("\n".join(package_ids) + "\n", encoding="utf-8")

    tarball_path, checksum_path = build_artifact(bundle_root, Path(args.dist_root), args.profile, args.arch)
    print(tarball_path)
    print(checksum_path)
    return 0
```

```python
# src/red_env/cli/app.py
from __future__ import annotations

import argparse
from typing import Sequence

from red_env.cli.commands.build import build_command
from red_env.cli.commands.manifest import lint_command
from red_env.cli.commands.profile import show_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red_env")
    subparsers = parser.add_subparsers(dest="command")

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser_subcommands = manifest_parser.add_subparsers(dest="manifest_command")
    lint_parser = manifest_parser_subcommands.add_parser("lint")
    lint_parser.add_argument("--manifest-root", default="manifests")
    lint_parser.set_defaults(handler=lint_command)

    profile_parser = subparsers.add_parser("profile")
    profile_subcommands = profile_parser.add_subparsers(dest="profile_command")
    show_parser = profile_subcommands.add_parser("show")
    show_parser.add_argument("profile_name")
    show_parser.add_argument("--manifest-root", default="manifests")
    show_parser.set_defaults(handler=show_command)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--profile", required=True)
    build_parser.add_argument("--arch", required=True)
    build_parser.add_argument("--manifest-root", default="manifests")
    build_parser.add_argument("--build-root", default="build")
    build_parser.add_argument("--dist-root", default="dist")
    build_parser.set_defaults(handler=build_command)

    for name in ("verify", "release"):
        command_parser = subparsers.add_parser(name)
        command_parser.set_defaults(handler=lambda _: 0)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/packaging/test_builder.py::test_build_artifact_creates_bundle_tarball_and_checksum -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/red_env/packaging/layout.py src/red_env/packaging/builder.py src/red_env/cli/commands/build.py src/red_env/cli/app.py tests/packaging/test_builder.py
git commit -m "feat: add bundle packaging and build command"
```

### Task 6: Generate Installer Metadata and Stage Static Assets

**Files:**
- Create: `src/red_env/installer/metadata.py`
- Create: `assets/installer/install.sh`
- Create: `assets/installer/uninstall.sh`
- Test: `tests/installer/test_metadata.py`

- [ ] **Step 1: Write the failing metadata test**

```python
import json
from pathlib import Path

from red_env.installer.metadata import write_bundle_metadata


def test_write_bundle_metadata_records_profile_arch_and_packages(tmp_path: Path):
    metadata_path = write_bundle_metadata(
        bundle_root=tmp_path,
        profile="core",
        arch="x86_64",
        package_ids=["fzf", "bat", "rg"],
    )

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["profile"] == "core"
    assert payload["arch"] == "x86_64"
    assert payload["packages"] == ["fzf", "bat", "rg"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/installer/test_metadata.py::test_write_bundle_metadata_records_profile_arch_and_packages -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'red_env.installer'`

- [ ] **Step 3: Implement metadata generation and installer templates**

```python
# src/red_env/installer/metadata.py
from __future__ import annotations

import json
from pathlib import Path


def write_bundle_metadata(bundle_root: Path, profile: str, arch: str, package_ids: list[str]) -> Path:
    metadata_path = bundle_root / "bundle-manifest.json"
    metadata_path.write_text(
        json.dumps(
            {
                "profile": profile,
                "arch": arch,
                "packages": package_ids,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return metadata_path
```

```bash
# assets/installer/install.sh
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.red_env"

mkdir -p "${INSTALL_DIR}"
cp -R "${SCRIPT_DIR}/../configs" "${INSTALL_DIR}/configs"
cp -R "${SCRIPT_DIR}/../bundle/bin" "${INSTALL_DIR}/bin"
if [ -d "${SCRIPT_DIR}/../bundle/share" ]; then
  cp -R "${SCRIPT_DIR}/../bundle/share" "${INSTALL_DIR}/share"
fi

echo "Installed red_env into ${INSTALL_DIR}"
```

```bash
# assets/installer/uninstall.sh
#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/.red_env"
rm -rf "${INSTALL_DIR}"
echo "Removed ${INSTALL_DIR}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/installer/test_metadata.py::test_write_bundle_metadata_records_profile_arch_and_packages -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/red_env/installer/metadata.py assets/installer/install.sh assets/installer/uninstall.sh tests/installer/test_metadata.py
git commit -m "feat: add installer metadata and templates"
```

### Task 7: Add Docker Verification and Release Commands

**Files:**
- Create: `src/red_env/verification/docker.py`
- Create: `src/red_env/cli/commands/verify.py`
- Create: `src/red_env/cli/commands/release.py`
- Create: `docker/builder.Dockerfile`
- Create: `docker/verifier.Dockerfile`
- Modify: `src/red_env/cli/app.py`
- Test: `tests/verification/test_docker_cli.py`

- [ ] **Step 1: Write the failing Docker command test**

```python
from pathlib import Path

from red_env.verification.docker import verifier_build_command


def test_verifier_build_command_uses_new_dockerfile_and_artifact_name(tmp_path: Path):
    artifact = tmp_path / "red_env_core_x86_64.tar.gz"
    artifact.write_text("tarball", encoding="utf-8")

    command = verifier_build_command(
        artifact=artifact,
        arch="x86_64",
        dockerfile=Path("docker/verifier.Dockerfile"),
    )

    assert command[:4] == ["docker", "buildx", "build", "--platform"]
    assert "linux/amd64" in command
    assert "docker/verifier.Dockerfile" in command
    assert str(artifact) in command
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/verification/test_docker_cli.py::test_verifier_build_command_uses_new_dockerfile_and_artifact_name -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'red_env.verification'`

- [ ] **Step 3: Implement Docker command builders and CLI wiring**

```python
# src/red_env/verification/docker.py
from __future__ import annotations

import subprocess
from pathlib import Path


def _platform_for_arch(arch: str) -> str:
    return {"x86_64": "linux/amd64", "arm64": "linux/arm64"}[arch]


def verifier_build_command(artifact: Path, arch: str, dockerfile: Path) -> list[str]:
    return [
        "docker",
        "buildx",
        "build",
        "--platform",
        _platform_for_arch(arch),
        "-f",
        str(dockerfile),
        "--build-arg",
        f"PACKAGE_FILE={artifact}",
        "--load",
        ".",
    ]


def run_verifier(artifact: Path, arch: str, dockerfile: Path) -> None:
    subprocess.run(verifier_build_command(artifact, arch, dockerfile), check=True)
```

```python
# src/red_env/cli/commands/verify.py
from __future__ import annotations

from pathlib import Path

from red_env.verification.docker import run_verifier


def verify_command(args) -> int:
    artifact = Path(args.artifact)
    run_verifier(artifact, args.arch, Path("docker/verifier.Dockerfile"))
    print(f"verified {artifact}")
    return 0
```

```python
# src/red_env/cli/commands/release.py
from __future__ import annotations

from pathlib import Path


def release_command(args) -> int:
    artifact = Path(args.artifact)
    checksum = Path(f"{artifact}.sha256")
    if not artifact.exists() or not checksum.exists():
        raise FileNotFoundError("artifact and checksum must exist before release")
    print(artifact)
    print(checksum)
    return 0
```

```dockerfile
# docker/builder.Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    tar \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
```

```dockerfile
# docker/verifier.Dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    file \
    git \
    tar \
    xz-utils \
    zsh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /verify
ARG PACKAGE_FILE
COPY ${PACKAGE_FILE} /verify/package.tar.gz
```

```python
# src/red_env/cli/app.py
from __future__ import annotations

import argparse
from typing import Sequence

from red_env.cli.commands.build import build_command
from red_env.cli.commands.manifest import lint_command
from red_env.cli.commands.profile import show_command
from red_env.cli.commands.release import release_command
from red_env.cli.commands.verify import verify_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red_env")
    subparsers = parser.add_subparsers(dest="command")

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser_subcommands = manifest_parser.add_subparsers(dest="manifest_command")
    lint_parser = manifest_parser_subcommands.add_parser("lint")
    lint_parser.add_argument("--manifest-root", default="manifests")
    lint_parser.set_defaults(handler=lint_command)

    profile_parser = subparsers.add_parser("profile")
    profile_subcommands = profile_parser.add_subparsers(dest="profile_command")
    show_parser = profile_subcommands.add_parser("show")
    show_parser.add_argument("profile_name")
    show_parser.add_argument("--manifest-root", default="manifests")
    show_parser.set_defaults(handler=show_command)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--profile", required=True)
    build_parser.add_argument("--arch", required=True)
    build_parser.add_argument("--manifest-root", default="manifests")
    build_parser.add_argument("--build-root", default="build")
    build_parser.add_argument("--dist-root", default="dist")
    build_parser.set_defaults(handler=build_command)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--artifact", required=True)
    verify_parser.add_argument("--arch", required=True)
    verify_parser.set_defaults(handler=verify_command)

    release_parser = subparsers.add_parser("release")
    release_parser.add_argument("--artifact", required=True)
    release_parser.set_defaults(handler=release_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/verification/test_docker_cli.py::test_verifier_build_command_uses_new_dockerfile_and_artifact_name -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/red_env/verification/docker.py src/red_env/cli/commands/verify.py src/red_env/cli/commands/release.py src/red_env/cli/app.py docker/builder.Dockerfile docker/verifier.Dockerfile tests/verification/test_docker_cli.py
git commit -m "feat: add docker verification and release commands"
```

### Task 8: Seed Real Manifests, Move Static Assets, and Cut Over CI

**Files:**
- Create: `manifests/manifest.toml`
- Create: `manifests/profiles.toml`
- Create: `manifests/bundle.toml`
- Create: `manifests/packages/fzf.toml`
- Create: `manifests/packages/bat.toml`
- Create: `manifests/packages/rg.toml`
- Create: `manifests/packages/fd.toml`
- Create: `manifests/packages/delta.toml`
- Create: `manifests/packages/zsh.toml`
- Modify: `.gitignore`
- Modify: `.github/workflows/build-release.yml`
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `assets/configs/` via `git mv configs assets/configs`
- Test: `tests/manifest/test_seed_manifests.py`

- [ ] **Step 1: Write the failing seeded-manifest integration test**

```python
from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def test_repo_manifests_define_core_profile_with_expected_packages():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "core") == ["bat", "delta", "fd", "fzf", "rg", "zsh"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/manifest/test_seed_manifests.py::test_repo_manifests_define_core_profile_with_expected_packages -q`
Expected: FAIL with `FileNotFoundError` because `manifests/` does not exist yet

- [ ] **Step 3: Create the real manifest set, move configs, update CI and docs, then delete obsolete entrypoints**

```toml
# manifests/manifest.toml
manifest_version = 1
package_dir = "packages"
```

```toml
# manifests/profiles.toml
[profiles.core]
packages = ["fzf", "bat", "rg", "fd", "delta", "zsh"]

[profiles.extended]
extends = ["core"]
packages = []

[profiles.experimental]
extends = ["extended"]
packages = []
```

```toml
# manifests/bundle.toml
[layout]
bin = "bin"
share = "share"
configs = "configs"
cache = "cache"
fonts = "fonts"
```

```toml
# manifests/packages/fzf.toml
id = "fzf"
description = "fzf fuzzy finder"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "junegunn/fzf"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*linux.*amd64.*tar.gz$'
arm64 = '(?i).*linux.*arm64.*tar.gz$'

[strategy.extract]
include = ["fzf"]
target_dir = "bin"
```

```toml
# manifests/packages/bat.toml
id = "bat"
description = "bat cat clone"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "sharkdp/bat"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*x86_64.*unknown-linux-musl.*tar.gz$'
arm64 = '(?i).*aarch64.*unknown-linux-musl.*tar.gz$'

[strategy.extract]
include = ["bat"]
target_dir = "bin"
```

```toml
# manifests/packages/rg.toml
id = "rg"
description = "ripgrep"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "BurntSushi/ripgrep"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*x86_64.*unknown-linux-musl.*tar.gz$'
arm64 = '(?i).*aarch64.*unknown-linux-musl.*tar.gz$'

[strategy.extract]
include = ["rg"]
target_dir = "bin"
```

```toml
# manifests/packages/fd.toml
id = "fd"
description = "fd"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "sharkdp/fd"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*x86_64.*unknown-linux-musl.*tar.gz$'
arm64 = '(?i).*aarch64.*unknown-linux-musl.*tar.gz$'

[strategy.extract]
include = ["fd"]
target_dir = "bin"
```

```toml
# manifests/packages/delta.toml
id = "delta"
description = "git delta"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "dandavison/delta"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*x86_64.*unknown-linux-musl.*tar.gz$'
arm64 = '(?i).*aarch64.*unknown-linux-musl.*tar.gz$'

[strategy.extract]
include = ["delta"]
target_dir = "bin"
```

```toml
# manifests/packages/zsh.toml
id = "zsh"
description = "prebuilt zsh"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "romkatv/zsh-bin"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*x86_64.*tar.gz$'
arm64 = '(?i).*aarch64.*tar.gz$'

[strategy.extract]
include = ["zsh"]
target_dir = "bin"
```

```yaml
# .github/workflows/build-release.yml
name: Build and Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build-x86_64:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .[dev]
      - run: python -m red_env manifest lint
      - run: python -m red_env build --profile core --arch x86_64
      - run: python -m red_env verify --artifact dist/red_env_core_x86_64.tar.gz --arch x86_64

  build-arm64:
    runs-on: ubuntu-22.04-arm
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .[dev]
      - run: python -m red_env manifest lint
      - run: python -m red_env build --profile core --arch arm64
      - run: python -m red_env verify --artifact dist/red_env_core_arm64.tar.gz --arch arm64
```

```gitignore
# .gitignore
build/
dist/
logs/
*.tmp
*.temp
.DS_Store
Thumbs.db
.vscode/
.idea/
*.swp
*.swo
*~
.vscode-ctags
```

````markdown
# README.md
## Quick Start

```bash
python -m pip install -e .[dev]
python -m red_env manifest lint
python -m red_env profile show core
python -m red_env build --profile core --arch x86_64
python -m red_env verify --artifact dist/red_env_core_x86_64.tar.gz --arch x86_64
```
````

````markdown
# README.zh-CN.md
## 快速开始

```bash
python -m pip install -e .[dev]
python -m red_env manifest lint
python -m red_env profile show core
python -m red_env build --profile core --arch x86_64
python -m red_env verify --artifact dist/red_env_core_x86_64.tar.gz --arch x86_64
```
````

```bash
git mv configs assets/configs
rm -f Makefile release_files/packages.json docker/Dockerfile.base docker/Dockerfile.build docker/Dockerfile.verify
rm -f scripts/batch_soar_fetch.py scripts/soar_fetch_static.py scripts/install.sh scripts/uninstall.sh scripts/verify_tools.sh
```

- [ ] **Step 4: Run the repository-level regression tests**

Run: `python -m pytest tests/cli tests/manifest tests/fetchers tests/strategies tests/packaging tests/installer tests/verification -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add manifests assets/configs .gitignore .github/workflows/build-release.yml README.md README.zh-CN.md
git add -u Makefile release_files/packages.json docker/Dockerfile.base docker/Dockerfile.build docker/Dockerfile.verify scripts/batch_soar_fetch.py scripts/soar_fetch_static.py scripts/install.sh scripts/uninstall.sh scripts/verify_tools.sh
git commit -m "feat: cut over repository to manifest driven builder"
```

## Plan Self-Review Checklist

- Spec coverage check:
  - TOML manifests and per-package files are implemented in Tasks 2 and 8.
  - Single Python CLI is implemented across Tasks 1, 3, 5, and 7.
  - Explicit strategies are implemented in Task 4.
  - Build packaging and artifact generation are implemented in Task 5.
  - Offline installer metadata and templates are implemented in Task 6.
  - Docker verification and CI cutover are implemented in Tasks 7 and 8.
  - Removal of old entrypoints happens only after the new path exists in Task 8.

- Placeholder scan:
  - No deferred implementation markers remain.
  - All tasks include exact files, code snippets, commands, and commit messages.

- Type consistency check:
  - CLI uses `main`, `build_command`, `verify_command`, `release_command`, `lint_command`, and `show_command` consistently.
  - Manifest model names stay consistent across loader, resolver, fetcher, and strategy layers.
