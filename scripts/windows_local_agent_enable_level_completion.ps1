# Installs the review-only Level 4-20 completion queue on the owner's Windows PC.
# Requires current-user Task Scheduler ownership; NEVER interrupts active PR work.
[CmdletBinding()]
param([switch]$Install,[switch]$Status)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (($Install -and $Status) -or (-not $Install -and -not $Status)) {
  throw 'Specify exactly one of -Install and -Status.'
}
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$data=Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
$stopToken=Join-Path $data 'STOP'
$heartbeat=Join-Path $data 'heartbeat.json'
$completion=Join-Path $data 'level_completion_ledger.json'
$oldLedger=Join-Path $data 'ledger.json'
$taskName='PDUFA-Continuous-Development'
$guardName='PDUFA-Continuous-Watchdog'
$branch='automation/level-completion-queue-20261112'
$remoteRef='refs/remotes/origin/automation/level-completion-queue-20261112'
$files=@(
  'automation/scientific-level-completion-queue.json',
  'scripts/pdufa_level_completion.py',
  'scripts/level4_scientific_evidence.py',
  'tests/test_pdufa_level_completion.py',
  'tests/test_level4_scientific_evidence.py',
  'scripts/windows_local_agent_watchdog.ps1'
)
# Approved, exact Git blob IDs for this review slice; no branch drift.
$allowed=@{
 'automation/scientific-level-completion-queue.json'='94f40f5dfa2c299f8a23d650aef8dd8b7bd67098'
 'scripts/pdufa_level_completion.py'='aaa99fc25c2b7e37cc8f17afe0a5418612b9bd99'
 'scripts/level4_scientific_evidence.py'='2530d029f49b8ab4ec1f21f7db784d5864bf5c36'
 'tests/test_pdufa_level_completion.py'='fd8a2e92a294ec913ce35e8aa9bc085237ed3c27'
 'tests/test_level4_scientific_evidence.py'='5a30ed426188aa8da968639fc763842d9d15f0e6'
 'scripts/windows_local_agent_watchdog.ps1'='5b83e1913fd70e7f8aa72fcb5fc43844e11f3aae'
}
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
function AssertOwner($task) {
  $name=[string]$task.Principal.UserId
  if ([string]::IsNullOrWhiteSpace($name)) { throw 'Task principal missing.' }
  try {
    if($name -match '^S-1-[0-9]+(?:-[0-9]+)+$') {
      $sid=([Security.Principal.SecurityIdentifier]::new($name)).Value
    } else {
      $sid=([Security.Principal.NTAccount]::new($name)).Translate(
        [Security.Principal.SecurityIdentifier]).Value
    }
  } catch { throw 'Task principal could not be verified.' }
  if($sid -ne $who.User.Value) { throw 'Task belongs to a different Windows account.' }
}
function RequireSuccess([string]$name) {
  if($LASTEXITCODE -ne 0) { throw ($name+'_FAILED') }
}
$worker=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
AssertOwner $worker
if(@($worker.Actions).Count -ne 1 -or
   $worker.Actions[0].Arguments -notmatch '(?:windows_local_agent_continuous|pdufa_level_completion)\.py' -or
   $worker.Actions[0].Arguments -notmatch '(?<!\S)--run(?!\S)') {
  throw 'Unrecognized worker action. No modifications made.'
}
if($Status) {
  Write-Host ('Windows worker: '+$worker.State)
  if(Test-Path -LiteralPath $heartbeat -PathType Leaf) {
    $h=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
    Write-Host ('Heartbeat queue: '+$h.queue)
    Write-Host ('Heartbeat mode: '+$h.mode)
    Write-Host ('Level: '+$h.level+' Task: '+$h.task)
    Write-Host ('Heartbeat UTC: '+$h.updated_utc)
  }
  if(Test-Path -LiteralPath $completion -PathType Leaf) {
    & py -3.13 -B (Join-Path $root 'scripts/pdufa_level_completion.py') --status
    exit $LASTEXITCODE
  }
  Write-Host 'Completion queue has not started.'
  exit 2
}
if(-not(Test-Path -LiteralPath $oldLedger -PathType Leaf) -or
   -not(Test-Path -LiteralPath (Join-Path $root 'AGENTS.md') -PathType Leaf)) {
  throw 'Original engineering ledger or safety policy is missing.'
}
if(Test-Path -LiteralPath $stopToken) { throw 'Owner STOP exists; do not override it.' }
if($worker.State -eq 'Disabled') { throw 'Worker disabled; owner intervention required.' }
$runAction=[string]$worker.Actions[0].Arguments
if($runAction -match 'pdufa_level_completion\.py') {
  Write-Host 'LEVEL_COMPLETION_ALREADY_CONFIGURED: use -Status.'
  exit 0
}
if($worker.State -eq 'Running') {
  # Only allow an intentional graceful drain if the prior worker is provably
  # idle and BOTH approved draft queues have no pending/in-flight tasks.
  if(-not(Test-Path -LiteralPath $heartbeat -PathType Leaf)) {
    throw 'Running without heartbeat; do not terminate an in-flight PR.'
  }
  $h=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
  $age=((Get-Date).ToUniversalTime()-
       [datetime]::Parse([string]$h.updated_utc).ToUniversalTime()).TotalSeconds
  if($h.mode -notin @('IDLE','QUEUE_EXHAUSTED') -or
     $age -lt 0 -or $age -gt 90) {
    throw 'Worker is running or heartbeat is stale; no in-flight work may be terminated.'
  }
  $old=Get-Content -LiteralPath $oldLedger -Raw | ConvertFrom-Json
  foreach($group in @('tasks','validation_jobs')) {
    $key=$old.PSObject.Properties[$group]
    if($null -eq $key -or $null -eq $key.Value) {
      throw 'Approved draft queues have not both been verified exhausted.'
    }
    foreach($x in $key.Value.PSObject.Properties) {
      if($x.Value.status -in @('PENDING','RUNNING')) {
        throw 'Unfinished earlier task exists: no drain permitted.'
      }
    }
  }
} elseif($worker.State -ne 'Ready') {
  throw ('Unsafe Windows worker state: '+$worker.State)
}
$origin=(& git -C $root remote get-url origin | Out-String).Trim()
RequireSuccess 'READ_REMOTE'
if($origin -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)pdufa/pdufa-command-center(?:\.git)?/?$') {
  throw 'Unexpected GitHub remote; no changes made.'
}
$repoTop=(& git -C $root rev-parse --show-toplevel | Out-String).Trim().Replace('/','\').TrimEnd('\')
RequireSuccess 'ROOT'
if(-not [string]::Equals($repoTop,$root.Replace('/','\').TrimEnd('\'),
                         [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Unexpected working Git checkout.'
}
$oldAction=$worker.Actions[0]
$guard=Get-ScheduledTask -TaskName $guardName -ErrorAction SilentlyContinue
$guardEnabled=$false
if($guard) {
  AssertOwner $guard
  if(@($guard.Actions).Count -ne 1 -or
     $guard.Actions[0].Arguments -notmatch 'windows_local_agent_watchdog\.ps1') {
    throw 'Unexpected watchdog task; do not alter it.'
  }
  $guardEnabled=($guard.State -ne 'Disabled')
}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmssfff')
$stage=Join-Path $data ('completion-stage-'+$stamp)
$backup=Join-Path $data ('completion-backup-'+$stamp)
$backups=@()
$drained=$false
$changedAction=$false
$filesReady=$false
New-Item -ItemType Directory -Path $stage,$backup -Force | Out-Null
try {
  if($guardEnabled) {
    Disable-ScheduledTask -TaskName $guardName -ErrorAction Stop | Out-Null
  }
  if((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
    # Existing Python honors STOP between bounded tasks. This has been approved
    # by the owner for idle-only migration. No forced process termination.
    Set-Content -LiteralPath $stopToken -Value 'GRACEFUL_IDLE_UPGRADE' -Encoding ASCII
    $drained=$true
    $ready=$false
    for($i=0;$i -lt 35;$i++) {
      Start-Sleep -Seconds 2
      if((Get-ScheduledTask -TaskName $taskName).State -eq 'Ready') {
        $ready=$true
        break
      }
    }
    if(-not $ready) { throw 'Graceful idle drain timed out; no forced stop attempted.' }
  }
  $state=Get-ScheduledTask -TaskName $taskName
  if($state.State -ne 'Ready') { throw 'Worker unexpectedly active during upgrade.' }
  & git -C $root fetch --no-tags origin ('+refs/heads/'+$branch+':'+$remoteRef)
  RequireSuccess 'FETCH_REVIEWED_QUEUE'
  $revision=(& git -C $root rev-parse ($remoteRef+'^{commit}') | Out-String).Trim()
  RequireSuccess 'REVISION'
  if($revision -notmatch '^[0-9a-f]{40}$') { throw 'Invalid reviewed commit.' }
  foreach($path in $files) {
    $blob=(& git -C $root rev-parse ($revision+':'+$path) | Out-String).Trim()
    RequireSuccess 'BLOB'
    if($blob -ne $allowed[$path]) {
      throw ('Reviewed file changed since approval: '+$path)
    }
    $target=Join-Path $stage ($path.Replace('/','\'))
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    $url='https://raw.githubusercontent.com/pdufa/pdufa-command-center/'+$revision+'/'+$path
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target -ErrorAction Stop
    $actual=(& git -C $root hash-object $target | Out-String).Trim()
    RequireSuccess 'HASH'
    if($actual -ne $blob) { throw ('Downloaded source hash mismatch: '+$path) }
  }
  foreach($path in $files) {
    $local=Join-Path $root ($path.Replace('/','\'))
    $incoming=Join-Path $stage ($path.Replace('/','\'))
    $original=Join-Path $backup ($path.Replace('/','\'))
    $existed=(Test-Path -LiteralPath $local -PathType Leaf)
    if($existed) {
      New-Item -ItemType Directory -Path (Split-Path $original) -Force | Out-Null
      Copy-Item -LiteralPath $local -Destination $original -ErrorAction Stop
    }
    $backups+=@{file=$local; backup=$original; existed=$existed}
    New-Item -ItemType Directory -Path (Split-Path $local) -Force | Out-Null
    Copy-Item -LiteralPath $incoming -Destination $local -Force -ErrorAction Stop
  }
  & py -3.13 -B (Join-Path $root 'scripts/pdufa_level_completion.py') --self-test
  RequireSuccess 'COMPLETION_SELF_TEST'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_level_completion.py' -v
  RequireSuccess 'QUEUE_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level4_scientific_evidence.py' -v
  RequireSuccess 'LEVEL4_REGRESSIONS'
  & py -3.13 -B (Join-Path $root 'scripts/audit_raas_retirement.py') --check
  RequireSuccess 'RETIRED_DEPENDENCY_AUDIT'
  $filesReady=$true
  $python=(Get-Command py.exe -ErrorAction Stop).Source
  $controller=Join-Path $root 'scripts/pdufa_level_completion.py'
  $action=New-ScheduledTaskAction -Execute $python -Argument ('-3.13 "{0}" --run' -f $controller) -WorkingDirectory $root
  Set-ScheduledTask -TaskName $taskName -Action $action -ErrorAction Stop | Out-Null
  $changedAction=$true
  if($drained) { Remove-Item -LiteralPath $stopToken -Force -ErrorAction Stop }
} catch {
  if($changedAction) {
    Set-ScheduledTask -TaskName $taskName -Action $oldAction -ErrorAction SilentlyContinue | Out-Null
  }
  if(-not $filesReady) {
    foreach($record in $backups) {
      if($record.existed) {
        Copy-Item -LiteralPath $record.backup -Destination $record.file -Force -ErrorAction SilentlyContinue
      } else {
        Remove-Item -LiteralPath $record.file -Force -ErrorAction SilentlyContinue
      }
    }
  }
  if($drained -and (Test-Path -LiteralPath $stopToken)) {
    Remove-Item -LiteralPath $stopToken -Force -ErrorAction SilentlyContinue
  }
  throw
} finally {
  if($guardEnabled) {
    Enable-ScheduledTask -TaskName $guardName -ErrorAction Stop | Out-Null
  }
  Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
if(-not $changedAction) { throw 'Completion task action was not installed.' }
Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
$verified=$false
for($i=0;$i -lt 30;$i++) {
  Start-Sleep -Seconds 2
  if(-not(Test-Path -LiteralPath $heartbeat -PathType Leaf) -or
     -not(Test-Path -LiteralPath $completion -PathType Leaf)) { continue }
  try {
    $h=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
    $l=Get-Content -LiteralPath $completion -Raw | ConvertFrom-Json
    $age=((Get-Date).ToUniversalTime()-
         [datetime]::Parse([string]$h.updated_utc).ToUniversalTime()).TotalSeconds
    $first=$l.levels.PSObject.Properties['4'].Value.steps.AUDIT_EXISTING_DRAFTS.status
    if($h.queue -eq 'LEVEL_COMPLETION' -and $age -ge 0 -and $age -lt 45 -and
       $first -in @('RUNNING','DONE','BLOCKED') -and
       (Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
      $verified=$true
      break
    }
  } catch { }
}
if(-not $verified) {
  Write-Warning 'LEVEL_COMPLETION_START_NOT_VERIFIED. No automatic rollback of possibly active work.'
  exit 2
}
Write-Host 'LEVEL_COMPLETION_STARTED_AND_VERIFIED: worker loaded queue and started Level 4.'
Write-Host ('Persistent ledger: '+$completion)
Write-Host ('Rollback backups retained: '+$backup)
Write-Host 'Draft-only; scientific review and acceptance remain independent.'
