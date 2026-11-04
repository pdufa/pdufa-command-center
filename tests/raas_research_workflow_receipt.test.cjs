"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const child=require("node:child_process");
const {createReceipt}=require("../scripts/raas_research_workflow_receipt.cjs");
function config(temp,event){
 return {
  GITHUB_EVENT_NAME:event,GITHUB_SHA:"abc123",GITHUB_RUN_ID:"1234",
  RAAS_RECEIPT_SCOPE:"ACTIVE_2024_2025_FDA_RESEARCH",
  RAAS_RECEIPT_EXPECTED:"research.json,results.csv",
  RAAS_RECEIPT_REQUIRED:"research.json",
  RUNNER_TEMP:temp,RAAS_RECEIPT_OUTPUT:path.join(temp,"receipt.json")
 };
}
test("PR check says TESTS_ONLY and never claims live prices or outcomes",()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"raas-receipt-"));
 try{
  const r=createReceipt(config(tmp,"pull_request"));
  assert.equal(r.status,"TESTS_ONLY_LIVE_RESEARCH_SKIPPED");
  assert.equal(r.liveResearchStepsEligible,false);
  assert.equal(r.outputArtifactCount,0);
  assert.equal(r.approvedRaasCalibrations,0);
  assert.equal(r.historicalMarketCapsValidated,0);
  assert.equal(r.independentlyAdjustedReturnsValidated,0);
  assert.deepEqual(r.missingRequiredArtifacts,[]);
 }finally{fs.rmSync(tmp,{recursive:true,force:true})}
});
test("main cannot be green without its expected source artifact",()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"raas-receipt-"));
 try{
  const cfg=config(tmp,"push");
  const r=child.spawnSync(process.execPath,
   ["scripts/raas_research_workflow_receipt.cjs"],{
    cwd:path.resolve(__dirname,".."),env:{...process.env,...cfg},encoding:"utf8"
   });
  assert.equal(r.status,1);
  assert.match(r.stderr,/RAAS_LIVE_RESEARCH_REQUIRED_OUTPUT_MISSING/);
  const receipt=JSON.parse(fs.readFileSync(cfg.RAAS_RECEIPT_OUTPUT,"utf8"));
  assert.equal(receipt.status,"LIVE_RESEARCH_REQUIRED_OUTPUT_MISSING");
  assert.deepEqual(receipt.missingRequiredArtifacts,["research.json"]);
 }finally{fs.rmSync(tmp,{recursive:true,force:true})}
});
test("existing source outputs permit a research receipt, not a validated RAAS score",()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"raas-receipt-"));
 try{
  fs.writeFileSync(path.join(tmp,"research.json"),'{"status":"research"}');
  const r=createReceipt(config(tmp,"workflow_dispatch"));
  assert.equal(r.status,"LIVE_RESEARCH_OUTPUT_PRESENT_NOT_VALIDATED");
  assert.equal(r.outputArtifactCount,1);
  assert.equal(r.independentlyAdjustedReturnsValidated,0);
  assert.equal(r.approvedRaasCalibrations,0);
  assert.deepEqual(r.expectedArtifacts,[{name:"research.json",present:true},{name:"results.csv",present:false}]);
 }finally{fs.rmSync(tmp,{recursive:true,force:true})}
});
test("invalid paths, duplicate files and unsupported execution modes fail closed",()=>{
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"raas-receipt-"));
 try{
  const base=config(tmp,"push");
  for(const override of [
   {GITHUB_EVENT_NAME:""},
   {RAAS_RECEIPT_EXPECTED:"../evil.json"},
   {RAAS_RECEIPT_EXPECTED:"research.json,research.json"},
   {RAAS_RECEIPT_REQUIRED:"not-in-list.json"},
   {RAAS_RECEIPT_SCOPE:"score=100"}
  ])assert.throws(()=>createReceipt({...base,...override}),/RAAS_RECEIPT_INPUT_INVALID/);
 }finally{fs.rmSync(tmp,{recursive:true,force:true})}
});
test("historical workflows publish execution receipts, not silent green no-artifact results",()=>{
 const workflowDir=path.resolve(__dirname,"../.github/workflows");
 for(const name of ["raas-active-2024-2025-original-source-research.yml",
  "raas-active-2024-2025-fda-outcome-discovery.yml",
  "raas-alpaca-active-two-year-study.yml"]){
  const src=fs.readFileSync(path.join(workflowDir,name),"utf8");
  assert.match(src,/node scripts\/raas_research_workflow_receipt\.cjs/);
  assert.match(src,/RAAS_RECEIPT_EXPECTED/);
  assert.match(src,/RAAS_RECEIPT_REQUIRED/);
  assert.match(src,/if: always\(\)/);
  assert.match(src,/research-execution-receipt\.json/);
  assert.match(src,/if-no-files-found: warn/);
 }
});
