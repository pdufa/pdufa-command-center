# PDUFA Levels 1-3 local integration; no push or production deployment.
# Usage: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\pdufa-level123-local.ps1
param([switch]$FullTests)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path (Join-Path $repo '.git'))) { throw 'Installation script must be inside a Git checkout.' }
$base='codex/level1-6-explicit-scientific-readiness-20261114'
$research='codex/assessment-123-catalog-audit-20261114'
$focus='new-platform/frontend/app/focus/page.tsx'
$past='new-platform/frontend/app/past/page.tsx'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$work=Join-Path $HOME "pdufa-level123-$stamp"
$branch="integration/level123-$stamp"
$log=Join-Path $HOME "pdufa-level123-$stamp.log"
function Git([string[]]$cmd) {
  & git -C $repo @cmd
  if($LASTEXITCODE -ne 0){throw "Git command failed: $($cmd -join ' ')"}
}
function WorkGit([string[]]$cmd){
  & git -C $work @cmd
  if($LASTEXITCODE -ne 0){throw "Worktree git command failed: $($cmd -join ' ')"}
}
function Conflicts {
  @(& git -C $work diff --name-only --diff-filter=U) | Where-Object {$_ -and $_.Trim()}
}
function RunCheck([string]$command,[string[]]$cmd,[string]$folder){
  Push-Location $folder
  try {
    Write-Host "Running: $command $($cmd -join ' ')" -ForegroundColor Cyan
    & $command @cmd
    if ($LASTEXITCODE -ne 0){throw "Command failed: $command $($cmd -join ' ')"}
  } finally {Pop-Location}
}
foreach($c in @('git.exe','node.exe','npm.cmd')){
  if(-not (Get-Command $c -ErrorAction SilentlyContinue)){throw "Missing $c; install it before proceeding."}
}
$py = if(Get-Command 'py.exe' -ErrorAction SilentlyContinue){'py.exe'}elseif(Get-Command 'python.exe' -ErrorAction SilentlyContinue){'python.exe'}else{throw 'Python 3 is required.'}
$origin=(& git -C $repo remote get-url origin).Trim()
if($LASTEXITCODE -ne 0 -or $origin -notmatch 'pdufa/pdufa-command-center(\.git)?$'){throw "Unexpected repository origin: $origin"}
Start-Transcript -Path $log | Out-Null
try{
  Write-Host 'Levels 1-3 PAST / FOCUS / ASSESSMENTS integration (local only)' -ForegroundColor Green
  Write-Host "Existing checkout: $repo"
  Write-Host "New separate worktree: $work"
  Git @('fetch','--no-tags','origin',
     '+refs/heads/main:refs/remotes/origin/main',
     "+refs/heads/${base}:refs/remotes/origin/${base}",
     "+refs/heads/${research}:refs/remotes/origin/${research}")
  # Known source snapshots; do not silently overwrite newer pages.
  $guard=@(
    @('origin/main',$focus,'9074a281a4947592a54ef957ccf6d452fbed4436'),
    @('origin/main',$past,'f8e7cce9c6cfca1124a3b322bf40f41c1548523b'),
    @("origin/$base",$focus,'5b111abc0101c2ec1056dacb193cbd10e51929d9'),
    @("origin/$base",$past,'3a8baef91c9a23dfc61fe6aa739302fe271d908c'),
    @("origin/$research",$focus,'e9737cc23c26c866a5dfb954116404d710fc66e7')
  )
  foreach($g in $guard){
    $actual=(& git -C $repo rev-parse "$($g[0]):$($g[1])").Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -ne $g[2]){
      throw "Source changed: $($g[0]):$($g[1]). Stopped to protect newer work."
    }
  }
  Git @('worktree','add','-b',$branch,$work,"origin/$base")
  # First merge current production into development; the two pre-reviewed
  # UI conflicts are resolved using the foundation's pre-integrated pages.
  & git -C $work merge --no-commit --no-ff origin/main
  if($LASTEXITCODE -ne 0){
    $conflicts=@(Conflicts)
    if($conflicts.Count -eq 0){throw 'Main merge failed without standard file conflicts.'}
    foreach($file in $conflicts){
      if($file -notin @($focus,$past)){throw "Unexpected main conflict: $file. Manual review required."}
    }
    foreach($file in $conflicts){
      WorkGit @('checkout','--ours','--',$file)
      WorkGit @('add','--',$file)
    }
  }
  if(@(Conflicts).Count -gt 0){throw 'Main conflicts remain.'}
  WorkGit @('commit','-m','Integrate production with Level 1-3 assessment foundation')
  # Merge 32-trial saved scientific research and assessment tabs.
  & git -C $work merge --no-commit --no-ff "origin/$research"
  if($LASTEXITCODE -ne 0){
    $conflicts=@(Conflicts)
    if($conflicts.Count -eq 0){throw 'Saved-results merge failed without standard file conflicts.'}
    foreach($file in $conflicts){if($file -ne $focus){throw "Unexpected research conflict: $file."}}
    WorkGit @('checkout','--ours','--',$focus)
    $path=Join-Path $work ($focus.Replace('/','\'))
    $source=[IO.File]::ReadAllText($path)
    if(-not $source.Contains('import FocusSavedAssessments from "../FocusSavedAssessments";')){
      if(-not $source.StartsWith('"use client";')){throw 'FOCUS page is not a client component.'}
      $source=$source.Replace('"use client";','"use client";' + "`n" + 'import FocusSavedAssessments from "../FocusSavedAssessments";')
    }
    if(-not $source.Contains('<FocusSavedAssessments/>')){
      $marker='<AssessmentLauncher source="FOCUS"/>'
      if(-not $source.Contains($marker)){throw 'Missing launcher marker; manual review required.'}
      $source=$source.Replace($marker,$marker+'<FocusSavedAssessments/>')
    }
    [IO.File]::WriteAllText($path,$source,(New-Object System.Text.UTF8Encoding($false)))
    WorkGit @('add','--',$focus)
  }
  if(@(Conflicts).Count -gt 0){throw 'Saved-results conflicts remain.'}
  WorkGit @('commit','-m','Integrate saved Level 1-3 FOCUS assessments')
  $required=@{
    $focus=@('NumericSortSettings','FocusSavedAssessments','AssessmentLauncher','FocusLevelCells','PredictionCells','sortedTrials.map')
    $past=@('NumericSortSettings','AssessmentLauncher','ExactTrialIntakeSelector','PredictionCells','assessmentLevelLabels')
    'new-platform/frontend/app/assessments/page.tsx'=@('AssessmentWorkbench','FocusSavedAssessments','AssessmentLauncher')
  }
  foreach($file in $required.Keys){
    $body=[IO.File]::ReadAllText((Join-Path $work ($file.Replace('/','\'))))
    foreach($marker in $required[$file]){if(-not $body.Contains($marker)){throw "Feature missing in $file : $marker"}}
  }
  $frontend=Join-Path $work 'new-platform/frontend'
  RunCheck 'npm.cmd' @('ci') $frontend
  RunCheck 'npm.cmd' @('run','typecheck') $frontend
  RunCheck 'npm.cmd' @('test') $frontend
  RunCheck 'npm.cmd' @('run','build') $frontend
  $venv=Join-Path $work '.venv'
  if($py -eq 'py.exe'){RunCheck $py @('-3','-m','venv',$venv) $work}else{RunCheck $py @('-m','venv',$venv) $work}
  $python=Join-Path $venv 'Scripts/python.exe'
  RunCheck $python @('-m','pip','install','-r','new-platform/backend/requirements.txt') $work
  RunCheck $python @('-m','pytest','-q','new-platform/backend') $work
  RunCheck $python @('scripts/audit_raas_retirement.py','--check') $work
  if($FullTests){RunCheck $python @('-m','pytest','-q') $work}
  Write-Host 'LOCAL INTEGRATION AND TESTS PASSED' -ForegroundColor Green
  Write-Host "Worktree: $work; Branch: $branch; Log: $log"
  Write-Host "To preview: cd `"$frontend`"; npm.cmd run dev"
  Write-Host 'Production is unchanged; scoring gaps still require source-backed validation.'
}catch{
  Write-Host "STOPPED: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Saved log: $log; worktree: $work"
  throw
}finally{Stop-Transcript | Out-Null}
