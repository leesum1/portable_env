from pathlib import Path
import tomllib


def test_third_party_oh_my_zsh_plugins_are_pinned_to_stable_refs():
    expected_refs = {
        "manifests/packages/oh-my-zsh-zsh-autosuggestions.toml": "v0.7.1",
        "manifests/packages/oh-my-zsh-zsh-syntax-highlighting.toml": "0.8.0",
    }

    for manifest_path, expected_ref in expected_refs.items():
        package_manifest = tomllib.loads(Path(manifest_path).read_text(encoding="utf-8"))
        assert package_manifest["source"]["ref"] == expected_ref
