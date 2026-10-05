# Project Management MVP implementation plan

## Scope and decisions

- One local Docker container: FastAPI serves the statically exported Next.js frontend at `/` and API routes under `/api`.
- Python dependencies use `uv`; SQLite lives on a persistent Docker volume and is created when missing.
- Registration and sign-in use persistent SQLite accounts with Argon2 password hashes. The seeded `user` / `password` demo account remains available. One board per user remains the target.
- Preserve the demo's five fixed columns and their order. Support renaming columns and creating, editing, removing, reordering, and moving cards.
- OpenRouter uses `openai/gpt-oss-120b`. Read `OPENROUTER_API_KEY` from the root `.env` at backend runtime only.
- Confirmed: JSON documents the relational SQLite schema; board data is not stored as JSON blobs.
- Confirmed: AI history lasts only for the current session and is not stored in SQLite. Implemented in Part 10: browser memory, cleared on reload or logout.
- Preserve existing styling and the root `AGENTS.md` palette. No additional boards, configurable column counts, or unrelated features.

## Execution and verification

- Complete parts in order; check items off only after completing the work and relevant verification.
- Obtain approval of this plan before Part 2 and of the Kanban database design before Part 6. The user explicitly authorized registration after Part 4, including the minimal accounts persistence needed for it.
- Keep working documentation and test results in `docs/`; keep README instructions minimal.
- Verify current compatible library versions and official documentation during implementation, and commit dependency lockfiles. Existing versions documented in the frontend instructions are a baseline, not a claim that they are latest.
- Use temporary databases and mocked OpenRouter responses in automated tests; keep live AI checks separate.
- Establish the root cause of failures with evidence before fixing them. Record blocked or untested checks, including unavailable operating systems.

## Part 1: Plan and frontend documentation

- [x] Read project instructions and inspect frontend source, configuration, and existing tests.
- [x] Record the relational-schema and session-only history decisions.
- [x] Expand all ten parts with implementation checklists, verification, and success criteria.
- [x] Create `frontend/AGENTS.md` describing the existing code and development commands.
- [x] User authorized proceeding to Part 2 on 2026-10-05. Session reset behavior remains the proposed default for later chat implementation.

Verification: Cross-check frontend descriptions against source and distinguish implemented behavior from planned features. Application tests are unnecessary for documentation-only changes.

Success: Accurate planning documents are complete and the user approves proceeding.

## Part 2: Docker and backend scaffolding

- [x] Create a minimal FastAPI project in `backend/` with `pyproject.toml`, a `uv` lockfile, and a backend test setup.
- [x] Add a health API and temporary static hello-world page that calls the API and displays its result.
- [x] Add Docker and Compose configuration for one application container, a localhost port binding, runtime environment variables, and a persistent database volume.
- [x] Exclude secrets, local databases, dependencies, and generated artifacts from the Docker build context and version control as appropriate.
- [x] Add start/stop shell scripts for macOS/Linux and PowerShell scripts for Windows in `scripts/`. Start builds and launches the container; stop preserves database data.
- [x] Document prerequisites, local URL, commands, and environment setup without exposing secrets. Update backend/scripts instructions to describe the implementation.
- [x] Test health and static routes with FastAPI tests; build/start Docker, verify the page's API call, then stop and restart.
- [x] Verify scripts on available platforms and record any platforms not tested.

Verification: See [PART2.md](PART2.md) for passing checks and platform limitations. Windows and native Linux script execution remain unverified.

Success: The container serves the example page and API locally; scripts report failures clearly and preserve persistent data when stopping.

## Part 3: Serve the existing frontend

- [x] Configure Next.js static export and copy its output into the final Python image through a Node build stage, with no Node server at runtime.
- [x] Replace the temporary page with the exported frontend. Serve assets while keeping `/api` routes and errors separate from HTML routing.
- [x] Preserve demo data, interactions, typography, and responsive layout. Account for Google font downloads currently required during the build.
- [x] Allow Playwright to target the FastAPI-served site as well as frontend development.
- [x] Run frontend lint, TypeScript checks, unit/component tests, and production build.
- [x] Extend movement tests for empty columns, same-column moves, unknown targets, and preservation of card membership/order.
- [x] Run browser tests against Docker for rendering, rename, add/remove, and drag/drop. Verify assets load and missing API routes return API errors.

Verification: See [PART3.md](PART3.md) for passing checks, commands, and remaining tooling advisories.

