const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
require.extensions['.tsx']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,f);
const {default:Matrix,FocusOverallHeaders,FocusOverviewCells,FocusTwentyHeaders,
 FocusTwentyCells,FOCUS_TWENTY_LEVEL_LABELS,ownerSurveyStatus}
 =require('../app/FocusOverallLevelMatrix.tsx');

const nct='NCT04576949';
const levelMap=()=>Object.fromEntries([1,2,3].map(level=>[String(level),{
 state:'COMPLETED',report:{nct,level,mode:'CURRENT_EVIDENCE',
  runId:'a'.repeat(36),executedAt:'2026-11-15T01:00:00Z',
  score:{value:null,kind:'NOT_VALIDATED'},fdaPrediction:{outcome:'ABSTAIN',confidence:'UNVALIDATED'}}
}]));

test('overall survey result, direction, then exact 20 level names in that order',()=>{
 assert.equal(FOCUS_TWENTY_LEVEL_LABELS.length,20);
 assert.equal(new Set(FOCUS_TWENTY_LEVEL_LABELS).size,20);
 const head=renderToStaticMarkup(React.createElement('table',null,
  React.createElement('thead',null,React.createElement('tr',null,
   React.createElement(FocusOverallHeaders),React.createElement(FocusTwentyHeaders)))));
 const overall=head.indexOf('Overall prediction survey result');
 const direction=head.indexOf('FDA direction');
 const l01=head.indexOf('L01-Trial identity'),l20=head.indexOf('L20-Integrated review');
 assert.ok(overall>=0&&direction>overall&&l01>direction&&l20>l01);
 for(let l=1;l<=20;l++)assert.match(head,new RegExp('L'+String(l).padStart(2,'0')+'-'));
});

test('all 32 FOCUS rows have distinct overall, direction and L01–L20 cells without made-up scores',()=>{
 const trials=Array.from({length:32},(_,i)=>({
  nct:'NCT'+String(i+1).padStart(8,'0'),ticker:'T'+String(i).padStart(2,'0'),
  company:'Synthetic company '+i,
  levels:Object.fromEntries([1,2,3].map(level=>[String(level),{
   ...levelMap()[String(level)],report:{...levelMap()[String(level)].report,
    nct:'NCT'+String(i+1).padStart(8,'0')}
  }]))
 }));
 const html=renderToStaticMarkup(React.createElement(Matrix,{trials,initiallyExpanded:true}));
 assert.match(html,/data-testid="focus-overall-direction-level20-table"/);
 const allRows=[...html.matchAll(/<tr\b/g)];
 assert.equal(allRows.length,33,'one header plus 32 independent trials');
 assert.equal((html.match(/data-testid="focus-overall-survey-result"/g)||[]).length,32);
 assert.equal((html.match(/data-testid="focus-overall-direction"/g)||[]).length,32);
 for(let l=1;l<=20;l++)
  assert.equal((html.match(new RegExp('data-assessment-level="L'+String(l).padStart(2,'0')+'"','g'))||[]).length,32);
 assert.equal((html.match(/>ABSTAIN<\/strong>/g)||[]).length,32);
 assert.match(html,/Research saved · unscored/);
 assert.match(html,/Rubric pending/);
 assert.doesNotMatch(html,/>100%|APPROVAL LEAN|CRL LEAN/);
});

test('report identity mismatch never contributes to overall survey, FDA direction or an automatic numerical score',()=>{
 const good=levelMap(),status=ownerSurveyStatus(nct,good);
 assert.deepEqual(status,{completed:3,overall:'NOT VALIDATED',direction:'ABSTAIN'});
 const corrupted={...good,'2':{...good['2'],report:{...good['2'].report,nct:'NCT99999999'}}};
 assert.deepEqual(ownerSurveyStatus(nct,corrupted),{
  completed:2,overall:'NOT VALIDATED',direction:'NOT AVAILABLE'});
 const body=renderToStaticMarkup(React.createElement('table',null,
  React.createElement('tbody',null,React.createElement('tr',null,
   React.createElement(FocusOverviewCells,{nct,levels:good}),
   React.createElement(FocusTwentyCells,{nct,levels:good})))));
 assert.match(body,/3\/3 current research surveys saved/);
 assert.match(body,/ABSTAIN/);
 assert.doesNotMatch(body,/Approval Lean|CRL Lean/);
});

