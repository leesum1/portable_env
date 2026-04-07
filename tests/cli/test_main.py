from red_env.cli.app import main


def test_main_shows_expected_subcommands(capsys):
    exit_code = main(["--help"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "manifest" in captured.out
    assert "profile" in captured.out
    assert "build" in captured.out
    assert "verify" in captured.out
    assert "release" in captured.out
