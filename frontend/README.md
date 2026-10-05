# Kanban Studio

Use Node.js 24 LTS and `npm ci`.

- `npm run dev`: frontend-only development at port 3000; real sign-in requires FastAPI via Docker or `npm start`.
- `npm run build`: static export to `out/` (requires Google Fonts network access).
- `npm start`: serve the export via FastAPI at port 8000; requires Python 3.14 and uv.
- `npm run lint`, `npx tsc --noEmit`, `npm run test:unit`: frontend checks.
- `npx playwright install chromium`: install the browser for tests.
- `npm run test:e2e`: browser tests against frontend development.
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e`: test a running Docker app (macOS/Linux).

In PowerShell set `$env:PLAYWRIGHT_BASE_URL="http://127.0.0.1:8000"` before running the browser tests.

For Docker, use the root [README](../README.md). Choose **Create an account**, or sign in with `user` / `password`. Board edits persist through the FastAPI/SQLite API. Column renames use Save column; cards support Edit, Save card, and Cancel.
