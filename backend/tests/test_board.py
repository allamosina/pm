import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import board, users
from app.database import transaction
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path, tmp_path / "board.sqlite3")) as client:
        client.post("/api/auth/login", json={"username": "user", "password": "password"})
        yield client


def get(client):
    response = client.get("/api/board")
    assert response.status_code == 200
    return response.json()


def ids(snapshot, column):
    return next(c["cardIds"] for c in snapshot["columns"] if c["id"] == column)


def change(client, method, path, **payload):
    payload["expected_revision"] = get(client)["revision"]
    response = client.request(method, "/api/board" + path, json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()


def assert_order_integrity(client):
    snapshot = get(client)
    members = [cid for c in snapshot["columns"] for cid in c["cardIds"]]
    assert sorted(members) == sorted(snapshot["cards"])
    assert len(members) == len(set(members))
    with transaction(client.app.state.database_path) as db:
        for row in db.execute("SELECT DISTINCT board_id, column_id FROM cards"):
            positions = [r[0] for r in db.execute(
                "SELECT position FROM cards WHERE board_id=? AND column_id=? ORDER BY position", tuple(row))]
            assert positions == list(range(len(positions)))
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_initial_board_and_shape(client):
    value = get(client)
    assert set(value) == {"columns", "cards", "revision"}
    assert value["revision"] == 0
    assert [c["id"] for c in value["columns"]] == ["col-backlog", "col-discovery", "col-progress", "col-review", "col-done"]
    assert len(value["cards"]) == 8
    for cid, card in value["cards"].items():
        assert UUID(cid).version == 4
        assert set(card) == {"id", "title", "details"}
    assert client.get("/api/board").headers["cache-control"] == "no-store"
    assert_order_integrity(client)


def test_create_edit_rename_delete(client):
    initial = get(client)
    created = change(client, "POST", "/cards", column_id="col-backlog", title="  New card  ", details="", position=1)
    cid = next(iter(set(created["cards"]) - set(initial["cards"])))
    assert ids(created, "col-backlog")[1] == cid
    assert created["cards"][cid] == {"id": cid, "title": "New card", "details": ""}
    edited = change(client, "PATCH", f"/cards/{cid}", title="Edited", details="Updated notes")
    assert edited["cards"][cid]["details"] == "Updated notes"
    renamed = change(client, "PATCH", "/columns/col-review", title="  QA  ")
    assert renamed["columns"][3]["title"] == "QA"
    response = client.delete(f"/api/board/cards/{cid}", params={"expected_revision": renamed["revision"]})
    assert response.status_code == 200
    assert cid not in response.json()["cards"]
    assert response.json()["revision"] == 4
    assert ids(response.json(), "col-backlog") == ids(initial, "col-backlog")
    assert_order_integrity(client)


def test_append_and_move_reorder_empty_column(client):
    initial = get(client)
    a, b = ids(initial, "col-backlog")
    value = change(client, "POST", f"/cards/{b}/move", column_id="col-backlog", position=0)
    assert ids(value, "col-backlog") == [b, a]
    value = change(client, "POST", f"/cards/{b}/move", column_id="col-review", position=1)
    assert ids(value, "col-backlog") == [a]
    assert ids(value, "col-review")[-1] == b
    value = change(client, "POST", f"/cards/{a}/move", column_id="col-review", position=0)
    assert ids(value, "col-backlog") == []
    value = change(client, "POST", f"/cards/{b}/move", column_id="col-backlog", position=0)
    assert ids(value, "col-backlog") == [b]
    value = change(client, "POST", "/cards", column_id="col-backlog", title="Append")
    assert ids(value, "col-backlog")[0] == b
    assert len(ids(value, "col-backlog")) == 2
    assert_order_integrity(client)


def test_noop_preserves_revision(client):
    before = get(client)
    cid = ids(before, "col-backlog")[0]
    assert change(client, "POST", f"/cards/{cid}/move", column_id="col-backlog", position=0) == before
    assert change(client, "PATCH", "/columns/col-backlog", title="Backlog") == before
    assert change(client, "PATCH", f"/cards/{cid}", title=before["cards"][cid]["title"], details=before["cards"][cid]["details"]) == before


@pytest.mark.parametrize("payload", [
    {"title": " "}, {"title": "\t\n"}, {"title": "x" * 201}, {"title": None},
    {"details": "x" * 10001}, {"details": None}, {"column_id": "missing"},
    {"position": -1}, {"position": 500}, {"position": 1.5}, {"position": True},
    {"expected_revision": -1}, {"expected_revision": True},
    {"board_id": 2}, {"user_id": 2},
])
def test_invalid_create_is_atomic(client, payload):
    before = get(client)
    response = client.post("/api/board/cards", json={"column_id": "col-backlog", "title": "Card", "expected_revision": 0, **payload})
    assert response.status_code in (404, 422)
    assert get(client) == before


@pytest.mark.parametrize("title", ["", "  ", "x" * 81, None])
def test_invalid_column_title(client, title):
    before = get(client)
    assert client.patch("/api/board/columns/col-backlog", json={"title": title, "expected_revision": 0}).status_code == 422
    assert get(client) == before


def test_invalid_moves_and_unknown_ids(client):
    before = get(client)
    cid = ids(before, "col-backlog")[0]
    for column, position, status in [("missing", 0, 404), ("col-review", 100, 422), ("col-review", -1, 422), ("col-backlog", 2, 422)]:
        assert client.post(f"/api/board/cards/{cid}/move", json={"column_id": column, "position": position, "expected_revision": 0}).status_code == status
        assert get(client) == before
    assert client.patch("/api/board/columns/missing", json={"title": "Title", "expected_revision": 0}).status_code == 404
    assert client.patch("/api/board/cards/missing", json={"title": "Title", "details": "", "expected_revision": 0}).status_code == 404
    assert client.delete("/api/board/cards/missing?expected_revision=0").status_code == 404


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "", None),
    ("POST", "/cards", {"title": "Card", "column_id": "col-backlog", "expected_revision": 0}),
    ("PATCH", "/columns/col-backlog", {"title": "Name", "expected_revision": 0}),
    ("PATCH", "/cards/missing", {"title": "Name", "details": "", "expected_revision": 0}),
    ("POST", "/cards/missing/move", {"column_id": "col-backlog", "position": 0, "expected_revision": 0}),
    ("DELETE", "/cards/missing?expected_revision=0", None),
])
def test_all_board_routes_require_login(client, method, path, payload):
    client.post("/api/auth/logout")
    assert client.request(method, "/api/board" + path, json=payload).status_code == 401


