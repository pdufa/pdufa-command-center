# Read-only Level 456 local staging smoke test.
# Never starts, stops, or modifies containers; never prints secrets.
$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot ".env"
$composeFile = Join-Path $PSScriptRoot "compose.yaml"
$base = "http://127.0.0.1:8765/api/assessment-runtime"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Local 456 staging .env is missing. Run Start-Scientific456Local.ps1 first."
}
$keyLines = @(Get-Content -LiteralPath $envFile |
    Where-Object { $_ -match '^SCIENTIFIC456_INTERNAL_API_KEY=[0-9a-f]{64}$' })
if ($keyLines.Count -ne 1) {
    throw "Expected one valid generated isolated staging key; no request was sent."
}
$key = ($keyLines[0] -split '=',2)[1]
$headers = @{ "X-Pdufa-Internal-Key" = $key }

# Safety: confirm the committed service config disables research writes.
$config = [System.IO.File]::ReadAllText($composeFile)
if (-not $config.Contains('PDUFA_MIGRATION_READ_ONLY: "1"')) {
    throw "The local staging configuration is not read-only. Refusing verification."
}
if (-not $config.Contains('"127.0.0.1:8765:8000"')) {
    throw "API is not configured for the exact localhost port. Refusing verification."
}

Write-Host "Checking standalone Level 456 staging on 127.0.0.1 only..." -ForegroundColor Cyan
$version = Invoke-RestMethod -Method Get -Uri "$base/version" -TimeoutSec 10
if ($version.stagingMode -ne "SCIENTIFIC_456_ISOLATED_ONLY" -or
    $version.scientific456Enabled -ne $true -or
    $version.legacy123Separate -ne $true -or
    (($version.levels -join ',') -ne "4,5,6") -or
    $version.fdaModel -ne "ABSTAIN") {
    throw "Unexpected staging contract or disabled state. Do not attempt assessments."
}
Write-Host "PASS: isolated Levels 4, 5, 6 contract and abstaining FDA forecast" -ForegroundColor Green

$health = Invoke-RestMethod -Method Get -Uri "$base/health" -TimeoutSec 10
if ($health.status -ne "READY" -or
    $health.stagingMode -ne "SCIENTIFIC_456_ISOLATED_ONLY") {
    throw "PostgreSQL staging readiness has not been verified."
}
Write-Host "PASS: independent local PostgreSQL database reachable" -ForegroundColor Green

$history = Invoke-RestMethod -Method Get -Headers $headers -Uri "$base/history/NCT00000000?contract=SCIENTIFIC_1_6" -TimeoutSec 10
if ($history.nct -ne "NCT00000000" -or
    $history.hasMore -ne $false -or
    @($history.runs).Count -ne 0) {
    throw "Read-only synthetic-NCT history did not return the expected empty result."
}
Write-Host "PASS: authenticated exact-contract history read with no writes" -ForegroundColor Green

Write-Host "LOCAL STAGING READY FOR READ-ONLY INSPECTION. Assessment writes remain disabled." -ForegroundColor Green
Write-Host "This does NOT connect to the public Vercel dashboard or enable FDA forecasts." -ForegroundColor Yellow
