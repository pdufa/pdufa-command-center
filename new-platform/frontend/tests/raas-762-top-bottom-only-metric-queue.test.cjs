"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true}}).outputText,file);
const {buildRaas762MetricEvidenceQueue}=require("../lib/raas-762-metric-evidence-queue.ts");
const review=require("../data/raas-reviewed-metric-assessments.json").records;
const ledger=fs.readFileSync(path.resolve(__dirname,"../public/raas-trial-score-ledger.csv"),"utf8");

function makeIndex(){
 const rows=ledger.trimEnd().split(/\r?\n/).slice(1);
 const records=rows.map(x=>{
  const cols=x.split(",");
  const id=cols[0],ticker=cols[1],posted=cols[4]==="True";
  if(!/^NCT\d{8}$/.test(id)||!ticker||!["True","False"].includes(cols[4]))
   throw Error("MALFORMED_EXACT_NCT_LEDGER");
  return {
   nctId:id,ticker,postedResults:posted,
   sourceUrl:"https://clinicaltrials.gov/study/"+id,
   registeredPhases:["PHASE3"],registeredConditions:[],
   registeredInterventions:[],primaryDefinitions:[],primaryResults:[],
   registeredDesign:undefined,seriousAdverseEventTermCount:0,
   postedPrimaryOutcomeCount:0,postedOtherOutcomeCount:0,
   seriousEventDetails:[],retrievedAt:"2026-11-05T00:00:00Z",
   resultsFirstPosted:null,registryLastUpdated:null,
   registryStatus:posted?"COMPLETED":"RECRUITING"
  };
 });
 return {schemaVersion:1,scope:"RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
  summary:{researchNcts:762,registryRecords:762,
   approvedOverallRaasScores:0},records};
}
let result;
test("only TOP (425) and BOTTOM (337) spreadsheet NCTs receive their one 30-metric checklist",()=>{
 const index=makeIndex();
 assert.equal(index.records.length,762);
 assert.equal(new Set(index.records.map(x=>x.nctId)).size,762);
 result=buildRaas762MetricEvidenceQueue(index);
 assert.equal(result.summary.exactNcts,762);
 assert.equal(result.summary.stageResearchRows,762);
 assert.equal(result.summary.topTrialRows,425);
 assert.equal(result.summary.bottomTrialRows,337);
 assert.equal(result.summary.metricSlots,22860);
 assert.equal(result.csv.trimEnd().split(/\r?\n/).length,22861);
 assert.equal(result.summary.researchOnly,true);
 assert.equal(result.summary.fullyValidatedRaasScores,0);
 assert.equal(result.summary.calibratedFdaPredictions,0);
});
test("exact NCT/stage review data is never misassigned to opposite spreadsheet or to 11k pool",()=>{
 if(!result)result=buildRaas762MetricEvidenceQueue(makeIndex());
 assert.equal(review.length,82);
 assert.equal(result.summary.provisionalReviewSlots,71);
 assert.equal(result.summary.otherStageReviewsPreserved,11);
 assert.equal(result.summary.independentlyReviewedMetricSlots,0);
 assert.equal(result.summary.provisionalReviewSlots+
  result.summary.metricSlotsRequiringReviewedGrades,22860);
 const lines=result.csv.trimEnd().split(/\r?\n/);
 const ids=new Map();
 const sample=lines.filter(x=>x.startsWith("NCT06445023,"));
 assert.equal(sample.length,30);
 assert.ok(sample.every(x=>x.includes(",TOP_RESEARCH_ONLY,NO,pre-")));
 assert.ok(sample.every(x=>!x.includes(",post-")));
 const hdr=lines[0].split(",");
 assert.ok(hdr.includes("provisionalComponentScoreOrBlank"));
 assert.ok(hdr.includes("overallRaasScore"));
 for(const line of lines.slice(1)){
  const columns=line.split(",");
  const id=columns[0],stage=columns[2],metric=columns[4];
  const k=id+"|"+stage;
  const found=ids.get(k)||new Set();
  assert.ok(!found.has(metric),"Duplicate NCT stage metric "+k+" "+metric);
  found.add(metric);ids.set(k,found);
  assert.equal(columns[3],"NO");
  assert.ok(["TOP_RESEARCH_ONLY","BOTTOM_RESEARCH_ONLY"].includes(stage));
  assert.ok(metric.startsWith(stage==="TOP_RESEARCH_ONLY"?"pre-":"post-"));
 }
});
test("all 762 spreadsheet identities must be exact and never expand to master POOL",()=>{
 const index=makeIndex();
 assert.throws(()=>buildRaas762MetricEvidenceQueue({
  ...index,records:index.records.slice(0,761)}),/EXACT_ROSTER_REQUIRED/);
 assert.throws(()=>buildRaas762MetricEvidenceQueue({
  ...index,records:[...index.records,index.records[0]]}),/EXACT_ROSTER_REQUIRED/);
 assert.throws(()=>buildRaas762MetricEvidenceQueue({
  ...index,records:[...index.records.slice(0,761),{
   ...index.records.at(-1),nctId:"NCTinvalid"}]}),/INVALID_SOURCE_IDENTITY/);
});
test("mobile scoring workspace exports only the two tab populations",()=>{
 const code=fs.readFileSync(path.resolve(__dirname,"../app/Raas762ScoringWorkspace.tsx"),"utf8");
 assert.ok(code.includes("22860-exact-slots"));
 assert.ok(code.includes("425 TOP × 30 + 337 BOTTOM × 30"));
 assert.ok(!code.includes("45720-exact-slots"));
 assert.ok(code.includes("22,860 metric rows"));
 assert.ok(code.includes("other 11"));
});
