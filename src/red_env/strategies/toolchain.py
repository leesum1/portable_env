from __future__ import annotations

import os
from pathlib import Path


def locked_flag(extract: dict[str, object], package_id: str) -> bool:
    """Return whether the build must run against a committed lock file.

    Source builds default to locked mode so that the dependency graph cannot
    drift between builds; packages whose upstream tarball ships no lock file
    can opt out with ``locked = false`` in their manifest.
    """
    value = extract.get("locked", True)
    if not isinstance(value, bool):
        raise ValueError(f"package {package_id}: strategy.extract.locked must be a boolean")
    return value


def cargo_environment(cache_dir: Path | None) -> dict[str, str]:
    """Environment for cargo/zigbuild with a persistent, reusable cache."""
    env = os.environ.copy()
    env.setdefault("CARGO_TERM_COLOR", "always")
    # Incremental artifacts belong to a source tree we delete after every
    # build, so keeping them in the shared cache would only grow it.
    env["CARGO_INCREMENTAL"] = "0"
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        env["CARGO_HOME"] = str(cache_dir / "cargo")
        env["CARGO_ZIGBUILD_CACHE_DIR"] = str(cache_dir / "zig")
    return env


def go_environment(cache_dir: Path | None, go_version: str | None, goarch: str) -> dict[str, str]:
    """Environment for a static, cross-compiled Go build with a shared cache."""
    env = os.environ.copy()
    env["CGO_ENABLED"] = "0"
    env["GOOS"] = "linux"
    env["GOARCH"] = goarch
    if go_version:
        # Let the go command switch to the pinned toolchain instead of
        # silently compiling with whatever is on PATH.
        env["GOTOOLCHAIN"] = go_version if go_version.startswith("go") else f"go{go_version}"
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        env["GOCACHE"] = str(cache_dir / "go-build")
        env["GOMODCACHE"] = str(cache_dir / "go-mod")
    return env
