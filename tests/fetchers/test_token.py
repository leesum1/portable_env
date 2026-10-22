from __future__ import annotations

import subprocess

import pytest

from red_env.fetchers import token


@pytest.fixture(autouse=True)
def _reset_token_cache():
    token.reset_token_cache()
    yield
    token.reset_token_cache()


def _no_gh(monkeypatch):
    monkeypatch.setattr(token.shutil, "which", lambda _name: None)


def test_gh_token_environment_variable_wins(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "from-gh-token")
    monkeypatch.setenv("GITHUB_TOKEN", "from-github-token")
    _no_gh(monkeypatch)

    assert token.github_token() == "from-gh-token"


def test_github_token_environment_variable_is_the_fallback(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "from-github-token")
    _no_gh(monkeypatch)

    assert token.github_token() == "from-github-token"


def test_blank_environment_variables_are_ignored(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "   ")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _no_gh(monkeypatch)

    assert token.github_token() is None


def test_falls_back_to_the_github_cli(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(token.shutil, "which", lambda name: "/usr/bin/gh" if name == "gh" else None)
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="cli-token-value\n", stderr="")

    monkeypatch.setattr(token.subprocess, "run", fake_run)

    assert token.github_token() == "cli-token-value"
    assert calls == [["/usr/bin/gh", "auth", "token"]]


def test_github_cli_result_is_cached(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(token.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="cli-token-value\n", stderr="")

    monkeypatch.setattr(token.subprocess, "run", fake_run)

    assert token.github_token() == "cli-token-value"
    assert token.github_token() == "cli-token-value"
    assert len(calls) == 1


def test_missing_gh_cli_yields_no_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _no_gh(monkeypatch)

    assert token.github_token() is None


def test_failed_gh_auth_yields_no_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(token.shutil, "which", lambda _name: "/usr/bin/gh")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="not logged in")

    monkeypatch.setattr(token.subprocess, "run", fake_run)

    assert token.github_token() is None


def test_empty_gh_output_yields_no_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(token.shutil, "which", lambda _name: "/usr/bin/gh")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="\n", stderr="")

    monkeypatch.setattr(token.subprocess, "run", fake_run)

    assert token.github_token() is None


def test_gh_timeout_is_not_fatal(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(token.shutil, "which", lambda _name: "/usr/bin/gh")

    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 10)

    monkeypatch.setattr(token.subprocess, "run", fake_run)

    assert token.github_token() is None
