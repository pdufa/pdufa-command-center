# One-time Level 6 approved engineering-slice installer; retains independent science review.
# Never clears scientific acceptance blockers, owner STOP, or failures from new tests.
# Installs verified source code, retries only original Level 6 placeholders, and enables watchdog.
# Read-only -Preflight diagnoses local prerequisites without stopping any worker.
# Requires current-user Task Scheduler ownership; NEVER interrupts active PR work.
[CmdletBinding()]
param([switch]$Install,[switch]$Status,[switch]$Preflight,
      [string]$ReviewedReleaseCommit='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if (@(@($Install,$Status,$Preflight) | Where-Object { $_ }).Count -ne 1) {
  throw 'Specify exactly one of -Install, -Status and -Preflight.'
}
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$data=Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
$stopToken=Join-Path $data 'STOP'
$heartbeat=Join-Path $data 'heartbeat.json'
$completion=Join-Path $data 'level_completion_ledger.json'
$sequence=Join-Path $data 'sequential_level_status.json'
$engineering=Join-Path $data 'engineering_lane_ledger.json'
$oldLedger=Join-Path $data 'ledger.json'
$taskName='PDUFA-Continuous-Development'
$guardName='PDUFA-Continuous-Watchdog'
$authorizationPath=Join-Path $data 'reviewed-release-authorization.json'
$reviewedMode=-not [string]::IsNullOrWhiteSpace($ReviewedReleaseCommit)
if($reviewedMode -and $ReviewedReleaseCommit -cnotmatch '^[0-9a-f]{40}$') {
  throw 'Reviewed release requires an exact commit.'
}
$branch='feature/phase-first-cumulative-level-assessments-20261112'
$remoteRef='refs/remotes/origin/feature/phase-first-cumulative-level-assessments-20261112'
$files=@(
  'automation/scientific-level-completion-queue.json',
  'automation/level5-candidate-roster-20261111.json',
  'automation/focus-assessment-roster-snapshot-20261112.json',
  'automation/assessment-level-acceptance-contract.json',
  'scripts/pdufa_level_completion.py',
  'scripts/pdufa_runtime_status.py',
  'scripts/windows_pdufa_reviewed_release_updater.ps1',
  'scripts/pdufa_cumulative_level_assessments.py',
  'scripts/pdufa_strict_level_runner.py',
  'scripts/pdufa_engineering_review_lanes.py',
  'scripts/level4_scientific_evidence.py',
  'scripts/level5_contradictory_evidence.py',
  'scripts/level6_cross_disciplinary_inventory.py',
  'scripts/pdufa_level_remediation_planner.py',
  'scripts/pdufa_predictive_preflight.py',
  'tests/test_pdufa_level_completion.py',
  'tests/test_pdufa_runtime_status.py',
  'tests/test_windows_reviewed_release_updater.py',
  'tests/test_reviewed_release_repair_contract.py',
  'tests/test_pdufa_cumulative_level_assessments.py',
  'tests/test_pdufa_strict_level_runner.py',
  'tests/test_pdufa_engineering_review_lanes.py',
  'tests/test_level4_scientific_evidence.py',
  'tests/test_level5_contradictory_evidence.py',
  'tests/test_level6_cross_disciplinary_inventory.py',
  'tests/test_level5_implementation_integration.py',
  'tests/test_level6_implementation_integration.py',
  'tests/test_pdufa_level_remediation_planner.py',
  'tests/test_pdufa_predictive_preflight.py',
  'scripts/windows_local_agent_watchdog.ps1',
  'scripts/level7_model_validation_readiness.py',
  'scripts/level7_source_readiness_inventory.py',
  'tests/test_level7_model_validation_readiness.py',
  'tests/test_level7_source_readiness_inventory.py',
  'tests/test_level7_implementation_integration.py',
  'tests/test_pdufa_partial_install_integration.py'
)
# Approved, exact Git blob IDs for this review slice; no branch drift.
$allowed=@{
 'automation/scientific-level-completion-queue.json'='9c363bbaa8b485c38a41aeb71127c78b91175206'
 'automation/level5-candidate-roster-20261111.json'='2eba75caf3a6d435db53ea4dbdcf63959532ff06'
 'automation/focus-assessment-roster-snapshot-20261112.json'='4c626ceb8bffb5b53e8bad6a9ff28c8179818d20'
 'automation/assessment-level-acceptance-contract.json'='0122099f2a9453c029af68b0da54af0ba525162f'
 'scripts/pdufa_level_completion.py'='c0ed28d9670762161050abdaf99cfe1254442d08'
 'scripts/pdufa_runtime_status.py'='79474599a92dfe3886e91b9abc268209f5ba4c5d'
 'scripts/windows_pdufa_reviewed_release_updater.ps1'='777dc7439268028e2482a1d101482a087410db12'
 'scripts/pdufa_cumulative_level_assessments.py'='cf5854d2b5532238ccd4afa4644f83c6e30e9f98'
 'scripts/pdufa_strict_level_runner.py'='c63f9e3f191f53a42c7fafc4e184a065dec5d7b9'
 'scripts/pdufa_engineering_review_lanes.py'='8e9f7c57165ecf2cc1ea3bfc86151707eb6b7c35'
 'scripts/level4_scientific_evidence.py'='2530d029f49b8ab4ec1f21f7db784d5864bf5c36'
 'scripts/level5_contradictory_evidence.py'='2c5eee95d0760baa2d3f5f1aea3e2012fe964a07'
 'scripts/level6_cross_disciplinary_inventory.py'='f5dbe151a8a7c7657dcacb9581281dc627b708bf'
 'scripts/pdufa_level_remediation_planner.py'='741d04cf3a803860c1c590499d139df86e0889d5'
 'scripts/pdufa_predictive_preflight.py'='4a72120f696b207c9d3eae2d632a6344b6bd17cc'
 'tests/test_pdufa_level_completion.py'='7e6a6f2500d8833161b7c4e3270d80e0dba43785'
 'tests/test_pdufa_runtime_status.py'='b9db89cd3128041da0c5d3bff5d0941a32e3d941'
 'tests/test_windows_reviewed_release_updater.py'='ea65962f9ccbb836a1066c4676ae40503a185c10'
 'tests/test_reviewed_release_repair_contract.py'='ebd85a1057ac21c58a668ab3f068d1e3c43c8e8a'
 'tests/test_pdufa_cumulative_level_assessments.py'='851b3669f7f30b65840e81445254f6c1f564af7d'
 'tests/test_pdufa_strict_level_runner.py'='cb1ebbb5ab0c77fd9f1c05cb65d52cf3744b561b'
 'tests/test_pdufa_engineering_review_lanes.py'='a26e87b32274aec7edb210b68fa991421bfe956b'
 'tests/test_level4_scientific_evidence.py'='5a30ed426188aa8da968639fc763842d9d15f0e6'
 'tests/test_level5_contradictory_evidence.py'='5ae934b3c74036791c01f170ff3bb45fe8972d0c'
 'tests/test_level6_cross_disciplinary_inventory.py'='1dcf90611b77059d3f17b11ae512abeb18a94ac4'
 'tests/test_level5_implementation_integration.py'='7fde843748dda101efaedba9138383c4132f95c7'
 'tests/test_level6_implementation_integration.py'='2bd0db180e1595f5cf787a59a9fd2cc1bf88b22f'
 'tests/test_pdufa_level_remediation_planner.py'='f39e67f7a2a41562b129cfbb1ade67f28fb64937'
 'tests/test_pdufa_predictive_preflight.py'='b4259309e9134ff5b82e154b5aae8c5d1c386e3f'
 'scripts/windows_local_agent_watchdog.ps1'='3904b3262e1efc02349ba96b239a8ff12f925131'
 'scripts/level7_model_validation_readiness.py'='f9044bf35dc72d3c1160978ee30f9f61fe5929c9'
 'scripts/level7_source_readiness_inventory.py'='815e43453e054278943c7aea2a87ee480acfae64'
 'tests/test_level7_model_validation_readiness.py'='e78aae6150fbe4c2fd749c7c0584c4da8fb3e278'
 'tests/test_level7_source_readiness_inventory.py'='dcb91feacde4d5af3f1ab76cf0a44726627b8f20'
 'tests/test_level7_implementation_integration.py'='db09d5d1712e65623fdf3194c6b00d5f8e3c19ed'
 'tests/test_pdufa_partial_install_integration.py'='7c2e8f66604084f2940d996b18828909c251e7ec'
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
function RemoveOwnedUpgradeStop([string]$Path,[string]$Marker) {
  if(Test-Path -LiteralPath $Path -PathType Leaf) {
    # Capture the name atomically before inspecting it. An owner replacement at
    # the original path can never be removed by this cleanup operation.
    $captured=$Path+'.upgrade-stop-'+[guid]::NewGuid().ToString('N')+'.captured'
    [IO.File]::Move($Path,$captured)
    try {
      $content=([string](Get-Content -LiteralPath $captured -Raw -ErrorAction Stop)).Trim()
    } catch {
      try { [IO.File]::Move($captured,$Path) } catch {
        Write-Warning ('Unreadable STOP retained at '+$captured)
      }
      throw
    }
    if($content -ceq $Marker) {
      Remove-Item -LiteralPath $captured -Force -ErrorAction Stop
      if(Test-Path -LiteralPath $Path) {
        throw 'Owner STOP replaced the upgrade marker; preserved.'
      }
    } else {
      try { [IO.File]::Move($captured,$Path) } catch {
        Write-Warning ('Owner STOP and captured STOP both preserved: '+$captured)
      }
      throw 'Owner STOP changed during upgrade; preserved.'
    }
  }
}
function WriteReleaseAuthorization($Authorization) {
  $tmp=Join-Path $data ('authorization-'+[guid]::NewGuid().ToString('N')+'.tmp')
  [IO.File]::WriteAllText($tmp,(ConvertTo-Json $Authorization -Depth 6),[Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $authorizationPath -Force
}
function AcquireInstallerLock([string]$Path) {
  return [IO.File]::Open($Path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
}
$worker=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
AssertOwner $worker
if(@($worker.Actions).Count -ne 1 -or
   $worker.Actions[0].Arguments -notmatch '(?:windows_local_agent_continuous|pdufa_level_completion|pdufa_strict_level_runner|pdufa_engineering_review_lanes)\.py' -or
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
  if(Test-Path -LiteralPath $engineering -PathType Leaf) {
    & py -3.13 -B (Join-Path $root 'scripts/pdufa_engineering_review_lanes.py') --status
    exit $LASTEXITCODE
  }
  Write-Host 'Engineering progression worker has not started.'
  exit 2
}
$runAction=[string]$worker.Actions[0].Arguments
if(-not(Test-Path -LiteralPath (Join-Path $root 'AGENTS.md') -PathType Leaf)) {
  throw 'Permanent safety policy is missing.'
}
# The engineering controller uses its own ledger. An old legacy ledger may be
# absent once migrated, and must not block a safe Level 6 upgrade.
if($runAction -match 'pdufa_engineering_review_lanes\.py') {
  if(-not(Test-Path -LiteralPath $engineering -PathType Leaf) -or
     -not(Test-Path -LiteralPath $completion -PathType Leaf)) {
    throw 'Current engineering completion ledgers are missing.'
  }
} elseif(-not(Test-Path -LiteralPath $oldLedger -PathType Leaf)) {
  throw 'Legacy worker ledger missing; no safe migration.'
}
if(Test-Path -LiteralPath $stopToken) { throw 'Owner STOP exists; do not override it.' }
if($worker.State -eq 'Disabled') { throw 'Worker disabled; owner intervention required.' }
# A previously configured engineering worker still needs the reviewed Level6
# module and ledger retry migration; do not incorrectly exit early.
if($runAction -match 'pdufa_engineering_review_lanes\.py') {
  Write-Host 'ENGINEERING_LANE_FOUND: verifying safe Level6 upgrade conditions.'
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
  if($h.mode -notin @('IDLE','QUEUE_EXHAUSTED','IDLE_AWAITING_APPROVED_WORK','AWAITING_INDEPENDENT_REVIEW_OR_APPROVED_WORK','AWAITING_APPROVED_WORK_OR_REVIEW','ENGINEERING_AWAITING_APPROVED_WORK') -or
     $age -lt 0 -or $age -gt 90 -or
     $null -ne $h.task) {
    throw 'Worker is running or heartbeat is stale; no in-flight work may be terminated.'
  }
  if($runAction -match 'pdufa_engineering_review_lanes\.py') {
    # This task no longer processes legacy draft tasks; preserve them untouched.
    # Verify no real current engineering step is marked RUNNING before draining.
    $q=Get-Content -LiteralPath $engineering -Raw | ConvertFrom-Json
    $l=Get-Content -LiteralPath $completion -Raw | ConvertFrom-Json
    $currentTask=$q.PSObject.Properties['active_task']
    $completionTask=$l.PSObject.Properties['active']
    if(($null -ne $currentTask -and $null -ne $currentTask.Value) -or
       ($null -ne $completionTask -and $null -ne $completionTask.Value)) {
      throw 'Live engineering step is active; do not drain.'
    }
  } else {
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
# Diagnose the *whole active execution path* before pausing any Windows task.
foreach($tool in @('git','gh','py.exe')) {
  if(-not(Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw ('REQUIRED_TOOL_MISSING: '+$tool)
  }
}
& py -3.13 -c 'import sys; assert sys.version_info >= (3, 13)'
RequireSuccess 'PYTHON_3_13_NOT_AVAILABLE'
& gh auth status --hostname github.com 2>$null
RequireSuccess 'GH_AUTH_NOT_READY'
# Both paths require the original Level 6 inventory; release approval cannot
# manufacture missing source receipts.
$level6Report=Join-Path $data 'level6\dated-cross-domain-source-gap-inventory.json'
if(-not(Test-Path -LiteralPath $level6Report -PathType Leaf)) {
  throw 'LEVEL7_PRIOR_SOURCE_RECEIPTS_NOT_AVAILABLE'
}
if(-not $reviewedMode) {
$approved=(& gh pr view 1163 --repo pdufa/pdufa-command-center --json number,isDraft,state,headRefName,baseRefName | Out-String).Trim()
RequireSuccess 'LEVEL6_DRAFT_PR_LOOKUP_FAILED'
$pr=$approved | ConvertFrom-Json
if($pr.number -ne 1163 -or $pr.state -ne 'OPEN' -or -not $pr.isDraft -or
   $pr.headRefName -ne 'feature/level6-cross-disciplinary-evidence-20261112' -or
   $pr.baseRefName -ne 'automation/level5-checkpoints-one-command-20261112') {
  throw 'LEVEL6_PR_NO_LONGER_APPROVED_DRAFT'
}
$review7=(& gh pr view 1169 --repo pdufa/pdufa-command-center --json number,isDraft,state,headRefName,baseRefName | Out-String).Trim()
RequireSuccess 'LEVEL7_DRAFT_PR_LOOKUP_FAILED'
$p7=$review7 | ConvertFrom-Json
if($p7.number -ne 1169 -or $p7.state -ne 'OPEN' -or -not $p7.isDraft -or
   $p7.headRefName -ne 'automation/level7-engineering-readiness-20261112' -or
   $p7.baseRefName -ne 'automation/predictive-preflight-all-levels-20261112') {
  throw 'LEVEL7_PR_NO_LONGER_APPROVED_DRAFT'
}
$scorePr=(& gh pr view 1172 --repo pdufa/pdufa-command-center --json number,isDraft,state,headRefName,baseRefName | Out-String).Trim() | ConvertFrom-Json
RequireSuccess 'SCORED_ASSESSMENT_DRAFT_PR_LOOKUP_FAILED'
if($scorePr.number -ne 1172 -or $scorePr.state -ne 'OPEN' -or -not $scorePr.isDraft -or
   $scorePr.headRefName -ne 'feature/phase-first-cumulative-level-assessments-20261112' -or
   $scorePr.baseRefName -ne 'automation/windows-reviewed-release-poller-20261112') {
  throw 'SCORED_ASSESSMENT_PR_NOT_EXPECTED_DRAFT'
}
}
# A reviewed release is independently authorized here, even when called by the
# poller. A local receipt or its approval booleans never bypass online review.
$authorization=$null
if($reviewedMode) {
  $mainRef='refs/remotes/origin/main'
  & git -C $root fetch --no-tags origin ('+refs/heads/main:'+$mainRef)
  RequireSuccess 'PROTECTED_MAIN_FETCH'
  $main=(& git -C $root rev-parse ($mainRef+'^{commit}') | Out-String).Trim()
  RequireSuccess 'PROTECTED_MAIN_REVISION'
  if($main -cnotmatch '^[0-9a-f]{40}$') { throw 'Invalid main commit.' }
  $channelText=& git -C $root show ($main+':automation/windows-release-channel.json')
  RequireSuccess 'REVIEWED_CHANNEL_REQUIRED'
  $channel=$channelText | Out-String | ConvertFrom-Json
  if($channel.schema_version -ne 1 -or $channel.channel -cne 'pdufa-reviewed-windows' -or
     $channel.enabled -isnot [bool] -or -not $channel.enabled -or
     $channel.release_commit -cne $ReviewedReleaseCommit -or
     $channel.installer_path -cne 'scripts/windows_pdufa_level6_unblock.ps1' -or
     $channel.installer_git_blob_sha1 -cnotmatch '^[0-9a-f]{40}$' -or
     ($channel.approved_pr -isnot [int] -and $channel.approved_pr -isnot [long]) -or
     $channel.approved_pr -lt 1 -or $channel.approved_pr -gt [int]::MaxValue) {
    throw 'REVIEWED_RELEASE_CHANNEL_MISMATCH'
  }
  $protectText=& gh api 'repos/pdufa/pdufa-command-center/branches/main/protection' 2>$null
  RequireSuccess 'PROTECTED_MAIN_REQUIRED'
  $protect=$protectText | Out-String | ConvertFrom-Json
  if($null -eq $protect.required_pull_request_reviews -or
     $protect.required_pull_request_reviews.required_approving_review_count -lt 1 -or
     $null -eq $protect.required_status_checks -or
     @($protect.required_status_checks.contexts).Count -lt 1) {
    throw 'Protected main requires independent approval and required checks.'
  }
  $prText=& gh pr view $channel.approved_pr --repo pdufa/pdufa-command-center --json number,state,isDraft,mergedAt,baseRefName,reviewDecision,mergeCommit 2>$null
  RequireSuccess 'REVIEWED_RELEASE_APPROVAL_LOOKUP'
  $releasePr=$prText | Out-String | ConvertFrom-Json
  if($releasePr.number -ne $channel.approved_pr -or $releasePr.state -cne 'MERGED' -or
     $releasePr.isDraft -ne $false -or $releasePr.baseRefName -cne 'main' -or
     $releasePr.reviewDecision -cne 'APPROVED' -or
     [string]::IsNullOrWhiteSpace([string]$releasePr.mergedAt) -or
     $releasePr.mergeCommit.oid -cne $ReviewedReleaseCommit) {
    throw 'RELEASE_PR_NOT_INDEPENDENTLY_APPROVED_AND_MERGED_INTO_MAIN'
  }
  & gh pr checks $channel.approved_pr --repo pdufa/pdufa-command-center --required
  RequireSuccess 'REQUIRED_RELEASE_CI_NOT_GREEN'
  & git -C $root merge-base --is-ancestor $ReviewedReleaseCommit $mainRef
  RequireSuccess 'RELEASE_NOT_REACHABLE_FROM_MAIN'
  $selfBlob=(& git -C $root rev-parse ($ReviewedReleaseCommit+':scripts/windows_pdufa_level6_unblock.ps1') | Out-String).Trim()
  RequireSuccess 'REVIEWED_INSTALLER_SOURCE_BLOB'
  $localBlob=(& git -C $root hash-object $PSCommandPath | Out-String).Trim()
  RequireSuccess 'REVIEWED_INSTALLER_LOCAL_BLOB'
  if($selfBlob -cne $channel.installer_git_blob_sha1 -or $localBlob -cne $selfBlob) {
    throw 'REVIEWED_INSTALLER_HASH_MISMATCH'
  }
  $revision=$ReviewedReleaseCommit
  $authorization=[ordered]@{
    schema_version=1; repository='pdufa/pdufa-command-center'
    release_commit=$revision; installer_path='scripts/windows_pdufa_level6_unblock.ps1'
    installer_git_blob_sha1=$selfBlob; approved_pr=$channel.approved_pr; approved_base='main'
    approval_verified=$true; required_checks_verified=$true; source_main_commit=$main
    authorization_verified_at_utc=(Get-Date).ToUniversalTime().ToString('o')
    files=$allowed
  }
} else {
$published=(& git -C $root ls-remote --exit-code origin ('refs/heads/'+$branch) | Out-String).Trim()
RequireSuccess 'APPROVED_RELEASE_BRANCH_NOT_ACCESSIBLE'
if($published -notmatch '^[0-9a-f]{40}\s+refs/heads/') {
  throw 'Remote release ref was not uniquely resolved.'
}
  & git -C $root fetch --no-tags origin ('+refs/heads/'+$branch+':'+$remoteRef)
  RequireSuccess 'FETCH_REVIEWED_QUEUE'
  $revision=(& git -C $root rev-parse ($remoteRef+'^{commit}') | Out-String).Trim()
  RequireSuccess 'REVISION'
}
if($revision -cnotmatch '^[0-9a-f]{40}$') { throw 'Invalid reviewed commit.' }
foreach($path in $files) {
  $blob=(& git -C $root rev-parse ($revision+':'+$path) | Out-String).Trim()
  RequireSuccess 'PREFLIGHT_SOURCE_BLOB'
  if($blob -cne $allowed[$path]) { throw ('Reviewed file changed since approval: '+$path) }
}
# Verify network dependencies BEFORE stopping any existing working controller.
# The installer and original-source collector both require these endpoints.
try {
  $registry=Invoke-WebRequest -UseBasicParsing -Uri 'https://clinicaltrials.gov/api/v2/studies/NCT05507203' -TimeoutSec 20 -ErrorAction Stop
  $study=$registry.Content | ConvertFrom-Json
  if($study.protocolSection.identificationModule.nctId -ne 'NCT05507203') {
    throw 'Returned registry trial identity did not match test NCT.'
  }
} catch {
  throw ('CLINICAL_REGISTRY_HOST_CONNECTIVITY_FAILED: '+$_.Exception.GetType().Name)
}
try {
  $releaseSha=$revision
  $sourceProbeUrl='https://raw.githubusercontent.com/pdufa/pdufa-command-center/'+
                  $releaseSha+'/scripts/pdufa_level_completion.py'
  $sourceProbe=Invoke-WebRequest -UseBasicParsing -Uri $sourceProbeUrl -TimeoutSec 20 -ErrorAction Stop
  if($sourceProbe.Content -notmatch 'LEVEL_COMPLETION') {
    throw 'GitHub release source returned unexpected content.'
  }
} catch {
  throw ('GITHUB_RAW_RELEASE_DOWNLOAD_BLOCKED: '+$_.Exception.GetType().Name)
}
if($Preflight) {
  Write-Host 'PDUFA_INSTALL_PREFLIGHT_PASS: toolchain, current worker ownership, safe idle state, GitHub PR and release ref verified. No processes modified.'
  Write-Host ('Current worker: '+$worker.State)
  Write-Host ('Exact release commit: '+$revision)
  exit 0
}
$stamp=(Get-Date).ToUniversalTime().ToString('yyyyMMddHHmmssfff')
$stage=Join-Path $data ('completion-stage-'+$stamp)
$backup=Join-Path $data ('completion-backup-'+$stamp)
$backups=@()
$drained=$false
$changedAction=$false
$authorizationChanged=$false
$authorizationExisted=$false
$authorizationBackup=Join-Path $backup 'reviewed-release-authorization.json'
$upgradeStopMarker='PDUFA_INSTALLER_IDLE_UPGRADE_'+[guid]::NewGuid().ToString('N')
$installationLock=$null
try {
$installationLock=AcquireInstallerLock (Join-Path $data 'reviewed-install.lock')
$authorizationExisted=Test-Path -LiteralPath $authorizationPath -PathType Leaf
$worker=Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
AssertOwner $worker
$oldAction=$worker.Actions[0]
New-Item -ItemType Directory -Path $stage,$backup -Force | Out-Null
try {
  # Download and verify every byte before pausing watchdog or worker.
  foreach($path in $files) {
    $blob=(& git -C $root rev-parse ($revision+':'+$path) | Out-String).Trim()
    RequireSuccess 'BLOB'
    if($blob -cne $allowed[$path]) { throw ('Reviewed file changed since approval: '+$path) }
    $target=Join-Path $stage ($path.Replace('/','\'))
    New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
    $url='https://raw.githubusercontent.com/pdufa/pdufa-command-center/'+$revision+'/'+$path
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target -TimeoutSec 30 -ErrorAction Stop
    $actual=(& git -C $root hash-object $target | Out-String).Trim()
    RequireSuccess 'HASH'
    if($actual -cne $blob) { throw ('Downloaded source hash mismatch: '+$path) }
  }
  if(Test-Path -LiteralPath $stopToken) { throw 'Owner STOP appeared before drain.' }
  if((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
    $currentHeartbeat=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
    $currentAge=((Get-Date).ToUniversalTime()-[datetime]::Parse([string]$currentHeartbeat.updated_utc).ToUniversalTime()).TotalSeconds
    if($currentHeartbeat.mode -notin @('IDLE','QUEUE_EXHAUSTED','IDLE_AWAITING_APPROVED_WORK','AWAITING_INDEPENDENT_REVIEW_OR_APPROVED_WORK','AWAITING_APPROVED_WORK_OR_REVIEW','ENGINEERING_AWAITING_APPROVED_WORK') -or
       $currentAge -lt 0 -or $currentAge -gt 90 -or $null -ne $currentHeartbeat.task) {
      throw 'Worker became busy during staging; no drain permitted.'
    }
  }
  if($guardEnabled) {
    Disable-ScheduledTask -TaskName $guardName -ErrorAction Stop | Out-Null
  }
  if((Get-ScheduledTask -TaskName $taskName).State -eq 'Running') {
    # Existing Python honors STOP between bounded tasks. This has been approved
    # by the owner for idle-only migration. No forced process termination.
    # CreateNew refuses to overwrite a STOP written after the last check.
    $stopStream=[IO.File]::Open($stopToken,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {
      $markerBytes=[Text.Encoding]::ASCII.GetBytes($upgradeStopMarker)
      $stopStream.Write($markerBytes,0,$markerBytes.Length)
    } finally { $stopStream.Dispose() }
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
  if($reviewedMode) {
    if($authorizationExisted) {
      Copy-Item -LiteralPath $authorizationPath -Destination $authorizationBackup -ErrorAction Stop
    }
    WriteReleaseAuthorization $authorization
    $authorizationChanged=$true
  }
  & py -3.13 -B (Join-Path $root 'scripts/pdufa_level_completion.py') --self-test
  RequireSuccess 'COMPLETION_SELF_TEST'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_level_completion.py' -v
  RequireSuccess 'QUEUE_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_cumulative_level_assessments.py' -v
  RequireSuccess 'CUMULATIVE_LEVEL4_TO20_SCORED_ASSESSMENT_REGRESSIONS'
  & py -3.13 -B (Join-Path $root 'scripts/pdufa_strict_level_runner.py') --self-test
  RequireSuccess 'STRICT_SEQUENCE_SELF_TEST'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_strict_level_runner.py' -v
  RequireSuccess 'STRICT_SEQUENCE_REGRESSIONS'
  & py -3.13 -B (Join-Path $root 'scripts/pdufa_engineering_review_lanes.py') --self-test
  RequireSuccess 'ENGINEERING_LANE_SELF_TEST'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_engineering_review_lanes.py' -v
  RequireSuccess 'ENGINEERING_LANE_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level4_scientific_evidence.py' -v
  RequireSuccess 'LEVEL4_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level5_contradictory_evidence.py' -v
  RequireSuccess 'LEVEL5_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level5_implementation_integration.py' -v
  RequireSuccess 'LEVEL5_INTEGRATION_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level6_cross_disciplinary_inventory.py' -v
  RequireSuccess 'LEVEL6_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level6_implementation_integration.py' -v
  RequireSuccess 'LEVEL6_INTEGRATION_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level7_model_validation_readiness.py' -v
  RequireSuccess 'LEVEL7_TEMPORAL_READINESS_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level7_source_readiness_inventory.py' -v
  RequireSuccess 'LEVEL7_REGISTRY_RECEIPT_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_level7_implementation_integration.py' -v
  RequireSuccess 'LEVEL7_ENGINEERING_INTEGRATION_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_level_remediation_planner.py' -v
  RequireSuccess 'SERIAL_REMEDIATION_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_predictive_preflight.py' -v
  RequireSuccess 'PREDICTIVE_PREFLIGHT_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_partial_install_integration.py' -v
  RequireSuccess 'EXACT_WINDOWS_INSTALLED_FILES_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_pdufa_runtime_status.py' -v
  RequireSuccess 'RUNTIME_VERSION_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_windows_reviewed_release_updater.py' -v
  RequireSuccess 'REVIEWED_RELEASE_UPDATER_REGRESSIONS'
  & py -3.13 -B -m unittest discover -s (Join-Path $root 'tests') -p 'test_reviewed_release_repair_contract.py' -v
  RequireSuccess 'REVIEWED_RELEASE_RECOVERY_REGRESSIONS'
  & py -3.13 -B (Join-Path $root 'scripts/pdufa_predictive_preflight.py') --out (Join-Path $data 'predictive_preflight_report.json')
  RequireSuccess 'PREDICTIVE_PREFLIGHT_RELEASE_PIN_CHECK'
  & py -3.13 -B (Join-Path $root 'scripts/audit_raas_retirement.py') --check
  RequireSuccess 'RETIRED_DEPENDENCY_AUDIT'
  $python=(Get-Command py.exe -ErrorAction Stop).Source
  $controller=Join-Path $root 'scripts/pdufa_engineering_review_lanes.py'
  $action=New-ScheduledTaskAction -Execute $python -Argument ('-3.13 "{0}" --run' -f $controller) -WorkingDirectory $root
  Set-ScheduledTask -TaskName $taskName -Action $action -ErrorAction Stop | Out-Null
  $changedAction=$true
  if($drained) { RemoveOwnedUpgradeStop $stopToken $upgradeStopMarker }
  if(Test-Path -LiteralPath $stopToken) { throw 'Owner STOP appeared before activation.' }
} catch {
  # Unlike the old installer, failures AFTER tests but BEFORE scheduled-task
  # activation must still restore the old files. Never leave a half-upgraded
  # controller behind. Never revert an already running process.
  $canRestore=$true
  if((Get-ScheduledTask -TaskName $taskName).State -ne 'Ready') {
    $canRestore=$false
    Write-Warning 'Worker no longer idle: manual recovery required; preserve installed files.'
  } elseif($changedAction) {
    try {
      Set-ScheduledTask -TaskName $taskName -Action $oldAction -ErrorAction Stop | Out-Null
    } catch {
      $canRestore=$false
      Write-Warning 'Could not restore original Task Scheduler action; manual recovery required.'
    }
  }
  if($canRestore) {
    foreach($record in $backups) {
      if($record.existed) {
        Copy-Item -LiteralPath $record.backup -Destination $record.file -Force -ErrorAction Stop
      } else {
        Remove-Item -LiteralPath $record.file -Force -ErrorAction Stop
      }
    }
    if($authorizationChanged) {
      if($authorizationExisted) {
        Copy-Item -LiteralPath $authorizationBackup -Destination $authorizationPath -Force -ErrorAction Stop
      } else {
        Remove-Item -LiteralPath $authorizationPath -Force -ErrorAction Stop
      }
    }
    Write-Warning 'Pre-start upgrade failed; previously installed controller files restored.'
  }
  if($drained -and (Test-Path -LiteralPath $stopToken)) {
    try { RemoveOwnedUpgradeStop $stopToken $upgradeStopMarker } catch {
      Write-Warning 'Owner STOP preserved after failed upgrade.'
    }
  }
  throw
} finally {
  if($guardEnabled) {
    Enable-ScheduledTask -TaskName $guardName -ErrorAction Stop | Out-Null
  }
  Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
if(-not $changedAction) { throw 'Completion task action was not installed.' }
if(Test-Path -LiteralPath $stopToken) { throw 'Owner STOP appeared before restart.' }
$startRequestedUtc=(Get-Date).ToUniversalTime()
Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
$verified=$false
# Startup online release verification may take up to 60 seconds. A startup
# pulse alone never certifies successful activation.
for($i=0;$i -lt 60;$i++) {
  Start-Sleep -Seconds 2
  if(-not(Test-Path -LiteralPath $heartbeat -PathType Leaf) -or
     -not(Test-Path -LiteralPath $completion -PathType Leaf) -or
     -not(Test-Path -LiteralPath $sequence -PathType Leaf) -or
     -not(Test-Path -LiteralPath $engineering -PathType Leaf)) { continue }
  try {
    $h=Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
    $l=Get-Content -LiteralPath $completion -Raw | ConvertFrom-Json
    $q=Get-Content -LiteralPath $sequence -Raw | ConvertFrom-Json
    $e=Get-Content -LiteralPath $engineering -Raw | ConvertFrom-Json
    $age=((Get-Date).ToUniversalTime()-
         [datetime]::Parse([string]$h.updated_utc).ToUniversalTime()).TotalSeconds
    $first=$l.levels.PSObject.Properties['4'].Value.steps.AUDIT_EXISTING_DRAFTS.status
    $fresh=[datetime]::Parse([string]$h.updated_utc).ToUniversalTime() -ge $startRequestedUtc.AddSeconds(-2)
    $releaseMatches=$true
    if($reviewedMode) {
      $releaseMatches=($h.runtime_version.release_commit -ceq $ReviewedReleaseCommit -and
                       $h.runtime_version.files_match_authorization -eq $true -and
                       @($h.runtime_version.disk_changed_since_start).Count -eq 0)
      foreach($path in $files) {
        $entry=$h.runtime_version.startup_files.PSObject.Properties[$path]
        if($null -eq $entry -or $entry.Value -cne $allowed[$path]) { $releaseMatches=$false }
      }
    }
    if($fresh -and $h.queue -eq 'LEVEL_COMPLETION' -and
       $releaseMatches -and
       $e.mode -eq 'ENGINEERING_ADVANCE_REVIEW_SEPARATE' -and
       $q.mode -eq 'STRICT_LEVEL_BY_LEVEL' -and
       $age -ge 0 -and $age -lt 45 -and
       $h.mode -like 'ENGINEERING_*' -and
       $h.mode -notin @('ENGINEERING_STARTING','ENGINEERING_STARTUP_BLOCKED') -and
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
Write-Host 'LEVEL6_APPROVED_ENGINEERING_SLICE_STARTED_AND_VERIFIED: phase-first source gap inventory now eligible for verified retry.'
Write-Host ('Persistent completion ledger: '+$completion)
Write-Host ('Independent scientific acceptance ledger: '+$sequence)
Write-Host ('Engineering milestone ledger: '+$engineering)
Write-Host ('Rollback backups retained: '+$backup)
Write-Host 'Draft-only; scientific review and acceptance remain independent.'
# Install scheduled watchdog if absent; it respects owner STOP and never kills an
# active worker. Failure here is explicit rather than misreporting a full setup.
$watchdogScript=Join-Path $root 'scripts/windows_local_agent_watchdog.ps1'
& $watchdogScript -Install
if($LASTEXITCODE -ne 0) { throw 'WATCHDOG_INSTALL_FAILED_AFTER_LEVEL6_WORKER_STARTED' }
Write-Host 'LEVEL6_WATCHDOG_INSTALLED_AND_ENABLED: checks every 2 minutes while owner signed in.'
# One consolidated setup includes the reviewed-update transport. Registration
# does not enable a channel, install another release, or start another worker.
& (Join-Path $root 'scripts/windows_pdufa_reviewed_release_updater.ps1') -Install
if($LASTEXITCODE -ne 0) { throw 'REVIEWED_UPDATER_REGISTRATION_FAILED_AFTER_WORKER_STARTED' }
if($reviewedMode) {
  $installedReceiptPath=Join-Path $data 'installed-release-receipt.json'
  $receipt=[ordered]@{
    schema_version=1; state='INSTALLED_AND_RESTART_VERIFIED'
    repository='pdufa/pdufa-command-center'; release_commit=$ReviewedReleaseCommit
    installer_git_blob_sha1=$selfBlob; approved_pr=$authorization.approved_pr
    installed_at_utc=(Get-Date).ToUniversalTime().ToString('o')
    independent_scientific_acceptance=$false
  }
  $tmp=Join-Path $data ('installed-release-'+[guid]::NewGuid().ToString('N')+'.tmp')
  [IO.File]::WriteAllText($tmp,(ConvertTo-Json $receipt -Depth 6),[Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $tmp -Destination $installedReceiptPath -Force
}
} finally {
  if($installationLock) { $installationLock.Dispose() }
}
