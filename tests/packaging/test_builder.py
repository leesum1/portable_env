from pathlib import Path

from red_env.packaging.builder import build_artifact


def test_build_artifact_creates_bundle_tarball_and_checksum(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    (bundle_root / "bin").mkdir(parents=True)
    (bundle_root / "bin" / "fzf").write_text("fzf", encoding="utf-8")

    output_dir = tmp_path / "dist"
    tarball_path, checksum_path = build_artifact(bundle_root, output_dir, "core", "x86_64")

    assert tarball_path.name == "red_env_core_x86_64.tar.gz"
    assert checksum_path.name == "red_env_core_x86_64.tar.gz.sha256"
    assert tarball_path.exists()
    assert checksum_path.exists()
