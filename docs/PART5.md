# Part 5 design review

Prepared on 2026-10-05. Status: design validated; user approval pending. No application code, running SQLite file, or container was changed in this step.

Deliverables:

- [database-schema.json](database-schema.json): proposed relational tables, exact SQL column definitions and constraints, indexes, stage IDs, and initialization rules.
- [DATABASE.md](DATABASE.md): ownership, ordering, transactions, frontend mapping, migration from registration, and operation walkthrough.

## Validation performed

Parsed the JSON and generated the proposed tables/indexes directly from its definitions in a fresh SQLite `:memory:` connection. Started with the existing registration table shape and synthetic account/hash values to check compatibility. The check used no production accounts or disk database.

| Check | Result |
| --- | --- |
| JSON parsing and generated SQL | Passed. |
| Existing account IDs and hashes preserved; repeat DDL | Passed. |
| One-board uniqueness and missing-user foreign key | Invalid inserts rejected. |
| Five allowed column ID/position pairs | Extra stage and invalid position rejected. |
| Card relationship, negative position, blank title, oversized details | Invalid writes rejected. |
| Sequential create/edit/rename/reorder/cross-column move/empty-column move/delete examples | Expected final orders and titles verified. |
| Alice updates Bob's card using Alice's board scope | Zero matching rows; Bob's card and revision unchanged. |
| Failed second operation after a first mutation and revision increment | Entire transaction rolled back. |
| Stale revision comparison | Zero matching rows; no changes. |
| Positions after successful operations | Contiguous `0..n-1` in each affected column. |
| `foreign_key_check` / `integrity_check` | No foreign-key violations / `ok`. |
| `git diff --check` | Passed. |

These checks validate the proposed SQL and documented examples, not an implemented API. Part 6 still needs implementation tests for authorization, initialization/one-time seeding, concurrency, file reopen persistence, and transactions. Part 7 will verify frontend mapping and Docker-volume persistence with real board data.

## Approval requested

Approve the design, including eight independently copied demo cards per new board, fixed stage IDs/colors, title/details limits, and board revisions for stale-write detection. Existing accounts and their password hashes remain intact.

The approval checkpoint is explicitly required by Part 5 in [PLAN.md](PLAN.md): “Obtain user sign-off before implementing the database.” Leave that item open until the user approves; do not begin Part 6 beforehand.
