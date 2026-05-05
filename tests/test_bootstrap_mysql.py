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
