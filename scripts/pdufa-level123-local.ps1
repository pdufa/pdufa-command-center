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
function InvokeRepoGit([string[]]$cmd) {
  & git.exe -C $repo @cmd
  if($LASTEXITCODE -ne 0){throw "Git command failed: $($cmd -join ' ')"}
}
function WorkGit([string[]]$cmd){
  & git.exe -C $work @cmd
  if($LASTEXITCODE -ne 0){throw "Worktree git command failed: $($cmd -join ' ')"}
}
function Conflicts {
  @(& git.exe -C $work diff --name-only --diff-filter=U) | Where-Object {$_ -and $_.Trim()}
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
$origin=(& git.exe -C $repo remote get-url origin).Trim()
if($LASTEXITCODE -ne 0 -or $origin -notmatch 'pdufa/pdufa-command-center(\.git)?$'){throw "Unexpected repository origin: $origin"}
Start-Transcript -Path $log | Out-Null
try{
  Write-Host 'Levels 1-3 PAST / FOCUS / ASSESSMENTS integration (local only)' -ForegroundColor Green
  Write-Host "Existing checkout: $repo"
  Write-Host "New separate worktree: $work"
  InvokeRepoGit @('fetch','--no-tags','origin',
     '+refs/heads/main:refs/remotes/origin/main',
     "+refs/heads/${base}:refs/remotes/origin/${base}",
     "+refs/heads/${research}:refs/remotes/origin/${research}")
  # Use the latest production pages as the base. Never replace newer sorting/UI
  # with an older assessment copy. Structural patches below will fail closed.
  InvokeRepoGit @('worktree','add','-b',$branch,$work,'origin/main')
  & git.exe -C $work -c user.name='PDUFA local integration' -c user.email='pdufa-integration@localhost' merge --no-commit --no-ff "origin/$base"
  if($LASTEXITCODE -ne 0){
    $conflicts=@(Conflicts)
    if($conflicts.Count -eq 0){throw 'Foundation merge failed without standard file conflicts.'}
    foreach($file in $conflicts){
      if($file -notin @($focus,$past)){throw "Unexpected foundation conflict: $file. Manual review required."}
    }
    foreach($file in $conflicts){
      WorkGit @('checkout','--ours','--',$file)
      WorkGit @('add','--',$file)
    }
  }
  if(@(Conflicts).Count -gt 0){throw 'Foundation conflicts remain.'}
  WorkGit @('-c','user.name=PDUFA local integration','-c','user.email=pdufa-integration@localhost','commit','-m','Integrate Level 1-3 foundation onto current production')
  # Merge 32-trial saved scientific research and assessment tabs.
  # Use a command-scoped Git identity. No global or checkout Git config is changed.
  & git.exe -C $work -c user.name='PDUFA local integration' -c user.email='pdufa-integration@localhost' merge --no-commit --no-ff "origin/$research"
  if($LASTEXITCODE -ne 0){
    $conflicts=@(Conflicts)
    if($conflicts.Count -eq 0){throw 'Saved-results merge failed without standard file conflicts.'}
    foreach($file in $conflicts){
      if($file -ne $focus){throw "Unexpected research conflict: $file. Manual review required."}
    }
    WorkGit @('checkout','--ours','--',$focus)
    WorkGit @('add','--',$focus)
  }
  if(@(Conflicts).Count -gt 0){throw 'Saved-results conflicts remain.'}
  WorkGit @('-c','user.name=PDUFA local integration','-c','user.email=pdufa-integration@localhost','commit','-m','Integrate saved Level 1-3 scientific research')
  # Graft the assessment controls onto the CURRENT production table pages.
  # Each anchor must exist exactly once; unfamiliar UI changes require review.
  function RewriteOnce([string]$value,[string]$needle,[string]$replacement){
    $first=$value.IndexOf($needle,[StringComparison]::Ordinal)
    if($first -lt 0 -or $value.IndexOf($needle,$first+1,[StringComparison]::Ordinal) -ge 0){
      throw "Unexpected or missing page anchor: $needle"
    }
    return $value.Replace($needle,$replacement)
  }
  $utf8=New-Object System.Text.UTF8Encoding($false)
  $focusPath=Join-Path $work ($focus.Replace('/','\'))
  $f=[IO.File]::ReadAllText($focusPath)
  $focusImports=@'
import FocusSavedAssessments from "../FocusSavedAssessments";
import {FocusLevelHeaders,FocusLevelSubheaders,FocusLevelCells} from '../FocusLevelColumns';
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import AssessmentLauncher from '../AssessmentLauncher';
import ScientificStepsReadiness from '../ScientificStepsReadiness';
import {ExactTrialIntakeSelector} from '../ExactTrialScientificIntake';
'@
  $f=RewriteOnce $f '"use client";' ('"use client";'+[Environment]::NewLine+$focusImports)
  $f=RewriteOnce $f '<IndicationIntelligence mode="focus"/>' ('<AssessmentLauncher source="FOCUS"/><FocusSavedAssessments/><ScientificStepsReadiness cohort="FOCUS"/>'+[Environment]::NewLine+'  <IndicationIntelligence mode="focus"/>')
  $focusNctBefore='<td style={{padding:10}}><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">{t.nct}</a></td>'
  $focusNctAfter='<td style={{padding:10}}><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">{t.nct}</a><div style={{marginTop:5,fontSize:12}}><Link href={"/analyze-now?nct="+encodeURIComponent(t.nct)}>Saved research history</Link></div><details><summary>Exact-trial source intake</summary><ExactTrialIntakeSelector cohort="FOCUS" nctId={t.nct}/></details></td>'
  $f=RewriteOnce $f $focusNctBefore $focusNctAfter
  $f=RewriteOnce $f '</tr></thead>' '<PredictionHeaders/><FocusLevelHeaders/></tr><tr><th colSpan={31}>Level 1-3 saved scientific research</th><FocusLevelSubheaders/></tr></thead>'
  $focusRowEnd='title={label} style={{padding:10,whiteSpace:"nowrap"}}>Not assessed</td>)}'
  $f=RewriteOnce $f $focusRowEnd ($focusRowEnd+'<PredictionCells nct={t.nct}/><FocusLevelCells nct={t.nct}/>')
  $f=RewriteOnce $f '<p style={{fontSize:12,color:"#4f6556",marginTop:15}}>' '<PredictionLegend/><p style={{fontSize:12,color:"#4f6556",marginTop:15}}>'
  [IO.File]::WriteAllText($focusPath,$f,$utf8)

  $pastPath=Join-Path $work ($past.Replace('/','\'))
  $p=[IO.File]::ReadAllText($pastPath)
  $pastImports=@'
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import ScientificStepsReadiness from "../ScientificStepsReadiness";
import AssessmentLauncher from "../AssessmentLauncher";
import {ExactTrialIntakeSelector} from "../ExactTrialScientificIntake";
'@
  $p=RewriteOnce $p '"use client";' ('"use client";'+[Environment]::NewLine+$pastImports)
  $p=RewriteOnce $p ' const [sortRules,setSortRules]=useState<NumericSortRule[]>([]);' (' const [sortRules,setSortRules]=useState<NumericSortRule[]>([]);'+[Environment]::NewLine+' const [verifiedNctByEvent,setVerifiedNctByEvent]=useState<Record<string,string>>({});')
  # Insert before the heading using an ASCII-only anchor so Windows PowerShell 5.1
  # does not misdecode the Unicode em dash when loading an unsigned .ps1 file.
  $p=RewriteOnce $p '<h1>PAST' ('<AssessmentLauncher source="HISTORICAL"/><ScientificStepsReadiness cohort="PAST"/>'+[Environment]::NewLine+' <h1>PAST')
  $p=RewriteOnce $p '<th style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>Overall Score' '<PredictionHeaders/><th style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>Overall Score'
  $pastNct=@'
<td style={{padding:9}}><details><summary>Not linked - enter candidate NCT</summary><label>Exact NCT <input aria-label={"Candidate NCT for "+r.eventKey} value={verifiedNctByEvent[r.eventKey]??""} onChange={e=>setVerifiedNctByEvent(prev=>({...prev,[r.eventKey]:e.target.value.toUpperCase()}))} placeholder="NCT12345678" maxLength={11}/></label>{/^NCT\d{8}$/.test(verifiedNctByEvent[r.eventKey]??"")?<ExactTrialIntakeSelector cohort="PAST" nctId={verifiedNctByEvent[r.eventKey]}/>:<p>Historical event-to-NCT link unverified; do not use for blind scoring.</p>}</details></td>
'@
  $p=RewriteOnce $p '<td style={{padding:9}}>Not linked</td>' $pastNct.Trim()
  $p=RewriteOnce $p '<td style={{padding:9,whiteSpace:"nowrap"}}>Not assessed</td>{assessmentLevelLabels.map' '<PredictionCells nct={verifiedNctByEvent[r.eventKey]}/><td style={{padding:9,whiteSpace:"nowrap"}}>Not assessed</td>{assessmentLevelLabels.map'
  $p=RewriteOnce $p '<p style={{fontSize:12,color:"#526458"}}>' '<PredictionLegend/><p style={{fontSize:12,color:"#526458"}}>'
  [IO.File]::WriteAllText($pastPath,$p,$utf8)
  WorkGit @('add','--',$focus,$past)
  WorkGit @('-c','user.name=PDUFA local integration','-c','user.email=pdufa-integration@localhost','commit','-m','Preserve production sorting and add Level 1-3 tables and launchers')
  # Repair Windows-only test portability and retain the source-verified PAST
  # historical comparison safeguards before running the full regression suite.
  $repair=Join-Path $repo 'scripts\pdufa-level123-repair-tests.ps1'
  if(-not (Test-Path -LiteralPath $repair)){throw 'Missing Level 1-3 repair helper.'}
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $repair -Worktree $work
  if($LASTEXITCODE -ne 0){throw 'Portable regression repair did not complete.'}
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
