from red_env.fetchers.github_release import select_asset_url


def test_select_asset_url_matches_arch_regex():
    release_payload = {
        "assets": [
            {"name": "tool_linux_amd64.tar.gz", "browser_download_url": "https://example.invalid/amd64.tar.gz"},
            {"name": "tool_linux_arm64.tar.gz", "browser_download_url": "https://example.invalid/arm64.tar.gz"},
        ]
    }

    url = select_asset_url(release_payload, r"(?i).*amd64.*tar.gz$")
    assert url == "https://example.invalid/amd64.tar.gz"
