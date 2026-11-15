# Repair portable Level 1-3 integration test failures in an existing worktree.
# This tool never pushes, merges, deploys, or edits the original Git checkout.
param(
  [Parameter(Mandatory=$true)][string]$Worktree,
  [switch]$RunTests
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$work=(Resolve-Path -LiteralPath $Worktree).Path
if(-not (Test-Path (Join-Path $work '.git'))){throw "Not a Git worktree: $work"}
$branch=(& git.exe -C $work branch --show-current).Trim()
if($branch -notmatch '^integration/level123-\d{8}-\d{6}$'){
  throw "Expected a local Level 1-3 integration branch; got: $branch"
}
$changed=@(& git.exe -C $work status --porcelain)
if($changed.Count -gt 0){throw 'Worktree has uncommitted changes; stop to protect existing work.'}
function RewriteOnce([string]$body,[string]$original,[string]$replacement){
  $i=$body.IndexOf($original,[StringComparison]::Ordinal)
  if($i -lt 0 -or $body.IndexOf($original,$i+1,[StringComparison]::Ordinal) -ge 0){
    throw "Missing or duplicated expected anchor: $original"
  }
  return $body.Replace($original,$replacement)
}
$enc=New-Object System.Text.UTF8Encoding($false)
$focusPath=Join-Path $work 'new-platform\frontend\app\focus\page.tsx'
$pastPath=Join-Path $work 'new-platform\frontend\app\past\page.tsx'
$nightlyTestPath=Join-Path $work 'new-platform\frontend\tests\main-phase3-nightly-health.test.cjs'
$censusTestPath=Join-Path $work 'new-platform\frontend\tests\phase3-census-sources.test.cjs'
$f=[IO.File]::ReadAllText($focusPath)
$f=RewriteOnce $f '>Saved research history</Link>' '>View exact-trial research history</Link>'
$p=[IO.File]::ReadAllText($pastPath)
$p=RewriteOnce $p 'Reveal verified FDA decisions (exclude from blind scoring)' 'Show historical comparison data (unverified event match; exclude from blind scoring)'
$p=RewriteOnce $p 'Historical event-to-NCT link unverified; do not use for blind scoring.' 'Historical event-to-NCT linkage remains unverified; no intake displayed.'
$p=RewriteOnce $p 'const verified=known.find(k=>k.ticker===r.ticker&&k.actualFdaActionDate===r.cutoffDate);' 'const candidates=known.filter(k=>k.ticker===r.ticker&&k.actualFdaActionDate===r.cutoffDate);const tentative=candidates.length===1?candidates[0]:null;const comparisonLabel=candidates.length>1?"Ambiguous historical matches":candidates.length===1?"Unverified match: ":"Not verified";'
$p=RewriteOnce $p '!reveal?"Hidden":verified?verified.approvalType:"Not verified"' '!reveal?"Hidden":tentative?comparisonLabel+tentative.approvalType:comparisonLabel'
$p=RewriteOnce $p '!reveal?"Hidden":verified?verified.actualOutcome:"Not verified"' '!reveal?"Hidden":tentative?comparisonLabel+tentative.actualOutcome:comparisonLabel'
$p=RewriteOnce $p 'Decision data is deliberately separated from blind predictions.' 'Historical comparisons are matched only by ticker and date, not by source-verified FDA event identity; do not treat these as confirmed FDA decisions. Decision data is deliberately separated from blind predictions.'
$nightly=[IO.File]::ReadAllText($nightlyTestPath)
$nightly=RewriteOnce $nightly 'assert.ok(workflow.includes("      - name: "+INTEGRITY_STEP+"\n"),' 'assert.ok(workflow.replace(/\r\n/g,"\n").includes("      - name: "+INTEGRITY_STEP+"\n"),'
$census=[IO.File]::ReadAllText($censusTestPath)
$censusReplacement=@'
const python = process.platform === "win32" ? "py" : "python3";
  const args = process.platform === "win32"
    ? ["-3","scripts/build_phase3_census_sources.py","--check"]
    : ["scripts/build_phase3_census_sources.py","--check"];
  const result = spawnSync(python,args,{cwd:root,encoding:"utf8"});
'@
$census=RewriteOnce $census 'const result = spawnSync("python3",["scripts/build_phase3_census_sources.py","--check"],{cwd:root,encoding:"utf8"});' ($censusReplacement.TrimEnd())
foreach($pair in @(@($focusPath,$f),@($pastPath,$p),@($nightlyTestPath,$nightly),@($censusTestPath,$census))){
  [IO.File]::WriteAllText([string]$pair[0],[string]$pair[1],$enc)
}
& git.exe -C $work add -- 'new-platform/frontend/app/focus/page.tsx' 'new-platform/frontend/app/past/page.tsx' 'new-platform/frontend/tests/main-phase3-nightly-health.test.cjs' 'new-platform/frontend/tests/phase3-census-sources.test.cjs'
if($LASTEXITCODE -ne 0){throw 'Failed to stage repair.'}
& git.exe -C $work -c user.name='PDUFA local integration' -c user.email='pdufa-integration@localhost' commit -m 'Fix Level 1-3 integration labels and Windows portable tests'
if($LASTEXITCODE -ne 0){throw 'Failed to commit repair.'}
Write-Host "LEVEL 1-3 REPAIR COMMITTED in $work" -ForegroundColor Green
if($RunTests){
  $frontend=Join-Path $work 'new-platform\frontend'
  Push-Location $frontend
  try{
    & npm.cmd run typecheck
    if($LASTEXITCODE -ne 0){throw 'Typecheck failed.'}
    & npm.cmd test
    if($LASTEXITCODE -ne 0){throw 'Frontend tests failed.'}
    & npm.cmd run build
    if($LASTEXITCODE -ne 0){throw 'Frontend production build failed.'}
  }finally{Pop-Location}
  Write-Host 'FRONTEND TYPECHECK, TESTS AND BUILD PASSED' -ForegroundColor Green
}
