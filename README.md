# Project Management MVP

Requires Docker Desktop (macOS/Windows), or Docker Engine with Compose v2 (Linux), running with Linux containers.

- macOS/Linux: `./scripts/start.sh` / `./scripts/stop.sh`
- Windows PowerShell: `./scripts/start.ps1` / `./scripts/stop.ps1`
- Open http://localhost:8000. Choose **Create an account**, or sign in with the demo `user` / `password`, to see the Kanban board; `/api/health` reports server status. Board edits persist across reloads and restarts. Use Edit on a card, and Save column after renaming a stage.

Compose reads `OPENROUTER_API_KEY` from the root `.env` if present; manual board operations work without it. Stop preserves the `pm-data` volume containing SQLite accounts and boards. Port 8000 must be free.

Backend tests: `cd backend && uv run --locked pytest` (Python 3.14 and `uv`).
Plan and verification notes: [docs/PLAN.md](docs/PLAN.md), [docs/PART10.md](docs/PART10.md).

Live AI connectivity check: `docker compose exec -T app python -m app.check_openrouter` (requires a valid key). Authenticated AI changes are available at `POST /api/chat`; use the Board assistant sidebar to create, edit, or move cards. Conversation clears on reload/sign-out.
