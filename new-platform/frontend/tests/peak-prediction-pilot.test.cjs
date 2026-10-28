const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,file);

const {
  PEAK_PILOT,PEAK_SOURCES,PEAK_PILOT_METRICS,PEAK_HISTORICAL_PRECEDENTS,
  PEAK_SOURCE_COVERAGE,validatePeakPilot
}=require("../lib/peak-prediction-pilot.ts");
const {SECONDARY_PREDICTION_GROUPS,PREDICTION_METRICS}=require("../lib/prediction-priority-metrics.ts");

test("legacy GEM PEAK identity and reported figures remain internally consistent without certifying source truth",()=>{
  assert.doesNotThrow(validatePeakPilot);
  assert.equal(PEAK_PILOT.stage,"GEM");
  assert.equal(PEAK_PILOT.nctId,"NCT05208047");
  assert.equal(PEAK_PILOT.exactPipelineId,"APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130");
  assert.equal(PEAK_PILOT.pdufaDate,"2026-11-30");
  assert.equal(PEAK_PILOT.snapshotDate,"2026-10-26");
  assert.equal(PEAK_PILOT.randomizedPatients,413);
  assert.equal(PEAK_PILOT.combinationN,204);
  assert.equal(PEAK_PILOT.activeControlN,209);
  assert.equal(PEAK_PILOT.medianPfsCombinationMonths-PEAK_PILOT.medianPfsControlMonths,7.300000000000001);
  assert.equal(PEAK_PILOT.hazardRatioPfs,0.5);
  assert.deepEqual([PEAK_PILOT.hazardRatioLow95,PEAK_PILOT.hazardRatioHigh95],[0.39,0.65]);
  assert.equal(PEAK_PILOT.orrCombinationPct-PEAK_PILOT.orrControlPct,20);
  assert.equal(PEAK_PILOT.grade3LiverEnzymeCombinationPct,10.8);
  assert.equal(PEAK_PILOT.grade3LiverEnzymeControlPct,1.4);
});

test("all 12 named metric observations show real values, partial boundaries or explicit gaps",()=>{
  assert.equal(PEAK_PILOT_METRICS.length,12);
  assert.equal(PEAK_SOURCE_COVERAGE.directlyReported,7);
  assert.equal(PEAK_SOURCE_COVERAGE.partiallyReviewed,2);
  assert.equal(PEAK_SOURCE_COVERAGE.notReviewed,3);
  PEAK_PILOT_METRICS.forEach((x,i)=>{
    assert.equal(x.rank,i+1);
    assert.equal(x.label,PREDICTION_METRICS[i].label);
    if(x.status==="NOT_REVIEWED"){assert.equal(x.observed,"—");assert.equal(x.source,null)}
    if(x.source)assert.ok(PEAK_SOURCES[x.source].url.startsWith("https://"));
  });
  assert.match(PEAK_PILOT_METRICS[4].observed,/0 treatment-related deaths/);
  assert.match(PEAK_PILOT_METRICS[4].note,/cannot infer/i);
  assert.equal(PREDICTION_METRICS.length,60);
  assert.equal(SECONDARY_PREDICTION_GROUPS.length,4);
});

test("historical examples have dated decision outcomes, but remain ineligible for FDA probability calibration",()=>{
  assert.equal(PEAK_HISTORICAL_PRECEDENTS.length,3);
  assert.equal(PEAK_PILOT.researchedHistoricalPrecedents,3);
  assert.equal(PEAK_PILOT.modelEligibleHistoricalCases,0);
  assert.deepEqual(PEAK_HISTORICAL_PRECEDENTS.map(x=>x.drug),["Sunitinib","Regorafenib","Ripretinib"]);
  assert.ok(PEAK_HISTORICAL_PRECEDENTS.every(x=>/FDA approved/.test(x.outcome)));
  assert.ok(PEAK_HISTORICAL_PRECEDENTS.every(x=>x.qualification.includes("but")||x.qualification.includes("different")));
});

test("the pilot route displays the saved first-case result and keeps historical and legacy details closed",async()=>{
  global.IS_REACT_ACT_ENVIRONMENT=true;
  const Page=require("../app/prediction-pilot/page.tsx").default;
  let root;
  try{
    await act(async()=>{root=create(React.createElement(Page))});
    let json=JSON.stringify(root.toJSON());
    assert.match(json,/Bezuclastinib/);
    assert.match(json,/NCT05208047/);
    assert.match(json,/Nov/);
    assert.match(json,/0.50/);
    assert.match(json,/7.3 mo/);
    assert.match(json,/10.8% \/ 1.4%/);
    assert.match(json,/NOT VALIDATED/);
    assert.match(json,/INDETERMINATE/);
    assert.match(json,/PEAK-NCT05208047-20261027-research-001/);
    assert.match(json,/CGT9486-21-301/);
    assert.match(json,/2026-10-27T23:19:59Z/);
    assert.ok(json.includes('"7","/12"'));
    const details=root.root.findAllByType("details");
    details.forEach(d=>assert.equal(d.props.open,undefined));
    const saved=root.root.findAllByProps({"aria-label":"Persisted trial assessment"})[0];
    assert.ok(saved);
    const earlier=root.root.findAllByProps({"aria-label":"Earlier frozen manual pilot preview"})[0];
    assert.equal(earlier.type,"details");
    assert.equal(earlier.props.open,undefined);
    const metricSection=root.root.findAllByProps({"aria-label":"Twelve primary prediction factors"})[0];
    assert.ok(metricSection);
    assert.equal(metricSection.findByType("tbody").findAllByType("tr").length,12);
    for(const group of SECONDARY_PREDICTION_GROUPS){
      const disclosure=details.find(d=>d.findAllByType("summary")[0]?.children.join("").startsWith(group.title));
      assert.ok(disclosure);
      assert.equal(disclosure.findByType("tbody").findAllByType("tr").length,12);
    }
    assert.doesNotMatch(json,/100% probability of approval/);
  }finally{if(root)await act(async()=>root.unmount())}
});

test("pilot route never mutates saved scores, historical cohort, FS FA presets or trades",()=>{
  const page=fs.readFileSync(path.join(__dirname,"../app/prediction-pilot/page.tsx"),"utf8");
  const data=fs.readFileSync(path.join(__dirname,"../lib/peak-prediction-pilot.ts"),"utf8");
  for(const s of [page,data]) {
    assert.doesNotMatch(s,/fetch\(|\bPUT\b|\bPOST\b|\bonClick=|\bonSubmit=|ordersEnabled:\s*true/);
    assert.match(s,/research|Research/);
  }
  assert.match(page,/force-static/);
  assert.match(page,/read-only|Read-only/i);
  const workspace=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
  assert.match(workspace,/href="\/prediction-pilot"[^>]*>FIRST TRIAL ASSESSMENT<\/a>/);
});
