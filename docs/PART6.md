# Part 6: persistent board backend

Completed on 2026-10-05 after the user authorized Part 6 and approved the Part 5 design.

## Behavior

- Schema version 1 adds boards, columns, and cards to the existing SQLite database. Account IDs, usernames, and password hashes are preserved.
- Each account receives one board, the five fixed colored-stage IDs, and eight independently seeded demo cards. Existing boards are never reseeded, even when empty.
- Registration creates the account and complete board in one transaction before issuing a session.
- Authenticated board operations read the acting user from the session, resolve that user's board, and scope all card/column queries to it.
- Every write checks `expected_revision` inside `BEGIN IMMEDIATE`. Changes and revision updates commit together; no-ops preserve the revision. Reads return a consistent board snapshot.
- The existing frontend still uses its temporary demo state. Part 7 will connect it to these endpoints; browser board edits are not yet saved by this API.

## API contract

All routes require the existing `pm_session` cookie. Successful responses are the full board, with `Cache-Control: no-store`:

```json
{
  "columns": [{"id": "col-backlog", "title": "Backlog", "cardIds": ["card-uuid"]}],
  "cards": {"card-uuid": {"id": "card-uuid", "title": "Example", "details": ""}},
  "revision": 1
}
```

The example abbreviates the five-column response. Card IDs are UUID4 strings, not the old demo IDs.

| Method and path | Request | Success |
| --- | --- | --- |
| `GET /api/board` | None | 200 |
| `PATCH /api/board/columns/{id}` | `title`, `expected_revision` | 200 |
| `POST /api/board/cards` | `column_id`, `title`, `expected_revision`; optional `details` (default empty), `position` (default append) | 201 |
| `PATCH /api/board/cards/{id}` | `title`, `details`, `expected_revision` | 200 |
| `POST /api/board/cards/{id}/move` | `column_id`, `position`, `expected_revision` | 200 |
| `DELETE /api/board/cards/{id}?expected_revision=N` | No body | 200 |

Mutation bodies reject extra fields such as `user_id` or `board_id`. Titles are trimmed and required: at most 80 characters for columns and 200 for cards. Details allow 0–10,000 characters. Body revisions/positions must be nonnegative integers, not booleans or fractional values.

Move positions refer to the destination list **after removing the moving card**: zero inserts first and the destination length appends. Moving into an empty column uses zero. Both affected lists are rewritten to contiguous positions in the same transaction. Use the returned revision for the next write.

Errors: 401 requires sign-in; 404 means the target was not found on the caller's board; 409 means a stale revision (reload and retry); 422 means invalid input/position; 503 with `Retry-After: 1` means SQLite remained busy after the connection timeout. Unexpected database errors are not disguised as a duplicate username or successful write.

Interactive API documentation is available at http://localhost:8000/docs after signing in through the app in the same browser/hostname.

## Code map

| File | Responsibility |
| --- | --- |
| `backend/app/schema.sql` | Approved table definitions and index. |
| `backend/app/database.py` | Foreign-key-enabled connections, explicit transactions, and schema version checks. |
| `backend/app/seed.py` | Fixed columns and one-time example cards with fresh UUIDs. |
| `backend/app/users.py` | Additive startup, missing-board backfill, atomic registration. |
| `backend/app/board.py` | Ownership, snapshots, revisions, and reusable card/column operations. |
| `backend/app/board_api.py` | Validated request/response models and authenticated routes. |
| `backend/tests/test_board.py` | Persistence, authorization, mutation, concurrency, and failure tests. |

Transaction handling follows [Python's sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html). Request constraints use [Pydantic field validation](https://pydantic.dev/docs/validation/latest/concepts/fields/).

## Verification

- All **68 backend tests passed** with isolated temporary SQLite files. Coverage includes existing auth/static behavior plus board CRUD, rename, same-column reorder, cross-column and empty-column moves, append, no-ops, malformed input, unknown IDs, unauthenticated access, and cross-user isolation.
- Concurrent writes with the same revision produce one successful commit and one conflict.
- Injected failures verified rollback of partial movement, account/board seeding, schema initialization, and changes after revision increment. Future schema versions are rejected without modification.
- Reopening an upgraded legacy database preserves IDs/hashes, column renames, revisions, and deliberately empty boards. Foreign-key and fixed-column constraints were checked.
- Docker build/start passed. A real HTTP smoke test registered a disposable account and exercised read/create/edit/rename/move/delete. Its complete response matched after a container restart.
- All pre-migration account records were compared with a SQLite backup and matched exactly. Every account has one board, and the foreign-key check passed.
- The disposable account was removed afterward, verifying cascade cleanup of its board/columns/cards. Existing users were not removed.
- Python compilation and `git diff --check` passed. Frontend tests were not repeated because frontend code did not change in this part.

Pre-migration backup retained in the Docker data volume: `/data/pm-before-part6-20261005.sqlite3`. It contains account data and should be treated like the main database.

Run backend tests from `backend/` with `uv run --locked pytest`. Part 7 has not started.
