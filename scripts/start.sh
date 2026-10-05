#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up --build --detach --wait --wait-timeout 90
printf 'Project Management is ready at http://localhost:8000\n'
