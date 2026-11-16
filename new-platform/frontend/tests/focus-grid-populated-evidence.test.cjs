const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file
);
const {FOCUS_CHART_SNAPSHOT_TRIALS}=require('../lib/focus-chart-snapshot.ts');
const {provisionalFocusScore,provisionalFocusOverall,focusSavedDirection}=require('../lib/focus-provisional-scores.ts');
const {FocusOverviewCells,FocusTwentyCells}=require('../app/FocusOverallLevelMatrix.tsx');
const focus=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');

function focusLevels(trial){
 return Object.fromEntries([1,2,3].map(level=>{
  const r=trial.levels[String(level)].report;
  return [String(level),{state:'COMPLETED',
   report:{...r,fdaPrediction:{outcome:'ABSTAIN',confidence:'NOT_VALIDATED'}},
   missingEvidence:[]
  }];
 }));
}
test('32 exact FOCUS rows, 96 level scores and 32 pooled overall values from original source reports',()=>{
 assert.equal(FOCUS_CHART_SNAPSHOT_TRIALS.length,32);
 const allNcts=new Set();
 for(const trial of FOCUS_CHART_SNAPSHOT_TRIALS){
  assert.ok(!allNcts.has(trial.nct));
  allNcts.add(trial.nct);
  const levels=focusLevels(trial);
  for(const level of [1,2,3]){
   const score=provisionalFocusScore(trial.nct,level,levels[String(level)].report);
   assert.ok(score&&Number.isInteger(score.evidenceReadinessScore));
  }
  const overall=provisionalFocusOverall(trial.nct,levels);
  assert.ok(overall&&Number.isInteger(overall.evidenceReadinessScore));
  assert.equal(focusSavedDirection(trial.nct,levels),'ABSTAIN');
 }
});
test('all 32 FOCUS main table overview cells display real overall and inline L01, L02, L03 numbers even when collapsed',()=>{
 const html=renderToStaticMarkup(React.createElement('table',null,
  React.createElement('tbody',null,FOCUS_CHART_SNAPSHOT_TRIALS.map(t=>
   React.createElement('tr',{key:t.nct},React.createElement(FocusOverviewCells,{nct:t.nct,levels:focusLevels(t)}))
  ))));
 assert.equal((html.match(/data-testid="overall-evidence-readiness-value"/g)||[]).length,32);
 assert.equal((html.match(/data-testid="focus-overall-level123-inline"/g)||[]).length,32);
 assert.equal((html.match(/data-testid="overall-fda-direction"/g)||[]).length,32);
 assert.doesNotMatch(html,/>Pending<\/strong>/);
 assert.doesNotMatch(html,/APPROVAL LEAN|CRL LEAN|100% FDA probability/);
 const row=FOCUS_CHART_SNAPSHOT_TRIALS[0];
 const values=[1,2,3].map(l=>provisionalFocusScore(row.nct,l,focusLevels(row)[l].report).evidenceReadinessScore);
 for(const n of values)assert.match(html,new RegExp(''+n+'/100'));
});
test('expanded L01–L03 remain source-backed for all 32 FOCUS rows, pending only L04–L20',()=>{
 const html=renderToStaticMarkup(React.createElement('table',null,
  React.createElement('tbody',null,FOCUS_CHART_SNAPSHOT_TRIALS.map(t=>
   React.createElement('tr',{key:t.nct},
    React.createElement(FocusTwentyCells,{nct:t.nct,levels:focusLevels(t)})
   )
  ))));
 for(const i of [1,2,3])
  assert.equal((html.match(new RegExp('data-testid="provisional-L0'+i+'-score"','g'))||[]).length,32);
 assert.equal((html.match(/data-assessment-level="L20"/g)||[]).length,32);
 assert.match(html,/Rubric pending/);
});
test('live FOCUS table defaults to pinned snapshot and retains sorting, current-data refresh and source labeling',()=>{
 assert.match(focus,/FOCUS_CHART_SNAPSHOT_TRIALS/);
 assert.match(focus,/useState<Record<string,FocusTrialLevels>>\(datedSourceLevels\)/);
 assert.match(focus,/useState<Record<string,Record<string,number\|null>>>\(datedSourceScores\)/);
 assert.match(focus,/setSavedLevels\(datedSourceLevels\)/);
 assert.match(focus,/setSavedLevels\(levels\)/);
 assert.match(focus,/provisionalFocusScore\(nct,level,levels\?\.\[String\(level\)\]\?\.report\)/);
 assert.match(focus,/data-testid="focus-main-grid-evidence-source"/);
 assert.match(focus,/<FocusOverviewCells nct=\{t.nct\} levels=\{savedLevels\[t.nct\]\}/);
 assert.match(focus,/<FocusTwentyCells nct=\{t.nct\} levels=\{savedLevels\[t.nct\]\}/);
 assert.match(focus,/aria-label="Survey Columns"/);
 assert.match(focus,/sortNumericRows/);
});
