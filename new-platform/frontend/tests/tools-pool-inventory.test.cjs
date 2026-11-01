const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
  mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,file);
const {
  verifiedToolPool,selectToolTrialIds,filterToolTrials,buildToolsResults,renderToolsSpreadsheetCsv
}=require("../lib/tools-pool-inventory.ts");
const trial=(nct,stage,ticker="ACME")=>({id:"TRIAL|"+nct,ticker,company:"Company",drug:"Drug",indication:"Disease",stage});
const trials=[
  trial("NCT00000001","Phase 1"),
  trial("NCT00000002","Phase 2"),
  trial("NCT00000003","Phase 3"),
  {id:"RESULT|a",ticker:"ACME",stage:"Phase 3 Results"},
  {id:"APPLICATION|a",ticker:"ACME",stage:"FDA Acceptance"}
];
const raw=()=>({
  pipeline:trials,asOf:"2026-10-31T20:00:00Z",
  sourceHealth:{
    state:"PARTIAL",clinicalRows:4,regulatoryRows:1,
    pipelineSourceParity:{exactPrograms:5}
  }
});
const granted={status:"GRANTED",verification:"SOURCE_RECORDED",source:"https://www.fda.gov/drugs/example",
  designationDate:"2026-10-20",checkedAt:"2026-10-30",note:"Saved source"};
const index={
  availableKeys:{fast_track:true,orphan_drug:true},
  programs:{"ACME|one":{eventKey:"ACME|one",ticker:"ACME",drug:"Drug",indication:"Disease",
    designations:{fast_track:granted,orphan_drug:granted}}},
  trialEvents:{NCT00000001:["ACME|one"],NCT00000002:["WRONG|other"]}
};
test("counts every real unique NCT stage without counting result announcements twice",()=>{
  const result=verifiedToolPool(raw());
  assert.equal(result.stageStats.trials,3);
  assert.equal(result.stageStats.stages["Phase 1"].trials,1);
  assert.equal(result.stageStats.stages["Phase 3"].trials,1);
  assert.equal(result.stageStats.standaloneResults,1);
  assert.equal(result.stageStats.regulatoryEvents,1);
  assert.equal(result.sourceState,"PARTIAL");
});
test("zero selected always returns zero rows without changing POOL stage totals",()=>{
  const snapshot=verifiedToolPool(raw());
  const result=buildToolsResults(snapshot,null,[],[],"",0,50);
  assert.equal(result.total,0);
  assert.equal(result.stageStats.trials,3);
  assert.equal(result.selectionSummary.selectedCount,0);
});
test("selected stages use OR; selected designations use OR; together they use AND",()=>{
  const snapshot=verifiedToolPool(raw());
  const matched=selectToolTrialIds(snapshot.poolRows,index,["fast_track","orphan_drug"]);
  assert.deepEqual([...matched],["TRIAL|NCT00000001"]);
  assert.equal(filterToolTrials(snapshot.poolRows,["Phase 1","Phase 3"],null,"").length,2);
  const pass=buildToolsResults(snapshot,index,["Phase 1","Phase 3"],["fast_track"],"",0,50);
  assert.equal(pass.total,1);
  assert.equal(pass.selectionSummary.selectedCount,3);
  assert.equal(pass.selectionSummary.stageTotal,2);
  assert.equal(pass.selectionSummary.designationCountSum,1);
  assert.equal(pass.selectionSummary.matchingUniqueTrials,1);
  assert.equal(pass.spreadsheetRows[0].designationMatches.fast_track.length,1);
  const noMatch=buildToolsResults(snapshot,index,["Phase 3"],["fast_track"],"",0,50);
  assert.equal(noMatch.total,0);
});
test("designation-only selection counts exact NCT plus issuer, never ticker alone",()=>{
  const snapshot=verifiedToolPool(raw());
  const data=buildToolsResults(snapshot,index,[],["fast_track"],"",0,50);
  assert.equal(data.total,1);
  assert.equal(data.rows[0].id,"TRIAL|NCT00000001");
  const badIndex={...index,programs:{"ACME|one":{...index.programs["ACME|one"],ticker:"OTHER"}}};
  assert.equal(selectToolTrialIds(snapshot.poolRows,badIndex,["fast_track"]).size,0);
});
test("source parity failure and stale POOL never produce invented trial totals",()=>{
  assert.throws(()=>verifiedToolPool({...raw(),sourceHealth:{...raw().sourceHealth,state:"STALE"}}),/POOL_SOURCE_STALE/);
  assert.throws(()=>verifiedToolPool({...raw(),sourceHealth:{...raw().sourceHealth,regulatoryRows:2}}),/POOL_SOURCE_PARITY_FAILED/);
});
test("CSV exports all filtered rows and prevents spreadsheet formula execution",()=>{
  const sample=[{...trials[0],company:'=HYPERLINK("https://evil")'}];
  const csv=renderToolsSpreadsheetCsv(sample,["Phase 1"],[],null,"2026-10-31");
  assert.equal(csv.charCodeAt(0),0xFEFF);
  assert.match(csv,/'=HYPERLINK/);
  assert.match(csv,/NCT00000001/);
});

test("POOL heading shows exactly one selector-calculated trial count and clinical stage list has no duplicate",()=>{
  const ui=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  assert.match(ui,/<h2>POOL<\/h2>\s*<p className=\{styles\.stageTrialMatchCount\}/);
  assert.equal((ui.match(/className=\{styles\.stageTrialMatchCount\}/g)||[]).length,1);
  assert.match(ui,/const matchingTrialLabel=!hasSelections\?"0 matching trials"/);
  assert.match(ui,/page\?count\(page\.total\)\+" matching trials"/);
  assert.match(ui,/error\?"Trial count unavailable"/);
  assert.match(ui,/<div className=\{styles\.stageDropdownLabel\}>Clinical development stages<\/div>/);
  assert.match(ui,/Counts beside each stage describe the full POOL/);
});

test("when FDA program evidence lacks an exact NCT crosswalk, TOOLS reports unavailable, not zero",()=>{
  const root=require("node:path").join(__dirname,"..");
  const route=fs.readFileSync(require("node:path").join(root,"app/api/scope-funnel/route.ts"),"utf8");
  const designations=fs.readFileSync(require("node:path").join(root,"app/PoolDesignationSelector.tsx"),"utf8");
  assert.match(route,/Object\.keys\(index\.trialEvents\)\.length===0/);
  assert.match(route,/DESIGNATION_NCT_LINKAGE_UNAVAILABLE/);
  assert.match(route,/status:422/);
  assert.match(designations,/No reviewed trial-to-designation links/);
});
