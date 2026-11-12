# Upgrade the active, local PDUFA agent to its existing second approved queue.
# Does not delete the ledger, override owner STOP, merge or deploy changes.
[CmdletBinding()]
param([switch]$Install,[switch]$Status)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (($Install -and $Status) -or (-not $Install -and -not $Status)) {
  throw 'Specify -Install or -Status.'
}
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$data=Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
$ledger=Join-Path $data 'ledger.json'
$stop=Join-Path $data 'STOP'
$workerTask='PDUFA-Continuous-Development'
$watchdogTask='PDUFA-Continuous-Watchdog'
$originBranch='automation/windows-local-agent-monitor'
$remoteRef='refs/remotes/origin/automation/windows-local-agent-monitor'
$paths=@('scripts/windows_local_agent_continuous.py','scripts/windows_local_agent_followon.py')
# Pin the reviewed blobs: a moved branch must not silently change the worker.
$approvedBlobs=@{
  'scripts/windows_local_agent_continuous.py'='8f248946968c78d84c79f4ad1eb89ea87bc7483c'
  'scripts/windows_local_agent_followon.py'='2e29a10ca3bc47285a955a9ad0c2e70220c80430'
}
$current=[Security.Principal.WindowsIdentity]::GetCurrent()
function VerifyOwner($task) {
  $id=[string]$task.Principal.UserId
  if ([string]::IsNullOrWhiteSpace($id)) { throw 'Task owner missing.' }
  try {
    if ($id -match '^S-1-[0-9]+(?:-[0-9]+)+$') {
      $sid=([Security.Principal.SecurityIdentifier]::new($id)).Value
    } else {
      $sid=([Security.Principal.NTAccount]::new($id)).Translate([Security.Principal.SecurityIdentifier]).Value
    }
  } catch { throw 'Cannot validate task Windows identity.' }
  if ($sid -ne $current.User.Value) { throw 'Task belongs to another Windows user.' }
}
function RequireSuccess([string]$phase) {
  if ($LASTEXITCODE -ne 0) { throw ($phase + '_FAILED') }
}
$task=Get-ScheduledTask -TaskName $workerTask -ErrorAction Stop
VerifyOwner $task
if (@($task.Actions).Count -ne 1 -or
    $task.Actions[0].Arguments -notmatch 'windows_local_agent_continuous\.py' -or
    $task.Actions[0].Arguments -notmatch '(?<!\S)--run(?!\S)') {
  throw 'The registered task is not the approved continuous worker.'
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'AGENTS.md') -PathType Leaf) -or
    -not (Test-Path -LiteralPath $ledger -PathType Leaf)) {
  throw 'Approved repository policy or existing progress ledger missing.'
}
if ($Status) {
  Write-Host ('Worker task: '+$task.State)
  & py -3.13 -B (Join-Path $root $paths[0]) --status
  exit $LASTEXITCODE
}
if ($task.State -ne 'Ready') {
  throw 'Worker must be Ready, not Running or Disabled, before safe upgrade. Do not terminate in-flight PR work.'
}
if (Test-Path -LiteralPath $stop) {
  throw 'Owner STOP is set. No changes made; owner must explicitly resume.'
}
$gitRoot=(& git -C $root rev-parse --show-toplevel)
RequireSuccess 'GIT_ROOT'
$normalizedGitRoot=(([string]$gitRoot).Replace('/','\')).TrimEnd('\')
$normalizedRoot=($root.Replace('/','\')).TrimEnd('\')
if (-not [string]::Equals($normalizedGitRoot,$normalizedRoot,[StringComparison]::OrdinalIgnoreCase)) {
  throw 'Local folder does not match Git checkout root.'
}
$remote=(& git -C $root remote get-url origin)
RequireSuccess 'GIT_ORIGIN'
if (([string]$remote).Trim() -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)pdufa/pdufa-command-center(?:\.git)?/?$') {
  throw 'Unexpected GitHub origin; aborting.'
}
$guard=Get-ScheduledTask -TaskName $watchdogTask -ErrorAction SilentlyContinue
$guardWasEnabled=$false
if ($null -ne $guard) {
  VerifyOwner $guard
  if (@($guard.Actions).Count -ne 1 -or
      $guard.Actions[0].Arguments -notmatch 'windows_local_agent_watchdog\.ps1' -or
      $guard.Actions[0].Arguments -notmatch '(?<!\S)-Check(?!\S)') {
    throw 'Unexpected watchdog task; aborting.'
  }
  $guardWasEnabled=$guard.State -ne 'Disabled'
}
$stage=Join-Path $data ('upgrade-stage-'+(Get-Date -Format 'yyyyMMddHHmmss'))
$backup=Join-Path $data ('upgrade-backup-'+(Get-Date -Format 'yyyyMMddHHmmss'))
$replaced=@()
$installed=$false
try {
  if ($guardWasEnabled) {
    Disable-ScheduledTask -TaskName $watchdogTask -ErrorAction Stop | Out-Null
    Stop-ScheduledTask -TaskName $watchdogTask -ErrorAction SilentlyContinue
  }
  $task=Get-ScheduledTask -TaskName $workerTask -ErrorAction Stop
  if ($task.State -ne 'Ready') { throw 'Worker became active during preflight; no files modified.' }
  & git -C $root fetch --no-tags origin ('+refs/heads/'+$originBranch+':'+$remoteRef)
  RequireSuccess 'FETCH_APPROVED_DEVELOPMENT_BASE'
  $source=((& git -C $root rev-parse ($remoteRef+'^{commit}')) | Out-String).Trim()
  RequireSuccess 'REVIEW_COMMIT'
  if ($source -notmatch '^[0-9a-f]{40}$') { throw 'Invalid source revision.' }
  New-Item -ItemType Directory -Path $stage,$backup -Force | Out-Null
  foreach ($p in $paths) {
    $blob=((& git -C $root rev-parse ($source+':'+$p)) | Out-String).Trim()
    RequireSuccess 'SOURCE_BLOB'
    if ($blob -notmatch '^[0-9a-f]{40}$' -or $blob -ne $approvedBlobs[$p]) {
      throw 'Approved source blob changed; review required before upgrading.'
    }
    $tmp=Join-Path $stage ([IO.Path]::GetFileName($p))
    $uri='https://raw.githubusercontent.com/pdufa/pdufa-command-center/'+$source+'/'+$p
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $tmp -ErrorAction Stop
    $actual=((& git -C $root hash-object $tmp) | Out-String).Trim()
    RequireSuccess 'HASH_DOWNLOADED_SOURCE'
    if ($actual -ne $blob) { throw 'Source blob hash mismatch; no changes made.' }
  }
  foreach ($p in $paths) {
    $dest=Join-Path $root $p
    $tmp=Join-Path $stage ([IO.Path]::GetFileName($p))
    $prior=Join-Path $backup ([IO.Path]::GetFileName($p))
    $hadFile=Test-Path -LiteralPath $dest -PathType Leaf
    if ($hadFile) { Copy-Item -LiteralPath $dest -Destination $prior -ErrorAction Stop }
    $replaced+=@{destination=$dest;backup=$prior;hadFile=$hadFile}
    Copy-Item -LiteralPath $tmp -Destination $dest -Force -ErrorAction Stop
  }
  & py -3.13 -B (Join-Path $root $paths[0]) --self-test
  RequireSuccess 'CONTINUATION_SELF_TEST'
  & py -3.13 -B (Join-Path $root $paths[0]) --status
  RequireSuccess 'EXISTING_LEDGER_VALIDATION'
  $installed=$true
  Write-Host ('CONTINUATION_FILES_READY: approved commit '+$source)
  Write-Host ('Original progress ledger preserved: '+$ledger)
  Write-Host ('Source backups: '+$backup)
} catch {
  if (-not $installed) {
    foreach ($item in $replaced) {
      if ($item.hadFile) {
        Copy-Item -LiteralPath $item.backup -Destination $item.destination -Force -ErrorAction SilentlyContinue
      } else {
        Remove-Item -LiteralPath $item.destination -Force -ErrorAction SilentlyContinue
      }
    }
  }
  throw
} finally {
  if ($guardWasEnabled) {
    Enable-ScheduledTask -TaskName $watchdogTask -ErrorAction Stop | Out-Null
  }
  Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
# Activates only existing reviewed-template follow-on queue, not live production changes.
Start-ScheduledTask -TaskName $workerTask -ErrorAction Stop
Write-Host 'CONTINUATION_START_REQUESTED: Stage 4-20 follow-on source-validation drafts.'
Write-Host 'The subsequent scientific/production installation still requires reviewed implementations and acceptance tests.'
Write-Host 'No merge, deployment, broker order, ledger reset, or STOP override performed.'
