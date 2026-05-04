import pytest

from src.models.entities import Base, DomainSourceCatalog, GlossaryScopeMap
from src.services.glossary_service import normalize_source_name, validate_export_format


def test_domain_source_catalog_and_scope_map_tables_registered() -> None:
    tables = set(Base.metadata.tables.keys())
    assert "domain_source_catalog" in tables
    assert "glossary_scope_map" in tables


def test_domain_source_catalog_source_name_is_unique() -> None:
    source_name_column = DomainSourceCatalog.__table__.c.source_name
    assert source_name_column.unique is True


def test_glossary_scope_map_foreign_keys_target_expected_columns() -> None:
    glossary_fk_targets = {
        fk.target_fullname for fk in GlossaryScopeMap.__table__.c.glossary_id.foreign_keys
    }
    source_fk_targets = {
        fk.target_fullname for fk in GlossaryScopeMap.__table__.c.source_catalog_id.foreign_keys
    }

    assert "glossary_master.glossary_id" in glossary_fk_targets
    assert "domain_source_catalog.source_catalog_id" in source_fk_targets


def test_normalize_source_name_strips_whitespace() -> None:
    assert normalize_source_name("  wikipedia  ") == "wikipedia"


@pytest.mark.parametrize("source_name", ["", "   "])
def test_normalize_source_name_raises_for_blank_input(source_name: str) -> None:
    with pytest.raises(ValueError):
        normalize_source_name(source_name)


@pytest.mark.parametrize("fmt", ["csv", "xlsx", "json"])
def test_validate_export_format_accepts_supported_formats(fmt: str) -> None:
    assert validate_export_format(fmt) == fmt


@pytest.mark.parametrize("fmt", ["xml", "txt", ""])
def test_validate_export_format_rejects_unsupported_formats(fmt: str) -> None:
    with pytest.raises(ValueError):
        validate_export_format(fmt)
