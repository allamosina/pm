# Registration

Added on 2026-10-05 at the user's explicit request, extending Part 4 beyond fixed credentials.

## Use

Open http://localhost:8000 and choose **Create an account**. Enter a username and password, then select **Create account**. Registration signs you in immediately.

- Usernames are case-sensitive and contain 3–32 ASCII letters, digits, underscores, or hyphens.
- Passwords contain 8–128 characters and are not trimmed.
- Duplicate usernames show an error without changing the existing account.
- The original `user` / `password` demo account remains available.

## Implementation

`POST /api/auth/register` validates input, inserts a user into SQLite, and issues the existing session cookie. Login now verifies stored Argon2id password hashes using pwdlib, following [FastAPI's password-hashing guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#password-hashing). Responses expose only usernames, never hashes.

The [implemented users schema](registration-schema.json) has an integer primary key, unique username, and password hash. Startup creates the table if missing and seeds the demo account only if absent. Parameterized SQL and a unique constraint protect inserts. Accounts use `/data/pm.sqlite3` in Docker's persistent volume; the local default is `backend/data/pm.sqlite3`.

Sessions remain in memory with an eight-hour expiry. Accounts survive server restarts, while sessions require a new sign-in. The frontend displays the username returned by the backend and clears temporary board state on logout.

Only account persistence was advanced to satisfy registration. The board remains an in-memory demo and resets on reload; the full relational Kanban schema still requires Part 5 review before implementation.

## Verification

- 27 backend tests passed, covering registration, validation, duplicates, unchanged original passwords, Argon2 hash storage, login/logout, and persistence across app recreation.
- 16 frontend component/unit tests passed; lint and TypeScript passed.
- Docker production build and health checks passed.
- 10 Chromium tests passed, including register, refresh, duplicate feedback, logout, and sign-in with the new account.
- A registered test account also survived a Docker container restart and its stored password verified successfully. That disposable account was then removed.
- JSON schema syntax and `git diff --check` passed.

Repeat browser checks with `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e` from `frontend/`. Registration tests create a uniquely named `e2e_reg_*` account and print its exact username for targeted cleanup; avoid broad deletion of accounts. Backend tests use temporary isolated databases.
