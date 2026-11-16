# Local-only, free Level 456 staging. Never touches running PowerShell tests.
# Generates secrets once into a gitignored .env and keeps writes disabled.
$ErrorActionPreference = "Stop"
$compose = Join-Path $PSScriptRoot "compose.yaml"
$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is not available. Install or start it before running this script."
}
& docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose is not available. No containers were changed."
}

if (-not (Test-Path -LiteralPath $envFile)) {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $dbBytes = New-Object byte[] 32
        $keyBytes = New-Object byte[] 32
        $rng.GetBytes($dbBytes)
        $rng.GetBytes($keyBytes)
    }
    finally {
        $rng.Dispose()
    }
    $dbPassword = ([BitConverter]::ToString($dbBytes)).Replace("-", "").ToLowerInvariant()
    $apiKey = ([BitConverter]::ToString($keyBytes)).Replace("-", "").ToLowerInvariant()
    $body = "SCIENTIFIC456_DB_PASSWORD=$dbPassword" + [Environment]::NewLine +
            "SCIENTIFIC456_INTERNAL_API_KEY=$apiKey" + [Environment]::NewLine
    [System.IO.File]::WriteAllText($envFile, $body, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Created local credentials in ignored .env (not displayed)." -ForegroundColor Green
}

Write-Host "Starting isolated local PostgreSQL and read-only Level 456 API..." -ForegroundColor Cyan
& docker compose --env-file $envFile -f $compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose could not start Level 456 staging. No production service was modified."
}

Write-Host "Service startup requested. Check status using:" -ForegroundColor Cyan
Write-Host "docker compose --env-file `"$envFile`" -f `"$compose`" ps"
Write-Host "docker compose --env-file `"$envFile`" -f `"$compose`" logs --tail=40 api"
Write-Host "Read-only API: http://127.0.0.1:8765/api/assessment-runtime/version"
Write-Host "Database readiness: http://127.0.0.1:8765/api/assessment-runtime/health"
Write-Host "Assessment writes remain disabled (PDUFA_MIGRATION_READ_ONLY=1)." -ForegroundColor Yellow
