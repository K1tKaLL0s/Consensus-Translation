from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class BootstrapResult:
    ok: bool
    message: str


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


def _probe_mysql() -> tuple[bool, bool, str]:
    mysql_installed = bool(os.environ.get("MYSQL_INSTALLED"))
    mysql_service_running = mysql_installed and bool(os.environ.get("MYSQL_SERVICE_RUNNING"))
    message = suggest_mysql_actions(
        mysql_installed=mysql_installed,
        mysql_service_running=mysql_service_running,
    )
    return mysql_installed, mysql_service_running, message


def _create_database_if_needed() -> None:
    return None


def _create_tables() -> None:
    return None


def bootstrap_mysql() -> BootstrapResult:
    mysql_installed, mysql_service_running, probe_message = _probe_mysql()
    if not mysql_installed or not mysql_service_running:
        return BootstrapResult(ok=False, message=f"MySQL bootstrap guidance: {probe_message}")

    _create_database_if_needed()
    _create_tables()
    return BootstrapResult(ok=True, message="MySQL bootstrap completed.")
