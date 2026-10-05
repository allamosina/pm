import sqlite3
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.database import transaction


def owned_board(db: sqlite3.Connection, username: str) -> sqlite3.Row:
    board = db.execute("""SELECT boards.id, boards.revision FROM boards
        JOIN users ON users.id = boards.user_id WHERE users.username = ?""", (username,)).fetchone()
    if board is None:
        raise HTTPException(404, "Board not found")
    return board


def snapshot(db: sqlite3.Connection, board_id: int) -> dict:
    columns = [{"id": row["id"], "title": row["title"], "cardIds": []} for row in db.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position", (board_id,))]
    by_column = {column["id"]: column for column in columns}
    cards = {}
    for row in db.execute("SELECT * FROM cards WHERE board_id = ? ORDER BY position, id", (board_id,)):
        cards[row["id"]] = {key: row[key] for key in ("id", "title", "details")}
        by_column[row["column_id"]]["cardIds"].append(row["id"])
    revision = db.execute("SELECT revision FROM boards WHERE id = ?", (board_id,)).fetchone()[0]
    return {"columns": columns, "cards": cards, "revision": revision}


def read_board(path: Path, username: str) -> dict:
    with transaction(path) as db:
        return snapshot(db, owned_board(db, username)["id"])


def mutate_board(path: Path, username: str, expected_revision: int,
                 operation: Callable[[sqlite3.Connection, int], bool]) -> dict:
    with transaction(path, write=True) as db:
        board = owned_board(db, username)
        if board["revision"] != expected_revision:
            raise HTTPException(409, "Board changed. Reload and try again.")
        if operation(db, board["id"]):
            db.execute("UPDATE boards SET revision = revision + 1 WHERE id = ?", (board["id"],))
        return snapshot(db, board["id"])


def column_exists(db, board_id, column_id):
    row = db.execute("SELECT title FROM columns WHERE board_id = ? AND id = ?", (board_id, column_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Column not found")
    return row


def get_card(db, board_id, card_id):
    row = db.execute("SELECT * FROM cards WHERE board_id = ? AND id = ?", (board_id, card_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Card not found")
    return row


def card_ids(db, board_id, column_id):
    return [row[0] for row in db.execute(
        "SELECT id FROM cards WHERE board_id = ? AND column_id = ? ORDER BY position, id", (board_id, column_id))]


def write_order(db, board_id, column_id, ids):
    db.executemany("UPDATE cards SET column_id = ?, position = ? WHERE board_id = ? AND id = ?",
                   [(column_id, position, board_id, card_id) for position, card_id in enumerate(ids)])


def rename_column(db, board_id, column_id, title):
    old = column_exists(db, board_id, column_id)
    if old["title"] == title:
        return False
    db.execute("UPDATE columns SET title = ? WHERE board_id = ? AND id = ?", (title, board_id, column_id))
    return True


def create_card(db, board_id, column_id, title, details, position):
    column_exists(db, board_id, column_id)
    ids = card_ids(db, board_id, column_id)
    position = len(ids) if position is None else position
    if not 0 <= position <= len(ids):
        raise HTTPException(422, "Position outside destination column")
    card_id = str(uuid4())
    db.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?)",
               (card_id, board_id, column_id, title, details, position))
    ids.insert(position, card_id)
    write_order(db, board_id, column_id, ids)
    return True


def edit_card(db, board_id, card_id, title, details):
    old = get_card(db, board_id, card_id)
    if (old["title"], old["details"]) == (title, details):
        return False
    db.execute("UPDATE cards SET title = ?, details = ? WHERE board_id = ? AND id = ?",
               (title, details, board_id, card_id))
    return True


def move_card(db, board_id, card_id, column_id, position):
    card = get_card(db, board_id, card_id)
    column_exists(db, board_id, column_id)
    source = card["column_id"]
    old_order = card_ids(db, board_id, source)
    destination = [cid for cid in card_ids(db, board_id, column_id) if cid != card_id]
    if not 0 <= position <= len(destination):
        raise HTTPException(422, "Position outside destination column")
    destination.insert(position, card_id)
    if source == column_id and destination == old_order:
        return False
    if source != column_id:
        write_order(db, board_id, source, [cid for cid in old_order if cid != card_id])
    write_order(db, board_id, column_id, destination)
    return True


def delete_card(db, board_id, card_id):
    card = get_card(db, board_id, card_id)
    db.execute("DELETE FROM cards WHERE board_id = ? AND id = ?", (board_id, card_id))
    write_order(db, board_id, card["column_id"], card_ids(db, board_id, card["column_id"]))
    return True