Success: FastAPI serves the interactive demo at `/` in Docker without a runtime Next.js server. State is still temporary at this stage.

## Part 4: Dummy sign-in and logout

- [x] Add login, current-session, and logout endpoints accepting only `user` / `password`.
- [x] Use a backend-validated session cookie appropriate for local HTTP, including HttpOnly and SameSite settings. Frontend visibility alone must not authorize API access.
- [x] Display login at `/` until the session is validated; add logout and clear user-specific frontend state.
- [x] Keep the static shell public but protect board/AI APIs when added. Derive the acting user from the session, never a client-supplied user ID.
- [x] Test valid/invalid credentials, missing/invalid sessions, session inspection, and logout invalidation on the backend.
- [x] Test login feedback, board visibility, refresh with an active session, and logout in component/browser tests.

Verification: See [PART4.md](PART4.md) for results and manual checks.

Success: Valid sign-in reveals the board, refresh honors an active session, and logout prevents subsequent authenticated API access.

## Registration scope extension (after Part 4)

The user requested registration on 2026-10-05. This supersedes the fixed-credentials-only limitation and authorizes a minimal users table ahead of the full Kanban schema review.

- [x] Persist unique usernames and Argon2 password hashes in SQLite; preserve the demo account.
- [x] Add registration with validation and duplicate-name feedback, auto sign-in, and actual account identity display.
- [x] Test registration, login, duplicate protection, hash storage, and persistence across app recreation.
- [x] Verify the full flow in Docker/browser and record results in [REGISTRATION.md](REGISTRATION.md).

At this stage the board was an in-memory demo. Parts 6–7 subsequently added persistence.

## Part 5: Relational database design

- [x] Create `docs/database-schema.json` describing proposed tables, columns, types, primary/foreign keys, uniqueness constraints, and indexes.
- [x] Propose users, boards, columns, and cards tables. Define one board per user, stable IDs, fixed column positions, card ownership, and ordering within each column.
- [x] Create `docs/DATABASE.md` explaining relationships, mapping to frontend `BoardData` JSON, validation, transactions, initialization, and Docker volume persistence.
- [x] Define initial user/board/column creation. Propose seeding the existing demo cards once on first creation, never on each restart.
- [x] Document foreign-key enforcement, atomic movement/reordering, and user isolation; exclude chat history from the schema.
- [x] Validate JSON syntax and walk through create/edit/delete, rename, reorder, and cross-column move examples against the design.
- [x] User approved the design by authorizing Part 6 on 2026-10-05.

Verification: See [PART5.md](PART5.md). Proposed SQL and operation examples passed isolated in-memory SQLite checks; no running application database was modified. The user subsequently approved implementation on 2026-10-05.

Success: Valid JSON documents an approved relational schema and its operations. Approval was granted and the schema implemented in Part 6.

## Part 6: Persistent backend API

- [x] Implement the approved schema, foreign-key enforcement, automatic database creation, and one-time seed data.
- [x] Connect the authenticated MVP identity to its database user and board.
- [x] Define request/response models and routes for reading the board, renaming columns, and creating, editing, deleting, moving, and reordering cards.
- [x] Preserve the frontend board shape where practical and generate persistent card IDs on the backend.
- [x] Validate titles, IDs, target columns, and positions. Keep column count/order fixed and scope every lookup/mutation to the authenticated user's board.
- [x] Make movement and ordering updates transactional so cards belong to exactly one column and failed writes leave no partial changes.
- [x] Add backend unit/integration tests using temporary SQLite files for initialization, repeated startup, all mutations, empty-column moves, reordering, and reopen persistence.
- [x] Test invalid payloads, unknown IDs, unauthorized access, cross-user isolation with a second test user, and transaction rollback.

Verification: See [PART6.md](PART6.md): 68 backend tests and Docker API/restart checks passed. Existing accounts were preserved. Frontend integration was subsequently completed in Part 7.

Success: Changes persist correctly; initialization does not duplicate data and API callers cannot access another user's board.

## Part 7: Connect the frontend to persistence

- [x] Replace demo initialization with authenticated API loading and a small shared same-origin API client.
- [x] Connect rename, add/remove, and drag/reorder to backend mutations. Commit column renames instead of saving every keystroke.
- [x] Add card title/details editing with save and cancel while preserving the existing design.
- [x] Add loading, empty, saving, and error states. Prevent overlapping saves where needed; restore or reload authoritative state after failed optimistic updates.
- [x] Return to login and clear board/chat state when a session expires.
- [x] Add component tests for API-backed actions, editing/cancel, failed saves, and session expiry.
- [x] Run browser tests against FastAPI/SQLite for all card operations, rename, same-column reorder, cross-column moves, and empty-column drops.
- [x] Verify persistence through reload, logout/login, and container restart using the same volume; check desktop and narrow layouts.

