import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.auth import router as auth_router
from app.board_api import router as board_router
from app.users import initialize_users
from app.chat import router as chat_router

def create_app(static_dir: Path | None = None, database_path: Path | None = None) -> FastAPI:
    database_path = database_path or Path(os.environ.get(
        "DATABASE_PATH", Path(__file__).resolve().parents[1] / "data" / "pm.sqlite3"
    ))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialize_users(database_path)
        yield

    app = FastAPI(title="Project Management API", lifespan=lifespan)
    app.state.database_path = database_path
    app.state.sessions = {}
    app.include_router(auth_router)
    app.include_router(board_router)
    app.include_router(chat_router)

    @app.exception_handler(sqlite3.OperationalError)
    async def database_error(request: Request, error: sqlite3.OperationalError):
        if getattr(error, "sqlite_errorcode", 0) & 0xFF in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            return JSONResponse(status_code=503, content={"detail": "Database busy. Please retry."},
                                headers={"Retry-After": "1"})
        raise error

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
    def missing_api(path: str) -> None:
        raise HTTPException(status_code=404, detail="Not Found")

    directory = static_dir or Path(
        os.environ.get("STATIC_DIR", Path(__file__).resolve().parents[2] / "frontend" / "out")
    )
    app.mount("/", StaticFiles(directory=directory, html=True, check_dir=False))
    return app


app = create_app()
