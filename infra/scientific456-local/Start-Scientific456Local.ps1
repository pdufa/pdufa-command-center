# Start a LOCAL ONLY Level 456 PostgreSQL sandbox; no production services.
# The PowerShell window running other tests is unaffected.
$ErrorActionPreference = "Stop"
$compose = Join-Path $PSScriptRoot "compose.yaml"
$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is unavailable. Install or start it first."
}
& docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose is unavailable. No containers were changed."
}

# Refuse remote Docker contexts: local loopback on a remote Docker engine
# would not be a local-only sandbox on this Windows PC.
$contextJson = & docker context inspect
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect Docker context. No containers were changed."
}
$contextText = $contextJson -join [Environment]::NewLine
$contexts = @($contextText | ConvertFrom-Json)
if ($contexts.Count -ne 1) {
    throw "Docker context was not uniquely identified. No containers were changed."
}
$dockerHost = [string]$contexts[0].Endpoints.docker.Host
if ($dockerHost -notmatch '^(npipe|unix)://') {
    throw "Remote Docker context refused. Use local Docker Desktop rather than TCP or SSH."
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
    $utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false
    [System.IO.File]::WriteAllText($envFile, $body, $utf8)
    Write-Host "Generated independent local secrets in gitignored .env (values hidden)." -ForegroundColor Green
}

$entries = @(Get-Content -LiteralPath $envFile)
$dbMatches = @($entries | Where-Object { $_ -match '^SCIENTIFIC456_DB_PASSWORD=[0-9a-f]{64}$' })
$keyMatches = @($entries | Where-Object { $_ -match '^SCIENTIFIC456_INTERNAL_API_KEY=[0-9a-f]{64}$' })
if ($entries.Count -ne 2 -or $dbMatches.Count -ne 1 -or $keyMatches.Count -ne 1) {
    throw "The local .env must contain exactly two generated 64-character secrets. No containers were changed."
}
& docker compose --env-file $envFile -f $compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "Local Docker Compose config is invalid. No containers were changed."
}

Write-Host "Starting independent PostgreSQL and read-only Level 456 API..." -ForegroundColor Cyan
& docker compose --env-file $envFile -f $compose up -d --build
if ($LASTEXITCODE -ne 0) {
    throw "Local Level 456 Docker startup failed. Production was not touched."
}

Write-Host "Local version: http://127.0.0.1:8765/api/assessment-runtime/version"
Write-Host "Local readiness: http://127.0.0.1:8765/api/assessment-runtime/health"
Write-Host "Run the separate Test-Scientific456Local.ps1 for a read-only smoke test."
Write-Host "Assessment writes remain disabled." -ForegroundColor Yellow
