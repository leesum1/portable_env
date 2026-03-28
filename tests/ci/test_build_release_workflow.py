from pathlib import Path


def test_build_release_workflow_runs_cli_from_temp_directory():
    workflow = Path(".github/workflows/build-release.yml").read_text(encoding="utf-8")

    assert "working-directory: /tmp" in workflow
    assert '--manifest-root "$GITHUB_WORKSPACE/manifests"' in workflow
    assert '--dockerfile "$GITHUB_WORKSPACE/docker/verifier.Dockerfile"' in workflow