Verification: See [PART7.md](PART7.md): 21 frontend tests, 8 real-backend browser tests, lint, types, Docker build, responsive inspection, and browser/container restart persistence checks passed.

Success: The board is fully editable and persistent; failed requests never falsely imply a saved change.

## Part 8: OpenRouter connectivity

- [x] Add a minimal backend client using the runtime key and `openai/gpt-oss-120b`; keep secrets out of frontend code, image layers, responses, and logs.
- [x] Verify current official API documentation and model/provider Structured Outputs support before Part 9. Report incompatibility instead of silently switching models.
- [x] Set a timeout and provide clear handling for missing configuration, authentication failure, rate limits, provider failures, and timeouts.
- [x] Add mocked tests for request construction, successful parsing, and failure cases.
- [x] Run a separate live backend `2+2` connectivity check, verify the answer is 4, and record the result without secrets.

Verification: See [PART8.md](PART8.md): 101 backend tests, Docker build/health checks, current provider capability metadata, and the live container `2+2 = 4` check passed.

Success: A real call works through the container's backend configuration; routine automated tests need no API credentials or network access.

## Part 9: Structured AI board changes

- [x] Add an authenticated chat endpoint accepting the user's question and session history. Read the current board from SQLite on every AI call.
- [x] Send board JSON, question, and history with instructions limiting changes to supported operations on the current user's board.
- [x] Define/document a Structured Outputs schema containing an assistant response and optional create/edit/move operations, allowing multiple cards in one request.
- [x] Validate the full response and all referenced cards/columns before applying changes. Reuse manual board mutation logic.
- [x] Apply each batch in one transaction and return the reply and authoritative board only after successful validation and commit.
- [x] Use a simple board revision check to reject stale AI changes after intervening edits, with clear feedback to retry against fresh state.
- [x] Accept history per request without backend persistence and treat history/board text as data, never authorization. Browser memory, subsequent-turn submission, and reload/logout clearing are implemented with the sidebar in Part 10.
- [x] Test reply-only responses, each operation, multi-card batches, history inclusion, and current board context with mocked outputs.
- [x] Test malformed/schema-invalid responses, invalid IDs, cross-user references, failed batches, stale board state, and provider errors; assert no unintended or partial writes.
- [x] Run small live Structured Outputs checks for a reply-only question and a board change using disposable test data.

Verification: See [PART9.md](PART9.md): all 131 backend cases passed across the full and follow-up runs, Docker build/start passed, and live reply/create/edit/move checks passed. One live schema-invalid proposal was safely rejected and is documented.

Success: AI can create/edit/move multiple cards atomically; invalid or stale outputs leave the board unchanged and replies reflect committed results.

## Part 10: AI sidebar and final acceptance

- [x] Add a responsive sidebar matching existing typography/colors, with accessible input, send action, conversation display, loading state, and error feedback.
- [x] Connect chat to the backend, prevent duplicate submissions, keep history only in browser memory, include it in subsequent turns, and clear it on reload/logout.
- [x] Refresh the board from successful AI responses automatically. Coordinate manual saves and AI requests to avoid local state races.
- [x] Preserve drafts after request failures and support retry without presenting failed changes as completed.
- [x] Add component tests for reply-only chat, board updates, multiple turns, pending/error states, and history reset.
- [x] Run deterministic browser tests with mocked provider responses through the real backend for create/edit/move, multi-card requests, and automatic refresh.
- [x] Verify keyboard access, focus, scrolling, and desktop/narrow-screen board and sidebar layouts.
- [x] Run final lint, type checks, production build, frontend unit/component/browser tests, backend tests, and Docker smoke checks. Record results and limitations in `docs/`.
- [x] Verify fresh database startup and restart with existing data; perform a final live chat smoke check and update concise run instructions and component instructions.

Verification: See [PART10.md](PART10.md): 26 frontend tests, 131 backend tests, ten browser acceptance cases across final/focused runs, production build, layout inspection, live sidebar creation, and restart persistence checks passed. Platform/provider limitations are documented.

Success: A signed-in user can manage a persistent board manually and through AI in the local Docker app, with automatic board updates and no conversation history retained after the session.
