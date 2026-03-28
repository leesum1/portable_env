import io
from urllib.error import HTTPError
from pathlib import Path
import tomllib

import pytest

from red_env.fetchers.github_release import download_package_asset, select_asset_url
from red_env.fetchers import github_release
from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec


def test_select_asset_url_matches_arch_regex():
    release_payload = {
        "assets": [
            {"name": "tool_linux_amd64.tar.gz", "browser_download_url": "https://example.invalid/amd64.tar.gz"},
            {"name": "tool_linux_arm64.tar.gz", "browser_download_url": "https://example.invalid/arm64.tar.gz"},
        ]
    }

    url = select_asset_url(release_payload, r"(?i).*amd64.*tar.gz$")
    assert url == "https://example.invalid/amd64.tar.gz"


def test_select_asset_url_with_unanchored_regex_succeeds():
    release_payload = {
        "assets": [
            {"name": "tool_linux_amd64.tar.gz", "browser_download_url": "https://example.invalid/amd64.tar.gz"},
        ]
    }

    url = select_asset_url(release_payload, r"amd64\.tar\.gz$")
    assert url == "https://example.invalid/amd64.tar.gz"


def test_download_package_asset_raises_for_unknown_arch(tmp_path: Path):
    package = PackageSpec(
        id="fzf",
        description="fzf",
        profiles=["core"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="junegunn/fzf"),
        strategy=StrategySpec(
            type="archive_extract",
            match={"x86_64": r"amd64"},
            extract={"include": ["fzf"], "target_dir": "bin"},
        ),
    )

    destination = tmp_path / "asset"
    with pytest.raises(ValueError, match="unsupported architecture"):
        download_package_asset(package, "arm64", destination)


def test_zsh_manifest_regex_selects_linux_assets_not_windows_variants():
    manifest_path = Path("manifests/packages/zsh.toml")
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))

    release_payload = {
        "assets": [
            {
                "name": "zsh-x86_64.tar.gz",
                "browser_download_url": "https://example.invalid/zsh-cygwin-x86_64.tar.gz",
            },
            {
                "name": "zsh-aarch64.tar.gz",
                "browser_download_url": "https://example.invalid/zsh-cygwin-aarch64.tar.gz",
            },
            {
                "name": "zsh-5.8-linux-x86_64.tar.gz",
                "browser_download_url": "https://example.invalid/zsh-linux-x86_64.tar.gz",
            },
            {
                "name": "zsh-5.8-linux-aarch64.tar.gz",
                "browser_download_url": "https://example.invalid/zsh-linux-aarch64.tar.gz",
            },
        ]
    }

    x86_regex = manifest["strategy"]["match"]["x86_64"]
    arm_regex = manifest["strategy"]["match"]["arm64"]

    assert select_asset_url(release_payload, x86_regex) == "https://example.invalid/zsh-linux-x86_64.tar.gz"
    assert select_asset_url(release_payload, arm_regex) == "https://example.invalid/zsh-linux-aarch64.tar.gz"


def test_fetch_json_adds_bearer_header_from_gh_token(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "gh-token-value")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    captured: dict[str, object] = {}

    class DummyResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["accept"] = request.get_header("Accept")
        captured["user_agent"] = request.headers.get("User-agent")
        return DummyResponse(b'{"assets": []}')

    monkeypatch.setattr("red_env.fetchers.github_release.urllib.request.urlopen", fake_urlopen)

    payload = github_release._fetch_json("https://api.github.com/repos/owner/repo/releases/latest")
    assert payload == {"assets": []}
    assert captured["authorization"] == "Bearer gh-token-value"
    assert captured["accept"] == "application/vnd.github+json"
    assert captured["user_agent"] == "red-env/0.1.0"


def test_fetch_json_falls_back_to_github_token(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "github-token-value")
    captured: dict[str, object] = {}

    class DummyResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        return DummyResponse(b'{"assets": []}')

    monkeypatch.setattr("red_env.fetchers.github_release.urllib.request.urlopen", fake_urlopen)

    github_release._fetch_json("https://api.github.com/repos/owner/repo/releases/latest")
    assert captured["authorization"] == "Bearer github-token-value"


def test_fetch_json_raises_clear_error_on_rate_limit(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "gh-token-value")

    def fake_urlopen(request, timeout):
        raise HTTPError(
            url=request.full_url,
            code=403,
            msg="rate limit exceeded",
            hdrs={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9999999999"},
            fp=None,
        )

    monkeypatch.setattr("red_env.fetchers.github_release.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError) as excinfo:
        github_release._fetch_json("https://api.github.com/repos/owner/repo/releases/latest")

    message = str(excinfo.value)
    assert "GitHub API rate limit exceeded" in message
    assert "https://api.github.com/repos/owner/repo/releases/latest" in message
    assert "remaining=0" in message
    assert "auth_token=yes" in message
