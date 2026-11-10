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
function flattenedText(node){
  if(typeof node==="string"||typeof node==="number")return String(node);
  if(Array.isArray(node))return node.map(flattenedText).join("");
  return node&&node.children?flattenedText(node.children):"";
}

const expected=[
 ["2026-01","January",6,7,4,"#0B65E5"],
 ["2026-02","February",8,8,7,"#159447"],
 ["2026-03","March",6,6,5,"#C58A00"],
 ["2026-04","April",8,8,6,"#E46B15"],
 ["2026-05","May",4,4,3,"#DA345B"],
 ["2026-06","June",15,17,13,"#2167B0"],
 ["2026-07","July",8,9,7,"#C05249"],
 ["2026-08","August",10,10,10,"#8655B8"],
 ["2026-09","September",19,20,20,"#B47D14"],
 ["2026-10","October",16,17,17,"#0B827B"]
];

test("Jan–Oct v2 historical cohorts carry 106 fixed cases, 100 matches, and ten distinct month colors",()=>{
  assert.equal(data.schemaVersion,2);
  assert.equal(data.dataset,"HISTORICAL_MONTHLY_LEVEL_COMPARISONS_2026_V2");
  assert.equal(data.methodGuardrails.notLiveAccuracy,true);
  assert.equal(data.methodGuardrails.validatedBlindPredictionCount,0);
  assert.equal(data.methodGuardrails.validBlindAccuracy,null);
  assert.equal(data.methodGuardrails.doNotPromoteHistoricalToLiveAccuracy,true);
  assert.equal(data.methodGuardrails.cohortsNotPopulationComparable,true);
  assert.equal(data.cohorts.length,10);
  assert.equal(data.runs.length,10);
  assert.equal(new Set(data.cohorts.map(c=>c.color.toLowerCase())).size,10);
  assert.equal(new Set(data.cohorts.map(c=>c.cohortId)).size,10);
  let matched=0,total=0,always=0;
  for(const [i,[month,name,correct,count,baseline,color]] of expected.entries()){
    const c=data.cohorts[i],run=data.runs.find(r=>r.cohortId===c.cohortId);
    assert.equal(c.yearMonth,month);
    assert.equal(c.monthLabel,name);
    assert.equal(c.color,color);
    assert.equal(c.benchmarkCases.length,count);
    assert.equal(c.benchmarkCaseIds.length,count);
    assert.equal(new Set(c.benchmarkCaseIds).size,count);
    assert.equal(c.alwaysApproveMatches,baseline);
    assert.equal(c.sourceListedCount,c.benchmarkCases.length+c.excludedCases.length);
    assert.ok(c.sourceUrl.startsWith("https://github.com/"));
    assert.ok(c.sourceBlobSha);
    assert.ok(run);
    assert.equal(run.assessmentLevel,3);
    assert.equal(run.assessmentBlind,false);
    assert.equal(run.priorOutcomeExposure,true);
    assert.equal(run.validatedBlindAccuracy,null);
    assert.equal(run.validatedBlindCases,0);
    assert.ok(run.methodVersion);
    assert.ok(run.predictionFreezeUrl.startsWith("https://github.com/"));
    assert.equal(run.caseCalls.length,count);
    const caseMap=new Map(c.benchmarkCases.map(x=>[x.id,x.actualDecision]));
    assert.equal(new Set(run.caseCalls.map(x=>x.caseId)).size,count);
    assert.equal(run.caseCalls.filter(x=>x.call===caseMap.get(x.caseId)).length,correct);
    matched+=correct;total+=count;always+=baseline;
  }
  assert.equal(matched,100);
  assert.equal(total,106);
  assert.equal(always,92);
});

