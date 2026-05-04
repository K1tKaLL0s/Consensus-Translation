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
