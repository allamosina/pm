# Backend instructions

Follow root `AGENTS.md` and `docs/PLAN.md`. Part 4 and the registration extension provide persistent user accounts. Part 6 implements persistent boards and authenticated board APIs. Part 8 provides a backend OpenRouter client and explicit live connectivity check; Part 9 implements authenticated structured AI changes; Part 10 connects the browser sidebar.

- Python 3.14, FastAPI, and Uvicorn. Dependencies are declared in `pyproject.toml` and locked in `uv.lock`; use `uv` to manage them.
- `app/main.py` exposes `create_app`, `GET /api/health`, a JSON 404 for unknown `/api/*` routes, and the exported frontend at `/`. `STATIC_DIR` overrides the default `frontend/out/` directory; Docker sets it to `/app/static`.
- Resolve static paths relative to the module, not the current working directory. Register future API routes before the API fallback and static mount.
- From `backend/`: `uv run --locked pytest` runs tests; `uv run --locked uvicorn app.main:app --reload` starts local development. Build the frontend first to serve `/`.
- `tests/test_app.py` checks health, static assets, JSON API errors, and HTML 404s using FastAPI TestClient with an isolated static fixture. Browser tests exercise the actual export.
- Docker installs only runtime dependencies. Compose uses `/data/pm.sqlite3` through `DATABASE_PATH` for users and the approved Kanban tables (schema version 1).
- Keep secrets on the backend and out of logs and source control.

## Authentication

- `app/auth.py` provides POST `/api/auth/login`, GET `/api/auth/session`, and POST `/api/auth/logout`. POST `/api/auth/register` creates accounts and signs them in. The seeded `user` / `password` demo account remains available.
- `current_user` is the shared FastAPI dependency for authenticated identity. Board routes already use it; add it to every future AI route; never accept the acting user from client input.
- Sessions use random opaque tokens in `app.state.sessions`, a browser-session cookie named `pm_session` (HttpOnly, SameSite=Strict, Path=/), and an eight-hour server expiry. Secure is omitted because this MVP uses local HTTP.
- Logout revokes the token server-side; repeated logout is harmless. Login rotates the current cookie's token. Restarting the single backend process invalidates sessions. Do not run multiple workers with this in-memory session store.
- Tests in `tests/test_auth.py` cover credentials, cookie flags, rotation, expiry, independent sessions, invalid tokens, and replay after logout.

- `app/users.py` initializes SQLite at app startup and stores Argon2 hashes via pwdlib. Local default: `backend/data/pm.sqlite3`. Tests must pass a temporary `database_path` to `create_app`.
- Registration usernames are case-sensitive, 3–32 ASCII letters/digits/underscores/hyphens; passwords are 8–128 characters and never trimmed. SQLite uniqueness handles duplicate registration atomically.
- Sessions currently identify a user by the immutable unique username. Board operations resolve its database ID and owning board.
- Current full schema: `docs/database-schema.json`; API contract and verification: `docs/PART6.md`. Never reset existing accounts or reseed existing boards.

## Persistent boards

- `database.py` opens connections with foreign keys enabled and explicit read/write transactions. `schema.sql` defines version 1; reject unsupported newer versions. Do not use `executescript` inside an active transaction.
- `seed.py` creates five fixed columns and eight example cards with fresh UUIDs once per board. Startup backfills existing users; registration creates the account and board atomically.
- `board.py` provides ownership-scoped reads, revision-checked mutations, and reusable operations; `board_api.py` defines `/api/board` endpoints. All mutations return the authoritative board and require `expected_revision`.
- Every card operation must include the authenticated board ID, even though card UUIDs are globally unique. Every column operation requires board ID plus stable stage ID.
- Keep position changes and revision increments in one transaction. Preserve no-op revisions; reject stale requests with 409. SQLite lock timeouts return 503 with retry feedback.
- `tests/test_board.py` covers temporary-file persistence, migration, ownership, ordering, concurrency, and rollback. The frontend uses these APIs as of Part 7.

## OpenRouter

- `app/openrouter.py` provides async `complete(messages, response_format=None)` using runtime `OPENROUTER_API_KEY` and fixed `openai/gpt-oss-120b`. Compose injects the root `.env` at runtime; direct Python execution needs the environment variable set.
- Uses locked runtime `httpx2`, non-streaming completions, 2048 output tokens, low reasoning effort, parameter-compatible provider routing, a 10-second connection timeout, and a 60-second total deadline. No automatic retries or model fallback.
- `OpenRouterError` contains a safe code/message. Never return/log raw provider errors, request headers, prompts, or keys. Check embedded errors even for HTTP 200; reject empty/truncated responses.
- `response_format` can pass a JSON Schema to compatible providers. The chat service validates the resulting content and board operations; this client returns text only.
- `docker compose exec -T app python -m app.check_openrouter` explicitly runs the live `2+2` check. Normal tests use mocked HTTP and require no real key/network.
- `tests/test_openrouter.py` covers construction, parsing, missing configuration, HTTP/embedded errors, network timeouts, total deadline, incomplete responses, and live-check logic. Part 8 adds no public AI route.

## Structured chat

- `app/chat.py` exposes authenticated POST `/api/chat` with `question` and optional user/assistant `history`. It returns `reply` and the authoritative `board`; history is not stored server-side.
- `Proposal` defines strict create/edit/move operations; the generated format is documented in `docs/ai-response-schema.json`. Keep the documentation synchronized when the models change.
- Read current state before generation; never hold a database transaction across a provider call. SQLite work runs in the thread pool.
- Recheck session after generation and use `mutate_board` with the original revision. Validate every reference and sequential position before writes; reuse manual operations in one transaction. Reject stale reply-only results too.
- At most 20 operations. New-card IDs are generated by SQLite service code and cannot be referenced within the same proposal. No AI delete/column rename operations.
- Invalid provider output returns 502 without partial changes. Provider authentication errors must not return 401 (reserved for app session expiry). See `docs/PART9.md` for limits, tests, and live-provider limitations.

- `tests/browser_app.py` is an isolated deterministic browser fixture, never a production entry point. Use a temporary database; see `docs/PART10.md`.
