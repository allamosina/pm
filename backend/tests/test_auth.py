import time

import pytest
from fastapi.testclient import TestClient

from app.auth import COOKIE
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text("Public shell")
    with TestClient(create_app(tmp_path, tmp_path / "test.sqlite3")) as client:
        yield client


def sign_in(client):
    return client.post("/api/auth/login", json={"username": "user", "password": "password"})


def test_session_requires_authentication_and_shell_is_public(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/auth/session").status_code == 401
    client.cookies.set(COOKIE, "forged-token")
    assert client.get("/api/auth/session").status_code == 401


@pytest.mark.parametrize("username,password", [("user", "wrong"), ("wrong", "password"), ("USER", "password"), ("", "")])
def test_wrong_credentials(client, username, password):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 401
    assert COOKIE not in client.cookies
    assert client.get("/api/auth/session").status_code == 401


def test_login_session_and_cookie_flags(client):
    response = sign_in(client)
    assert response.json() == {"username": "user"}
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie
    assert "Secure" not in cookie  # Local HTTP MVP.
    assert "Max-Age" not in cookie  # Browser-session cookie.
    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json() == {"username": "user"}
    assert session.headers["cache-control"] == "no-store"


def test_logout_revokes_token_even_if_replayed(client):
    sign_in(client)
    old_token = client.cookies[COOKIE]
    assert client.post("/api/auth/logout").status_code == 204
    assert COOKIE not in client.cookies
    client.cookies.set(COOKIE, old_token)
    assert client.get("/api/auth/session").status_code == 401
    assert client.post("/api/auth/logout").status_code == 204


def test_login_rotates_session(client):
    sign_in(client)
    old_token = client.cookies[COOKIE]
    sign_in(client)
    assert client.cookies[COOKIE] != old_token
    client.cookies.clear()
    client.cookies.set(COOKIE, old_token)
    assert client.get("/api/auth/session").status_code == 401


def test_expired_session(client):
    sign_in(client)
    token = client.cookies[COOKIE]
    client.app.state.sessions[token] = ("user", time.time() - 1)
    assert client.get("/api/auth/session").status_code == 401
    assert token not in client.app.state.sessions


def test_sessions_are_independent(client):
    sign_in(client)
    first_token = client.cookies[COOKIE]
    client.cookies.clear()
    sign_in(client)
    client.post("/api/auth/logout")
    client.cookies.set(COOKIE, first_token)
    assert client.get("/api/auth/session").status_code == 200


def test_malformed_login(client):
    assert client.post("/api/auth/login", json={"username": "user"}).status_code == 422


def test_registration_login_and_password_storage(client):
    import sqlite3
    from contextlib import closing
    payload = {"username": "alice", "password": "a-long-password"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json() == {"username": "alice"}
    assert client.get("/api/auth/session").json() == {"username": "alice"}
    with closing(sqlite3.connect(client.app.state.database_path)) as db:
        stored = db.execute("SELECT password_hash FROM users WHERE username = ?", ("alice",)).fetchone()[0]
    assert stored.startswith("$argon2id$")
    assert payload["password"] not in stored
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={**payload, "password": "incorrect"}).status_code == 401
    assert client.post("/api/auth/login", json=payload).status_code == 200


def test_duplicate_registration_does_not_replace_password(client):
    payload = {"username": "alice", "password": "original-password"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json={**payload, "password": "replacement-password"}).status_code == 409
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json=payload).status_code == 200
    assert client.post("/api/auth/register", json={"username": "user", "password": "replacement-password"}).status_code == 409


@pytest.mark.parametrize("username,password", [("ab", "password"), ("a b", "password"), ("a" * 33, "password"), ("alice", "short"), ("alice", "x" * 129)])
def test_registration_validation(client, username, password):
    assert client.post("/api/auth/register", json={"username": username, "password": password}).status_code == 422
    assert client.get("/api/auth/session").status_code == 401


def test_accounts_survive_app_restart(tmp_path):
    database_path = tmp_path / "accounts.sqlite3"
    payload = {"username": "persistent", "password": "test-password"}
    with TestClient(create_app(tmp_path, database_path)) as first:
        first.post("/api/auth/register", json=payload)
        old_token = first.cookies[COOKIE]
    with TestClient(create_app(tmp_path, database_path)) as second:
        second.cookies.set(COOKIE, old_token)
        assert second.get("/api/auth/session").status_code == 401
        assert second.post("/api/auth/login", json=payload).json() == {"username": "persistent"}
        assert sign_in(second).status_code == 200
