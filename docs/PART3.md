# Part 3 implementation and verification

Completed on 2026-10-05. The demo Kanban is running at http://localhost:8000.

## Implementation

- Next.js exports to `frontend/out/` with trailing slashes. Docker uses a Node 24 build stage and copies only the export into the final Python image.
- FastAPI serves the exported HTML, JavaScript, CSS, and fonts. Unknown `/api/*` requests return JSON 404 errors independently of the exported HTML 404 page.
- `STATIC_DIR` selects the export directory; locally it defaults to `frontend/out/`, and Docker uses `/app/static`.
- The five-column demo and its styling remain unchanged. Card changes are still held in browser memory and reset on reload. Authentication, persistence, and AI are later parts.
- Playwright accepts `PLAYWRIGHT_BASE_URL` to test a running FastAPI/Docker app; without it, tests start Next.js development at port 3000.
- Updated Next.js/React and testing dependencies, refreshed the lockfile, and corrected test imports and jest-dom's Vitest type integration. Use Node 24 LTS for local commands.
- Manrope and Space Grotesk download from Google Fonts during the build and are included in the export; no Google Fonts request is required at runtime.

Configuration follows the official [Next.js static export guide](https://nextjs.org/docs/app/guides/static-exports) and [Playwright web-server configuration](https://playwright.dev/docs/test-webserver).

## Verification

| Check | Result |
| --- | --- |
| Frontend lint | Passed. |
| Frontend unit/component tests | 11 passed, including empty-column movement, same-column append, invalid targets, and non-mutating card membership/order checks. |
| TypeScript | Passed. |
| Local static export | Passed using `npm run build -- --webpack`; local Turbopack worker IPC was blocked by the environment. |
| Docker production build | Passed using standard `npm run build` with Turbopack. |
| Backend tests | 8 passed: health, static delivery, HTML 404, and JSON errors for five API methods. |
| Chromium against Docker | 6 passed: render, add, drag/drop, rename/remove, narrow viewport/assets, and API routing. |
| Final runtime image | Export present; Node executable absent; root `.env` absent from `/app`. |
| Production dependency audit | Zero vulnerabilities reported by `npm audit --omit=dev`. |
| Whitespace checks | `git diff --check` passed. |

## Findings and limitations

- Initial builds exposed missing Vitest imports and Jest-specific matcher types. Explicit Vitest imports and `@testing-library/jest-dom/vitest` resolved the type errors.
- Docker initially included host dependency folders because directory inclusion rules reopened their contents. Explicit dependency/cache exclusions reduced the build context from about 496 MB to a few hundred KB.
- The browser delete test initially matched both a draggable card and its nested button. Exact accessible-name matching resolved the test ambiguity.
- Five high-severity advisories remain in the development-only ESLint dependency chain rooted in `braces`. The audit's proposed fix downgrades `eslint-config-next` to 14.2.35; it was not applied to the Next.js 16 project. These tooling dependencies are absent from the final Python image.
- Browser validation used Chromium on macOS against Docker's Linux container. Native Windows/Linux host testing was not performed.

## Repeat the checks

From the repository root, run `./scripts/start.sh` (PowerShell: `./scripts/start.ps1`). Then, from `frontend/` with Node 24:

```bash
npm ci
npm run lint
npm run test:unit
npx tsc --noEmit
npx playwright install chromium
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 npm run test:e2e
```

In PowerShell set `$env:PLAYWRIGHT_BASE_URL="http://127.0.0.1:8000"` before `npm run test:e2e`. Backend tests run from `backend/` with `uv run --locked pytest`.