test("Level 3 default drives old-prediction summary, cumulative weighted graph and table, never blind accuracy",()=>{
  const html=renderToStaticMarkup(React.createElement(Chart));
  for(const key of ["historical-monthly-level-trend","historical-monthly-level-line-chart",
    "historical-monthly-level-table","historical-level-summary-3","historical-level-rate-3",
    "historical-assessment-level-dropdown","historical-pdufa-year-dropdown",
    "historical-level-year-controls","historical-level-tag-3"]){
    assert.match(html,new RegExp('data-testid="'+key+'"'));
  }
  assert.match(html,/100 \/ 106 matched/);
  assert.match(html,/94\.3%/);
  assert.match(html,/Cumulative FDA agreement trend/);
  assert.match(html,/case-count-weighted cumulative trend/);
  assert.match(html,/not genuine blind accuracy/i);
  assert.match(html,/VERIFIED BLIND ACCURACY/);
  assert.match(html,/Level 4 — not assessed/);
  assert.match(html,/Compare all recorded levels/);
  assert.match(html,/Displaying Level 3 results for PDUFA 2026/);
  assert.match(html,/PDUFA Year/);
  assert.match(html,/id="historical-pdufa-year-select"/);
  assert.match(html,/Cumulative FDA agreement trend · Jan–Oct 2026/);
  for(const [month,name,,,color] of expected){
    assert.match(html,new RegExp('data-testid="month-color-'+month+'"'));
    assert.ok(html.includes(name));
    assert.ok(html.includes(color));
  }
  for(const fragment of ["85.7%","88.2%","88.9%","95.0%","94.1%"]){
    assert.ok(html.includes(fragment),fragment+" monthly value absent");
  }
});

test("PDUFA Year dropdown filters the table, annual cumulative trend and totals without altering 2026",()=>{
  const june=data.cohorts[5],run=data.runs[5];
  const prefix="TEST_2027_";
  const fresh={
    ...june,cohortId:"historical-2027-01-v1",
    yearMonth:"2027-01",monthLabel:"January",color:"#345DAA",
    benchmarkCaseIds:june.benchmarkCaseIds.map(id=>prefix+id),
    benchmarkCases:june.benchmarkCases.map(x=>({...x,id:prefix+x.id}))
  };
  const nextRun={
    ...run,cohortId:fresh.cohortId,runId:"TEST_LEVEL3_2027_JANUARY",
    caseCalls:run.caseCalls.map(x=>({...x,caseId:prefix+x.caseId}))
  };
  data.cohorts.push(fresh);
  data.runs.push(nextRun);
  let renderer=null;
  try{
    TestRenderer.act(()=>{renderer=TestRenderer.create(React.createElement(Chart))});
    const yearControl=renderer.root.findByProps({"data-testid":"historical-pdufa-year-dropdown"});
    const levelControl=renderer.root.findByProps({"data-testid":"historical-assessment-level-dropdown"});
    assert.equal(yearControl.props.value,"2026");
    assert.equal(levelControl.props.value,"3");
    let html=JSON.stringify(renderer.toJSON());
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/100 \/ 106 matched/);
    assert.match(html,/2027/); // The new recorded year becomes selectable.
    TestRenderer.act(()=>yearControl.props.onChange({currentTarget:{value:"2027"}}));
    html=JSON.stringify(renderer.toJSON());
    assert.equal(yearControl.props.value,"2027");
    assert.equal(levelControl.props.value,"3");
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/15 \/ 17 matched/);
    assert.match(html,/88\.2%/);
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/1 \/ 1 months assessed/);
    assert.doesNotMatch(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/100 \/ 106 matched/);
    assert.match(html,/historical-monthly-level-table/);
    assert.match(html,/2027-01/);
    assert.doesNotMatch(html,/month-color-2026-01/);
    assert.match(html,/Cumulative FDA agreement trend/);
    TestRenderer.act(()=>yearControl.props.onChange({currentTarget:{value:"2026"}}));
    html=JSON.stringify(renderer.toJSON());
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/100 \/ 106 matched/);
    assert.doesNotMatch(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/15 \/ 17 matched/);
  }finally{
    if(renderer)TestRenderer.act(()=>renderer.unmount());
    data.runs.pop();
    data.cohorts.pop();
  }
});

