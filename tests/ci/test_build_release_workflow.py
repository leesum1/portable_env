from pathlib import Path


def test_build_release_workflow_runs_cli_from_temp_directory():
    workflow = Path(".github/workflows/build-release.yml").read_text(encoding="utf-8")

    assert "working-directory: /tmp" in workflow
    assert '--manifest-root "$GITHUB_WORKSPACE/manifests"' in workflow
    assert '--dockerfile "$GITHUB_WORKSPACE/docker/verifier.Dockerfile"' in workflow


def test_build_release_workflow_exports_github_token_for_build_steps():
    workflow = Path(".github/workflows/build-release.yml").read_text(encoding="utf-8")

    assert "GH_TOKEN: ${{ github.token }}" in workflow


def test_workflow_toolchain_pins_match_the_manifest():
    import tomllib

    manifest = tomllib.loads(Path("manifests/manifest.toml").read_text(encoding="utf-8"))
    workflow = Path(".github/workflows/build-release.yml").read_text(encoding="utf-8")

    assert f'RUST_VERSION: "{manifest["toolchains"]["rust"]}"' in workflow
    assert f'GO_VERSION: "{manifest["toolchains"]["go"]}"' in workflow


def test_dockerfile_toolchain_pins_match_the_manifest():
    import re
    import tomllib

    manifest = tomllib.loads(Path("manifests/manifest.toml").read_text(encoding="utf-8"))
    dockerfile = Path("docker/builder-full.Dockerfile").read_text(encoding="utf-8")

    rust_arg = re.search(r"^ARG RUST_VERSION=(.+)$", dockerfile, re.MULTILINE)
    go_arg = re.search(r"^ARG GO_VERSION=(.+)$", dockerfile, re.MULTILINE)
    assert rust_arg is not None and rust_arg.group(1).strip() == manifest["toolchains"]["rust"]
    assert go_arg is not None and go_arg.group(1).strip() == manifest["toolchains"]["go"]


def test_dockerfile_pins_the_base_image_by_digest():
    dockerfile = Path("docker/builder-full.Dockerfile").read_text(encoding="utf-8")

    assert "ARG BASE_IMAGE=" in dockerfile
    assert "@sha256:" in dockerfile
    assert "FROM ${BASE_IMAGE}" in dockerfile


def test_workflow_runs_the_test_suite():
    workflow = Path(".github/workflows/build-release.yml").read_text(encoding="utf-8")

    assert "python -m pytest -q" in workflow