def test_cross_user_isolation(client):
    alice = get(client)
    cid = next(iter(alice["cards"]))
    assert client.post("/api/auth/register", json={"username": "bob", "password": "password"}).status_code == 201
    bob = get(client)
    assert set(alice["cards"]).isdisjoint(bob["cards"])
    for method, suffix, payload in [
        ("PATCH", f"/cards/{cid}", {"title": "Stolen", "details": "", "expected_revision": 0}),
        ("POST", f"/cards/{cid}/move", {"column_id": "col-done", "position": 0, "expected_revision": 0}),
        ("DELETE", f"/cards/{cid}?expected_revision=0", None),
    ]:
        assert client.request(method, "/api/board" + suffix, json=payload).status_code == 404
        assert get(client) == bob
    change(client, "PATCH", "/columns/col-backlog", title="Bob's backlog")
    client.post("/api/auth/login", json={"username": "user", "password": "password"})
    assert get(client) == alice


def test_stale_revision_is_rejected(client):
    changed = change(client, "PATCH", "/columns/col-backlog", title="Ideas")
    assert client.post("/api/board/cards", json={"column_id": "col-backlog", "title": "Stale", "expected_revision": 0}).status_code == 409
    assert get(client) == changed
    assert client.post("/api/board/cards", json={"column_id": "col-backlog", "title": "No revision"}).status_code == 422


def test_concurrent_writes_use_revision_check(client):
    gate = Barrier(2)
    def update(title):
        gate.wait()
        try:
            return board.mutate_board(client.app.state.database_path, "user", 0,
                lambda db, bid: board.rename_column(db, bid, "col-backlog", title))
        except HTTPException as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ["First", "Second"]))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    assert get(client)["revision"] == 1


