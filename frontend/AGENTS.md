# Frontend instructions

Follow root `AGENTS.md` and review `../docs/PLAN.md` before changes. This file describes the current persistent frontend; the plan records completed implementation and verification.

## Stack and source map

The frontend uses Next.js App Router, strict TypeScript, React, and Tailwind CSS v4. `package.json` currently declares Next.js 16.3.8 and React/React DOM 19.3.0. Drag/drop uses `@dnd-kit/core` and `@dnd-kit/sortable`; `clsx` combines classes. The `@/*` alias maps to `src/*`.

| Path | Responsibility |
| --- | --- |
| `src/app/page.tsx` | Renders `AuthGate` at `/`. |
| `src/app/layout.tsx` | Metadata, global CSS, Manrope and Space Grotesk via `next/font/google`. |
| `src/app/globals.css` | Tailwind import, shared colors, surfaces, shadows, and typography. |
| `src/components/KanbanBoard.tsx` | Client component loading authoritative board snapshots, serializing saves, handling revisions/errors, and owning drag state. |
| `src/components/KanbanColumn.tsx` | Droppable column, editable title, card count, sortable list, and new-card form. |
| `src/components/KanbanCard.tsx` | Sortable card with edit/save/cancel and remove controls; the content is the drag handle. |
| `src/components/KanbanCardPreview.tsx` | Presentation-only drag overlay card. |
| `src/components/NewCardForm.tsx` | Expandable create form, submit/cancel, input trimming, and blank-title rejection. |
| `src/lib/kanban.ts` | Board types including revision and pure `moveCard` helper. Test fixtures live under `src/test/`. |

## Existing behavior

- `Card`: `id`, `title`, `details`. `Column`: `id`, `title`, ordered `cardIds`. `BoardData`: ordered columns, cards keyed by ID, and revision.
- `KanbanBoard` loads `/api/board` on mount; the backend owns seeds, IDs, ownership, ordering, and persistence. No browser storage is used.
- `src/lib/api.ts` is a small same-origin JSON client with no-store requests and typed HTTP errors.
- Column names are drafts until Save column or Enter; Cancel rename or Escape discards the draft. Blank titles cannot be submitted.
- Cards support create, edit/save/cancel, remove, reorder, and cross-column drag/drop. Forms retain drafts after failed saves.
- Only one mutation runs at a time; controls and drag are disabled during saves. State changes only after server confirmation. Every mutation sends the current revision and adopts the returned board.
- Failed writes reload authoritative state, including after ambiguous network failures. If reload fails, further mutations are blocked until Reload board succeeds. Conflicts are reported for review and retry.
- Dragging uses a pointer sensor with a six-pixel activation distance, pointer-aware collision detection, and an overlay. The card content is the drag handle; edit/remove controls are separate. KeyboardSensor uses sortableKeyboardCoordinates; Space/arrows/Space moves cards and Escape cancels. Pointer intersections prefer cards over columns; distance detection is the keyboard fallback.
- `moveCard` calculates destination ordering. Dropping on a column appends; dropping on another column's card inserts before it.
- `AuthGate` validates the session before mounting the board. A board API 401 clears identity, unmounts the board and drafts, and shows sign-in. Logout also unmounts the board; persisted data returns after signing in again. Chat history/drafts also clear on unmount.

## Styling

Preserve the rounded cards, surfaces, typography, and shared CSS variables:

| Variable | Value |
| --- | --- |
| `--accent-yellow` | `#ecad0a` |
| `--primary-blue` | `#209dd7` |
| `--secondary-purple` | `#753991` |
| `--navy-dark` | `#032147` |
| `--gray-text` | `#888888` |

Use established fonts and meaningful control labels. The board displays five columns at `lg` (with internal horizontal scrolling where needed) and one column below it. The assistant is beside the board at `xl` and below it on narrower screens.

