$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..')
try {
    docker compose down
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed to stop the app. See the output above.' }
    Write-Host 'Project Management stopped. Database volume preserved.'
} finally {
    Pop-Location
}
