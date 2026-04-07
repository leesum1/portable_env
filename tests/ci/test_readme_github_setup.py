from pathlib import Path


def test_english_readme_mentions_github_token_for_builds():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "GH_TOKEN" in readme
    assert "GITHUB_TOKEN" in readme


def test_chinese_readme_mentions_github_token_for_builds():
    readme = Path("README.zh-CN.md").read_text(encoding="utf-8")

    assert "GH_TOKEN" in readme
    assert "GITHUB_TOKEN" in readme
