# Code review

Date: 2026-10-05. Scope: the whole repository at commit `de5f85f`: backend, frontend, Docker, scripts, tests, and docs.

## Summary

The codebase is small, consistent, and in good shape. The trickiest parts are designed carefully and covered by tests:

- revision-checked transactions
- ownership scoping on every query
- AI proposals that are validated before anything is written
- reconciling the board after a failed save

No high-severity issues were found. There is one medium issue: a card edit form can overwrite a newer AI change. The rest are low-severity robustness, UX, and hygiene items.

Checks run for this review, all passing:

| Check | Result |
| --- | --- |
| Backend `uv run --locked pytest` | 131 passed |
| Frontend `npm run lint`, `npx tsc --noEmit` | clean |
| Frontend `npm run test:unit` | 26 passed |
| Playwright against Docker | 9 passed, 1 skipped (chat case, by design) |
| Playwright chat case against mocked `browser_app.py` | 1 passed |
| `docs/ai-response-schema.json` vs `chat.RESPONSE_FORMAT` | identical |
| `npm audit --omit=dev` | 0 vulnerabilities |
| `npm audit` (including dev) | 5 high, all through `braces` (build/test tooling only) |

## Findings

### M1. A card edit form can overwrite a newer AI change (medium)

`frontend/src/components/KanbanCard.tsx:16-17, 39, 59`; `frontend/src/components/KanbanBoard.tsx:84-88, 215`

When the user opens Edit, the form copies `card.title` and `card.details` into local state. `save()` always sends the latest `board.revision`, not the revision the form was opened from. The chat sidebar stays enabled while a card is being edited. So the following sequence silently undoes the AI's change, and the revision check cannot catch it:

1. Open Edit on card X.
2. Ask the assistant to rename card X. The AI commits the change, and the board refreshes with a new revision.
3. The open form still shows the old values. Clicking Save card sends those old values with the new revision, and the server accepts them.

Actions:

- [x] Remember the card version when an edit starts. If the saved card changes while the form is open, show an alert with the saved version and rename the button to "Overwrite changes", so the user can review it, cancel, or overwrite deliberately. Unrelated board changes do not interrupt the edit.
- [x] Add a component test (`frontend/src/components/KanbanCard.test.tsx`). It fails on the previous code and passes with the fix.

Status: fixed. Unit tests (28), lint, and type checks pass. The Docker browser suite was not re-run after this change.

### L1. Login can fail with a 500 when session cleanup runs concurrently (low)

`backend/app/auth.py:36-38`

`start_session` iterates over a snapshot of the sessions and then calls `sessions.pop(token)` with no default. Sync FastAPI routes run in a thread pool. If another request removes the same expired token between the snapshot and the `pop`, for example `current_user` at `auth.py:28` or a concurrent login, then `pop` raises `KeyError` and the login returns a 500. This is rare, but it is a real crash path with a one-line fix.

Actions:

- [ ] Change the call to `sessions.pop(token, None)`.

### L2. The full board is sent to the AI on every chat request, with no size limit (low)

`backend/app/chat.py:120-126`; `backend/app/board.py:79-90`

There is no limit on the number of cards per board, and details can be up to 10,000 characters each. Every chat request also includes up to 40 history messages of up to 4,000 characters each. A heavily used board can therefore produce very large prompts: higher cost, slower replies, and eventually provider context errors. Those errors surface only as a generic 502.

Actions:

- [ ] Choose one simple limit: a maximum number of cards per board (checked in `create_card`), or a character budget for the serialized prompt that returns a clear 413/422 message.

### L3. The frontend hides the backend's error messages (low)

`frontend/src/lib/api.ts:14-20`

The backend returns specific, safe `detail` messages, for example "OPENROUTER_API_KEY is not configured on the backend." (503), "AI referenced an unknown card. No changes saved." (502), and "Database busy. Please retry." (503). The client replaces all of them with generic text. A missing API key therefore shows "AI request failed. Review the board before retrying", which suggests a partial change that did not happen.

