from sqlalchemy.exc import OperationalError

from devkit.db import is_transient_db_error, normalize_postgres_dsn


def test_normalize_postgres_dsn() -> None:
    assert normalize_postgres_dsn("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_postgres_dsn("postgresql+psycopg://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"


def test_transient_error_detection() -> None:
    assert is_transient_db_error(OperationalError("stmt", {}, Exception("down")))
    assert not is_transient_db_error(ValueError("nope"))
