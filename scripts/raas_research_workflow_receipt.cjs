"use strict";
/** Fail-closed provenance for RAAS source-research Actions.
 * Passing unit tests on a pull request never means Alpaca/FDA research ran.
 * File existence only proves an artifact was emitted, never validation.
 */
const fs=require("node:fs");
const path=require("node:path");

function entries(value){
 return String(value||"").split(",").map(x=>x.trim()).filter(Boolean);
}
function validBasename(name){
 return /^[a-z0-9][a-z0-9._-]{0,127}$/.test(name)&&name!=="."&&name!==".."&&!name.includes("..");
}
function createReceipt(env=process.env){
 const event=env.GITHUB_EVENT_NAME||"";
 const scope=env.RAAS_RECEIPT_SCOPE||"";
 const temp=env.RUNNER_TEMP||"";
 const expected=entries(env.RAAS_RECEIPT_EXPECTED);
 const required=entries(env.RAAS_RECEIPT_REQUIRED);
 if(!["pull_request","push","schedule","workflow_dispatch"].includes(event)||
    !/^[A-Z0-9_]{3,80}$/.test(scope)||!temp||!path.isAbsolute(temp)||
    expected.length===0||new Set(expected).size!==expected.length||
    required.length===0||required.some(x=>!expected.includes(x))||
    expected.some(x=>!validBasename(x)))
  throw Error("RAAS_RECEIPT_INPUT_INVALID");
 const files=expected.map(name=>{
  const file=path.join(temp,name);
  const exists=fs.existsSync(file)&&fs.statSync(file).isFile();
  const nonempty=exists&&fs.statSync(file).size>0;
  return {name,present:nonempty};
 });
 const isPR=event==="pull_request";
 const found=files.filter(x=>x.present).map(x=>x.name);
 const missingRequired=required.filter(x=>!found.includes(x));
 const state=isPR?"TESTS_ONLY_LIVE_RESEARCH_SKIPPED":
  missingRequired.length?"LIVE_RESEARCH_REQUIRED_OUTPUT_MISSING":
  "LIVE_RESEARCH_OUTPUT_PRESENT_NOT_VALIDATED";
 return {
  schemaVersion:1,scope:"RAAS_RESEARCH_ACTION_EXECUTION_RECEIPT",
  workflowScope:scope,
  sourceCommit:env.GITHUB_SHA||null,
  runId:env.GITHUB_RUN_ID||null,
  event,
  status:state,
  liveSourceCollectionAttempted:!isPR,
  outputArtifactCount:found.length,
  expectedArtifacts:files,
  missingRequiredArtifacts:isPR?[]:missingRequired,
  historicalMarketCapsValidated:0,
  independentlyAdjustedReturnsValidated:0,
  approvedRaasCalibrations:0,
  warning:isPR
   ?"This pull request only ran code/tests. All live research steps were skipped; test success is not an evidence collection result."
   :"Artifact presence does not prove market-data identity, historical cap, adjusted-return parity, cohort completeness, or RAAS calibration."
 };
}
function main(){
 const env=process.env;
 const result=createReceipt(env);
 const target=env.RAAS_RECEIPT_OUTPUT||path.join(env.RUNNER_TEMP,"raas-research-execution-receipt.json");
 if(!path.isAbsolute(target))throw Error("RAAS_RECEIPT_OUTPUT_MUST_BE_ABSOLUTE");
 fs.mkdirSync(path.dirname(target),{recursive:true});
 fs.writeFileSync(target,JSON.stringify(result,null,2)+"\n","utf8");
 const line="RAAS research execution: "+result.workflowScope+" · "+result.status+
   " · "+result.outputArtifactCount+"/"+result.expectedArtifacts.length+
   " nonempty output files (not validated)";
 process.stdout.write(line+"\n");
 if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,
  "### RAAS research execution receipt\n\n"+line+
  "\n\n"+result.warning+"\n");
 if(result.status==="LIVE_RESEARCH_REQUIRED_OUTPUT_MISSING"){
  process.stderr.write("RAAS_LIVE_RESEARCH_REQUIRED_OUTPUT_MISSING: "+result.missingRequiredArtifacts.join(", ")+"\n");
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={createReceipt};
