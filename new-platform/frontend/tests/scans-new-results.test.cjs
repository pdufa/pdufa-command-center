const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");

require.extensions[".ts"] = (module, filename) => module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"), {
    compilerOptions: {module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
  }).outputText,filename
);
const {newFromScanSummary,pacificDay} = require("../lib/scan-new-results.ts");

const clinical = {
  latest_run_id:39369399911, latest_run_started_at_utc:"2026-10-20T04:24:25Z",
  updated_at_utc:"2026-10-20T04:37:21Z",
  scans:[
    {scan:"2",changed_trials_this_execution:62},
    {scan:"3",collected_at_utc:"2026-10-20T04:32:53.368525Z"},
    {scan:"4",new_records:1}
  ]
};
const pipeline = {
  status:"COMPLETE",started_at:"2026-10-20T04:31:58Z",finished_at:"2026-10-20T04:32:53Z",
  new_master_programs:[{ticker:"PTGX",drug:"Rusfertide",nct_id:"NCT05210790"}]
};
const gem = {run_id:39369399911,generated_at_utc:"2026-10-20T04:36:32Z"};
const ledger = {
  stages:{
    GEM_JR:{last_complete_snapshot:"2026-10-19",entries:{
      "A":{status:"ACTIVE",ticker:"AXSM",drug:"AXS-12",nct_id:"NCT03881852",periods:[{found:"2026-10-16",left:null}]}
    }},
    GEM:{last_complete_snapshot:"2026-10-19",entries:{
      "B":{status:"ACTIVE",ticker:"SVRA",drug:"MOLBREEVI",nct_id:"NCT04544293",periods:[{found:"2026-10-16",left:null}]}
    }}
  }
};

test("shows 1 new pipeline program, 1 new GEM JR result, 0 new GEM JR/GEM members and 62 updates", () => {
  const result = newFromScanSummary(clinical,gem,pipeline,ledger);
  assert.equal(result.runId,39369399911);
  assert.equal(result.scanPacificDate,"2026-10-19");
  assert.deepEqual([
    result.pipelineNewPrograms,result.gemJrNewResultRecords,
    result.gemJrNewMembersOnDate,result.gemNewMembersOnDate,result.pipelineChangedTrials
  ],[1,1,0,0,62]);
  assert.equal(result.membershipBasis,"SAME_DATE_LEDGER");
  assert.equal(result.rows.length,2);
  assert.deepEqual(result.rows[0],{
    kind:"NEW_PROGRAM",stage:"PIPELINE",ticker:"PTGX",drug:"Rusfertide",
    trialId:"NCT05210790",label:"NEW FROM SCAN — newly identified master program",exactRun:true
  });
  assert.equal(result.rows[1].kind,"NEW_PHASE3_RESULT");
  assert.equal(result.rows[1].ticker,null,"Do not invent a ticker for an aggregated result");
});

test("stale pipeline report cannot be presented as a new result from the current scan",() => {
  const result = newFromScanSummary(clinical,gem,{
    ...pipeline,started_at:"2026-10-18T04:31:58Z",finished_at:"2026-10-18T04:32:53Z"
  },ledger);
  assert.equal(result.pipelineNewPrograms,null);
  assert.ok(!result.rows.some(x=>x.ticker==="PTGX"));
  assert.equal(result.pipelineChangedTrials,62);
});

test("new pipeline programs require matching stage 3 artifact completion timestamp",() => {
  const wrong = structuredClone(clinical);
  wrong.scans[1].collected_at_utc="2026-10-20T03:02:53Z";
  const result=newFromScanSummary(wrong,gem,pipeline,ledger);
  assert.equal(result.pipelineNewPrograms,null);
  assert.ok(!result.rows.some(x=>x.ticker==="PTGX"));
});

test("unmatched GEM report and membership dates never imply zero new admissions",() => {
  const wrongGem = newFromScanSummary(clinical,{...gem,run_id:1},pipeline,ledger);
  assert.equal(wrongGem.gemNewMembersOnDate,null);
  assert.equal(wrongGem.gemJrNewMembersOnDate,null);
  assert.equal(wrongGem.membershipBasis,"UNVERIFIED");
  const oldLedger = structuredClone(ledger);
  oldLedger.stages.GEM.last_complete_snapshot="2026-10-17";
  const mixed = newFromScanSummary(clinical,gem,pipeline,oldLedger);
  assert.equal(mixed.gemNewMembersOnDate,null);
  assert.equal(mixed.gemJrNewMembersOnDate,0);
});

test("reports genuinely recorded same-date GEM stage admissions without duplicate records",() => {
  const saved = structuredClone(ledger);
  saved.stages.GEM_JR.entries.C = {
    status:"ACTIVE",ticker:"CORT",drug:"relacorilant",nct_id:"NCT04308590",
    periods:[{found:"2026-10-19",left:null},{found:"2026-10-19",left:null}]
  };
  saved.stages.GEM.entries.D = {
    status:"ACTIVE",ticker:"PRAX",drug:"ulixacaltamide",nct_id:"NCT06087276",
    periods:[{found:"2026-10-19",left:null}]
  };
  saved.stages.GEM.entries.E = {
    status:"LEFT",ticker:"OTHER",periods:[{found:"2026-10-19",left:"2026-10-19"}]
  };
  const result = newFromScanSummary(clinical,gem,pipeline,saved);
  assert.equal(result.gemJrNewMembersOnDate,1);
  assert.equal(result.gemNewMembersOnDate,1);
  assert.equal(result.rows.filter(r=>r.kind==="NEW_STAGE_MEMBER").length,2);
  assert.ok(result.rows.filter(r=>r.kind==="NEW_STAGE_MEMBER").every(r=>!r.exactRun));
});

test("unknown counts are not silently presented as zero; program IDs must be real NCT IDs",() => {
  const result=newFromScanSummary({...clinical,scans:[]},null,{
    ...pipeline,new_master_programs:[{ticker:"PTGX",nct_id:"not-an-nct"}]
  },null);
  assert.equal(result.pipelineNewPrograms,0);
  assert.equal(result.gemJrNewResultRecords,null);
  assert.equal(result.gemNewMembersOnDate,null);
  assert.equal(result.pipelineChangedTrials,null);
  assert.equal(result.rows.length,0);
});

test("Pacific date distinguishes late UTC evening and observes DST",() => {
  assert.equal(pacificDay("2026-10-20T04:24:25Z"),"2026-10-19");
  assert.equal(pacificDay("2026-01-20T05:24:25Z"),"2026-01-19");
  assert.equal(pacificDay("not a timestamp"),null);
});

test("SCANS page places new results summary ahead of job progress and identifies updates separately",()=>{
  const page=fs.readFileSync(require.resolve("../app/PublishedScansPanel.tsx"),"utf8");
  const panel=fs.readFileSync(require.resolve("../app/ScanNewResultsPanel.tsx"),"utf8");
  const api=fs.readFileSync(require.resolve("../app/api/published-scans/route.ts"),"utf8");
  assert.ok(page.includes("<ScanNewResultsPanel summary={record?.newFromScan}"));
  assert.ok(page.indexOf("<ScanNewResultsPanel")<page.indexOf("<LiveScansProgress />"));
  assert.ok(panel.includes("NEW FROM SCAN"));
  assert.ok(panel.includes("UPDATED / RECHECKED"));
  assert.ok(panel.includes("counts come from the"));
  assert.ok(api.includes("newFromScan: newFromScanSummary"));
});
