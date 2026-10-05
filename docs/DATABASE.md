# Kanban database design

Status: approved by the user and implemented in Part 6 on 2026-10-05. The three Kanban tables were added without replacing accounts. See [PART6.md](PART6.md) for endpoints and verification.

The machine-readable [database-schema.json](database-schema.json) documents SQL column definitions, primary and foreign keys, constraints, indexes, seed rules, and application invariants. It describes relational rows; JSON is used for documentation and API responses only.

## Tables and ownership

| Table | Key | Purpose |
| --- | --- | --- |
| `users` | Existing integer `id` | Preserve unique, case-sensitive usernames and Argon2 password hashes. |
| `boards` | Integer `id`; unique `user_id` | One board per account, with an integer `revision` starting at zero. |
| `columns` | Composite `(board_id, id)` | Five fixed stages with editable titles and fixed positions. |
| `cards` | UUID text `id` | Title, details, one owning board/column, and position within that column. |

```mermaid
erDiagram
    users ||--|| boards : owns
    boards ||--|{ columns : contains
    columns ||--o{ cards : contains
```

The diagram shows the intended application state. SQL uniqueness limits users to at most one board; initialization ensures every account has one. SQL constrains columns to the five allowed ID/position pairs; initialization and the absence of column create/delete routes ensure all five remain present. No triggers or ORM are needed for the MVP; use Python's existing `sqlite3` approach.

| Position | Stable column ID | Initial title | Existing accent |
| --- | --- | --- | --- |
| 0 | `col-backlog` | Backlog | Slate |
| 1 | `col-discovery` | Discovery | Blue |
| 2 | `col-progress` | In Progress | Yellow |
| 3 | `col-review` | Review | Purple |
| 4 | `col-done` | Done | Green |

Column IDs are reused across boards, so every column query must include `board_id`. This preserves the frontend's current IDs and color rules when a stage is renamed. Colors remain presentation code, not database fields. Card IDs are newly generated UUID4 strings and are globally unique, including seeded cards.

The composite card foreign key `(board_id, column_id)` references the matching column on that board. Foreign keys enforce valid relationships, not authorization: application code must never allow an existing card's `board_id` to change. A caller must not be able to move a card onto another user's board even if both columns exist.

## Initialization and existing data

1. Open the configured SQLite file and enable foreign keys before starting a transaction. Continue using `DATABASE_PATH`: `/data/pm.sqlite3` in Docker's existing named volume, or `backend/data/pm.sqlite3` locally.
2. Preserve the registration table and every existing ID, username, and password hash. Keep the existing demo-account seed behavior; do not reset its password.
3. In an additive initialization transaction, create missing Kanban tables/indexes and set `PRAGMA user_version = 1` when successful. The current registration-only database has no application schema version yet. Do not silently downgrade a future version.
4. For each existing account without a board, create its board, five columns, and eight demo cards in one transaction. Copy the current demo's titles, details, membership, and ordering from `frontend/src/lib/kanban.ts`, assigning fresh card UUIDs per board. The persisted board row is the seed marker.
5. Extend registration so its user, board, columns, and initial cards are created in one transaction before issuing the session. A failure leaves no incomplete account or board.
6. On repeat startup, skip every existing board. An empty board is intentional: do not restore deleted cards, original titles, or previous ordering. Interrupted creation rolls back and can be retried.

Approved seed behavior: every user starts with the same eight example cards, independently copied. Existing browser-only edits cannot be migrated reliably because the app never stored them on the server.

Normal stop/rebuild commands preserve the volume. The additive migration preserves the existing volume and accounts. Future schema changes should use explicit, ordered migrations; no migration framework is needed for this first additive change.

## Validation and ordering

- Strip surrounding whitespace from titles. Column titles must contain 1–80 characters; card titles 1–200. Check this in request validation and SQL. Details may be empty and have a 10,000-character limit; do not replace an intentionally empty value with demo placeholder text.
- Column IDs, positions, and owning board are immutable through the API. Duplicate titles are allowed because IDs identify stages/cards.
- Cards use integer positions `0..n-1` within each column. Read by `position`, then `id` as a deterministic tie-breaker. An index on `(board_id, column_id, position)` supports board/card reads and the composite foreign key.
- Card positions deliberately have no SQL uniqueness constraint: swapping positions would otherwise require temporary positions or deletion/reinsertion. The service reads affected lists, validates that each card appears exactly once, and rewrites contiguous positions inside a transaction. Database checks still reject negative positions. Tests must verify the stronger application invariant.
- An insertion/move accepts a destination index in the list after removing the moving card, from zero to that list's length inclusive. Append uses the list length; empty-column insertion uses zero. Resolve drag-over card/column IDs into this explicit final order in the frontend integration.

