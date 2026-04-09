from pathlib import Path


def test_oh_my_zsh_config_declares_plugins():
    zshrc = Path("assets/configs/zsh/zshrc").read_text(encoding="utf-8")

    # 检查插件声明
    assert "plugins=(" in zshrc
    assert "git" in zshrc
    assert "extract" in zshrc
    assert "z" in zshrc
    assert "zsh-autosuggestions" in zshrc
    assert "zsh-syntax-highlighting" in zshrc


def test_zshrc_uses_oh_my_zsh_bootstrap():
    zshrc = Path("assets/configs/zsh/zshrc").read_text(encoding="utf-8")

    # 检查 oh-my-zsh 初始化
    assert 'ZSH="${RED_ENV_HOME}/cache/oh-my-zsh"' in zshrc
    assert 'source "${ZSH}/oh-my-zsh.sh"' in zshrc


def test_zshrc_uses_utf8_locale_with_fallback_for_minimal_containers():
    zshrc = Path("assets/configs/zsh/zshrc").read_text(encoding="utf-8")

    assert "locale -a" in zshrc
    assert "en_US\\.utf-?8" in zshrc
    assert "export LANG=C.UTF-8" in zshrc
    assert "export LC_ALL=C.UTF-8" in zshrc
    assert 'RED_ENV_VERIFY_INTERACTIVE' in zshrc
