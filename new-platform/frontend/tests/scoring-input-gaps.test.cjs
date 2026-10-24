const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for(const extension of [".ts",".tsx"]) require.extensions[extension] = (mod,file) =>
  mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file);
const {scoreAuditView} = require("../lib/scoring-audit.ts");
const time = Date.parse("2026-10-24T04:00:00Z");
function report(){
  return {
    generated_at_utc:"2026-10-24T03:39:00Z",status:"REVIEW_REQUIRED",
    source_scan:{workflow:"PDUFA Overnight Sequential Scans",run_id:40057578041,conclusion:"success"},
    counts:{input_tests:3,data_gaps:2,reviews:0,models_mapped:9,overlaps:6},
    checks:[
      {Test:"Trade Score coverage",Status:"DATA GAP",Result:"0/45 missing", "Why it matters":"No fabricated trade score"},
      {Test:"Public PoA coverage",Status:"DATA GAP",Result:"0/45 missing", "Why it matters":"No fake public probability"},
      {Test:"Market overlap",Status:"SHARED INPUT",Result:"34 observations", "Why it matters":"Not independent"}
    ],
    provenance_note:"Saved source inputs, not necessarily fresh scan artifacts."
  };
}
test("correctly keeps source-input gaps rather than fabricating scores",()=>{
  const audit=scoreAuditView(report(),time);
  assert.equal(audit.freshness,"CURRENT");
  assert.equal(audit.audit.counts.data_gaps,2);
  assert.equal(audit.audit.source_scan.run_id,40057578041);
  const older=scoreAuditView(report(),time+72*60*60*1000);
  assert.equal(older.freshness,"STALE");
  assert.equal(scoreAuditView(report(),time-60*60*1000).freshness,"CLOCK_UNVERIFIED");
});
test("inconsistent or invalid published scoring evidence is withheld",()=>{
  for(const bad of [
    x=>x.counts.data_gaps=0,
    x=>x.counts.input_tests=20,
    x=>x.status="NO_INPUT_GAPS_FOUND",
    x=>x.source_scan.run_id=0,
    x=>x.checks[1].Status="READY_TO_TRADE",
    x=>x.checks[1]["Why it matters"]=null,
    x=>x.checks="unsourced",
  ]){
    const item=report();bad(item);
    assert.equal(scoreAuditView(item,time),null);
  }
  assert.equal(scoreAuditView(null,time),null);
});
test("SCANS shows its saved audit and collapsible evidence checklist",async()=>{
  const React=require("react");
  const {create,act}=require("react-test-renderer");
  const Component=require("../app/ScoringInputGapsPanel.tsx").default;
  global.IS_REACT_ACT_ENVIRONMENT=true;
  let view;
  try {
    await act(async()=>{view=create(React.createElement(Component,{report:report()}));});
    let content=JSON.stringify(view.toJSON());
    assert.match(content,/REVIEW REQUIRED/);
    assert.match(content,/"2"," data gaps"/);
    assert.match(content,/Trade Score coverage/);
    assert.match(content,/OPEN ORIGINAL NIGHTLY SCAN RUN/);
    assert.equal(view.root.findAllByType("details").length,1);
    await act(async()=>view.update(React.createElement(Component,{report:null})));
    content=JSON.stringify(view.toJSON());
    assert.match(content,/Not verified/);
    assert.doesNotMatch(content,/2 data gaps/);
  } finally {if(view)await act(async()=>view.unmount());}
});
test("authenticated scan report fetch includes scoring without changing core source gating",()=>{
  const src=fs.readFileSync(require("node:path").join(__dirname,"../app/api/published-scans/route.ts"),"utf8");
  assert.match(src,/nightly_scoring_audit\.json/);
  assert.match(src,/authConfigured\(\)/);
  assert.match(src,/hasSession\(/);
  assert.match(src,/clinical, sources, gem, daily, scoring/);
  assert.match(src,/\[clinical, sources, gem\]\.every\(Boolean\)/);
  const view=fs.readFileSync(require("node:path").join(__dirname,"../app/PublishedScansPanel.tsx"),"utf8");
  assert.match(view,/<ScoringInputGapsPanel report=\{record\.scoring\}/);
});
