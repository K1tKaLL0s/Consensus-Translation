import os

from sqlalchemy import create_engine

from src.models.entities import Base


def build_db_url() -> str:
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DB", "cn_jp_translate")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def init_db(db_url: str | None = None) -> None:
    engine = create_engine(db_url or build_db_url())
    Base.metadata.create_all(engine)


def main() -> None:
    init_db()


if __name__ == "__main__":
    main()
