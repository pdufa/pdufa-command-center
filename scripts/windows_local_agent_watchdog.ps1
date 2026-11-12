# PDUFA continuous agent watchdog. Recovery only; never clears STOP, auto-merges or deploys.
[CmdletBinding()]
param([switch]$Install, [switch]$Check, [switch]$Status, [switch]$Uninstall)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$workerName='PDUFA-Continuous-Development'
$watchdogName='PDUFA-Continuous-Watchdog'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$controller=Join-Path $PSScriptRoot 'windows_local_agent_continuous.py'
$data=Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
$stopToken=Join-Path $data 'STOP'
$ledger=Join-Path $data 'ledger.json'
$heartbeat=Join-Path $data 'heartbeat.json'
$watchdogStatus=Join-Path $data 'watchdog_status.json'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if (@(@($Install,$Check,$Status,$Uninstall) | Where-Object { $_ }).Count -ne 1) {
  throw 'Specify exactly one of -Install, -Check, -Status or -Uninstall.'
}
function Test-Owner([object]$task) {
  $owner=[string]$task.Principal.UserId
  if ([string]::IsNullOrWhiteSpace($owner)) { throw 'Scheduled task owner missing.' }
  try {
    if ($owner -match '^S-1-[0-9]+(?:-[0-9]+)+$') {
      $sid=([Security.Principal.SecurityIdentifier]::new($owner)).Value
    } else {
      $sid=([Security.Principal.NTAccount]::new($owner)).Translate([Security.Principal.SecurityIdentifier]).Value
    }
  } catch { throw 'Scheduled task owner could not be verified.' }
  if ($sid -ne $identity.User.Value) { throw 'Scheduled task belongs to another Windows user.' }
}
function Assert-Worker {
  $task=Get-ScheduledTask -TaskName $workerName -ErrorAction Stop
  Test-Owner $task
  $actions=@($task.Actions)
  if ($actions.Count -ne 1 -or
      $actions[0].Execute -notmatch '(?i)(^|[\\/])py(?:\.exe)?$' -or
      $actions[0].Arguments -notmatch 'windows_local_agent_continuous\.py' -or
      $actions[0].Arguments -notmatch '(?<!\S)--run(?!\S)') {
    throw 'Worker is not the approved continuous PDUFA worker.'
  }
  if (-not (Test-Path -LiteralPath $controller -PathType Leaf) -or
      -not (Test-Path -LiteralPath (Join-Path $repo 'AGENTS.md') -PathType Leaf) -or
      -not (Test-Path -LiteralPath $ledger -PathType Leaf)) {
    throw 'Missing activated worker, safety policy, or persistent ledger.'
  }
  return $task
}
function Assert-Own-Watchdog([object]$task) {
  Test-Owner $task
  $actions=@($task.Actions)
  if ($actions.Count -ne 1 -or
      $actions[0].Execute -notmatch '(?i)(^|[\\/])powershell(?:\.exe)?$' -or
      $actions[0].Arguments -notmatch 'windows_local_agent_watchdog\.ps1' -or
      $actions[0].Arguments -notmatch '(?<!\S)-Check(?!\S)') {
    throw 'Existing watchdog task is not the expected task. No changes made.'
  }
}
function Save-Check([string]$result,[string]$state) {
  New-Item -ItemType Directory -Path $data -Force | Out-Null
  $record=@{
    checked_utc=(Get-Date).ToUniversalTime().ToString('o')
    watchdog_result=$result
    worker_task_state=$state
    stop_requested=(Test-Path -LiteralPath $stopToken)
  }
  $temp=Join-Path $data ('.watchdog-'+$PID+'.tmp')
  try {
    $record | ConvertTo-Json | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $watchdogStatus -Force
  } finally { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}
if ($Uninstall) {
  $old=Get-ScheduledTask -TaskName $watchdogName -ErrorAction SilentlyContinue
  if ($null -ne $old) {
    Assert-Own-Watchdog $old
    Unregister-ScheduledTask -TaskName $watchdogName -Confirm:$false -ErrorAction Stop
  }
  Write-Host 'WATCHDOG_UNINSTALLED: worker, STOP and ledger unchanged.'
  exit 0
}
if ($Install) {
  $worker=Assert-Worker
  if ($worker.State -eq 'Disabled') { throw 'Worker is disabled; no recovery installed.' }
  $old=Get-ScheduledTask -TaskName $watchdogName -ErrorAction SilentlyContinue
  if ($null -ne $old) { Assert-Own-Watchdog $old }
  $scriptPath=(Resolve-Path -LiteralPath $PSCommandPath).Path
  if ($scriptPath.Contains('"')) { throw 'Unsafe path quote.' }
  $exe=Join-Path $PSHOME 'powershell.exe'
  $action=New-ScheduledTaskAction -Execute $exe -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Check' -f $scriptPath) -WorkingDirectory $repo
  $logon=New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
  # No RepetitionDuration means indefinite repetition per Windows Task Scheduler.
  $repeat=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2)
  $principal=New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
  $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $watchdogName -Action $action -Trigger @($logon,$repeat) -Principal $principal -Settings $settings -Description 'Safe PDUFA worker recovery; no merges or deployments' -Force -ErrorAction Stop | Out-Null
  [xml]$xml=Export-ScheduledTask -TaskName $watchdogName -ErrorAction Stop
  $timeTriggers=@($xml.SelectNodes("//*[local-name()='TimeTrigger']"))
  $intervalNode=if ($timeTriggers.Count -eq 1) { $timeTriggers[0].SelectSingleNode("*[local-name()='Repetition']/*[local-name()='Interval']") } else { $null }
  $durationNode=if ($timeTriggers.Count -eq 1) { $timeTriggers[0].SelectSingleNode("*[local-name()='Repetition']/*[local-name()='Duration']") } else { $null }
  $instancesNode=$xml.SelectSingleNode("//*[local-name()='MultipleInstancesPolicy']")
  $valid=($timeTriggers.Count -eq 1 -and $null -ne $intervalNode -and $intervalNode.InnerText -eq 'PT2M' -and $null -eq $durationNode -and $null -ne $instancesNode -and $instancesNode.InnerText -eq 'IgnoreNew')
  if (-not $valid) {
    Disable-ScheduledTask -TaskName $watchdogName -ErrorAction SilentlyContinue | Out-Null
    throw 'Task Scheduler did not preserve indefinite watchdog repetition; disabled.'
  }
  Write-Host 'WATCHDOG_INSTALLED: 2-minute checks and Windows sign-in checks.'
  Write-Host 'Completed stages stay completed; owner STOP and blockers are respected.'
  if (Test-Path -LiteralPath $stopToken) {
    Write-Host 'OWNER_STOP_PRESENT: no automatic restart.'
  } else {
    & $PSCommandPath -Check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  exit 0
}
if ($Status) {
  $worker=Get-ScheduledTask -TaskName $workerName -ErrorAction SilentlyContinue
  $guard=Get-ScheduledTask -TaskName $watchdogName -ErrorAction SilentlyContinue
  Write-Host ('Worker: '+$(if($worker){$worker.State}else{'NOT_INSTALLED'}))
  Write-Host ('Watchdog: '+$(if($guard){$guard.State}else{'NOT_INSTALLED'}))
  Write-Host ('Owner STOP: '+(Test-Path -LiteralPath $stopToken))
  if (Test-Path -LiteralPath $watchdogStatus -PathType Leaf) {
    $info=Get-Content -LiteralPath $watchdogStatus -Raw | ConvertFrom-Json
    Write-Host ('Last check UTC: '+$info.checked_utc)
    Write-Host ('Last action: '+$info.watchdog_result)
  }
  if (Test-Path -LiteralPath $heartbeat -PathType Leaf) {
    $pulse=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
    Write-Host ('Worker heartbeat UTC: '+$pulse.updated_utc)
    Write-Host ('Worker mode: '+$pulse.mode)
  }
  exit 0
}
$worker=Assert-Worker
if (Test-Path -LiteralPath $stopToken) {
  Save-Check 'OWNER_STOP_SUPPRESSES_RESTART' ([string]$worker.State)
  Write-Host 'OWNER_STOP_SUPPRESSES_RESTART'
  exit 0
}
if ($worker.State -eq 'Disabled') {
  Save-Check 'WORKER_DISABLED_NO_RESTART' ([string]$worker.State)
  Write-Host 'WORKER_DISABLED_NO_RESTART'
  exit 0
}
if ($worker.State -eq 'Running' -or $worker.State -eq 'Queued') {
  $result='ALREADY_RUNNING_OR_QUEUED'
  if ($worker.State -eq 'Running' -and (Test-Path -LiteralPath $heartbeat -PathType Leaf)) {
    try {
      $pulse=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
      $age=((Get-Date).ToUniversalTime()-[datetime]::Parse([string]$pulse.updated_utc).ToUniversalTime()).TotalMinutes
      if ($age -gt 5) { $result='RUNNING_STALE_HEARTBEAT_REVIEW_REQUIRED' }
    } catch { $result='RUNNING_UNREADABLE_HEARTBEAT_REVIEW_REQUIRED' }
  }
  Save-Check $result ([string]$worker.State)
  Write-Host $result
  exit 0
}
if ($worker.State -ne 'Ready') {
  Save-Check 'UNKNOWN_STATE_NO_RESTART' ([string]$worker.State)
  Write-Host ('UNKNOWN_STATE_NO_RESTART: '+$worker.State)
  exit 0
}
# Task Scheduler IgnoreNew and Python RUNNING.lock prevent duplicate workers.
Start-ScheduledTask -TaskName $workerName -ErrorAction Stop
Start-Sleep -Seconds 3
$after=Get-ScheduledTask -TaskName $workerName -ErrorAction Stop
$result=if($after.State -eq 'Running'){'RESTARTED_CONFIRMED_RUNNING'}else{'RESTART_REQUESTED_NOT_YET_CONFIRMED'}
Save-Check $result ([string]$after.State)
Write-Host $result
exit 0
