import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from app.users import UsernameTaken, add_user, verify_user

COOKIE = "pm_session"
SESSION_SECONDS = 8 * 60 * 60
router = APIRouter(prefix="/api/auth")


class Credentials(BaseModel):
    username: str
    password: str = Field(max_length=128)


class Registration(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


def current_user(request: Request) -> str:
    token = request.cookies.get(COOKIE)
    session = request.app.state.sessions.get(token)
    if session is None or session[1] <= time.time():
        request.app.state.sessions.pop(token, None)
        raise HTTPException(401, "Sign in required")
    return session[0]


def start_session(username: str, request: Request, response: Response):
    sessions = request.app.state.sessions
    now = time.time()
    for token, (_, expires) in list(sessions.items()):
        if expires <= now:
            sessions.pop(token)
    sessions.pop(request.cookies.get(COOKIE), None)
    token = secrets.token_urlsafe(32)
    sessions[token] = (username, now + SESSION_SECONDS)
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"username": username}


@router.post("/login")
def login(credentials: Credentials, request: Request, response: Response):
    if not verify_user(request.app.state.database_path, credentials.username, credentials.password):
        raise HTTPException(401, "Invalid username or password")
    return start_session(credentials.username, request, response)


@router.post("/register", status_code=201)
def register(credentials: Registration, request: Request, response: Response):
    try:
        add_user(request.app.state.database_path, credentials.username, credentials.password)
    except UsernameTaken:
        raise HTTPException(409, "Username already taken") from None
    return start_session(credentials.username, request, response)


@router.get("/session")
def session(response: Response, username: Annotated[str, Depends(current_user)]):
    response.headers["Cache-Control"] = "no-store"
    return {"username": username}


@router.post("/logout", status_code=204)
def logout(request: Request):
    request.app.state.sessions.pop(request.cookies.get(COOKIE), None)
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
    return response