Actions:

- [ ] Show the server's `detail` when it is a string, and fall back to the current generic text otherwise. Keep the 401 handling unchanged.

### L4. Card details are trimmed on create but not on edit (low)

`frontend/src/components/NewCardForm.tsx:19` trims `details`. `frontend/src/components/KanbanCard.tsx:39` sends `details` untrimmed. The backend does not strip `Details` in either case (`backend/app/board_api.py:15`). The same text can therefore be stored differently depending on the path, and an edit that only adds whitespace counts as a real change that bumps the revision.

Actions:

- [ ] Pick one rule, preferably in the backend `Details` type, so the frontend and AI paths stay consistent.

### L5. Remove deletes a card with one click (low, UX)

`frontend/src/components/KanbanCard.tsx:60-68`

There is no confirmation and no undo, and the delete is persisted immediately.

Actions:

- [ ] Add a lightweight confirm step, for example a second click on "Confirm remove". Update `tests/kanban.spec.ts` to match.

### L6. Login timing reveals whether a username exists (low, security)

`backend/app/users.py:43-46`

For an unknown username, `verify_user` returns without running Argon2, so the response is measurably faster. Registration already reveals taken names with a 409, and the app binds to `127.0.0.1`, so the impact is small. There is also no rate limiting on login.

Actions:

- [ ] Optional: verify against a fixed dummy hash when the user is missing. Revisit rate limiting if the app ever listens on anything other than localhost.

### L7. Hygiene items (low)

- `frontend/test-results/.last-run.json` is tracked in git even though `.gitignore:185` ignores `test-results/`. Action: [ ] `git rm --cached frontend/test-results/.last-run.json`.
- `INSERT INTO cards VALUES (...)` and `INSERT INTO columns VALUES (...)` rely on column order (`backend/app/seed.py:30, 32`, `backend/app/board.py:86`). Action: [ ] name the columns, so a future schema change cannot silently misplace values.
- `Cache-Control: no-store` is set separately in six handlers (`auth.py:43, 65, 72`; `board_api.py:64, 70`; `chat.py:144`). Action: [ ] optional: set it once with a small middleware for `/api/*`.
- The Docker image runs as root, and its base images use floating tags (`node:24-slim`, `python:3.14-slim`). Action: [ ] optional: add a non-root `USER` that owns `/data`.
- Dev-only `npm audit` advisories in `braces`. Action: [ ] update when `eslint-config-next`/Playwright publish fixed ranges. Avoid `npm audit fix --force`.

### Info: by design, no action unless scope changes

- The seeded `user` / `password` account is recreated at every startup and has no password-change path. This is acceptable only because Compose binds to `127.0.0.1`.
- Sessions live in memory: a restart signs everyone out, and the app must run as a single worker (documented in `backend/AGENTS.md`).
- A stale revision also rejects reply-only chat answers (documented in `docs/PART9.md`).
- SQLite runs in the default rollback-journal mode. WAL would let reads and writes overlap, but that is not needed for a single-user local app.

## Strengths worth keeping

- The acting user and board always come from the session (`current_user` and `owned_board`), never from request data. Every card and column query is scoped by `board_id`.
- `mutate_board` keeps the revision check, the changes, and the revision bump in one `BEGIN IMMEDIATE` transaction. No-op changes do not bump the revision.
- The AI path holds no transaction during the provider call, checks the session again before writing, validates every reference and position before the first write, and reuses the manual mutation functions.
- OpenRouter errors are mapped to safe codes. Provider authentication failures never surface as 401, so they cannot be confused with an expired app session.
- The frontend allows one save at a time, adopts the server's board after every write, and reconciles after ambiguous failures.
- Tests use temporary databases and mocked HTTP. The browser chat fixture is kept out of the production image.

## Suggested order

1. M1 (lost update), with its test. Done.
2. L1 (one-line fix) and L7 `git rm --cached`.
3. L3 and L4 (small consistency fixes).
4. L2, L5, and L6, depending on whether the app's scope grows.
