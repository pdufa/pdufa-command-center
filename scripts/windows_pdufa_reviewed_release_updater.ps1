# Windows reviewed-release updater. No automatic merges, science signoff, or trades.
# A GitHub *draft* PR is NOT deployable. Only a merged, reviewed PR into
# branch-protected main with required green checks may authorize a release.
[CmdletBinding()]
param([switch]$Install,[switch]$Check,[switch]$Status,[switch]$Uninstall)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (@(@($Install,$Check,$Status,$Uninstall) | Where-Object { $_ }).Count -ne 1) {
  throw 'Specify exactly one mode: -Install, -Check, -Status or -Uninstall.'
}
$repo='pdufa/pdufa-command-center'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$data=Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
$stop=Join-Path $data 'STOP'
$taskName='PDUFA-Reviewed-Release-Updater'
$workerName='PDUFA-Continuous-Development'
$script=Join-Path $PSScriptRoot 'windows_pdufa_reviewed_release_updater.ps1'
$installerRel='scripts/windows_pdufa_level6_unblock.ps1'
$installer=Join-Path $root ($installerRel.Replace('/','\'))
$statusPath=Join-Path $data 'reviewed-release-updater-status.json'
$mainRef='refs/remotes/origin/main'
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
function RequireSuccess([string]$name) {
  if($LASTEXITCODE -ne 0) { throw ($name+'_FAILED') }
}
function AssertOwner($task) {
  $id=[string]$task.Principal.UserId
  if([string]::IsNullOrWhiteSpace($id)) { throw 'Task owner missing.' }
  try {
    if($id -match '^S-1-[0-9]+(?:-[0-9]+)+$') {
      $sid=([Security.Principal.SecurityIdentifier]::new($id)).Value
    } else {
      $sid=([Security.Principal.NTAccount]::new($id)).Translate([Security.Principal.SecurityIdentifier]).Value
    }
  } catch { throw 'Task owner unverified.' }
  if($sid -ne $who.User.Value) { throw 'Task belongs to another Windows account.' }
}
function AssertUpdater($task) {
  AssertOwner $task
  if(@($task.Actions).Count -ne 1 -or
      $task.Actions[0].Execute -notmatch '(?i)(?:^|\\)powershell(?:\.exe)?$' -or
      $task.Actions[0].Arguments -notmatch [regex]::Escape($script) -or
      $task.Actions[0].Arguments -notmatch '(?:^|\s)-Check(?:\s|$)') {
    throw 'Existing updater task does not match the reviewed action.'
  }
}
function Record([string]$state,[string]$detail,[string]$commit='') {
  New-Item -ItemType Directory -Path $data -Force | Out-Null
  $record=[ordered]@{
    checked_at_utc=(Get-Date).ToUniversalTime().ToString('o')
    state=$state
    detail=$detail
    release_commit=$commit
    independent_scientific_acceptance=$false
    automatic_merges=$false
  }
  $tmp=Join-Path $data ('updater-status-'+[guid]::NewGuid().ToString('N')+'.tmp')
  [IO.File]::WriteAllText($tmp,(ConvertTo-Json $record -Depth 4),[Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $statusPath -Force
}
if($Status) {
  $t=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if($t) { AssertUpdater $t }
  Write-Host ('Updater task: '+$(if($t){$t.State}else{'NOT_INSTALLED'}))
  Write-Host ('Owner STOP: '+(Test-Path -LiteralPath $stop))
  if(Test-Path -LiteralPath $statusPath) { Get-Content -LiteralPath $statusPath -Raw | Write-Host }
  exit 0
}
if($Uninstall) {
  $t=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if($t) {
    AssertUpdater $t
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
  }
  Write-Host 'UPDATER_UNINSTALLED: worker and watchdog untouched.'
  exit 0
}
if($Install) {
  if(Test-Path -LiteralPath $stop) { throw 'Owner STOP present; updater setup suppressed.' }
  $worker=Get-ScheduledTask -TaskName $workerName -ErrorAction Stop
  AssertOwner $worker
  $old=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  if($old) { AssertUpdater $old }
  $exe=(Get-Command powershell.exe -ErrorAction Stop).Source
  $action=New-ScheduledTaskAction -Execute $exe -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Check' -f $script) -WorkingDirectory $root
  $logon=New-ScheduledTaskTrigger -AtLogOn -User $who.Name
  $repeat=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
  $principal=New-ScheduledTaskPrincipal -UserId $who.Name -LogonType Interactive -RunLevel Limited
  $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::FromMinutes(10)) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($logon,$repeat) -Principal $principal -Settings $settings -Description 'Only approved PDUFA releases from protected main; respects owner STOP' -Force -ErrorAction Stop | Out-Null
  [xml]$xml=Export-ScheduledTask -TaskName $taskName -ErrorAction Stop
  $repeatTriggers=@($xml.Task.Triggers.CalendarTrigger | Where-Object { $_.Repetition.Interval -eq 'PT15M' -and [string]::IsNullOrWhiteSpace([string]$_.Repetition.Duration) })
  if($repeatTriggers.Count -ne 1) {
    Disable-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Out-Null
    throw 'Required indefinite 15-minute polling not registered. Task disabled.'
  }
  Record 'UPDATER_INSTALLED' 'No update installed during setup.'
  Write-Host 'REVIEWED_RELEASE_UPDATER_INSTALLED: 15-minute checks and sign-in checks.'
  Write-Host 'No release will install until protected main contains a reviewed, enabled channel manifest.'
  exit 0
}
# -Check. Lock ensures no concurrent updater instances; the existing installer
# separately verifies Task Scheduler ownership, idle state, rollback and heartbeat.
if(Test-Path -LiteralPath $stop) {
  Record 'OWNER_STOP_SUPPRESSES_UPDATES' 'No changes.'
  Write-Host 'OWNER_STOP_SUPPRESSES_UPDATES'
  exit 0
}
$worker=Get-ScheduledTask -TaskName $workerName -ErrorAction Stop
AssertOwner $worker
$lock=$null
$backup=''
$installerChanged=$false
$installed=$false
$release=''
try {
  New-Item -ItemType Directory -Path $data -Force | Out-Null
  $lock=[IO.File]::Open((Join-Path $data 'reviewed-release-updater.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
  foreach($tool in @('git.exe','gh.exe','powershell.exe')) {
    if(-not(Get-Command $tool -ErrorAction SilentlyContinue)) { throw ('Required tool missing: '+$tool) }
  }
  $origin=(& git -C $root remote get-url origin | Out-String).Trim()
  RequireSuccess 'GIT_ORIGIN'
  if($origin -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)pdufa/pdufa-command-center(?:\.git)?/?$') {
    throw 'Repository origin mismatch.'
  }
  $checkout=(& git -C $root rev-parse --show-toplevel | Out-String).Trim()
  RequireSuccess 'GIT_CHECKOUT'
  if($checkout.Replace('/','\').TrimEnd('\') -ine $root.TrimEnd('\')) {
    throw 'Repository checkout mismatch.'
  }
  & gh auth status --hostname github.com *> $null
  RequireSuccess 'GITHUB_AUTH'
  & git -C $root fetch --no-tags origin ('+refs/heads/main:'+$mainRef) *> $null
  RequireSuccess 'PROTECTED_MAIN_FETCH'
  $main=(& git -C $root rev-parse ($mainRef+'^{commit}') | Out-String).Trim()
  RequireSuccess 'MAIN_REVISION'
  if($main -notmatch '^[a-f0-9]{40}$') { throw 'Invalid main revision.' }
  $channelText=& git -C $root show ($main+':automation/windows-release-channel.json') 2>$null
  if($LASTEXITCODE -ne 0) {
    Record 'NO_APPROVED_RELEASE_CHANNEL' 'No reviewed channel file merged to main.'
    Write-Host 'NO_APPROVED_RELEASE_CHANNEL: no changes.'
    exit 0
  }
  $channel=($channelText | Out-String | ConvertFrom-Json)
  if($channel.schema_version -ne 1 -or $channel.channel -ne 'pdufa-reviewed-windows' -or
      $channel.enabled -isnot [bool]) { throw 'Unrecognized release channel.' }
  if(-not $channel.enabled) {
    Record 'RELEASE_CHANNEL_DISABLED' 'Approved release channel is disabled.'
    Write-Host 'RELEASE_CHANNEL_DISABLED'
    exit 0
  }
  $release=[string]$channel.release_commit
  $blob=[string]$channel.installer_git_blob_sha1
  $prNumber=$channel.approved_pr
  if($release -notmatch '^[0-9a-f]{40}$' -or $blob -notmatch '^[0-9a-f]{40}$' -or
      $channel.installer_path -cne $installerRel -or
      $prNumber -isnot [int] -or $prNumber -lt 1) {
    throw 'Manifest has no exact approved installer version.'
  }
  if(Test-Path -LiteralPath $statusPath -PathType Leaf) {
    $prior=Get-Content -LiteralPath $statusPath -Raw | ConvertFrom-Json
    if($prior.state -eq 'INSTALLED_AND_RESTART_VERIFIED' -and $prior.release_commit -eq $release) {
      Write-Host 'APPROVED_RELEASE_ALREADY_INSTALLED'
      exit 0
    }
  }
  # GitHub branch protection must enforce independent approvals and CI.
  $protectionText=& gh api ('repos/'+$repo+'/branches/main/protection') 2>$null
  RequireSuccess 'PROTECTED_MAIN_REQUIRED'
  $protect=($protectionText | Out-String | ConvertFrom-Json)
  if($null -eq $protect.required_pull_request_reviews -or
      $protect.required_pull_request_reviews.required_approving_review_count -lt 1 -or
      $null -eq $protect.required_status_checks -or
      @($protect.required_status_checks.contexts).Count -lt 1) {
    throw 'Protected main requires at least one PR approval and CI status check.'
  }
  $prJson=& gh pr view $prNumber --repo $repo --json number,state,isDraft,mergedAt,baseRefName,reviewDecision,mergeCommit 2>$null
  RequireSuccess 'RELEASE_APPROVAL_LOOKUP'
  $pr=($prJson | Out-String | ConvertFrom-Json)
  if($pr.number -ne $prNumber -or $pr.state -ne 'MERGED' -or
      $pr.isDraft -ne $false -or [string]::IsNullOrWhiteSpace([string]$pr.mergedAt) -or
      $pr.baseRefName -ne 'main' -or $pr.reviewDecision -ne 'APPROVED' -or
      $pr.mergeCommit.oid -ne $release) {
    throw 'RELEASE_PR_NOT_INDEPENDENTLY_APPROVED_AND_MERGED_INTO_MAIN'
  }
  & gh pr checks $prNumber --repo $repo --required *> $null
  RequireSuccess 'REQUIRED_RELEASE_CI_NOT_GREEN'
  & git -C $root merge-base --is-ancestor $release $mainRef
  RequireSuccess 'RELEASE_NOT_REACHABLE_FROM_MAIN'
  $sourceBlob=(& git -C $root rev-parse ($release+':'+$installerRel) | Out-String).Trim()
  RequireSuccess 'RELEASE_SOURCE_BLOB'
  if($sourceBlob -cne $blob) { throw 'Release source blob mismatch.' }
  if(Test-Path -LiteralPath $stop) { throw 'Owner STOP appeared before download.' }
  $stage=Join-Path $data ('release-'+$release.Substring(0,12))
  New-Item -ItemType Directory -Path $stage -Force | Out-Null
  $incoming=Join-Path $stage 'incoming-installer.ps1'
  $source='https://raw.githubusercontent.com/'+$repo+'/'+$release+'/'+$installerRel
  Invoke-WebRequest -UseBasicParsing -Uri $source -OutFile $incoming -TimeoutSec 30 -ErrorAction Stop
  $fetchedBlob=(& git -C $root hash-object $incoming | Out-String).Trim()
  RequireSuccess 'DOWNLOADED_INSTALLER_HASH'
  if($fetchedBlob -cne $blob) { throw 'DOWNLOADED_INSTALLER_HASH_MISMATCH' }
  # The existing installer discovers repo root relative to its own script dir.
  # Back up and replace it in scripts/; restore on a pre-start failure.
  $backup=Join-Path $stage 'previous-installer.ps1'
  if(Test-Path -LiteralPath $installer -PathType Leaf) {
    Copy-Item -LiteralPath $installer -Destination $backup -Force -ErrorAction Stop
  }
  Copy-Item -LiteralPath $incoming -Destination $installer -Force -ErrorAction Stop
  $installerChanged=$true
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Preflight
  RequireSuccess 'RELEASE_PREFLIGHT'
  if(Test-Path -LiteralPath $stop) { throw 'Owner STOP appeared before install.' }
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $installer -Install
  RequireSuccess 'RELEASE_INSTALL_OR_RESTART'
  $installed=$true
  Record 'INSTALLED_AND_RESTART_VERIFIED' 'Installer returned successful restart verification.' $release
  Write-Host ('APPROVED_RELEASE_INSTALLED_AND_RESTART_VERIFIED: '+$release)
} catch {
  $reason=$_.Exception.Message
  if($installerChanged -and -not $installed) {
    $now=Get-ScheduledTask -TaskName $workerName -ErrorAction SilentlyContinue
    if($now -and $now.State -eq 'Ready') {
      if(Test-Path -LiteralPath $backup -PathType Leaf) {
        Copy-Item -LiteralPath $backup -Destination $installer -Force -ErrorAction Stop
      } else {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
      }
    } else {
      Write-Warning 'Worker may be active; do not overwrite active installation. Manual review needed.'
    }
  }
  Record 'UPDATE_BLOCKED_OR_FAILED' $reason $release
  throw
} finally {
  if($lock) { $lock.Dispose() }
}
