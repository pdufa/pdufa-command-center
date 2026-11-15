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
const {default:Chart,focusSurveyDatum,leastSquaresFit}=require('../app/FocusSurveyTrendChart.tsx');

function trial(i){
 const nct='NCT'+String(i+1).padStart(8,'0');
 return {nct,ticker:'T'+String(i+1).padStart(2,'0'),company:'Fixture '+i,
  levels:Object.fromEntries([1,2,3].map(level=>[String(level),{
   state:'COMPLETED',
   report:{runId:'a'.repeat(36),nct,level,mode:'CURRENT_EVIDENCE',executedAt:'2026-11-15T01:00:00Z'},
   missingEvidence:Array.from({length:(i+level)%4},(_,j)=>({id:'gap'+j,state:'UNVERIFIED',explanation:'Missing test evidence'})),
   evidenceChecks:{total:level===1?8:level===2?9:12,
    sourceVerified:Math.max(0,(level===1?8:level===2?9:12)-((i+level)%4)),
    unresolved:(i+level)%4}
  }]))};
}

test('least-squares trend is a real fitted line, never a fabricated point or a date slope',()=>{
 assert.deepEqual(leastSquaresFit([{x:0,y:2},{x:1,y:4},{x:2,y:6}]),{slope:2,intercept:2});
 assert.equal(leastSquaresFit([{x:1,y:4}]),null);
 assert.equal(leastSquaresFit([{x:1,y:4},{x:1,y:5}]),null);
 assert.equal(leastSquaresFit([{x:0,y:NaN},{x:1,y:4}]),null);
});

test('survey chart metrics come from saved evidence check states, not scientific scores or FDA calls',()=>{
 const t=trial(3);
 assert.equal(focusSurveyDatum(t,1,'UNRESOLVED').value,0);
 assert.equal(focusSurveyDatum(t,2,'UNRESOLVED').value,1);
 assert.equal(focusSurveyDatum(t,2,'VERIFIED_PERCENT').value,800/9);
 const bogus={...t,levels:{...t.levels,'2':{...t.levels['2'],report:{...t.levels['2'].report,nct:'NCT99999999'}}}};
 assert.equal(focusSurveyDatum(bogus,2,'UNRESOLVED').value,null,'different NCT must never be graphed');
 const noCounts={...t,levels:{...t.levels,'2':{...t.levels['2'],evidenceChecks:null}}};
 assert.equal(focusSurveyDatum(noCounts,2,'VERIFIED_PERCENT').value,null,'missing metrics are gaps, not 0');
 assert.equal(focusSurveyDatum(noCounts,2,'UNRESOLVED').value,1,'existing backend supports documented unresolved gaps');
 const noGaps={...t,levels:{...t.levels,'2':{...t.levels['2'],missingEvidence:undefined}}};
 assert.equal(focusSurveyDatum(noGaps,2,'UNRESOLVED').value,null);
});

test('all 32 FOCUS trials render 3 separate lines and 3 independent dashed fits',()=>{
 const trials=Array.from({length:32},(_,i)=>trial(i));
 const html=renderToStaticMarkup(React.createElement(Chart,{trials,total:32,selectedNct:trials[5].nct}));
 for(const level of [1,2,3]){
  assert.match(html,new RegExp('data-survey-level="L'+level+'"'));
  assert.match(html,new RegExp('data-testid="survey-fit-level-'+level+'"'));
  assert.match(html,new RegExp('Show Level '+level+' survey line'));
 }
 assert.match(html,/Survey chart metric/);
 assert.match(html,/Show trend line for each visible level/);
 assert.match(html,/32 distinct FOCUS trials/);
 assert.match(html,/not time/);
 assert.match(html,/not a time trend/);
 assert.match(html,/not a scientific score/);
 assert.match(html,/Unresolved source criteria/);
 assert.match(html,/NCT00000006/);
 assert.doesNotMatch(html,/FDA approval probability: [0-9]/);
 const noSourceMetrics=trials.map(t=>({...t,levels:Object.fromEntries([1,2,3].map(level=>[String(level),{...t.levels[level],evidenceChecks:null}]))}));
 const fallback=renderToStaticMarkup(React.createElement(Chart,{trials:noSourceMetrics,total:32}));
 assert.match(fallback,/data-testid="survey-fit-level-1"/);
 assert.match(fallback,/disabled=""[^>]*>Source-verified criteria/);
});

test('absent or misaligned reconciled NCTs fail closed without drawing partial cohort',()=>{
 const trials=Array.from({length:32},(_,i)=>trial(i));
 for(const candidate of [trials.slice(1),[...trials.slice(0,31),trials[0]],
  [...trials.slice(0,31),{...trials[31],nct:'NOT_AN_NCT'}]]){
  const html=renderToStaticMarkup(React.createElement(Chart,{trials:candidate,total:32}));
  assert.match(html,/Verified full FOCUS source roster unavailable or mismatched/);
  assert.doesNotMatch(html,/data-survey-level="L1"/);
 }
});

test('saved assessment page owns the source-linked trend graph, shown on the actual ASSESMENTS tab',()=>{
 const dir=path.join(__dirname,'../app');
 const saved=fs.readFileSync(path.join(dir,'FocusSavedAssessments.tsx'),'utf8');
 const nav=fs.readFileSync(path.join(dir,'GlobalNavigation.tsx'),'utf8');
 const assessments=fs.readFileSync(path.join(dir,'predictions/assessment/page.tsx'),'utf8');
 const alternative=fs.readFileSync(path.join(dir,'assessments/page.tsx'),'utf8');
 assert.match(nav,/label:"ASSESMENTS",href:"\/predictions\/assessment"/);
 assert.match(saved,/<FocusSurveyTrendChart trials=\{data\.trials\} total=\{data\.total\}/);
 assert.match(assessments,/<FocusSavedAssessments selectedNct=/);
 assert.match(alternative,/<FocusSavedAssessments selectedNct=/);
 const engine=fs.readFileSync(path.join(__dirname,'../../backend/app/focus_assessment_batch.py'),'utf8');
 assert.match(engine,/x\['state'\]=='SOURCE_VERIFIED'/);
 assert.match(engine,/evidenceChecks':evidence_counts/);
 assert.doesNotMatch(saved,/score\.value\/100.*trend/);
});
