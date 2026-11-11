# Install a recurring, review-only PDUFA local AI proposal task.
# Does not start the task, write code, or change GitHub/production.
param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$taskName = 'PDUFA-Local-AI-Proposals'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$controller = Join-Path $PSScriptRoot 'windows_local_agent_job.py'

if ($Remove) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Task removed: $taskName"
  exit 0
}
if (-not (Test-Path $controller)) { throw "Controller missing: $controller" }
if (-not (Test-Path (Join-Path $repo 'AGENTS.md'))) { throw "Safety policy missing" }

$python = (Get-Command py.exe -ErrorAction Stop).Source
$action = New-ScheduledTaskAction -Execute $python -Argument ('-3.13 "{0}"' -f $controller) -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(10) -RepetitionInterval (New-TimeSpan -Hours 4)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
# An interactive-token task works after the desktop is locked while logged in.
# It cannot run if the user signs out; this deliberate limitation avoids saving passwords.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Read-only Ollama proposals with redacted public GitHub issue status. No edits, push or deploy.' -Force | Out-Null
Write-Host "INSTALLED: $taskName"
Write-Host "Schedule: every 4 hours, beginning in approximately 10 minutes"
Write-Host "Security: current Windows user only; no administrator rights"
Write-Host "Reports: $env:USERPROFILE\\PDUFA-Agent-Reports`nRemote issue: https://github.com/pdufa/pdufa-command-center/issues/1096 (public, generic status only)"
Write-Host "PC must stay powered on, awake, signed in (may be locked)."
Write-Host "View task: Get-ScheduledTask -TaskName '$taskName'"
Write-Host "Disable task: Disable-ScheduledTask -TaskName '$taskName'"
Write-Host "Remove task: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\windows_local_agent_install_schedule.ps1 -Remove"
