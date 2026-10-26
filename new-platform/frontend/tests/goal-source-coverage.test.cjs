const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,
  }}).outputText,file);
require.extensions[".css"]=module=>{module.exports=new Proxy({}, {get:(_x,key)=>String(key)});};
const {goalSourceCoverage}=require("../lib/goal-source-coverage.ts");
const Panel=require("../app/GoalSourceCoverage.tsx").default;
const url="https://github.com/pdufa/pdufa-command-center/actions/runs/40057578041";
const scan={date:"2026-10-23",today:true,status:"PARTIAL",runId:40057578041,runUrl:url};
const report=()=>({
  latest_run_id:"40057578041",latest_run_url:url,execution_status:"COMPLETE",
  full_coverage_verified:false,
  findings_due:1121,findings_verified:995,findings_unresolved:23,
  findings_unavailable:93,findings_not_applicable:10,
  missing_required_source_families:["FDA","SEC","FINANCIAL"],
});

test("GOAL shows same-run source findings distinctly from clinical program counts",()=>{
  const audit=goalSourceCoverage(report(),scan);
  assert.ok(audit);
  assert.equal(audit.due,1121);
  assert.equal(audit.verified,995);
  assert.equal(audit.unresolved,23);
  assert.equal(audit.unavailable,93);
  assert.equal(audit.notApplicable,10);
  assert.equal(audit.coveragePercent,88.8);
  assert.deepEqual(audit.missingRequired,["FDA","SEC","FINANCIAL"]);
  assert.equal(audit.fullCoverage,false);
  assert.equal(audit.runUrl,url);
  assert.equal(audit.today,true);
  assert.equal(goalSourceCoverage(report(),{...scan,today:false}).today,false);
});

test("GOAL refuses another run, mismatched URLs, malformed counts and untrusted source families",()=>{
  const run=report();run.latest_run_id="40057578040";
  assert.equal(goalSourceCoverage(run,scan),null);
  const badUrl=report();badUrl.latest_run_url="https://evil.example/reports/40057578041";
  assert.equal(goalSourceCoverage(badUrl,scan),null);
  const wrongTotal=report();wrongTotal.findings_due=1120;
  assert.equal(goalSourceCoverage(wrongTotal,scan),null);
  const negative=report();negative.findings_unresolved=-1;
  assert.equal(goalSourceCoverage(negative,scan),null);
  const missing=report();delete missing.findings_unavailable;
  assert.equal(goalSourceCoverage(missing,scan),null);
  const fakeComplete=report();fakeComplete.full_coverage_verified=true;
  assert.equal(goalSourceCoverage(fakeComplete,scan),null);
  const unknown=report();unknown.execution_status="RUNNING";
  assert.equal(goalSourceCoverage(unknown,scan),null);
  const names=report();names.missing_required_source_families=["FDA","<img src=x>"];
  assert.equal(goalSourceCoverage(names,scan),null);
  const duplicates=report();duplicates.missing_required_source_families=["FDA","FDA"];
  assert.equal(goalSourceCoverage(duplicates,scan),null);
  assert.equal(goalSourceCoverage(report(),{...scan,status:"RUN_FAILED"}),null);
  assert.equal(goalSourceCoverage(report(),null),null);
  assert.equal(goalSourceCoverage(null,scan),null);
});

test("A complete source ledger cannot authorize a trade",()=>{
  const full=report();
  full.findings_verified=1111;
  full.findings_unresolved=0;
  full.findings_unavailable=0;
  full.full_coverage_verified=true;
  full.missing_required_source_families=[];
  const audit=goalSourceCoverage(full,scan);
  assert.equal(audit.fullCoverage,true);
  assert.equal(audit.notApplicable,10);
  assert.equal(audit.coveragePercent,99.1);
});

test("GOAL shows source audit as a read-only expandable mobile panel",async()=>{
  let view;
  try{
    await act(async()=>{view=create(React.createElement(Panel,{source:report(),scan,loading:false}));});
    const json=JSON.stringify(view.toJSON());
    assert.match(json,/Published coverage partial/);
    assert.match(json,/995/);
    assert.match(json,/1,121/);
    assert.match(json,/88.8/);
    assert.match(json,/of due findings/);
    assert.match(json,/Required source families still missing: FDA, SEC, FINANCIAL/);
    assert.match(json,/Full source coverage NOT verified/);
    assert.match(json,/source findings, not/);
    assert.match(json,/numbers of clinical trials/);
    const links=view.root.findAllByType("a");
    assert.equal(links.length,1);
    assert.equal(links[0].props.href,url);
    assert.equal(links[0].props.rel,"noopener noreferrer");
    assert.equal(view.root.findAllByType("button").length,0);
  }finally{if(view)await act(async()=>view.unmount());}
});

test("GOAL cannot reuse old source coverage when authentication GET fails or refreshes",()=>{
  const source=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.tsx"),"utf8");
  const component=fs.readFileSync(path.join(__dirname,"../app/GoalSourceCoverage.tsx"),"utf8");
  const css=fs.readFileSync(path.join(__dirname,"../app/GoalSourceCoverage.module.css"),"utf8");
  assert.match(source,/setSourceCoverageReport\(data && typeof data/);
  assert.match(source,/setSourceCoverageReport\(null\)/);
  assert.match(source,/<GoalSourceCoverage source=\{sourceCoverageReport\} scan=\{scanView\}/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.doesNotMatch(component,/fetch\(|localStorage|sessionStorage|method: ?["']POST|dispatchWorkflow|Twilio|placeOrder/i);
});


test("GOAL reconciles five categories including independently recorded SEC ticker conflicts",()=>{
  const historical=report();
  historical.findings_unresolved=21;
  historical.findings_conflicted=2;
  const audit=goalSourceCoverage(historical,scan);
  assert.ok(audit);
  assert.equal(audit.verified,995);
  assert.equal(audit.unresolved,21);
  assert.equal(audit.conflicted,2);
  assert.equal(audit.unavailable,93);
  assert.equal(audit.notApplicable,10);
  assert.equal(audit.due,1121);
  assert.equal(audit.fullCoverage,false);
  const missing=structuredClone(historical);
  delete missing.findings_conflicted;
  assert.equal(goalSourceCoverage(missing,scan),null,
    "do not silently drop two conflicts from 1121 declared findings");
  const forged=structuredClone(historical);
  forged.findings_conflicted=0;
  assert.equal(goalSourceCoverage(forged,scan),null);
  const negative=structuredClone(historical);
  negative.findings_conflicted=-1;
  assert.equal(goalSourceCoverage(negative,scan),null);
  const complete=structuredClone(historical);
  complete.full_coverage_verified=true;
  assert.equal(goalSourceCoverage(complete,scan),null);
});

test("GOAL presents conflicted source checks separately without treating them as approvals",async()=>{
  const current=report();
  current.findings_unresolved=21;
  current.findings_conflicted=2;
  let view;
  try {
    await act(async()=>{view=create(React.createElement(Panel,{source:current,scan,loading:false}));});
    const rendered=JSON.stringify(view.toJSON());
    assert.match(rendered,/Published coverage partial/);
    assert.match(rendered,/Conflicted/);
    assert.match(rendered,/21/);
    assert.match(rendered,/Cannot treat as verified/);
    assert.match(rendered,/Full source coverage NOT verified/);
    assert.doesNotMatch(rendered,/Source coverage not verified · inspect/);
  }finally{if(view)await act(async()=>view.unmount());}
});
