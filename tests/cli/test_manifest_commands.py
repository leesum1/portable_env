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
