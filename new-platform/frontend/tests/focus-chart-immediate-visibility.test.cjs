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
const {FOCUS_CHART_SNAPSHOT_TRIALS,FOCUS_CHART_SNAPSHOT_DATE}=require('../lib/focus-chart-snapshot.ts');
const {default:Chart,focusSurveyDatum,focusSurveyOverallDatum,focusSurveyDirection}=
 require('../app/FocusSurveyTrendChart.tsx');
const {default:SavedAssessments}=require('../app/FocusSavedAssessments.tsx');

test('snapshot fallback is exactly the dated 32-trial source; 96 numeric score observations are verifiable and no forecast invented',()=>{
 assert.equal(FOCUS_CHART_SNAPSHOT_DATE,'2026-11-15');
 assert.equal(FOCUS_CHART_SNAPSHOT_TRIALS.length,32);
 assert.equal(new Set(FOCUS_CHART_SNAPSHOT_TRIALS.map(t=>t.nct)).size,32);
 for(const trial of FOCUS_CHART_SNAPSHOT_TRIALS){
  assert.match(trial.nct,/^NCT[0-9]{8}$/);
  assert.ok(trial.ticker);
  for(const level of [1,2,3]){
   const v=focusSurveyDatum(trial,level,'VERIFIED_PERCENT').value;
   assert.ok(v!==null&&v>=0&&v<=100,trial.nct+' L'+level);
   const missing=focusSurveyDatum(trial,level,'UNRESOLVED').value;
   assert.ok(Number.isInteger(missing)&&missing>=0);
  }
  const o=focusSurveyOverallDatum(trial,'VERIFIED_PERCENT').value;
  assert.ok(o!==null&&o>=0&&o<=100);
  assert.equal(focusSurveyDirection(trial),'ABSTAIN');
 }
});

test('four numeric fits and categorical FDA line are present on the first server render without API access',()=>{
 const html=renderToStaticMarkup(React.createElement(Chart,{
  trials:FOCUS_CHART_SNAPSHOT_TRIALS,total:32
 }));
 for(const i of [1,2,3,4]){
  assert.match(html,new RegExp('data-survey-level="L'+i+'"'));
  assert.match(html,new RegExp('data-testid="survey-fit-level-'+i+'"'));
 }
 assert.equal((html.match(/data-testid="survey-overall-score"/g)||[]).length,32);
 assert.equal((html.match(/data-testid="survey-direction-abstain"/g)||[]).length,32);
 assert.doesNotMatch(html,/No suitable saved research check counts yet/);
});

test('ASSESSMENTS page shows populated four-line chart immediately before the protected API returns data',()=>{
 const html=renderToStaticMarkup(React.createElement(SavedAssessments,{}));
 assert.match(html,/data-testid="focus-chart-immediate-panel"/);
 assert.match(html,/Visible source-checked snapshot dated 2026-11-15/);
 assert.match(html,/id="focus-survey-trend-chart"/);
 for(const i of [1,2,3,4])assert.match(html,new RegExp('data-testid="survey-fit-level-'+i+'"'));
 assert.match(html,/Loading persisted assessments/);
 assert.ok(html.indexOf('focus-chart-immediate-panel')<html.indexOf('Loading persisted assessments'));
 assert.doesNotMatch(html,/FDA approval probability: [1-9][0-9]*%/);
});

test('FOCUS and both ASSESMENTS routes offer immediate navigation to chart',()=>{
 const root=path.join(__dirname,'../app');
 for(const file of ['focus/page.tsx','assessments/page.tsx','predictions/assessment/page.tsx']){
  const text=fs.readFileSync(path.join(root,file),'utf8');
  assert.match(text,/href="#focus-chart-quick-view"/);
 }
});
