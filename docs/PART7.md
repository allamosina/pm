# Part 7: Persistent frontend

Completed 2026-10-05.

## Behavior

The signed-in board loads from SQLite through `/api/board`. Creating, editing, deleting, reordering, moving cards, and renaming columns all use the Part 6 API. Backend IDs and revisions are authoritative; demo fixtures are used only by tests.

- Rename a column, then choose **Save column** or press Enter. **Cancel rename** or Escape discards the draft.
- Choose **Edit** on a card to change its title/details, then **Save card** or **Cancel**.
- Drag a card by its text area. Edit/remove buttons are separate from the drag handle.
- Saves run one at a time. Controls are disabled while saving, and the board adopts only confirmed server responses.
- Failed requests retain form drafts and reload the authoritative board. Revision conflicts prompt review/retry. If the reload also fails, further changes are blocked until **Reload board** succeeds. An uncertain network response does not imply a save failed or succeeded.
- A board API 401 returns to sign-in and unmounts private board/draft state. Saved data returns after login. Chat is still pending; no chat storage was introduced.

## Verification

- Frontend unit/component suite: **21 passed**, including loading/retry, confirmed rename/add/delete, edit/cancel, retained failed-save drafts, stale revision reload, uncertain-save lock/recovery, save serialization, and session expiry.
- ESLint and `tsc --noEmit`: passed.
- Docker production static export and healthy startup: passed using `./scripts/start.sh`.
- Playwright against the real FastAPI/SQLite container: **8 passed**. Covers CRUD, rename, same-column reorder, cross-column and empty-column drops, reload/logout/login persistence, expiry, registration/auth checks, and layouts at 1500px and 390px.
- Desktop and narrow full-page screenshots inspected with a card editor open; no horizontal page overflow or browser exceptions.
- Separate browser restart check: registered a disposable account, renamed a column and created a card through the UI, captured the full API snapshot, restarted the container using the existing volume, signed in through the UI, and verified the visible edits and exact snapshot equality.
- Removed all 11 accounts created during these checks and their cascading boards/cards. SQLite foreign-key check passed. Existing user board data was not edited by these tests.
- `git diff --check`: passed. Backend implementation was unchanged, so its 68 passing Part 6 tests were not rerun.

The first unit/browser test runs exposed ambiguous selectors matching dnd-kit's status region and Next.js's alert announcer. Assertions were narrowed to the intended messages; final suites pass.

Run browser tests with Docker running:

```sh
cd frontend
npm run test:unit
npm run lint
npx tsc --noEmit
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e
```

Browser tests create disposable accounts; they require the real backend and skip when `PLAYWRIGHT_BASE_URL` is absent. These tests do not delete accounts automatically because there is no public account-deletion API.

## Implementation references

`src/lib/api.ts` provides the same-origin JSON client. `KanbanBoard.tsx` owns API loading, save serialization, revisions, reconciliation, and session-expiry handling. Column/card/form components own unsaved drafts. `AuthGate.tsx` clears private UI state on expiry.

No dependencies were added or upgraded. Effect loading cancels on cleanup, following [React's fetching guidance](https://react.dev/learn/synchronizing-with-effects#fetching-data). The existing locked dnd-kit sortable API disables dragging while saving/editing; see [useSortable](https://docs.dndkit.com/presets/sortable/usesortable).

Part 8 (OpenRouter connectivity) remains unimplemented. Drag/drop is pointer-based; keyboard drag controls remain a final-accessibility follow-up.
