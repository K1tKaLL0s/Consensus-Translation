from sqlalchemy.engine import URL

from src.models.init_db import build_db_url
from src.models.entities import (
    Base,
    GlossaryMaster,
    SourceTerm,
)


def test_core_five_tables_registered() -> None:
    tables = set(Base.metadata.tables.keys())
    assert {
        "project_domain",
        "source_term",
        "candidate_trans",
        "consensus_log",
        "glossary_master",
    }.issubset(tables)


def test_source_term_proj_id_has_foreign_key() -> None:
    proj_id_column = SourceTerm.__table__.c.proj_id
    foreign_key_targets = {fk.target_fullname for fk in proj_id_column.foreign_keys}
    assert "project_domain.id" in foreign_key_targets


def test_glossary_master_has_status_field() -> None:
    assert "status" in GlossaryMaster.__table__.c


def test_build_db_url_returns_url_object_with_special_char_password(monkeypatch) -> None:
    monkeypatch.setenv("MYSQL_USER", "test_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "pa:ss@wo/rd?#[]")
    monkeypatch.setenv("MYSQL_HOST", "db.local")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_DB", "translation_db")

    db_url = build_db_url()

    assert isinstance(db_url, URL)
    assert db_url.drivername == "mysql+pymysql"
    assert db_url.database == "translation_db"
    assert db_url.password == "pa:ss@wo/rd?#[]"


def test_glossary_master_status_has_server_default_active() -> None:
    status_column = GlossaryMaster.__table__.c.status
    assert status_column.server_default is not None
    assert str(status_column.server_default.arg) == "'active'"
