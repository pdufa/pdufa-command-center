const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
const TestRenderer=require("react-test-renderer");
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);
const data=require("../data/historicalMonthlyLevelRuns2026.json");
const Chart=require("../app/HistoricalMonthlyLevelTrend.tsx").default;

const expected={
  "2026-06":{matches:15,total:17,baseline:13,color:"#2167B0"},
  "2026-07":{matches:8,total:9,baseline:7,color:"#C05249"},
  "2026-08":{matches:10,total:10,baseline:10,color:"#8655B8"},
  "2026-09":{matches:19,total:20,baseline:20,color:"#B47D14"},
  "2026-10":{matches:16,total:17,baseline:17,color:"#0B827B"}
};

test("June–October Level 3 source-linked monthly cohorts preserve denominator and unique month color",()=>{
  assert.equal(data.schemaVersion,1);
  assert.equal(data.methodGuardrails.notLiveAccuracy,true);
  assert.equal(data.methodGuardrails.validatedBlindPredictionCount,0);
  assert.equal(data.methodGuardrails.validBlindAccuracy,null);
  assert.equal(data.methodGuardrails.cohortsNotPopulationComparable,true);
  assert.equal(data.cohorts.length,5);
  assert.equal(data.runs.length,5);
  assert.equal(new Set(data.cohorts.map(c=>c.color)).size,5);
  assert.deepEqual(data.cohorts.map(c=>c.yearMonth),Object.keys(expected));
  for(const cohort of data.cohorts){
    const e=expected[cohort.yearMonth];
    const run=data.runs.find(r=>r.cohortId===cohort.cohortId);
    assert.ok(run);
    assert.equal(run.assessmentLevel,3);
    assert.equal(run.methodVersion,"MANUAL_LEVEL3_RECONSTRUCTION_V1");
    assert.equal(run.assessmentBlind,false);
    assert.equal(run.priorOutcomeExposure,true);
    assert.equal(run.validatedBlindCases,0);
    assert.equal(run.validatedBlindAccuracy,null);
    assert.equal(run.comparisonType,"RETROSPECTIVE_DIRECTIONAL_AGREEMENT_ONLY");
    assert.equal(cohort.color,e.color);
    assert.equal(cohort.benchmarkCaseIds.length,e.total);
    assert.equal(cohort.alwaysApproveMatches,e.baseline);
    assert.equal(cohort.benchmarkCaseIds.length,new Set(cohort.benchmarkCaseIds).size);
    assert.equal(run.caseCalls.length,e.total);
    assert.equal(new Set(run.caseCalls.map(c=>c.caseId)).size,e.total);
    const outcomes=new Map(cohort.benchmarkCases.map(c=>[c.id,c.actualDecision]));
    assert.equal(run.caseCalls.filter(c=>c.call===outcomes.get(c.caseId)).length,e.matches);
    assert.ok(cohort.sourceUrl.startsWith("https://github.com/"));
    assert.ok(run.predictionFreezeUrl.startsWith("https://github.com/"));
  }
});

test("Rendered monthly line chart identifies all five differently colored months, Level 3 and nonblind rates",()=>{
  const html=renderToStaticMarkup(React.createElement(Chart));
  assert.match(html,/data-testid="historical-monthly-level-trend"/);
  assert.match(html,/data-testid="historical-monthly-level-line-chart"/);
  assert.match(html,/data-testid="historical-monthly-level-table"/);
  assert.match(html,/data-testid="historical-level-tag-3"/);
  assert.match(html,/data-testid="historical-assessment-level-dropdown"/);
  assert.match(html,/id="historical-assessment-level-select"/);
  assert.match(html,/Level 4 — not yet assessed/);
  assert.match(html,/Compare all recorded levels/);
  assert.match(html,/Displaying Level 3 historical assessment results/);
  assert.match(html,/data-testid="level-line-3"/);
  for(const [month,{color}] of Object.entries(expected)){
    assert.ok(html.includes('data-testid="month-color-'+month+'"'));
    assert.ok(html.includes(color));
  }
  for(const rate of ["88.2%","88.9%","100.0%","95.0%","94.1%"])assert.ok(html.includes(rate),rate);
  assert.match(html,/Blind accuracy: N\/A/);
  assert.match(html,/not blind prediction accuracy/i);
  assert.match(html,/never added to/i);
});

test("Level dropdown switches to new Level 4 and compares it against retained Level 3",()=>{
  const extra={...data.runs[0],runId:"TEST_LEVEL4_JUNE",assessmentLevel:4,
    methodVersion:"REPLAY_TEST_V1",caseCalls:data.runs[0].caseCalls.map(c=>({...c}))};
  data.runs.push(extra);
  let renderer=null;
  try{
    TestRenderer.act(()=>{renderer=TestRenderer.create(React.createElement(Chart))});
    let html=JSON.stringify(renderer.toJSON());
    assert.match(html,/level-line-3/);
    assert.doesNotMatch(html,/level-line-4/);
    const select=renderer.root.findByProps({"data-testid":"historical-assessment-level-dropdown"});
    assert.equal(select.props.value,"3");
    TestRenderer.act(()=>select.props.onChange({currentTarget:{value:"4"}}));
    html=JSON.stringify(renderer.toJSON());
    assert.match(html,/level-line-4/);
    assert.doesNotMatch(html,/level-line-3/);
    assert.match(html,/historical-level-tag-4/);
    assert.match(html,/Level 4 historical assessment results/);
    TestRenderer.act(()=>select.props.onChange({currentTarget:{value:"all"}}));
    html=JSON.stringify(renderer.toJSON());
    assert.match(html,/level-line-3/);
    assert.match(html,/level-line-4/);
    assert.match(html,/strokeDasharray/);
    assert.match(html,/Comparing all recorded historical assessment levels/);
  }finally{
    if(renderer){TestRenderer.act(()=>renderer.unmount())}
    data.runs.pop();
  }
});

test("Changed case identity cannot silently improve a future level's denominator",()=>{
  const extra={...data.runs[0],runId:"TEST_LEVEL4_BAD",assessmentLevel:4,
    methodVersion:"REPLAY_TEST_V1",caseCalls:data.runs[0].caseCalls.map(c=>({...c}))};
  extra.caseCalls[0].caseId="WRONG_CASE";
  data.runs.push(extra);
  try{
    assert.throws(()=>renderToStaticMarkup(React.createElement(Chart)),
      /MUST_USE_FIXED_CASE_IDS/);
  }finally{data.runs.pop();}
});

test("The five-month line chart is mounted on the assessment dashboard",()=>{
  const page=fs.readFileSync(path.join(__dirname,"../app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/import HistoricalMonthlyLevelTrend from/);
  assert.match(page,/<HistoricalMonthlyLevelTrend\/>/);
});
