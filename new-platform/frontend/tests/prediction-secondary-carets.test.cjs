const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const React = require("react");
const {create,act} = require("react-test-renderer");

for (const ext of [".ts",".tsx"]) require.extensions[ext] = (module,file) =>
  module._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true},
  }).outputText,file);
const {
  PREDICTION_METRICS, PRIMARY_PREDICTION_METRICS,
  SECONDARY_PREDICTION_GROUPS, proposedMetricValue,
} = require("../lib/prediction-priority-metrics.ts");
const {default:PredictionPriorityMetrics} = require("../app/PredictionPriorityMetrics.tsx");

test("all 60 ordered prediction metrics are preserved with explicit denominators",()=>{
  assert.equal(PREDICTION_METRICS.length,60);
  assert.equal(new Set(PREDICTION_METRICS.map(m=>m.label)).size,60);
  assert.deepEqual(PREDICTION_METRICS.map(x=>x.rank),Array.from({length:60},(_,i)=>i+1));
  assert.equal(PRIMARY_PREDICTION_METRICS.length,12);
  assert.equal(PRIMARY_PREDICTION_METRICS[0].label,"Primary endpoint success");
  assert.equal(PRIMARY_PREDICTION_METRICS[5].label,"Manufacturing and quality readiness (CMC)");
  assert.equal(PRIMARY_PREDICTION_METRICS[11].label,"Information available before prediction date");
  assert.deepEqual(SECONDARY_PREDICTION_GROUPS.map(g=>[g.start,g.end]),[[13,24],[25,36],[37,48],[49,60]]);
  assert.equal(SECONDARY_PREDICTION_GROUPS.reduce((n,g)=>n+g.end-g.start+1,0),48);
  assert.equal(proposedMetricValue(PREDICTION_METRICS[0]),"— / 100");
  assert.equal(proposedMetricValue(PREDICTION_METRICS[11]),"— / —");
  assert.equal(proposedMetricValue(PREDICTION_METRICS[32]),"Not validated");
});

test("primary twelve render directly, all secondary groups are closed native disclosure carets",async()=>{
  global.IS_REACT_ACT_ENVIRONMENT=true;
  let root;
  try{
    await act(async()=>{root=create(React.createElement(PredictionPriorityMetrics))});
    const details=root.root.findAllByType("details");
    assert.equal(details.length,4);
    for(const group of details)assert.equal(group.props.open,undefined);
    const catalog=root.root.findAllByType("table");
    assert.equal(catalog.length,5);
    const tbody0=catalog[0].findByType("tbody");
    assert.equal(tbody0.findAllByType("tr").length,12);
    for(let i=1;i<5;i++)assert.equal(catalog[i].findByType("tbody").findAllByType("tr").length,12);
    const headings=details.map(d=>d.findByType("summary").children.join(""));
    assert.match(headings[0],/#13–24/);
    assert.match(headings[3],/#49–60/);
    const rendered=JSON.stringify(root.toJSON());
    assert.match(rendered,/hidden by default/);
    assert.match(rendered,/not yet independently scored/);
    assert.doesNotMatch(rendered,/80% chance/);
  }finally{if(root)await act(async()=>root.unmount())}
});

test("existing scored metric evidence is retained but moved behind a closed caret",()=>{
  const ui=fs.readFileSync(path.join(__dirname,"../app/NumericForecastMetrics.tsx"),"utf8");
  assert.match(ui,/<PredictionPriorityMetrics\s*\/>/);
  assert.match(ui,/primaryCards = cards\.slice\(0,4\)/);
  assert.match(ui,/secondaryCards = cards\.slice\(4\)/);
  assert.match(ui,/Existing research scores — 7 metrics/);
  assert.match(ui,/Additional research and readiness metrics — 4 items/);
  assert.match(ui,/Historical comparable scoring/);
  assert.match(ui,/FDA approval probability: — \/ 100% \(not validated\)/);
  assert.equal((ui.match(/<details/g)||[]).length,3);
  assert.equal((ui.match(/<\/details>/g)||[]).length,3);
  assert.doesNotMatch(ui,/<details[^>]*\sopen(?:\s|>|=)/);
  assert.doesNotMatch(ui,/fetch\(|\bPUT\b|\bPOST\b|\bonClick=/);
});
