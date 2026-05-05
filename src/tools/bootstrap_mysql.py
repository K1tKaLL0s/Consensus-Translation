from __future__ import annotations

import os
from collections.abc import Mapping


def check_llm_keys(env: Mapping[str, str] | None = None) -> dict[str, bool]:
    source = os.environ if env is None else env
    keys = {
        "deepseek": "DEEPSEEK_API_KEY",
        "kimi": "KIMI_API_KEY",
        "qwen": "QWEN_API_KEY",
    }
    return {name: bool(source.get(var)) for name, var in keys.items()}


def suggest_mysql_actions(
    mysql_installed: bool,
    mysql_service_running: bool,
) -> str:
    if not mysql_installed:
        return (
            "Install MySQL Server via winget: winget install Oracle.MySQL\n"
            "Install MySQL Server via choco: choco install mysql"
        )

    if not mysql_service_running:
        return (
            "Start MySQL service: Start-Service MySQL80\n"
            "Check service state: Get-Service MySQL80"
        )

    return "MySQL installation and service look healthy."
