# Part 4: dummy sign-in

Completed on 2026-10-05. Open http://localhost:8000 and sign in with `user` / `password`.

## Behavior

- POST `/api/auth/login` validates the fixed credentials and issues a random opaque token in an HttpOnly, SameSite=Strict, Path=/ browser-session cookie. The local HTTP setup does not set Secure.
- GET `/api/auth/session` validates the token on the backend and returns the current username, or HTTP 401 for missing, forged, expired, or revoked tokens. Successful session responses are not cached.
- POST `/api/auth/logout` removes the token from the backend and deletes the cookie; repeated logout succeeds harmlessly.
- Sessions expire after eight hours and are held in the single backend process's memory. Restarting it requires signing in again. No database changes or new dependencies were needed.
- `current_user` is the reusable dependency for future board and AI routes. The acting identity must come from it, never a client-supplied user ID.
- The public static shell checks the session before mounting the board. Login errors, session-check failures, pending submissions, and logout failures have explicit feedback.
- Successful logout unmounts the board and clears its temporary edits. Refresh still resets demo card changes; persistence comes later.
- Real authentication requires FastAPI. Frontend-only development tests mock session checks, while Docker tests use real cookies and backend validation.

Cookie handling follows the official [FastAPI response cookie documentation](https://fastapi.tiangolo.com/advanced/response-cookies/).

## Verification

| Check | Result |
| --- | --- |
| Backend | 19 tests passed, including wrong credentials, missing/forged/expired tokens, rotation, independent sessions, cookie flags, malformed requests, and replay after logout. |
| Frontend unit/component tests | 16 passed, including session gating, login feedback, logout state clearing, and unavailable-server cases. |
| Lint and TypeScript | Passed. |
| Docker production build and startup health | Passed. |
| Chromium against Docker | 9 passed: login/refresh/logout/re-login, invalid cookie, narrow-screen validation, and existing Kanban interactions/API routing. |
| Whitespace check | Passed. |

During verification, a component test incorrectly used Playwright's `exact` option with Testing Library; TypeScript identified it and the option was removed. A browser assertion also matched Next.js's route-announcer alert; filtering for the actual error text resolved that test ambiguity.

## Manual check

1. Open `/` in a fresh browser session and confirm the login form appears without the board.
2. Try an incorrect password and check the error message.
3. Sign in with `user` / `password`; refresh and confirm the board remains accessible.
4. Rename a column, sign out, and sign in again. The demo board returns with its original column names.
5. After logout, `/api/auth/session` returns HTTP 401.

For automated checks, run `uv run --locked pytest` from `backend/`. From `frontend/` using Node 24, run `npm run lint`, `npm run test:unit`, `npx tsc --noEmit`, and `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e` with Docker running. On PowerShell, set the environment variable with `$env:PLAYWRIGHT_BASE_URL="http://127.0.0.1:8000"` first.

Part 5 has not started; the relational database design still requires user approval before implementation. The development-tool advisories recorded in Part 3 are unchanged.
