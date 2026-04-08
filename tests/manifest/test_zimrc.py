from pathlib import Path


def test_zimrc_declares_offline_modules_with_explicit_local_paths_and_use_mkdir():
    zimrc = Path("assets/configs/zsh/zimrc").read_text(encoding="utf-8")

    expected_lines = [
        'zmodule "${ZIM_HOME}/modules/environment"',
        'zmodule "${ZIM_HOME}/modules/input"',
        'zmodule "${ZIM_HOME}/modules/utility"',
        'zmodule "${ZIM_HOME}/modules/git"',
        'zmodule "${ZIM_HOME}/modules/zsh-completions" --fpath src',
        'zmodule "${ZIM_HOME}/modules/completion"',
        'zmodule "${ZIM_HOME}/modules/zsh-syntax-highlighting"',
        'zmodule "${ZIM_HOME}/modules/zsh-autosuggestions"',
        'zmodule "${ZIM_HOME}/modules/zsh-history-substring-search"',
        'zmodule "${ZIM_HOME}/modules/pvenv"',
        'zmodule "${ZIM_HOME}/modules/zsh-z"',
        'zmodule "${ZIM_HOME}/modules/duration-info"',
        'zmodule "${ZIM_HOME}/modules/git-info"',
        'zmodule "${ZIM_HOME}/modules/asciiship"',
    ]

    for line in expected_lines:
        assert line in zimrc

    assert 'if [[ -z "${RED_ENV_DISABLE_ZSH_256COLOR:-}" ]]; then' in zimrc
    assert 'zmodule "${ZIM_HOME}/modules/zsh-256color"' in zimrc
    assert "fi" in zimrc
