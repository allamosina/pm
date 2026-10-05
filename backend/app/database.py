import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def transaction(path: Path, *, write: bool = False):
    db = sqlite3.connect(path, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_schema(db: sqlite3.Connection) -> None:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version > 1:
        raise RuntimeError(f"Unsupported database version: {version}")
    if version == 0:
        # Execute separately: executescript would commit the active transaction.
        for statement in Path(__file__).with_name("schema.sql").read_text().split(";"):
            if statement.strip():
                db.execute(statement)
        db.execute("PRAGMA user_version = 1")
