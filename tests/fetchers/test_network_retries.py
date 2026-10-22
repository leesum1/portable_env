from __future__ import annotations

import io
from urllib.error import HTTPError, URLError

import pytest

from red_env.fetchers import github_release


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(github_release.time, "sleep", lambda seconds: sleeps.append(seconds))
    return sleeps


def _flaky_urlopen(failures: int, payload: bytes = b'{"assets": []}'):
    calls: list[str] = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) <= failures:
            raise URLError(OSError(104, "Connection reset by peer"))
        return io.BytesIO(payload)

    return fake_urlopen, calls


def test_fetch_json_retries_a_dropped_connection(monkeypatch, _no_sleep):
    fake_urlopen, calls = _flaky_urlopen(failures=2)
    monkeypatch.setattr(github_release.urllib.request, "urlopen", fake_urlopen)

    assert github_release._fetch_json("https://api.github.com/repos/o/r/releases/latest") == {"assets": []}
    assert len(calls) == 3
    assert _no_sleep == [2.0, 4.0]


def test_fetch_json_gives_up_after_the_attempt_limit(monkeypatch):
    fake_urlopen, calls = _flaky_urlopen(failures=99)
    monkeypatch.setattr(github_release.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError) as excinfo:
        github_release._fetch_json("https://api.github.com/repos/o/r/releases/latest")

    assert len(calls) == github_release._RETRY_ATTEMPTS
    assert "network request failed after" in str(excinfo.value)


def test_fetch_json_does_not_retry_a_missing_resource(monkeypatch):
    calls: list[str] = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        raise HTTPError(url=request.full_url, code=404, msg="Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(github_release.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(HTTPError):
        github_release._fetch_json("https://api.github.com/repos/o/r/releases/latest")

    assert len(calls) == 1


def test_fetch_json_retries_a_server_error(monkeypatch, _no_sleep):
    calls: list[str] = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise HTTPError(url=request.full_url, code=503, msg="Service Unavailable", hdrs=None, fp=None)
        return io.BytesIO(b'{"assets": []}')

    monkeypatch.setattr(github_release.urllib.request, "urlopen", fake_urlopen)

    assert github_release._fetch_json("https://api.github.com/repos/o/r/releases/latest") == {"assets": []}
    assert len(calls) == 2


def test_download_retries_and_rewrites_the_destination(monkeypatch, tmp_path, _no_sleep):
    destination = tmp_path / "asset.tar.gz"
    calls: list[str] = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise URLError(OSError(104, "Connection reset by peer"))
        return io.BytesIO(b"payload")

    monkeypatch.setattr(github_release.urllib.request, "urlopen", fake_urlopen)

    github_release._download_to_path("https://example.test/asset.tar.gz", destination)

    assert destination.read_bytes() == b"payload"
    assert len(calls) == 2
