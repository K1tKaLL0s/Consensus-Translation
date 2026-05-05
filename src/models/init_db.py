import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from src.models.entities import Base


def build_db_url() -> URL:
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port_raw = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DB", "cn_jp_translate")
    port = int(port_raw) if port_raw else None
    return URL.create(
        drivername="mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"charset": "utf8mb4"},
    )


def init_db(db_url: str | URL | None = None) -> None:
    engine = create_engine(db_url or build_db_url())
    Base.metadata.create_all(engine)


def main() -> None:
    init_db()


if __name__ == "__main__":
    main()