test("Year dropdown is not populated from an unassessed cohort, and future years do not invent scores",()=>{
  const extra={...data.cohorts[5],
    cohortId:"historical-2027-01-v1",yearMonth:"2027-01",color:"#345DAA"};
  data.cohorts.push(extra);
  try{
    const html=renderToStaticMarkup(React.createElement(Chart));
    assert.match(html,/id="historical-pdufa-year-select"/);
    assert.doesNotMatch(html,/<option[^>]*value="2027"/);
    assert.match(html,/100 \/ 106 matched/);
  }finally{data.cohorts.pop();}
});

test("Level 4 addition updates all history widgets and compare-all without changing saved Level 3",()=>{
  const baseline=data.runs[5]; // June Level 3
  const extra={...baseline,runId:"TEST-L4-JUNE",assessmentLevel:4,
    revisionNumber:1,methodVersion:"REPLAY_LEVEL4_V1",
    caseCalls:baseline.caseCalls.map(x=>({...x}))};
  // Deliberately turn a matched June case into a miss.
  const c=data.cohorts[5],outcomes=new Map(c.benchmarkCases.map(x=>[x.id,x.actualDecision]));
  const matched=extra.caseCalls.find(x=>x.call===outcomes.get(x.caseId));
  assert.ok(matched);
  matched.call=matched.call==="APPROVAL"?"CRL":"APPROVAL";
  data.runs.push(extra);
  let renderer=null;
  try{
    TestRenderer.act(()=>{renderer=TestRenderer.create(React.createElement(Chart));});
    let html=JSON.stringify(renderer.toJSON());
    assert.match(html,/historical-level-summary-3/);
    assert.doesNotMatch(html,/historical-level-summary-4/);
    const select=renderer.root.findByProps({"data-testid":"historical-assessment-level-dropdown"});
    assert.equal(select.props.value,"3");
    TestRenderer.act(()=>select.props.onChange({currentTarget:{value:"4"}}));
    html=JSON.stringify(renderer.toJSON());
    assert.match(html,/historical-level-summary-4/);
    assert.doesNotMatch(html,/historical-level-summary-3/);
    assert.match(html,/level-line-4/);
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-4"})),/14 \/ 17 matched/);
    assert.match(html,/82\.4%/);
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-4"})),/1 \/ 10 months assessed/);
    assert.match(html,/Level 4 results/);
    TestRenderer.act(()=>select.props.onChange({currentTarget:{value:"all"}}));
    html=JSON.stringify(renderer.toJSON());
    assert.match(html,/historical-level-summary-3/);
    assert.match(html,/historical-level-summary-4/);
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-3"})),/100 \/ 106 matched/);
    assert.match(flattenedText(renderer.root.findByProps({"data-testid":"historical-level-summary-4"})),/14 \/ 17 matched/);
    assert.match(html,/level-line-3/);
    assert.match(html,/level-line-4/);
  }finally{
    if(renderer)TestRenderer.act(()=>renderer.unmount());
    data.runs.pop();
  }
});

test("Tampered cohort identity in a later level raises rather than changing comparison denominator",()=>{
  const baseline=data.runs[5];
  const extra={...baseline,runId:"TEST-L4-TAMPER",assessmentLevel:4,
    methodVersion:"BAD_TEST",caseCalls:baseline.caseCalls.map(x=>({...x}))};
  extra.caseCalls[0].caseId="NOT_A_LOCKED_CASE";
  data.runs.push(extra);
  try{
    assert.throws(()=>renderToStaticMarkup(React.createElement(Chart)),/MUST_USE_FIXED_CASE_IDS/);
  }finally{data.runs.pop();}
});

