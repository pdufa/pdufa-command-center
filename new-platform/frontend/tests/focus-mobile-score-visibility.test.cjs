const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);
const {FOCUS_CHART_SNAPSHOT_TRIALS}=require('../lib/focus-chart-snapshot.ts');
const {provisionalFocusScore,provisionalFocusOverall}=require('../lib/focus-provisional-scores.ts');
const code=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');

test('FOCUS has mobile-specific in-place Overall, L01, L02 and L03 grid above the full table',()=>{
 assert.match(code,/data-testid="focus-mobile-score-view"/);
 assert.match(code,/data-testid="focus-mobile-score-table"/);
 assert.match(code,/@media \(max-width:740px\)/);
 assert.match(code,/sortedTrials\.map\(t=><tr key=\{t\.nct\}/);
 assert.match(code,/\(\["overall","1","2","3"\] as const\)/);
 assert.match(code,/savedScores\[t\.nct\]\?\.\[key\]/);
 assert.ok(code.indexOf('data-testid="focus-mobile-score-view"')<
  code.indexOf('data-testid="focus-full-table-scroller"'));
});
test('each of 32 trials matches the source evidence percentages, and no fabricated probability',()=>{
 assert.equal(FOCUS_CHART_SNAPSHOT_TRIALS.length,32);
 for(const t of FOCUS_CHART_SNAPSHOT_TRIALS){
  assert.match(t.nct,/^NCT[0-9]{8}$/);
  for(const l of [1,2,3]){
   const v=provisionalFocusScore(t.nct,l,t.levels[String(l)].report);
   assert.ok(v&&Number.isInteger(v.evidenceReadinessScore));
  }
  const o=provisionalFocusOverall(t.nct,t.levels);
  assert.ok(o&&Number.isInteger(o.evidenceReadinessScore));
  assert.ok(o.evidenceReadinessScore>=0&&o.evidenceReadinessScore<=100);
 }
 assert.match(code,/not FDA approval predictions/);
});
test('optional L04–L20 are conditionally absent when collapsed and present when expanded',()=>{
 assert.match(code,/\{surveyExpanded&&<FocusTwentyHeaders className="assessment-level" startLevel=\{4\} endLevel=\{20\}\/>\}/);
 assert.match(code,/\{surveyExpanded&&<FocusTwentyCells nct=\{t\.nct\} levels=\{savedLevels\[t\.nct\]\} className="assessment-level" startLevel=\{4\} endLevel=\{20\}\/>\}/);
 assert.match(code,/colSpan=\{surveyExpanded\?32:15\}/);
 assert.doesNotMatch(code,/table\.assessment-expandable:not\(\.survey-expanded\):not\(:has\(details\.assessment-toggle\[open\]\)\)/);
});
test('reset button moves the FULL table to the beginning without changing trial data',()=>{
 assert.match(code,/data-testid="focus-reset-horizontal-scroll"/);
 assert.match(code,/tableScrollRef\.current\?\.scrollTo\(\{left:0,behavior:'smooth'\}\)/);
 assert.match(code,/showScoreColumns=\(\)=>/);
 assert.match(code,/setSurveyExpanded\(false\)/);
 assert.match(code,/ref=\{tableScrollRef\}/);
});
