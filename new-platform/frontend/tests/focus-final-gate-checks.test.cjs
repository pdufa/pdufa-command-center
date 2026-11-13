const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");

require.extensions[".ts"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      esModuleInterop:true}
  }).outputText,filename);

const snapshot=require("../data/p3PostDataActive.json");
const {assessFinalFocusRoster,FOCUS_FINAL_TRIAL_AUDIT}=require("../lib/focus-final-gate-checks.ts");

test("final 32 NCT roster is the ONLY population used by the seven trial gates",()=>{
  const audit=FOCUS_FINAL_TRIAL_AUDIT;
  assert.equal(snapshot.records.length,32,"Current dated final FOCUS listing has 32 entries");
  assert.equal(audit.trialCount,snapshot.records.length);
  assert.equal(audit.asOf,snapshot.asOf);
  assert.equal(audit.checksPerTrial,7);
  assert.equal(audit.totalChecks,32*7);
  assert.equal(audit.independentlyVerified,0);
  assert.equal(new Set(audit.rows.map(row=>row.nct)).size,32);
  assert.deepEqual(audit.rows.map(row=>row.nct),snapshot.records.map(row=>row.nct));
  assert.deepEqual(audit.rows.map(row=>row.ticker),snapshot.records.map(row=>row.ticker));
  assert.ok(audit.rows.every(row=>row.gates.length===7&&row.independentlyVerified===0));
  assert.ok(audit.rows.every(row=>row.gates.every(g=>
    ["RECORDED_POINTER","SOURCE_REVIEW_REQUIRED","MISSING_EVIDENCE"].includes(g.state))));
  assert.equal(audit.pointers+audit.review+audit.missing,203);
  const moduleSource=fs.readFileSync(path.join(__dirname,"../lib/focus-final-gate-checks.ts"),"utf8");
  assert.ok(!/import .*pool-pipeline-funnel|import .*tools-restricted-scope|import .*phase3-census/.test(moduleSource),
    "No other trial population is imported into current acceptance checks");
});

test("the FOCUS roster fails closed for duplicate NCT identities and malformed membership",()=>{
  const duplicate=JSON.parse(JSON.stringify(snapshot));
  duplicate.records[1].nct=duplicate.records[0].nct;
  assert.throws(()=>assessFinalFocusRoster(duplicate),/FOCUS_FINAL_IDENTITY_OR_DUPLICATE/);
  const invalid=JSON.parse(JSON.stringify(snapshot));
  invalid.records[0].nct="NCTinvalid";
  assert.throws(()=>assessFinalFocusRoster(invalid),/FOCUS_FINAL_IDENTITY_OR_DUPLICATE/);
  assert.throws(()=>assessFinalFocusRoster({...snapshot,records:[]}),/FOCUS_FINAL_ROSTER_INVALID/);
});

test("dated sources, missing identity detail and planned FDA dates never certify eligibility",()=>{
  const changed=JSON.parse(JSON.stringify(snapshot));
  changed.records[0].marketCap=299_999_999;
  changed.records[0].resultsUrl="";
  changed.records[0].fdaStatus="PDUFA approved by us";
  const gateRow=assessFinalFocusRoster(changed).rows[0];
  const byId=Object.fromEntries(gateRow.gates.map(g=>[g.id,g]));
  assert.equal(byId["listing-market-cap"].state,"MISSING_EVIDENCE");
  assert.equal(byId["final-phase3-readout"].state,"MISSING_EVIDENCE");
  assert.equal(byId["therapy-indication"].state,"MISSING_EVIDENCE");
  assert.equal(byId["commercial-rights"].state,"MISSING_EVIDENCE");
  assert.equal(byId["fda-pathway"].state,"SOURCE_REVIEW_REQUIRED");
  assert.equal(byId["sheets-sync"].state,"SOURCE_REVIEW_REQUIRED");
  assert.equal(gateRow.independentlyVerified,0);
});

test("FOCUS and MAIN display only the current final-list gate scope",()=>{
  const focus=fs.readFileSync(path.join(__dirname,"../app/focus/page.tsx"),"utf8");
  const main=fs.readFileSync(path.join(__dirname,"../app/main/page.tsx"),"utf8");
  assert.ok(focus.includes("finalGateByNct.get(t.nct)"));
  assert.ok(focus.includes("gateAudit.gates.map"));
  assert.ok(focus.includes("Acceptance gates · final FOCUS trials only"));
  assert.ok(main.includes("Current MAIN scope · 7 gates · Core Platform and Pipeline only"));
  assert.ok(main.includes("MAIN_ACTIVE_GATE_IDS"));
  assert.ok(!main.includes("currentScopeReplacements"));
  assert.ok(main.includes("FOCUS_FINAL_TRIAL_AUDIT.totalChecks"));
  assert.ok(!main.includes("Current 31-gate scope"));
});
