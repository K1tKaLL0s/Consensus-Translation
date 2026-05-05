from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.models.entities import Base


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


def _load_db_config() -> dict[str, str | int]:
    load_dotenv()
    host = os.getenv("DB_HOST", "127.0.0.1")
    port_raw = os.getenv("DB_PORT", "3306")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"Invalid DB_PORT value '{port_raw}'. Please configure a valid integer port.") from exc
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "cn_jp_translate")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def _build_server_url(config: Mapping[str, str | int]) -> URL:
    return URL.create(
        drivername="mysql+pymysql",
        username=str(config["user"]),
        password=str(config["password"]),
        host=str(config["host"]),
        port=int(config["port"]),
        database=None,
        query={"charset": "utf8mb4"},
    )


def _build_database_url(config: Mapping[str, str | int]) -> URL:
    return URL.create(
        drivername="mysql+pymysql",
        username=str(config["user"]),
        password=str(config["password"]),
        host=str(config["host"]),
        port=int(config["port"]),
        database=str(config["database"]),
        query={"charset": "utf8mb4"},
    )


def _create_server_engine(url: URL) -> Engine:
    return create_engine(url)


def _create_database_engine(url: URL) -> Engine:
    return create_engine(url)


def _create_server_session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()


def _dispose_engine(engine: object) -> None:
    dispose = getattr(engine, "dispose", None)
    if callable(dispose):
        dispose()


def _probe_mysql() -> tuple[bool, bool, str]:
    config = _load_db_config()
    engine = _create_server_engine(_build_server_url(config))

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return False, False, f"MySQL probe failed: {exc}"
    finally:
        _dispose_engine(engine)

    return True, True, "MySQL installation and service look healthy."


def _create_database_if_needed() -> None:
    config = _load_db_config()
    engine = _create_server_engine(_build_server_url(config))
    session = _create_server_session(engine)
    database = str(config["database"]).replace("`", "")

    try:
        session.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database}`"))
        session.commit()
    finally:
        session.close()
        _dispose_engine(engine)


def _create_tables() -> None:
    config = _load_db_config()
    engine = _create_database_engine(_build_database_url(config))
    try:
        Base.metadata.create_all(engine)
    finally:
        _dispose_engine(engine)


def bootstrap_mysql() -> BootstrapResult:
    try:
        mysql_installed, mysql_service_running, probe_message = _probe_mysql()
    except ValueError as exc:
        return BootstrapResult(ok=False, message=f"MySQL bootstrap failed: {exc}")

    if not mysql_installed or not mysql_service_running:
        return BootstrapResult(ok=False, message=f"MySQL bootstrap guidance: {probe_message}")

    try:
        _create_database_if_needed()
        _create_tables()
    except Exception as exc:
        return BootstrapResult(ok=False, message=f"MySQL bootstrap failed during schema setup: {exc}")

    return BootstrapResult(ok=True, message="MySQL bootstrap completed.")
