from pathlib import Path

import pytest

from red_env.cli.app import main


def _write_manifest(manifests: Path, profiles: str, packages: list[tuple[str, str]]) -> None:
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / "manifest.toml").write_text('manifest_version = 1\npackage_dir = "packages"\n', encoding="utf-8")
    (manifests / "profiles.toml").write_text(profiles, encoding="utf-8")
    (manifests / "bundle.toml").write_text('[layout]\nbin = "bin"\n', encoding="utf-8")

    package_dir = manifests / "packages"
    package_dir.mkdir(exist_ok=True)
    for name, content in packages:
        (package_dir / f"{name}.toml").write_text(content, encoding="utf-8")


def test_profile_show_prints_expanded_package_ids(tmp_path: Path, capsys):
    manifests = tmp_path / "manifests"
    (manifests / "packages").mkdir(parents=True)

    _write_manifest(
        manifests,
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
        [
            (
                "fzf",
                'id = "fzf"\ndescription = "fzf"\nprofiles = ["core"]\narchitectures = ["x86_64"]\n'
                '[source]\ntype = "github_release"\nrepo = "junegunn/fzf"\n[strategy]\ntype = "direct_binary"\n',
            ),
            (
                "bat",
                'id = "bat"\ndescription = "bat"\nprofiles = ["extended"]\narchitectures = ["x86_64"]\n'
                '[source]\ntype = "github_release"\nrepo = "sharkdp/bat"\n[strategy]\ntype = "direct_binary"\n',
            ),
        ],
    )

    exit_code = main(["profile", "show", "extended", "--manifest-root", str(manifests)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == ["bat", "fzf"]


def test_manifest_lint_reports_success(tmp_path: Path, capsys):
    manifests = tmp_path / "manifests"
    _write_manifest(
        manifests,
        '[profiles.core]\npackages = ["fzf", "bat"]\n',
        [
            (
                "fzf",
                'id = "fzf"\ndescription = "fzf"\nprofiles = ["core"]\narchitectures = ["x86_64"]\n'
                '[source]\ntype = "github_release"\nrepo = "junegunn/fzf"\n[strategy]\ntype = "direct_binary"\n',
            ),
            (
                "bat",
                'id = "bat"\ndescription = "bat"\nprofiles = ["core"]\narchitectures = ["x86_64"]\n'
                '[source]\ntype = "github_release"\nrepo = "sharkdp/bat"\n[strategy]\ntype = "direct_binary"\n',
            ),
        ],
    )

    exit_code = main(["manifest", "lint", "--manifest-root", str(manifests)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "manifest ok: 2 packages"


def test_manifest_lint_fails_when_package_references_unknown_profile(tmp_path: Path):
    manifests = tmp_path / "manifests"
    _write_manifest(
        manifests,
        '[profiles.core]\npackages = []\n',
        [
            (
                "broken",
                'id = "broken"\ndescription = "broken"\nprofiles = ["missing"]\narchitectures = ["x86_64"]\n'
                '[source]\ntype = "github_release"\nrepo = "example/broken"\n[strategy]\ntype = "direct_binary"\n',
            ),
        ],
    )

    with pytest.raises(ValueError) as excinfo:
        main(["manifest", "lint", "--manifest-root", str(manifests)])

    assert "package broken references unknown profile missing" in str(excinfo.value)


def test_manifest_lint_fails_on_profile_cycle(tmp_path: Path):
    manifests = tmp_path / "manifests"
    _write_manifest(
        manifests,
        '\n'.join(
            [
                '[profiles.a]',
                'packages = ["pkg"]',
                'extends = ["b"]',
                '',
                '[profiles.b]',
                'packages = ["pkg"]',
                'extends = ["a"]',
            ]
        ),
        [
            (
                "pkg",
                'id = "pkg"\ndescription = "pkg"\nprofiles = ["a", "b"]\narchitectures = ["x86_64"]\n'
                '[source]\ntype = "github_release"\nrepo = "example/pkg"\n[strategy]\ntype = "direct_binary"\n',
            ),
        ],
    )

    with pytest.raises(ValueError) as excinfo:
        main(["manifest", "lint", "--manifest-root", str(manifests)])

    assert "cyclic profile inheritance" in str(excinfo.value)
