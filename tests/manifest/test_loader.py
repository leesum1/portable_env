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
