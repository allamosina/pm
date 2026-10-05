#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose down
printf 'Project Management stopped. Database volume preserved.\n'
