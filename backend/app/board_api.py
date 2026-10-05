from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app import board
from app.auth import current_user

router = APIRouter(prefix="/api/board", tags=["board"])
User = Annotated[str, Depends(current_user)]
Revision = Annotated[int, Field(strict=True, ge=0)]
Position = Annotated[int, Field(strict=True, ge=0)]
CardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ColumnTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Details = Annotated[str, StringConstraints(max_length=10000)]


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: Revision


class RenameColumn(Mutation):
    title: ColumnTitle


class CreateCard(Mutation):
    column_id: str
    title: CardTitle
    details: Details = ""
    position: Position | None = None


class EditCard(Mutation):
    title: CardTitle
    details: Details


class MoveCard(Mutation):
    column_id: str
    position: Position


class Card(BaseModel):
    id: str
    title: str
    details: str


class Column(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class Board(BaseModel):
    columns: list[Column]
    cards: dict[str, Card]
    revision: int


def mutate(request, response, username, revision, operation):
    result = board.mutate_board(request.app.state.database_path, username, revision, operation)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("", response_model=Board)
def get_board(request: Request, response: Response, username: User):
    response.headers["Cache-Control"] = "no-store"
    return board.read_board(request.app.state.database_path, username)


@router.patch("/columns/{column_id}", response_model=Board)
def rename(column_id: str, payload: RenameColumn, request: Request, response: Response, username: User):
    return mutate(request, response, username, payload.expected_revision,
                  lambda db, bid: board.rename_column(db, bid, column_id, payload.title))


@router.post("/cards", response_model=Board, status_code=201)
def create(payload: CreateCard, request: Request, response: Response, username: User):
    return mutate(request, response, username, payload.expected_revision,
                  lambda db, bid: board.create_card(db, bid, payload.column_id, payload.title, payload.details, payload.position))


@router.patch("/cards/{card_id}", response_model=Board)
def edit(card_id: str, payload: EditCard, request: Request, response: Response, username: User):
    return mutate(request, response, username, payload.expected_revision,
                  lambda db, bid: board.edit_card(db, bid, card_id, payload.title, payload.details))


@router.post("/cards/{card_id}/move", response_model=Board)
def move(card_id: str, payload: MoveCard, request: Request, response: Response, username: User):
    return mutate(request, response, username, payload.expected_revision,
                  lambda db, bid: board.move_card(db, bid, card_id, payload.column_id, payload.position))


@router.delete("/cards/{card_id}", response_model=Board)
def delete(card_id: str, request: Request, response: Response, username: User,
           expected_revision: Annotated[int, Query(ge=0)]):
    return mutate(request, response, username, expected_revision,
                  lambda db, bid: board.delete_card(db, bid, card_id))