test("A later Level 3 revision changes its display but preserves original run and case population",()=>{
  const baseline=data.runs[5];
  const updated={...baseline,runId:"TEST-L3-JUNE-REV2",revisionNumber:2,
    methodVersion:"LEVEL3_REVISED_TEST",runDate:"2026-11-10",
    caseCalls:baseline.caseCalls.map(x=>({...x}))};
  const c=data.cohorts[5],outcomes=new Map(c.benchmarkCases.map(x=>[x.id,x.actualDecision]));
  const miss=updated.caseCalls.find(x=>x.call!==outcomes.get(x.caseId));
  assert.ok(miss);
  miss.call=outcomes.get(miss.caseId);
  data.runs.push(updated);
  try{
    const html=renderToStaticMarkup(React.createElement(Chart));
    assert.match(html,/101 \/ 106 matched/);
    assert.match(html,/95\.3%/);
    assert.match(html,/LEVEL3_REVISED_TEST/);
    assert.equal(baseline.revisionNumber,undefined);
  }finally{data.runs.pop();}
});

test("Page separates historical selected-level panel from future validated predictions and fixed archives",()=>{
  const page=fs.readFileSync(path.join(__dirname,"../app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<HistoricalMonthlyLevelTrend\/>/);
  assert.match(page,/FUTURE PREDICTIONS · LIVE \/ PROSPECTIVE/);
  assert.match(page,/<AssessmentStatusPies \{\.\.\.pies\}\/>/);
  assert.match(page,/data-testid="fixed-historical-level-3-archives"/);
  assert.ok(page.indexOf("<HistoricalMonthlyLevelTrend/>")<page.indexOf("<AssessmentStatusPies"));
  const scale=fs.readFileSync(path.join(__dirname,"../app/AssessmentLevelChart.tsx"),"utf8");
  assert.match(scale,/MAX_PLANNED_ASSESSMENT_LEVEL=20/);
  assert.match(scale,/row.level\/MAX_PLANNED_ASSESSMENT_LEVEL/);
  const prospective=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/fdaPredictionDecisionAudit.json"),"utf8"));
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.equal(prospective.records[0].actualDecisionVerified,false);
});

test("Full ten-month trend renders a mobile-safe polyline and visible cumulative legend",()=>{
  const html=renderToStaticMarkup(React.createElement(Chart));
  assert.match(html,/data-testid="historical-mobile-trend-line-chart"/);
  assert.match(html,/data-testid="mobile-cumulative-path-3"/);
  assert.match(html,/data-testid="historical-trend-key"/);
  assert.match(html,/Solid green line = cumulative historical agreement/);
  assert.match(html,/100 \/ 106 matched/);
  const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
  assert.match(css,/@media \(max-width: 650px\)/);
  assert.match(css,/\.historical-trend-desktop \{ display: none !important/);
  assert.match(css,/\.historical-trend-mobile \{ display: block !important/);
  assert.doesNotMatch(html,/min-width:650px/);
});

test("Predictions tab shows compact cumulative trend above the source roster; assessments retains full chart",()=>{
  const page=fs.readFileSync(path.join(__dirname,"../app/predictions/page.tsx"),"utf8");
  assert.match(page,/import HistoricalMonthlyLevelTrend/);
  assert.match(page,/<HistoricalMonthlyLevelTrend compact\/>/);
  assert.ok(page.indexOf("<HistoricalMonthlyLevelTrend compact/>")<page.indexOf("<FullRosterSourceScan/>"));
  const html=renderToStaticMarkup(React.createElement(Chart,{compact:true}));
  assert.match(html,/data-testid="historical-mobile-trend-line-chart"/);
  assert.match(html,/Full Level 3–20 historical chart/);
  assert.doesNotMatch(html,/data-testid="historical-monthly-level-table"/);
  assert.match(html,/100 of 106 retrospective matches/);
  const full=renderToStaticMarkup(React.createElement(Chart));
  assert.match(full,/id="historical-performance"/);
  assert.match(full,/data-testid="historical-monthly-level-table"/);
});
