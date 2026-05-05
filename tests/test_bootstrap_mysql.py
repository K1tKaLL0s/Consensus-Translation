from pathlib import Path

from src.tools import bootstrap_mysql as bootstrap_module
from src.tools.bootstrap_mysql import check_llm_keys, suggest_mysql_actions


ROOT = Path(__file__).resolve().parents[1]


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


def test_bootstrap_mysql_returns_ok_false_when_create_tables_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        bootstrap_module,
        "_probe_mysql",
        lambda: (True, True, "MySQL installation and service look healthy."),
    )
    monkeypatch.setattr(bootstrap_module, "_create_database_if_needed", lambda: None)

    def _raise_create_tables() -> None:
        raise RuntimeError("table creation exploded")

    monkeypatch.setattr(bootstrap_module, "_create_tables", _raise_create_tables)

    result = bootstrap_module.bootstrap_mysql()

    assert result.ok is False
    assert "table creation exploded" in result.message


def test_bootstrap_mysql_returns_ok_false_when_db_port_is_invalid(monkeypatch) -> None:
    monkeypatch.setenv("DB_PORT", "not-a-port")

    result = bootstrap_module.bootstrap_mysql()

    assert result.ok is False
    assert "port" in result.message.lower()


def test_create_database_if_needed_executes_create_database_sql(monkeypatch) -> None:
    executed = []

    class FakeSession:
        def execute(self, statement):
            executed.append(str(statement))

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(
        bootstrap_module,
        "_load_db_config",
        lambda: {
            "host": "127.0.0.1",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "cn_jp_translate",
        },
    )
    monkeypatch.setattr(bootstrap_module, "_create_server_engine", lambda _url: object())
    monkeypatch.setattr(bootstrap_module, "_create_server_session", lambda _engine: FakeSession())

    bootstrap_module._create_database_if_needed()

    assert any("CREATE DATABASE IF NOT EXISTS" in sql for sql in executed)


def test_readme_documents_run_ps1_init_entrypoint() -> None:
    readme_path = ROOT / "README.md"

    assert readme_path.exists()

    content = readme_path.read_text(encoding="utf-8")

    assert ".\\run.ps1 -Init" in content
