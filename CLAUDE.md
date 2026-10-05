# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Project requirements, technical decisions, color palette, and coding standards live in the root `AGENTS.md` (imported below). Each area has its own detailed instructions; read the relevant one before changing code there:

- `backend/AGENTS.md`: auth/sessions, persistent boards, OpenRouter client, structured chat rules
- `frontend/AGENTS.md`: component map, save/revision behavior, styling, test inventory
- `scripts/AGENTS.md`: start/stop script constraints
- `docs/PLAN.md`: completed parts and verification records (`docs/PARTn.md`); `docs/DATABASE.md` and `docs/database-schema.json` for the schema

@AGENTS.md

## Commands

Full app (Docker, port 8000): `./scripts/start.sh` / `./scripts/stop.sh`. Stop must never remove the `pm-data` volume.

Backend (from `backend/`, Python 3.14 + uv):

- `uv run --locked pytest`: all tests
- `uv run --locked pytest tests/test_board.py::test_name`: single test
- `uv run --locked uvicorn app.main:app --reload`: dev server (build the frontend first to serve `/`)
- `docker compose exec -T app python -m app.check_openrouter`: live OpenRouter check (needs a real key; normal tests mock HTTP)

Frontend (from `frontend/`, Node 24, `npm ci`):

- `npm run lint`, `npx tsc --noEmit`, `npm run test:unit`
- `npx vitest run src/lib/kanban.test.ts` or `npx vitest run -t "name"`: single unit test
- `npm run build`: static export to `out/` (needs Google Fonts network access)
- `npm start`: serve the export through FastAPI on 8000 (real sign-in only works this way or via Docker; `npm run dev` has no API)
- `npm run test:e2e`: Playwright; set `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000` to target the running Docker app. Board/auth specs need the real backend.
- Deterministic chat e2e: run `backend/tests/browser_app.py` (mocked OpenRouter, temp DB) on port 8001 and use `CHAT_MOCK_BACKEND=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:8001`. See `docs/PART10.md` for the exact commands. Never set `CHAT_MOCK_BACKEND` against a live-provider backend.

## Architecture

One container: a Node build stage runs `next build` (static export, no Next server, no API routes or Server Actions). The Python stage copies `out/` to `/app/static`, and FastAPI serves it at `/` with all APIs under `/api`. In `app/main.py`, new routers must be registered before the `/api` JSON 404 fallback and the static mount.

Request flow: `AuthGate` checks `/api/auth/session` and then mounts `KanbanBoard`, which loads `/api/board`. Sessions are opaque tokens in in-memory `app.state.sessions` (cookie `pm_session`), so run only one worker, and a restart logs everyone out. Every protected route depends on `current_user`. The acting user and board always come from the session, never from the request body.

Board consistency model: the backend is authoritative. Each board has a `revision`. Every mutation sends `expected_revision`, runs in a single `BEGIN IMMEDIATE` transaction (`board.py`), increments the revision once, and returns the full board, which the frontend adopts. A stale revision returns 409, and a SQLite lock timeout returns 503. The frontend runs one mutation at a time (a shared save lock that also covers chat) and reloads authoritative state after any failure.

AI chat (`chat.py`): it reads the board, closes the transaction, calls OpenRouter (`openrouter.complete`, model `openai/gpt-oss-120b`, JSON-schema response format), validates the `Proposal` (max 20 create/edit/move ops, no deletes or column renames), then applies it through `mutate_board` against the original revision in one transaction. Invalid output returns 502 with no partial writes. Chat history lives only in browser memory (`ChatSidebar`) and is sent with each request; it is never persisted. Keep `docs/ai-response-schema.json` in sync with the `Proposal` models.

Database: SQLite via plain `sqlite3` (no ORM), `schema.sql` at `user_version = 1`, foreign keys enabled per connection. The five fixed column IDs (`col-backlog` ... `col-done`) are reused across boards, so column/card queries always include `board_id`. Seeding happens once per board (at registration or a startup backfill) and never resets existing data. Tests must pass a temporary `database_path` to `create_app`.
