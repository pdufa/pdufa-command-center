const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
  mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,file);
const {
  verifiedToolPool,selectToolTrialIds,filterToolTrials,buildToolsResults,buildToolsOpeningInventory,renderToolsSpreadsheetCsv
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
test("opening inventory returns genuine paginated unique NCT trials without claiming filters",()=>{
  const snapshot=verifiedToolPool(raw());
  const opening=buildToolsOpeningInventory(snapshot,0,2);
  assert.equal(opening.inventoryMode,true);
  assert.equal(opening.total,3);
  assert.equal(opening.rows.length,2);
  assert.equal(opening.nextOffset,2);
  assert.deepEqual(opening.rows.map(row=>row.id),["TRIAL|NCT00000001","TRIAL|NCT00000002"]);
  assert.deepEqual(opening.spreadsheetRows.map(row=>row.nctId),["NCT00000001","NCT00000002"]);
  assert.equal(opening.selectionSummary.selectedCount,0);
  assert.equal(opening.selectionSummary.matchingUniqueTrials,3);
  assert.equal(opening.designationCoverage,null);
  assert.deepEqual(opening.spreadsheetRows[0].designationMatches,{});
  assert.equal(opening.spreadsheetRows[0].selectedStage,"");
  const second=buildToolsOpeningInventory(snapshot,2,2);
  assert.equal(second.rows.length,1);
  assert.equal(second.nextOffset,null);
  assert.equal(second.rows[0].id,"TRIAL|NCT00000003");
  // The actual filtered API's no-checkbox contract must remain zero.
  assert.equal(buildToolsResults(snapshot,null,[],[],"",0,50).total,0);
  const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
  assert.match(route,/openingInventory=inventoryParam==="1"/);
  assert.match(route,/openingInventory && \(!toolMode \|\| selectedStages.length>0 \|\| selectedDesignations.length>0/);
  assert.match(route,/buildToolsOpeningInventory\(inventory,Number\(offset\),Number\(limit\)\)/);
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
  assert.match(card,/PIPELINE eligibility is not yet verified/);
  assert.match(card,/selectedTrials/);
  assert.match(css,/\.toolsFunnelCard\{border:3px solid/);
  assert.match(page,/aria-controls="tools-first-phase"/);
  assert.match(page,/aria-controls="tools-first-designation"/);
  assert.match(page,/hasSelections&&<>/);
  assert.match(page,/activeFilter==="phase"/);
  assert.match(page,/activeFilter==="designation"/);
});


test("TOOLS selects full POOL even if only a small separate Pipeline subset is known",()=>{
  const {POOL_STAGES}=require("../lib/pool-pipeline-funnel.ts");
  const snapshot=verifiedToolPool(raw());
  const pipelineSubset=new Set(["TRIAL|NCT00000003"]);
  const early=buildToolsResults(snapshot,null,["Phase 1"],[],"",0,50,pipelineSubset);
  assert.equal(early.total,1,"Phase 1 is visible in TOOLS regardless of Phase 3 Pipeline");
  assert.equal(early.rows[0].id,"TRIAL|NCT00000001");
  const phase3=buildToolsResults(snapshot,null,["Phase 3"],[],"",0,50,pipelineSubset);
  assert.equal(phase3.total,1);
  const designationOnly=buildToolsResults(snapshot,index,[],["fast_track"],"",0,50,pipelineSubset);
  const allStages=buildToolsResults(snapshot,index,POOL_STAGES,["fast_track"],"",0,50,pipelineSubset);
  assert.equal(designationOnly.total,1);
  assert.equal(allStages.total,1);
  assert.equal(allStages.selectionSummary.designationUniqueTrials,1);
  const and=buildToolsResults(snapshot,index,["Phase 3"],["fast_track"],"",0,50,pipelineSubset);
  assert.equal(and.total,0,"AND between unrelated Phase 3 and Phase 1 designation yields zero");
  const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
  assert.match(route,/query,Number\(offset\),Number\(limit\)\);/);
  assert.doesNotMatch(route,/query,Number\(offset\),Number\(limit\),pipelineResearchNcts/);
});

test("FDA programs without verified NCT links remain visible as programs, not empty trial claims",()=>{
  const root=require("node:path").join(__dirname,"..");
  const route=fs.readFileSync(require("node:path").join(root,"app/api/scope-funnel/route.ts"),"utf8");
  const designations=fs.readFileSync(require("node:path").join(root,"app/PoolDesignationSelector.tsx"),"utf8");
  assert.doesNotMatch(route,/DESIGNATION_NCT_LINKAGE_UNAVAILABLE/);
  assert.match(route,/renderUnlinkedFdaProgramCsv/);
  assert.match(route,/trialTimelines/);
  assert.match(designations,/No reviewed trial-to-designation links/);
  const snapshot=verifiedToolPool(raw());
  const missingIndex={...index,trialEvents:{}};
  const result=buildToolsResults(snapshot,missingIndex,[],["fast_track"],"",0,50);
  assert.equal(result.total,0);
  assert.equal(result.designationCoverage.sourcePrograms,1);
  assert.equal(result.designationCoverage.noVerifiedNctLinks,true);
  assert.throws(()=>buildToolsResults(snapshot,null,[],["fast_track"],"",0,50),
    /FDA_DESIGNATION_EVIDENCE_UNAVAILABLE/);
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
  assert.match(sheet,/FDA source program records — not clinical trial counts/);
  assert.match(sheet,/No documented NCT-linked POOL trials match both the chosen phases/);
});

test("TOOLS shows zero TRIALS and an empty spreadsheet when no phase or FDA designation is selected",()=>{
  const ui=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  const funnel=fs.readFileSync(require("node:path").join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  const sheet=fs.readFileSync(require("node:path").join(__dirname,"../app/ToolsResultsSpreadsheet.tsx"),"utf8");
  const matrix=fs.readFileSync(require("node:path").join(__dirname,"../app/ToolsBenefitMatrix.tsx"),"utf8");
  const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
  assert.match(ui,/const hasSelections=selectedStages.length>0\|\|selectedDesignations.length>0/);
  assert.match(ui,/selectedTrials=\{!hasSelections\?0:/);
  assert.match(ui,/Select Phase 3 trials/);
  assert.match(ui,/setSelectedStages\(\["Phase 3"\]\)/);
  assert.match(funnel,/const trialStatus=!filterActive\?"0"/);
  assert.match(funnel,/pipelineResearch\?num\(pipelineResearch.screenedTrials\)/);
  assert.match(sheet,/const hasSelection=stages.length\+designations.length>0/);
  assert.match(sheet,/!hasSelection\?<tr><td/);
  assert.match(matrix,/!hasSelection\?<div/);
  assert.match(route,/params.has\("baseline"\)/);
  assert.doesNotMatch(ui+funnel+sheet+matrix+route,/baselineMode|screenedBaseline|allowScreenedBaseline/);
});
test("zero selection is zero even with 346 exact-NCT screened Pipeline records and an active text search",()=>{
  const snapshot=verifiedToolPool(raw());
  const pipelineIds=new Set(snapshot.poolRows.map(r=>r.id));
  const none=buildToolsResults(snapshot,null,[],[],"",0,50,pipelineIds);
  assert.equal(none.total,0);
  assert.deepEqual(none.rows,[]);
  assert.deepEqual(none.spreadsheetRows,[]);
  assert.equal(none.selectionSummary.selectedCount,0);
  assert.equal(buildToolsResults(snapshot,null,[],[],"NCT00000003",0,50,pipelineIds).total,0);
  const withStage=buildToolsResults(snapshot,null,["Phase 3"],[],"",0,50,pipelineIds);
  assert.ok(withStage.total>0,"Selecting Phase 3 permits recorded, screened trial matches");
  assert.equal(buildToolsResults(snapshot,null,[],[], "",0,50,new Set()).total,0);
});
test("one tap chooses Phase 3 AND Orphan Drug, clears search and resets offset",()=>{
  const ui=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  assert.match(ui,/function findPhase3OrphanTrials\(\)\{/);
  assert.match(ui,/setSelectedStages\(\["Phase 3"\]\)/);
  assert.match(ui,/setSelectedDesignations\(\["orphan_drug"\]\)/);
  assert.match(ui,/setOffset\(0\)/);
  assert.match(ui,/onClick=\{findPhase3OrphanTrials\}/);
  assert.match(ui,/Find Phase 3 \+ Orphan Drug trials/);
  assert.match(ui,/onClick=\{clearAllToolsSelections\}/);
  assert.match(ui,/onClick=\{clearPhaseSection\}/);
  assert.match(ui,/Clear This Section/);
  assert.match(ui,/pdufa-tools-clear-all-selections/);
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


test("Accelerated Approval CSV exports all 16 FDA program events, not an empty NCT spreadsheet",()=>{
  const path=require("node:path");
  const {buildDesignationIndex}=require("../lib/trial-designations.ts");
  const {designationSourceCoverage,renderUnlinkedFdaProgramCsv}=require("../lib/tools-pool-inventory.ts");
  const csv=fs.readFileSync(path.join(__dirname,"../../../data/prediction_engine_designations.csv"),"utf8");
  const index=buildDesignationIndex(csv,null,"2026-10-31");
  const coverage=designationSourceCoverage(verifiedToolPool(raw()).poolRows,index,["accelerated_approval"]);
  assert.equal(coverage.sourcePrograms,16);
  const rendered=renderUnlinkedFdaProgramCsv(coverage,"2026-10-31");
  assert.equal(rendered.charCodeAt(0),0xfeff);
  assert.match(rendered,/FDA PROGRAM EVENT — NOT A CLINICAL TRIAL/);
  assert.match(rendered,/NOT ESTABLISHED/);
  assert.equal(rendered.trim().split(/\r?\n/).length,17);
  const route=fs.readFileSync(path.join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
  assert.match(route,/result\.designationCoverage\?\.noVerifiedNctLinks/);
  assert.match(route,/pdufa-tools-fda-program-records-unlinked\.csv/);
});



test("all FDA selections retain separate program counts and exact linked NCT counts",()=>{
  const path=require("node:path");
  const funnel=fs.readFileSync(path.join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  assert.match(funnel,/selectedDesignations>0&&designationCoverage&&!loading&&!error/);
  assert.match(funnel,/num\(designationCoverage!\.sourcePrograms\)/);
  assert.match(funnel,/num\(designationCoverage!\.linkedNcts\)/);
  assert.match(funnel,/UNIQUE NCT TRIAL COUNT FROM SELECTED POOL/);
  assert.match(funnel,/crosswalk-linked NCTs in the unrestricted POOL/);
  assert.match(funnel,/FDA-to-NCT coverage may be incomplete/);
});
test("unlinked FDA source count is clearly visible in the TRIALS card but never labeled 16 trials",()=>{
  const path=require("node:path");
  const funnel=fs.readFileSync(path.join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  const selector=fs.readFileSync(path.join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  const css=fs.readFileSync(path.join(__dirname,"../app/FunnelWorkspace.module.css"),"utf8");
  assert.match(funnel,/FDA APPLICATION \/ PROGRAM RECORDS/);
  assert.match(funnel,/UNIQUE NCT TRIAL COUNT/);
  assert.match(funnel,/num\(designationCoverage!\.sourcePrograms\)/);
  assert.match(funnel,/NOT \{num\(designationCoverage!\.sourcePrograms\)\} distinct trials/);
  assert.match(funnel,/role="group" aria-label="FDA program record count, not clinical trials"/);
  assert.match(funnel,/SELECTED FILTERS/);
  assert.match(funnel,/Stages: \{stagesLabel\}/);
  assert.match(funnel,/FDA: \{designationsLabel\}/);
  assert.match(selector,/selectedDesignationLabels=\{selectedDesignations\.map/);
  assert.match(css,/\.toolsFunnelProgramBand\{display:flex/);
});


test("optional Pipeline readout data cannot suppress or fabricate TOOLS POOL results",()=>{
  const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
  assert.doesNotMatch(route,/PIPELINE_SCREEN_UNAVAILABLE/);
  assert.doesNotMatch(route,/\.filter\(row=>pipelineResearchNcts\.has\(row\.id\)\)/);
  assert.match(route,/buildToolsResults\(inventory,index,selectedStages,selectedDesignations,/);
  assert.match(route,/const rows=filterToolTrials\(inventory\.poolRows,selectedStages,matches,query\);/);
  assert.match(route,/timeline:trialTimelines\.get/);
  assert.match(route,/pdufa-tools-selected-trials\.csv/);
  const funnel=fs.readFileSync(require("node:path").join(__dirname,"../app/ToolsFunnel.tsx"),"utf8");
  assert.match(funnel,/The dated PIPELINE screen is a separate research subset and does not filter these results/);
});
test("published TOOLS snapshot freshness is reevaluated after caching, not frozen on first read",()=>{
  const {isToolsSnapshotFresh,parseToolsSnapshotTimestamp,TOOLS_SNAPSHOT_MAX_AGE_MS}=
    require("../lib/tools-snapshot-freshness.ts");
  const now=Date.UTC(2026,10,1,3,0,0);
  const produced=now-2*3600000;
  assert.equal(isToolsSnapshotFresh(produced,now),true);
  assert.equal(isToolsSnapshotFresh(produced,now+35*3600000),false,
    "a valid cache must expire even if the serverless process never restarts");
  assert.equal(isToolsSnapshotFresh(now-TOOLS_SNAPSHOT_MAX_AGE_MS,now),true);
  assert.equal(isToolsSnapshotFresh(now-TOOLS_SNAPSHOT_MAX_AGE_MS-1,now),false);
  assert.equal(isToolsSnapshotFresh(now+300001,now),false);
  assert.equal(isToolsSnapshotFresh(NaN,now),false);
  assert.ok(Number.isNaN(parseToolsSnapshotTimestamp("not a timestamp")));
  const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
  assert.match(route,/if\(isToolsSnapshotFresh\(publishedToolSnapshot.generatedAt,now\)\)/);
  assert.match(route,/publishedToolRetryAfter=now\+PUBLISHED_TOOL_RETRY_MS/);
  assert.doesNotMatch(route,/publishedToolSnapshotChecked/);
});


test("final live spreadsheet stays below every TOOLS selection and analysis section",()=>{
  const source=fs.readFileSync(require("node:path").join(__dirname,"../app/PoolStageExplorer.tsx"),"utf8");
  const head=source.indexOf('aria-label="Step 1 — choose a filter"');
  const stage=source.indexOf('id="tools-first-phase"');
  const fda=source.indexOf('id="tools-first-designation"');
  const funnel=source.indexOf('<ToolsFunnel');
  const research=source.indexOf('<ToolsResultsSpreadsheet');
  const final=source.indexOf('id="tools-final-trial-spreadsheet"');
  const closing=source.lastIndexOf('</section>');
  assert.ok([head,stage,fda,funnel,research,final,closing].every(n=>n>=0));
  assert.ok(head<stage&&stage<fda&&fda<funnel&&funnel<research&&research<final&&final<closing,
    "All selections, the trial funnel and research spreadsheet must precede the final live grid");
  assert.equal((source.match(/<ToolsOpeningTrialGrid\b/g)||[]).length,1,
    "Never render duplicate copies of the final live POOL spreadsheet");
  assert.match(source.slice(final),/rows=\{page\?\.spreadsheetRows\|\|\[\]\}/);
  assert.match(source.slice(final),/inventoryMode=\{!hasSelections\}/);
  assert.match(source.slice(final),/onNext=\{\(\)=>\{/);
  assert.match(source.slice(final),/loading=\{loading\}/);
});
