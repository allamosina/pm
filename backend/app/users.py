from pathlib import Path
import sqlite3

from pwdlib import PasswordHash

from app.database import initialize_schema, transaction
from app.seed import create_board

password_hash = PasswordHash.recommended()


class UsernameTaken(Exception):
    pass


def initialize_users(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with transaction(path, write=True) as db:
        initialize_schema(db)
        if db.execute("SELECT id FROM users WHERE username = ?", ("user",)).fetchone() is None:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                       ("user", password_hash.hash("password")))
        user_ids = [row[0] for row in db.execute("SELECT id FROM users")]
    for user_id in user_ids:
        with transaction(path, write=True) as db:
            if db.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,)).fetchone() is None:
                create_board(db, user_id)


def add_user(path: Path, username: str, password: str) -> None:
    hashed = password_hash.hash(password)
    with transaction(path, write=True) as db:
        try:
            user_id = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                 (username, hashed)).lastrowid
        except sqlite3.IntegrityError as error:
            if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
                raise UsernameTaken from error
            raise
        create_board(db, user_id)


def verify_user(path: Path, username: str, password: str) -> bool:
    with transaction(path) as db:
        row = db.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    return row is not None and password_hash.verify(password, row[0])