Enable `PRAGMA foreign_keys = ON` on **every** connection before a transaction, including registration connections. SQLite requires per-connection enablement and validates composite references against matching parent keys. [SQLite foreign-key documentation](https://www.sqlite.org/foreignkeys.html)

## Transactions and stale edits

Use a short `BEGIN IMMEDIATE` transaction for each mutation: resolve the authenticated board, compare its revision with the client's expected revision, validate ownership/targets, apply all changes, increment revision once, and commit. Roll back on validation or SQL failure. No-op requests can return the unchanged board without incrementing revision.

SQLite allows one writer at a time; an immediate transaction obtains the write transaction before reading the lists that will be modified. A busy database should yield clear retry feedback if the normal connection timeout is reached. Read a full board in one read transaction so columns, cards, and revision come from a consistent snapshot. [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html)

For AI, read the board and revision, close the read transaction, then call OpenRouter. Do not hold a database transaction during a network call. When applying the response, compare the saved revision inside the write transaction; reject a stale result with HTTP 409 and ask for a retry. A multi-card AI batch commits entirely or not at all and increments the revision once. Manual writes use the same revision rule and return an authoritative board for UI refresh.

## Frontend mapping and user isolation

Preserve `BoardData.columns` and `BoardData.cards`; add a top-level `revision` integer. `columns[].cardIds` is computed from card rows rather than stored separately. This avoids two competing records of where a card belongs. For example, a card row `(id="c1", column_id="col-backlog", position=0)` appears as `"c1"` in that column's `cardIds` and as `{id, title, details}` under `cards.c1`.

Use `current_user` to obtain the authenticated username, resolve `users.id`, and select `boards` by `user_id`. Never accept the acting user or owning board from request data. Every mutation scopes card/column queries to this board; a foreign card ID returns the same not-found response as an unknown ID. Check affected rows rather than reporting a successful edit when no owned record matched. Password hashes never appear in board JSON or AI prompts.

Login sessions remain in memory as implemented. Chat history remains session-only browser state and is not included in any table. No timestamps, audit tables, assignments, attachments, or additional board settings are proposed.

## Operation walkthrough

Assume Alice owns board 1 and Bob owns board 2. Start Alice's Backlog with `[A, B]` and Review with `[C]`; other columns are empty. IDs here are readable stand-ins for UUIDs. Apply these steps sequentially:

| Operation | Database effect / resulting order |
| --- | --- |
| Create D in Backlog | Generate ID D, insert at position 2; Backlog `[A, B, D]`. |
| Edit D | Change only D's title/details, scoped to board 1; order unchanged. |
| Rename Review to QA | Update board 1 / `col-review` title only; ID, position, and purple accent stay the same. |
| Reorder D to index 0 | Rewrite Backlog positions as `[D, A, B]`. |
| Move A to Review index 0 | Update A's column and rewrite both lists: Backlog `[D, B]`, Review `[A, C]`. |
| Move C to empty Done | Review becomes `[A]`; Done becomes `[C]` at position 0. |
| Delete D | Delete D scoped to board 1; compact Backlog to `[B]`. |
| Alice edits Bob's card | Scoped lookup matches no row; reject without changing either board or revision. |
| Invalid second operation in an AI batch | Roll back the first operation and any revision update as well. |
| Stale expected revision | Return conflict before changing rows. |
| Restart | Load saved names, memberships, and order; do not seed again. |

Each successful changing operation increments Alice's revision once; Bob's board stays unchanged. Design validation results are recorded in [PART5.md](PART5.md).

## Approval

The user approved the four-table design, one-time example-card seeding, field limits, and transaction/revision rules by authorizing Part 6 on 2026-10-05. This checkpoint comes from `docs/PLAN.md`: “Obtain user sign-off before implementing the database.” The existing registration table remains in place; approval applies to the proposed Kanban additions.
