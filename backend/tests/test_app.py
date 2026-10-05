import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Board</h1>")
    (tmp_path / "404.html").write_text("<h1>Page not found</h1>")
    assets = tmp_path / "_next" / "static"
    assets.mkdir(parents=True)
    (assets / "app.js").write_text("console.log('board')")
    with TestClient(create_app(tmp_path, tmp_path / "test.sqlite3")) as client:
        yield client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_page_and_script(client):
    page = client.get("/")
    script = client.get("/_next/static/app.js")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "Board" in page.text
    assert script.status_code == 200
    assert "console.log('board')" in script.text


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_missing_api_returns_json_not_frontend(client, method):
    response = getattr(client, method)("/api/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_missing_page_returns_html_404(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert "Page not found" in response.text
