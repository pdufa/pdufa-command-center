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
 }}).outputText,file);
const snapshot=require('../data/focus123EvidenceReadiness20261115.json');
const {provisionalFocusOverall,provisionalFocusScore,focusSavedDirection}=require('../lib/focus-provisional-scores.ts');
const {default:Chart}=require('../app/FocusSurveyTrendChart.tsx');
const {default:Matrix,FOCUS_TWENTY_LEVEL_LABELS}=require('../app/FocusOverallLevelMatrix.tsx');
const groups=new Map();
for(const r of snapshot.rows){if(!groups.has(r.nct))groups.set(r.nct,[]);groups.get(r.nct).push(r);}
const trials=[...groups.entries()].map(([nct,rows],i)=>({
 nct,ticker:'S'+String(i).padStart(2,'0'),company:'Source backed example '+i,
 levels:Object.fromEntries(rows.map(r=>[String(r.level),{
  state:'COMPLETED',
  report:{nct,level:r.level,mode:'CURRENT_EVIDENCE',runId:r.runId,
   engineVersion:snapshot.researchVersion+'/level-'+r.level,
   executedAt:r.executedAt,score:{kind:'NOT_VALIDATED',value:null},
   fdaPrediction:{outcome:'ABSTAIN',confidence:'NOT_VALIDATED'}},
  missingEvidence:Array.from({length:r.unresolved},(_,j)=>({id:'missing'+j,state:'UNVERIFIED',explanation:'Needs original source'}))
 }]))
}));
test('strict 32-trial 96-report identities, pooled overall documented-readiness scores, and prediction abstention',()=>{
 assert.equal(snapshot.rows.length,96);
 assert.equal(trials.length,32);
 assert.equal(FOCUS_TWENTY_LEVEL_LABELS.length,20);
 for(const t of trials){
  const rs=[1,2,3].map(level=>provisionalFocusScore(t.nct,level,t.levels[level].report));
  assert.ok(rs.every(Boolean));
  const overall=provisionalFocusOverall(t.nct,t.levels);
  const verified=rs.reduce((a,r)=>a+r.sourceVerified,0),applicable=rs.reduce((a,r)=>a+r.applicable,0);
  assert.equal(overall.evidenceReadinessScore,Math.round(100*verified/applicable));
  assert.equal(focusSavedDirection(t.nct,t.levels),'ABSTAIN');
  assert.equal(provisionalFocusOverall(t.nct,{...t.levels,'1':{report:{...t.levels['1'].report,runId:'stale'}}}),null);
 }
});
test('four numeric series and one separate categorical direction, all 32 observed, no fabricated FDA probability',()=>{
 const html=renderToStaticMarkup(React.createElement(Chart,{trials,total:32}));
 for(const id of ['L1','L2','L3','L4'])assert.match(html,new RegExp('data-survey-level="'+id+'"'));
 for(const id of [1,2,3,4])assert.match(html,new RegExp('survey-fit-level-'+id+'"'));
 assert.equal((html.match(/data-testid="survey-overall-score"/g)||[]).length,32);
 assert.equal((html.match(/data-testid="survey-direction-abstain"/g)||[]).length,32);
 assert.equal((html.match(/data-testid="survey-prediction-direction"/g)||[]).length,32);
 assert.match(html,/FDA direction · categorical/);
 assert.match(html,/NOT VALIDATED/);
 assert.doesNotMatch(html,/FDA approval probability: [0-9]+%/);
});
test('overall and direction stay visible with closed or open L01-L20 horizontal survey collapse',()=>{
 const collapsed=renderToStaticMarkup(React.createElement(Matrix,{trials:trials.slice(0,2)}));
 assert.match(collapsed,/survey-horizontal-collapse/);
 assert.match(collapsed,/Overall prediction survey result/);
 assert.match(collapsed,/FDA direction/);
 assert.doesNotMatch(collapsed,/L01-Trial identity/);
 const expanded=renderToStaticMarkup(React.createElement(Matrix,{trials:trials.slice(0,2),initiallyExpanded:true}));
 assert.match(expanded,/L01-Trial identity/);
 assert.match(expanded,/L20-Integrated review/);
 assert.equal((expanded.match(/data-assessment-level="L[0-9]{2}"/g)||[]).length,40);
 assert.equal((expanded.match(/data-testid="overall-evidence-readiness-value"/g)||[]).length,2);
});
test('current main FOCUS Survey Columns and numeric sorting retained alongside overall and direction',()=>{
 const focus=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
 const saved=fs.readFileSync(path.join(__dirname,'../app/FocusSavedAssessments.tsx'),'utf8');
 assert.match(focus,/aria-label="Survey Columns"/);
 assert.match(focus,/<FocusOverallHeaders expanded=\{surveyExpanded\}/);
 assert.match(focus,/<FocusOverviewCells nct=\{t.nct\} levels=\{savedLevels\[t.nct\]\}/);
 assert.match(saved,/<FocusOverallLevelMatrix trials=\{rows\}/);
 assert.match(saved,/<FocusSurveyTrendChart trials=\{chartTrials\}/);
});
