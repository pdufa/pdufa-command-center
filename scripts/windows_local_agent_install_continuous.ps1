# Activate a separate continuous Windows worker only AFTER verified real pilot PR.
# Never merges, deploys, or modifies the existing PDUFA production service.
param(
  [switch]$Activate,
  [switch]$Stop,
  [switch]$Status
)
$ErrorActionPreference = 'Stop'
$taskName = 'PDUFA-Continuous-Development'
$oldTask = 'PDUFA-Local-AI-Proposals'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$controller = Join-Path $PSScriptRoot 'windows_local_agent_continuous.py'
$python = (Get-Command py.exe -ErrorAction Stop).Source

if ($Stop) {
  & $python -3.13 $controller --stop
  # Graceful stop token is checked between bounded tasks. For immediate
  # emergency stop, the user may run Stop-ScheduledTask manually.
  Write-Host "STOP REQUESTED: no new stages will start."
  exit $LASTEXITCODE
}

if ($Status) {
  & $python -3.13 $controller --status
  $scriptResult = $LASTEXITCODE
  $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if ($task) { Write-Host ("Windows task state: " + $task.State) }
  else { Write-Host "Continuous task is not installed." }
  exit $scriptResult
}

if (-not $Activate) {
  Write-Host "Use -Activate, -Stop, or -Status. Nothing was changed."
  exit 2
}
if (-not (Test-Path $controller)) { throw "Continuous worker file missing" }
if (-not (Test-Path (Join-Path $repo 'AGENTS.md'))) { throw "Safety policy missing" }

Write-Host "PRECHECK: Verify repo, strict retirement audit, GitHub and local Ollama."
& $python -3.13 $controller --preflight
if ($LASTEXITCODE -ne 0) { throw "Preflight failed. Old schedule remains unchanged." }
& $python -3.13 $controller --self-test
if ($LASTEXITCODE -ne 0) { throw "Offline safety self-test failed. Old schedule remains unchanged." }
Write-Host "BASE CHECK: Audit the exact clean development PR baseline before consuming a pilot attempt."
& $python -3.13 $controller --base-check
if ($LASTEXITCODE -ne 0) { throw "Audited review base failed. Pilot not attempted; old schedule remains unchanged." }
Write-Host "COMMIT CHECK: Test a real isolated Git commit without push or PR."
& $python -3.13 $controller --commit-check
if ($LASTEXITCODE -ne 0) { throw "Local Git commit prerequisites failed. Pilot not attempted; old schedule remains unchanged." }
Write-Host "RECOVERY: Reopen only previously blocked Stage 4 commit attempt, preserving the failure history."
& $python -3.13 $controller --retry-stage4
if ($LASTEXITCODE -ne 0) { throw "Stage 4 retry not authorized. Pilot not attempted; old schedule remains unchanged." }

# A real pilot must create a draft PR and verify it remains a draft.
# Before the pilot, no unattended code application or issue update is enabled.
Write-Host "PILOT: Produce one bounded Level 4 research-only code scaffold."
& $python -3.13 $controller --clear-stop
if ($LASTEXITCODE -ne 0) { throw "Stop-control reset failed" }
& $python -3.13 $controller --pilot
if ($LASTEXITCODE -ne 0) {
  Write-Host "PILOT FAILED: continuous mode NOT activated."
  exit 2
}

# An interactive-token task runs even when the screen is locked, but not when
# the PC is powered off or the Windows user has signed out.
$userId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$action = New-ScheduledTaskAction -Execute $python -Argument ('-3.13 "{0}" --run' -f $controller) -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$prior = Get-ScheduledTask -TaskName $oldTask -ErrorAction SilentlyContinue

# Keep original task available for rollback, but disabled before continuous run
# so the old four-hour model job cannot compete for local resources.
if ($prior) {
  Disable-ScheduledTask -TaskName $oldTask -ErrorAction Stop | Out-Null
}
try {
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Continuous protected PDUFA engineering drafting; verified draft PRs only; manual STOP control' -Force | Out-Null
  Start-ScheduledTask -TaskName $taskName -ErrorAction Stop

  $healthy = $false
  for ($i = 0; $i -lt 16; $i++) {
    Start-Sleep -Seconds 2
    $current = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    & $python -3.13 $controller --status --require-running | Out-Null
    if ($LASTEXITCODE -eq 0 -and $current -and $current.State -eq 'Running') {
      $healthy = $true
      break
    }
  }
  if (-not $healthy) { throw "Continuous worker did not pass live heartbeat validation." }
} catch {
  Write-Host "ACTIVATION NOT CONFIRMED: restore the original schedule."
  Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  Disable-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
  if ($prior) {
    Enable-ScheduledTask -TaskName $oldTask -ErrorAction SilentlyContinue | Out-Null
  }
  throw
}

Write-Host "ACTIVATED: $taskName"
Write-Host "Verified real Level 4 draft PR pilot and current heartbeat."
Write-Host "Next stage starts when the preceding task finishes, not in four hours."
Write-Host "Only one code-generation and test task runs at a time."
Write-Host "Automatic merges, deployments, and clinical prediction changes: DISABLED."
Write-Host "Progress ledger: $env:USERPROFILE\PDUFA-Agent-Continuous\ledger.json"
Write-Host "Stop: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows_local_agent_install_continuous.ps1 -Stop"
Write-Host "Status: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows_local_agent_install_continuous.ps1 -Status"
Write-Host "PC must remain powered on and the Windows user signed in (locked is fine)."
