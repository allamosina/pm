# Part 10: AI sidebar and final acceptance

Completed 2026-10-05.

## User experience

The Board assistant sits beside the board on wide screens and below it on narrow screens. It can answer questions and create/edit/move cards. Successful replies immediately replace board state with the committed server snapshot.

Conversation and message drafts live only in React memory and clear on reload/logout/session expiry. Each request includes the most recent 40 successful history messages. Failed turns are not added to history; drafts remain for review and retry. Messages render as plain text. The conversation region scrolls to new messages and supports keyboard focus.

AI and manual operations share one synchronous save lock, preventing overlapping requests. Card controls and dragging are disabled while requests are pending. Chat submission is disabled during active dragging. Failures reload authoritative board state; an unsuccessful reload blocks further mutations until recovery. Network uncertainty is reported without implying success or inviting a blind retry.

Keyboard users can focus a card's text handle, press Space to pick it up, use arrows to move it, then Space to drop or Escape to cancel. Pointer targeting prefers the card or column under the pointer; keyboard collision detection uses distance. Forms retain their existing save/cancel controls.

## Final verification

- ESLint, TypeScript and 26 frontend unit/component tests: passed after final source changes.
- Complete backend suite: 131 passed in 21.49 seconds.
- Production Docker/static build and healthy startup: passed.
- Ten browser acceptance cases passed across the final acceptance run (nine cases) and focused keyboard follow-up (one case). Tests used the actual Docker-exported frontend with FastAPI and SQLite; only the OpenRouter function was mocked in an isolated test entry point.
- Browser coverage: authentication/registration, card CRUD, rename, reorder, cross-column and empty-column pointer drops, keyboard reorder, AI two-card creation, edit/move batches, automatic refresh, reply-only, multi-turn context, failed drafts, history reset on reload/logout, expiry, input focus and keyboard submission, desktop and 390px layouts.
- Desktop/narrow screenshots inspected; no horizontal page overflow. Conversation scrolling and accessible input/log regions were checked.
- Fresh database: isolated browser backend initialized a new `/tmp/pm-part10-browser.sqlite3`; backend tests independently cover fresh initialization and repeated startup.
- Live browser check against the production Docker app: requested one disposable card through the sidebar, received a real OpenRouter response, and verified automatic board refresh. After container recreation, login restored the exact saved board snapshot and conversation history was empty.
- Removed the disposable live account and its cascading board/cards; foreign-key check passed. Existing user data was preserved. Isolated browser data stayed outside the project and the test server was stopped.
- `git diff --check`: passed. No dependency changes were required.

## Issues found and resolved

Narrower columns exposed a pointer targeting error: the move request named a neighboring column even though the pointer was over an empty destination. Prefer pointer intersections, selecting a card before its containing column, with distance fallback for keyboard input.

Consecutive drag tests now wait for a stable handle before measuring coordinates. Keyboard tests wait for dnd-kit's deferred listener to attach and assert the stable active/target state instead of a transient pickup announcement. A TypeScript check caught an array/map API mismatch in the new collision detector; it was corrected before the successful build.

## Deterministic browser checks

`backend/tests/browser_app.py` is an isolated test entry point. It replaces only the provider function; production imports and Docker build inputs do not include it. Run with a temporary database and the current exported frontend:

```sh
# From repository root, with Docker running:
docker compose cp app:/app/static/. /tmp/pm-browser-static
PYTHONPATH="$PWD/backend" STATIC_DIR=/tmp/pm-browser-static DATABASE_PATH=/tmp/pm-browser-test.sqlite3 \
  backend/.venv/bin/uvicorn browser_app:app --app-dir backend/tests --host 127.0.0.1 --port 8001
```

In another terminal:

```sh
cd frontend
CHAT_MOCK_BACKEND=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:8001 npm run test:e2e
```

Stop the isolated server after testing. These fixtures create disposable accounts only in the chosen test database. Normal browser tests can target Docker at port 8000; the deterministic chat case skips unless `CHAT_MOCK_BACKEND` is set. Never point that flag at a live provider backend.

## Remaining limitations

Windows and native Linux start/stop scripts were not executed on those operating systems. OpenRouter can occasionally return invalid structured output; the backend rejects it without writes (see Part 9). Unknown outcomes after a lost response require reviewing the refreshed board before retrying. No chat persistence or background AI work was added.