def test_partial_move_rolls_back(client, monkeypatch):
    before = get(client)
    cid = ids(before, "col-backlog")[0]
    original = board.write_order
    def fail_after_write(*args):
        original(*args)
        raise sqlite3.IntegrityError("Injected write failure")
    monkeypatch.setattr(board, "write_order", fail_after_write)
    with pytest.raises(sqlite3.IntegrityError):
        change(client, "POST", f"/cards/{cid}/move", column_id="col-review", position=0)
    assert get(client) == before
    assert_order_integrity(client)


def test_registration_seed_failure_rolls_back_account(client, monkeypatch):
    original = users.create_board
    def fail_after_seed(*args):
        original(*args)
        raise sqlite3.IntegrityError("Injected seed failure")
    monkeypatch.setattr(users, "create_board", fail_after_seed)
    with pytest.raises(sqlite3.IntegrityError):
        client.post("/api/auth/register", json={"username": "failed", "password": "password"})
    with transaction(client.app.state.database_path) as db:
        assert db.execute("SELECT id FROM users WHERE username='failed'").fetchone() is None
        assert db.execute("SELECT COUNT(*) FROM boards").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 8


def test_legacy_accounts_and_reopen_persistence(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL)")
        saved_hash = users.password_hash.hash("legacy-password")
        db.execute("INSERT INTO users VALUES (42, 'legacy', ?)", (saved_hash,))
    with TestClient(create_app(tmp_path, path)) as first:
        assert first.post("/api/auth/login", json={"username": "legacy", "password": "legacy-password"}).status_code == 200
        original = get(first)
        assert len(original["cards"]) == 8
        changed = change(first, "PATCH", "/columns/col-review", title="Persisted QA")
        for cid in list(changed["cards"]):
            changed = first.delete(f"/api/board/cards/{cid}", params={"expected_revision": changed["revision"]}).json()
    with TestClient(create_app(tmp_path, path)) as second:
        second.post("/api/auth/login", json={"username": "legacy", "password": "legacy-password"})
        assert get(second) == changed
        assert not get(second)["cards"]
        with transaction(path) as db:
            assert tuple(db.execute("SELECT id,password_hash FROM users WHERE username='legacy'").fetchone()) == (42, saved_hash)
            assert db.execute("SELECT COUNT(*) FROM boards").fetchone()[0] == 2
            assert db.execute("PRAGMA user_version").fetchone()[0] == 1
            assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_future_database_version_not_modified(tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=2")
    with pytest.raises(RuntimeError, match="Unsupported database version"):
        users.initialize_users(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert not db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()


def test_foreign_keys_and_fixed_columns(client):
    with transaction(client.app.state.database_path, write=True) as db:
        bid = board.owned_board(db, "user")["id"]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO columns VALUES (?, 'extra', 'Extra', 5)", (bid,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE cards SET column_id='unknown' WHERE board_id=?", (bid,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO boards(user_id) VALUES ((SELECT id FROM users WHERE username='user'))")


def test_revision_and_changes_roll_back_if_response_read_fails(client, monkeypatch):
    before = get(client)
    original = board.snapshot
    def fail_snapshot(*args):
        raise sqlite3.OperationalError("Injected read failure")
    monkeypatch.setattr(board, "snapshot", fail_snapshot)
    with pytest.raises(sqlite3.OperationalError):
        client.patch("/api/board/columns/col-backlog", json={"title": "Not committed", "expected_revision": 0})
    monkeypatch.setattr(board, "snapshot", original)
    assert get(client) == before


def test_busy_database_returns_retry_response(client):
    with transaction(client.app.state.database_path, write=True):
        response = client.patch("/api/board/columns/col-backlog", json={"title": "Busy", "expected_revision": 0})
    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
    assert get(client)["revision"] == 0


def test_schema_initialization_failure_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / "interrupted.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL)")
        db.execute("INSERT INTO users VALUES (1, 'existing', 'unchanged')")
    original = users.initialize_schema
    def fail_after_schema(db):
        original(db)
        raise RuntimeError("Interrupted migration")
    monkeypatch.setattr(users, "initialize_schema", fail_after_schema)
    with pytest.raises(RuntimeError, match="Interrupted migration"):
        users.initialize_users(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("users",)]
        assert db.execute("SELECT password_hash FROM users").fetchone()[0] == "unchanged"
    monkeypatch.setattr(users, "initialize_schema", original)
    users.initialize_users(path)
    with transaction(path) as db:
        assert db.execute("SELECT COUNT(*) FROM boards").fetchone()[0] == 2