test('FOCUS and navigated ASSESMENTS show same ordered reusable result components, no source score promotion',()=>{
 const read=p=>fs.readFileSync(path.join(__dirname,'../app',p),'utf8');
 const focus=read('focus/page.tsx'),saved=read('FocusSavedAssessments.tsx');
 const navigation=read('GlobalNavigation.tsx');
 assert.match(navigation,/label:"ASSESMENTS",href:"\/predictions\/assessment"/);
 assert.match(focus,/<FocusOverallHeaders expanded=\{surveyLevelsExpanded\}/);
 assert.match(focus,/\{surveyLevelsExpanded&&<FocusTwentyHeaders\/>\}/);
 assert.match(focus,/\{surveyLevelsExpanded&&<FocusTwentyCells/);
 assert.match(focus,/<FocusOverviewCells nct=\{t\.nct\}/);
 assert.match(focus,/<FocusTwentyCells nct=\{t\.nct\}/);
 assert.match(saved,/<FocusOverallLevelMatrix trials=\{rows\}/);
 assert.ok(saved.indexOf('<FocusOverallLevelMatrix')<saved.indexOf('<FocusSurveyTrendChart'),
  'overall result sheet appears before trend chart');
 assert.match(read('predictions/assessment/page.tsx'),/<FocusSavedAssessments selectedNct=/);
 assert.match(read('assessments/page.tsx'),/<FocusSavedAssessments selectedNct=/);
 assert.doesNotMatch(read('FocusOverallLevelMatrix.tsx'),/score\.value\s*\+|sourceVerified\s*\/\s*total.*forecast/);
});

test('survey heading has original + 20 Levels horizontal collapse; initially collapsed for FOCUS and ASSESMENTS',()=>{
 const t={nct,ticker:'SYN',company:'Synthetic',levels:levelMap()};
 const collapsed=renderToStaticMarkup(React.createElement(Matrix,{trials:[t]}));
 assert.match(collapsed,/data-testid="survey-horizontal-collapse"/);
 assert.match(collapsed,/aria-expanded="false"/);
 assert.match(collapsed,/\+ 20 Levels/);
 assert.match(collapsed,/Overall prediction survey result/);
 assert.match(collapsed,/FDA direction/);
 assert.doesNotMatch(collapsed,/L01-Trial identity/);
 assert.doesNotMatch(collapsed,/L20-Integrated review/);
 assert.doesNotMatch(collapsed,/data-assessment-level="L01"/);
 const expanded=renderToStaticMarkup(React.createElement(Matrix,{trials:[t],initiallyExpanded:true}));
 assert.match(expanded,/aria-expanded="true"/);
 assert.match(expanded,/− 20 Levels/);
 assert.match(expanded,/L01-Trial identity/);
 assert.match(expanded,/L20-Integrated review/);
 assert.equal((expanded.match(/data-assessment-level="L[0-9]{2}"/g)||[]).length,20);
 assert.match(expanded,/data-testid="focus-overall-survey-result"/);
 assert.match(expanded,/data-testid="focus-overall-direction"/);
 const focus=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
 assert.match(focus,/const \[surveyLevelsExpanded,setSurveyLevelsExpanded\]=useState\(false\)/);
 assert.match(focus,/colSpan=\{surveyLevelsExpanded\?33:13\}/);
 assert.doesNotMatch(focus,/assessment-toggle\[open\]/,'no legacy details hack');
 const shared=fs.readFileSync(path.join(__dirname,'../app/FocusOverallLevelMatrix.tsx'),'utf8');
 assert.match(shared,/onClick=\{onToggle\}/);
 assert.match(shared,/aria-expanded=\{expanded\}/);
 assert.match(shared,/survey-horizontal-collapse/);
});
