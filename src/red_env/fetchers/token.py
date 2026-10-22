from __future__ import annotations

import os
import shutil
import subprocess

_ENVIRONMENT_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN")
_GH_CLI_TIMEOUT = 10
_UNRESOLVED = object()
_cached_gh_token: object = _UNRESOLVED


def github_token() -> str | None:
    """Return a GitHub token for API and archive requests.

    ``GH_TOKEN`` wins, then ``GITHUB_TOKEN``, so CI can inject a token
    explicitly. When neither is set, fall back to the token the GitHub CLI
    already stored locally, which is exactly what
    ``export GH_TOKEN=$(gh auth token)`` would have produced.

    Environment variables are read on every call (they are cheap and may change
    during a long build); only the ``gh`` invocation is cached.
    """
    from_environment = _from_environment()
    if from_environment is not None:
        return from_environment
    return _from_gh_cli_cached()


def reset_token_cache() -> None:
    """Forget the resolved ``gh`` token; used by tests and long-lived processes."""
    global _cached_gh_token
    _cached_gh_token = _UNRESOLVED


def _from_environment() -> str | None:
    for name in _ENVIRONMENT_VARIABLES:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def _from_gh_cli_cached() -> str | None:
    global _cached_gh_token
    if _cached_gh_token is _UNRESOLVED:
        _cached_gh_token = _from_gh_cli()
    return _cached_gh_token  # type: ignore[return-value]


def _from_gh_cli() -> str | None:
    gh = shutil.which("gh")
    if gh is None:
        return None
    try:
        completed = subprocess.run(
            [gh, "auth", "token"],
            capture_output=True,
            text=True,
            timeout=_GH_CLI_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    token = completed.stdout.strip()
    return token or None
