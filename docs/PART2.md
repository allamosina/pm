# Part 2 implementation and verification

Implemented on 2026-10-05. The app is running at http://localhost:8000.

## Implementation

- Python 3.14, FastAPI 0.142.2, Uvicorn 0.54.0; dependencies resolved in `backend/uv.lock`.
- Docker uses Python 3.14 slim and uv 0.12.23, installs locked runtime dependencies, and serves the temporary page and `/api/health`.
- Compose binds port 8000 to localhost, passes only the configured OpenRouter key at runtime, and mounts the named `pm-data` volume at `/data`.
- `DATABASE_PATH=/data/pm.sqlite3` is reserved for later implementation. No database schema or AI call is introduced here.
- The Docker build context allows only backend application inputs; secrets, local environments, and frontend artifacts are excluded.
- Bash and PowerShell start scripts wait for a healthy container; stop scripts preserve volumes.

The container approach follows the official [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/) and [FastAPI Docker guide](https://fastapi.tiangolo.com/deployment/docker/). Package versions were checked against PyPI during implementation.

## Verification results

| Check | Result |
| --- | --- |
| Backend tests with `uv run --locked pytest` from `backend/` | 3 passed; final run has no warnings. |
| Docker image build and `scripts/start.sh` | Passed; container becomes healthy before URL is printed. |
| Headless Chromium against the Docker app | Hello-world heading and `API connected: ok` displayed. |
| Browser with health request returning HTTP 503 | Displays `API unavailable. Refresh to try again.` |
| Stop and rebuild/restart using scripts | Passed. |
| Persistent volume | A temporary marker survived container removal/recreation; marker removed after verification. |
| Bash syntax and `git diff --check` | Passed. |
| Windows PowerShell scripts / native Linux host scripts | Reviewed but not executed; these environments are unavailable locally. The container itself was tested on Linux through Docker Desktop. |

## Issues resolved during verification

- Docker Desktop was initially stopped; its missing socket explained the failure. Starting Docker resolved it.
- Sandbox restrictions blocked uv's macOS configuration access and Chromium process registration; approved runs outside the sandbox succeeded.
- Invoking pytest from the repository root did not load backend configuration. Running from `backend/`, as documented, or specifying `-c backend/pyproject.toml` fixed collection.
- Installed Starlette deprecated the old `httpx` TestClient dependency. Its source explicitly selects `httpx2`; the development dependency and lockfile were updated and tests rerun successfully.

Part 3 has not started. The existing Next.js demo is unchanged and is not yet served by this container.
