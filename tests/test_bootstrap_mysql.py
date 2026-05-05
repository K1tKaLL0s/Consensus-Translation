from src.tools import bootstrap_mysql as bootstrap_module
from src.tools.bootstrap_mysql import check_llm_keys, suggest_mysql_actions


def test_suggest_mysql_actions_when_mysql_not_installed_contains_package_manager_hints() -> None:
    actions = suggest_mysql_actions(mysql_installed=False, mysql_service_running=False)

    lowered = actions.lower()
    assert "winget" in lowered
    assert "choco" in lowered


def test_suggest_mysql_actions_when_mysql_not_running_contains_start_service() -> None:
    actions = suggest_mysql_actions(mysql_installed=True, mysql_service_running=False)

    assert "Start-Service" in actions


def test_check_llm_keys_detects_deepseek_kimi_qwen() -> None:
    env = {
        "DEEPSEEK_API_KEY": "deepseek-key",
        "QWEN_API_KEY": "qwen-key",
    }

    result = check_llm_keys(env=env)

    assert result["deepseek"] is True
    assert result["kimi"] is False
    assert result["qwen"] is True


def test_bootstrap_mysql_returns_ok_true_when_probe_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(
        bootstrap_module,
        "_probe_mysql",
        lambda: (True, True, "MySQL installation and service look healthy."),
    )
    monkeypatch.setattr(bootstrap_module, "_create_database_if_needed", lambda: None)
    monkeypatch.setattr(bootstrap_module, "_create_tables", lambda: None)

    result = bootstrap_module.bootstrap_mysql()

    assert result.ok is True


def test_bootstrap_mysql_returns_ok_false_with_guidance_when_probe_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        bootstrap_module,
        "_probe_mysql",
        lambda: (
            False,
            False,
            "Install MySQL Server via winget: winget install Oracle.MySQL",
        ),
    )

    result = bootstrap_module.bootstrap_mysql()

    assert result.ok is False
    assert "install" in result.message.lower()
