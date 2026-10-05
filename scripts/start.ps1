$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try {
    docker compose up --build --detach --wait --wait-timeout 90
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed to start the app. See the output above.' }
    Write-Host 'Project Management is ready at http://localhost:8000'
} finally {
    Pop-Location
}
