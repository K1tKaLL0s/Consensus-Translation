from sqlalchemy import ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectDomain(Base):
    __tablename__ = "project_domain"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_name: Mapped[str] = mapped_column(String(128), nullable=False)


class SourceTerm(Base):
    __tablename__ = "source_term"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proj_id: Mapped[int] = mapped_column(ForeignKey("project_domain.id"), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)


class CandidateTrans(Base):
    __tablename__ = "candidate_trans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_term_id: Mapped[int] = mapped_column(ForeignKey("source_term.id"), nullable=False)
    candidate_text: Mapped[str] = mapped_column(Text, nullable=False)


class ConsensusLog(Base):
    __tablename__ = "consensus_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_term_id: Mapped[int] = mapped_column(ForeignKey("source_term.id"), nullable=False)
    decision_note: Mapped[str] = mapped_column(Text, nullable=False)


class GlossaryMaster(Base):
    __tablename__ = "glossary_master"

    glossary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )


class DomainSourceCatalog(Base):
    __tablename__ = "domain_source_catalog"

    source_catalog_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class GlossaryScopeMap(Base):
    __tablename__ = "glossary_scope_map"

    scope_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    glossary_id: Mapped[int] = mapped_column(
        ForeignKey("glossary_master.glossary_id"),
        nullable=False,
    )
    source_catalog_id: Mapped[int] = mapped_column(
        ForeignKey("domain_source_catalog.source_catalog_id"),
        nullable=False,
    )
