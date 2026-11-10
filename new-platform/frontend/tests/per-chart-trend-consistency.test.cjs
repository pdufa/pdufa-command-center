const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);
require.extensions[".ts"]=require.extensions[".tsx"];
const {default:Trend,cumulativeDatedAgreement}=require("../app/ChartTrendInset.tsx");

test("In-card trend is a real chronological cumulative line from separately dated decisions",()=>{
  const points=cumulativeDatedAgreement([
    {date:"2026-10-21",matched:false},
    {date:"2026-10-07",matched:true},
    {date:"2026-10-20",matched:true},
    {date:"2026-10-07",matched:true},
    {date:null,matched:true},
    {date:"2026-10-30",matched:null}
  ]);
  assert.deepEqual(points.map(p=>[p.at,p.value.toFixed(1)]),[
    ["2026-10-07","100.0"],
    ["2026-10-20","100.0"],
    ["2026-10-21","75.0"]
  ]);
  const html=renderToStaticMarkup(React.createElement(Trend,{
    testId:"example-historic-trend",title:"Historical cumulative direction",points,kind:"retrospective",emptyText:""
  }));
  assert.match(html,/data-testid="example-historic-trend-line"/);
  assert.match(html,/data-testid="example-historic-trend-best-fit"/);
  assert.doesNotMatch(html,/<polyline/);
  assert.match(html,/least-squares/i);
  assert.match(html,/75\.0%/);
  assert.match(html,/NOT BLIND/);
  assert.match(html,/not blind accuracy/i);
});

test("Missing, same-day, or single observations never create a synthetic trend line",()=>{
  const tests=[
    [],
    [{at:"2026-10-21",value:100}],
    [{at:"2026-10-21",value:100},{at:"2026-10-21",value:0}],
    [{at:"garbage",value:91}],
    [{at:"2026-10-21",value:200},{at:"2026-10-22",value:50}]
  ];
  for(const points of tests){
    const html=renderToStaticMarkup(React.createElement(Trend,{
      testId:"example-no-trend",title:"Prospective",points,kind:"prospective",
      emptyText:"Requires more verified decisions."
    }));
    assert.match(html,/data-testid="example-no-trend-empty"/);
    assert.doesNotMatch(html,/<polyline/);
    assert.match(html,/No trend line available yet/);
  }
});

test("Archived FDA chart data produces separate lines while one-case archive remains honest",()=>{
  const historical=require("../data/levelThreeOutcomeAwareRerunComparison2026.json");
  const four=cumulativeDatedAgreement(historical.caseComparisons.map(x=>({
    date:x.fdaActionDate,matched:x.didMatch
  })));
  assert.ok(four.length>=2);
  const october=require("../data/october2026RetrospectiveFdaComparison.json");
  const results=cumulativeDatedAgreement(october.cases.map(x=>({
    date:x.actualFdaActionDate??x.decisionAnnouncementDate??null,matched:x.sameDirection
  })));
  assert.ok(results.length>=2);
  const last=results.at(-1);
  assert.equal(last.value,100*16/17);
  const one=cumulativeDatedAgreement([{date:"2026-10-21",matched:true}]);
  assert.equal(one.length,1);
  const noLine=renderToStaticMarkup(React.createElement(Trend,{
    testId:"azn-single",title:"AZN one case",points:one,kind:"retrospective",
    emptyText:"Single case"
  }));
  assert.match(noLine,/data-testid="azn-single-empty"/);
});

test("Every comparison snapshot chart on the Predictions/Assessments pages owns a trend area",()=>{
  const read=name=>fs.readFileSync(path.join(__dirname,"../app",name),"utf8");
  const cases={
    "AssessmentStatusPies.tsx":["overall-accuracy-pie-trend","latest-prediction-pie-trend"],
    "AssessmentLevelChart.tsx":["trial-analysis-depth-trend"],
    "HistoricalTestingChart.tsx":["four-case-historical-donut-trend"],
    "October2026HistoricalAuditPanel.tsx":["october-historical-donut-trend"],
    "UltomirisHistoricalLevelThreePanel.tsx":["azn-historical-single-case-trend"],
    "HistoricalMonthlyLevelTrend.tsx":["historical-monthly-level-line-chart","historical-mobile-trend-line-chart"],
    "AssessmentTrendLines.tsx":["overall-accuracy-line","latest-outlook-line"]
  };
  for(const [file,ids] of Object.entries(cases)){
    const s=read(file);
    for(const id of ids)assert.ok(s.includes(id),file+" missing "+id);
  }
  const routes=read("predictions/page.tsx");
  const assessment=read("predictions/assessment/page.tsx");
  assert.match(routes,/<HistoricalMonthlyLevelTrend compact\/>/);
  for(const c of ["HistoricalMonthlyLevelTrend","AssessmentStatusPies","AssessmentLevelChart",
    "HistoricalTestingChart","October2026HistoricalAuditPanel","UltomirisHistoricalLevelThreePanel"]){
    assert.ok(assessment.includes("<"+c),"Unconnected chart "+c);
  }
});