Stage accents are defined in `globals.css` by stable `data-stage` IDs: Backlog slate, Discovery blue, In Progress yellow, Review purple, Done green. Column borders, accent bars, drop-target rings, and header labels share these colors; renaming a stage preserves its color.

## Commands and tests

Use Node.js 24 LTS. Run from `frontend/` after installing locked dependencies with `npm ci`:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Next.js development server. |
| `npm run build` | Build the frontend. |
| `npm run start` | Serve the static build through FastAPI at port 8000 (requires Python 3.14 and uv). |
| `npm run lint` | Run ESLint with Next.js/TypeScript rules. |
| `npx tsc --noEmit` | Check TypeScript types. |
| `npm run test:unit` | Run Vitest; `npm test` is equivalent. |
| `npm run test:unit:watch` | Run Vitest in watch mode. |
| `npm run test:e2e` | Run Playwright; requires its Chromium browser installation. |
| `npm run test:all` | Run unit tests followed by browser tests. |

- `src/lib/kanban.test.ts`: same-column reorder, cross-column insertion, append-to-column movement.
- `src/components/KanbanBoard.test.tsx`: API loading/retry, rename, add/remove, edit/cancel, failed saves, revision conflicts, mutation locking, and session expiry.
- `vitest.config.ts`: jsdom and React Testing Library tests under `src/`, excluding `tests/`; `src/test/setup.ts` loads jest-dom Vitest matchers.
- `tests/kanban.spec.ts`: real SQLite CRUD, rename, pointer reorder/cross-column/empty-column moves, reload/login persistence, expiry, and desktop/narrow layouts.
- `playwright.config.ts`: Chromium; starts/reuses Next.js development at `http://127.0.0.1:3000`. Set `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000` to test the running Docker/FastAPI app without starting Next.js. Board browser tests require the real backend and register disposable accounts; `tests/auth.spec.ts` requires the real backend and verifies login, refresh, logout, invalid cookies, and login validation.
- Existing test descriptions are not evidence that tests passed in the current environment.

## Integration constraints

- `next.config.ts` exports static assets to `out/` with trailing slashes. Docker builds them in a Node stage and copies them into the Python runtime; FastAPI serves them at `/`. Continue to avoid Next.js server-only runtime dependencies, API routes, and Server Actions.
- The Google font setup downloads Manrope and Space Grotesk during builds; internet access to Google Fonts is required. Exported fonts are served locally at runtime.
- Keep OpenRouter calls and credentials on the Python backend. Never expose the key through `NEXT_PUBLIC_*` variables.
- Preserve the board shape where practical when integrating the API. The backend is authoritative for persistent IDs, ownership, ordering, and mutations.
- Keep AI history session-only; do not add persistent chat storage.
- Add relevant behavioral tests when implementing features and update these instructions as the architecture changes. Do not describe planned features as implemented.

- `AuthGate.test.tsx` covers session gating, login feedback, logout state clearing, session-check failure, and failed logout. No credentials or session tokens are stored in localStorage.
- Real sign-in requires FastAPI: use Docker or build and run `npm start`. `npm run dev` alone serves UI code without authentication APIs.

## AI sidebar

- `ChatSidebar.tsx` owns only in-memory history/draft state, sends the last 40 successful messages, and appends turns only after a confirmed response. Reload/logout/expiry clears history by unmounting it.
- `KanbanBoard` sends chat through the same save lock as manual operations and adopts `reply`/`board` responses. Failed calls preserve drafts and reconcile state before another save. No automatic retries.
- `ChatSidebar.test.tsx` covers history, reset, pending state, duplicates, and failure drafts; board tests verify shared locking and response refresh.
- `tests/chat.spec.ts` uses real FastAPI/SQLite with `backend/tests/browser_app.py` mocking only OpenRouter. See `docs/PART10.md` for isolated commands. Never enable its `CHAT_MOCK_BACKEND` flag against a live provider backend.
