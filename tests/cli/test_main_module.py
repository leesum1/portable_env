import subprocess
import sys
from pathlib import Path


def test_main_module_help_from_repo_root():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "red_env", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "manifest" in result.stdout
    assert "profile" in result.stdout
    assert "build" in result.stdout
    assert "verify" in result.stdout
    assert "release" in result.stdout
