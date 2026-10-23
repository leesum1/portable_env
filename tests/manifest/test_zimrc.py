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


def test_zshrc_warns_instead_of_silently_dropping_plugins():
    zshrc = Path("assets/configs/zsh/zshrc").read_text(encoding="utf-8")

    # 缺 oh-my-zsh 时必须说清楚，否则用户只会看到"插件配了却不生效"
    assert "oh-my-zsh not found at" in zshrc
    assert "else" in zshrc
    # 这个分支永远为假：install.sh 把 bundle/<name> 复制到 ~/.red_env/<name>，
    # 所以 ~/.red_env/bundle/cache 不存在。
    assert "bundle/cache/oh-my-zsh" not in zshrc


def test_zshrc_uses_utf8_locale_with_fallback_for_minimal_containers():
    zshrc = Path("assets/configs/zsh/zshrc").read_text(encoding="utf-8")

    assert "locale -a" in zshrc
    assert "en_US\\.utf-?8" in zshrc
    assert "export LANG=C.UTF-8" in zshrc
    assert "export LC_ALL=C.UTF-8" in zshrc
    assert 'RED_ENV_VERIFY_INTERACTIVE' in zshrc
