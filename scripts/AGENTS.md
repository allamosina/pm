# Server scripts

- `start.sh` / `stop.sh`: Bash on macOS and Linux.
- `start.ps1` / `stop.ps1`: PowerShell on Windows.
- Scripts resolve the repository root from their own path, so they work from other directories.
- Start runs Docker Compose build/up and waits for health before reporting the URL. Failures must exit unsuccessfully.
- Stop runs Compose down without removing volumes. Never add `--volumes` to normal stop commands.
- Docker must be installed and running with Compose v2 and Linux containers. Port 8000 must be available.
