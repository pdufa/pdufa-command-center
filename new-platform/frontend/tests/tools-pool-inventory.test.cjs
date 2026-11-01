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

test("TOOLS shows three bordered funnel cards without fabricating PIPELINE qualification",()=>{
  const path=require("node:path");
  const page=fs.readFileSync(path.join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  const card=fs.readFileSync(path.join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  const css=fs.readFileSync(path.join(__dirname,"../app/FunnelWorkspace.module.css"),"utf8");
  assert.match(page,/<ToolsFunnel/);
  assert.match(card,/<h3>POOL<\/h3>/);
  assert.match(card,/<h3>PIPELINE<\/h3>/);
  assert.match(card,/<h3>TRIALS<\/h3>/);
  assert.match(card,/Not verified/);
  assert.match(card,/not a verified PIPELINE-qualified subset/);
  assert.match(card,/selectedTrials/);
  assert.match(css,/\.toolsFunnelCard\{border:3px solid/);
  assert.match(page,/<div className=\{styles\.stageDropdownLabel\}>Clinical development stages<\/div>/);
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

test("FDA selector discloses program source count and incomplete NCT crosswalk separately",()=>{
  const fs=require("node:fs"),path=require("node:path");
  const source=fs.readFileSync(path.join(__dirname,"../app/PoolDesignationSelector.tsx"),"utf8");
  const sheet=fs.readFileSync(path.join(__dirname,"../app/ToolsResultsSpreadsheet.tsx"),"utf8");
  assert.match(source,/Incomplete FDA-to-trial coverage/);
  assert.match(source,/positiveProgramIds\.size/);
  assert.match(source,/d\.records\.length\.toLocaleString/);
  assert.match(source,/d\.linkedTrials>0/);
  assert.match(source,/NCT count unknown/);
  assert.match(sheet,/Partial FDA coverage/);
  assert.match(sheet,/No documented NCT links match the selected filters/);
});

test("zero filters show zero immediately and do not show a misleading loading spinner",()=>{
  const ui=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  assert.match(ui,/\{hasSelections&&loading&&<p role="status">Calculating matching trial records/);
  assert.match(ui,/\{!hasSelections&&<p role="status"><strong>0 selected · 0 matching trials/);
  assert.match(ui,/loading=\{hasSelections&&loading\}/);
  assert.match(ui,/error=\{hasSelections\?error:""\}/);
});
test("one tap chooses Phase 3 AND Orphan Drug, clears search and resets offset",()=>{
  const ui=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  assert.match(ui,/function findPhase3OrphanTrials\(\)\{/);
  assert.match(ui,/setSelectedStages\(\["Phase 3"\]\)/);
  assert.match(ui,/setSelectedDesignations\(\["orphan_drug"\]\)/);
  assert.match(ui,/setOffset\(0\)/);
  assert.match(ui,/onClick=\{findPhase3OrphanTrials\}/);
  assert.match(ui,/Find Phase 3 \+ Orphan Drug trials/);
  assert.match(ui,/onClick=\{clearAllTrialSelectors\}/);
  const fda=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolDesignationSelector.tsx"),"utf8");
  assert.match(fda,/<details className=\{styles\.designationCoverageWarning\}>/);
  assert.match(fda,/FDA coverage limited:/);
});


test("selecting all 14 stages preserves designation-only unique NCT count",()=>{
  const {POOL_STAGES}=require("../lib/pool-pipeline-funnel.ts");
  assert.equal(POOL_STAGES.length,14);
  const snapshot=verifiedToolPool(raw());
  for(const selected of [["fast_track"],["orphan_drug"],["fast_track","orphan_drug"]]){
    const designationOnly=buildToolsResults(snapshot,index,[],selected,"",0,50);
    const allStages=buildToolsResults(snapshot,index,POOL_STAGES,selected,"",0,50);
    assert.equal(designationOnly.total,allStages.total,
      "The selected designation count must survive selection of every stage");
    assert.equal(allStages.total,allStages.selectionSummary.designationUniqueTrials);
    assert.equal(allStages.selectionSummary.stageTotal,snapshot.stageStats.trials);
    assert.equal(allStages.selectionSummary.stageSelectedCount,14);
  }
});
test("parity banner is shown only for all selected stages without active text search",()=>{
  const file=fs.readFileSync(require("node:path").join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  assert.match(file,/selectedStages===totalStages/);
  assert.match(file,/selectedDesignations>0&&!searchActive&&allStages&&!loading&&!error&&!noNctLink/);
  assert.match(file,/designationUniqueTrials===selectedTrials/);
  assert.match(file,/All-stage check passed:/);
  assert.match(file,/Count mismatch: selecting every clinical stage/);
});


test("Accelerated Approval: 16 documented program records cannot become a claimed zero-trial outcome",()=>{
  const path=require("node:path");
  const {buildDesignationIndex}=require("../lib/trial-designations.ts");
  const {designationSourceCoverage}=require("../lib/tools-pool-inventory.ts");
  const source=fs.readFileSync(path.join(__dirname,"../../../data/prediction_engine_designations.csv"),"utf8");
  const index=buildDesignationIndex(source,null,"2026-10-31T00:00:00Z");
  const snapshot=verifiedToolPool(raw());
  const coverage=designationSourceCoverage(snapshot.poolRows,index,["accelerated_approval"]);
  assert.equal(coverage.sourcePrograms,16);
  assert.equal(coverage.linkedNcts,0);
  assert.equal(coverage.unlinkedPrograms,16);
  assert.equal(coverage.noVerifiedNctLinks,true);
  assert.equal(coverage.programRows.length,16);
  assert.ok(coverage.programRows.every(row=>row.designations.some(d=>d.key==="accelerated_approval"&&d.source.startsWith("https://"))));
  const only=buildToolsResults(snapshot,index,[],["accelerated_approval"],"",0,50);
  const allStages=buildToolsResults(snapshot,index,require("../lib/pool-pipeline-funnel.ts").POOL_STAGES,["accelerated_approval"],"",0,50);
  assert.equal(only.designationCoverage.sourcePrograms,16);
  assert.equal(allStages.designationCoverage.sourcePrograms,16);
  assert.equal(allStages.designationCoverage.noVerifiedNctLinks,true);
  assert.equal(only.selectionSummary.noVerifiedNctLinks,true);
  assert.equal(allStages.selectionSummary.noVerifiedNctLinks,true);
});
test("all-stage parity must not claim success for programs without any NCT links",()=>{
  const path=require("node:path");
  const funnel=fs.readFileSync(path.join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  const sheet=fs.readFileSync(path.join(__dirname,"../app/ToolsResultsSpreadsheet.tsx"),"utf8");
  assert.match(funnel,/noNctLink\?"Not established"/);
  assert.match(funnel,/Program-record counts must not be presented as verified trial counts/);
  assert.match(sheet,/FDA source program records — not clinical trial counts/);
  assert.match(sheet,/trialCountUnverified\?"Not established"/);
  assert.match(sheet,/NCT link not established/);
  assert.match(sheet,/programRows\.map\(/);
});
