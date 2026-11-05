"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"]){
 require.extensions[ext]=(mod,file)=>mod._compile(ts.transpileModule(
  fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
   module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
   esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
  }}).outputText,file);
}
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {buildRaasReadoutStageReviewQueue:queue}
 =require("../lib/raas-readout-stage-review-queue.ts");
const source=fn=>fs.readFileSync(path.join(root,fn),"utf8");
const census=parsePhase3CensusCsv(source("public/phase3-census-2026-10-26.csv"));
const evidence=JSON.parse(source("public/phase3-public-readout-evidence-2026-11-01.json"));
const data=classifyPhase3Readouts(evidence,census.rows);

test("741 exact Phase 3 census NCTs reconcile to 2 TOP + 8 BOTTOM + 731 source-unverified",()=>{
 const a=queue(data);
 assert.equal(a.summary.totalSourceCensusNcts,741);
 assert.equal(a.summary.sourceClassifiedTopNcts,2);
 assert.equal(a.summary.sourceClassifiedBottomNcts,8);
 assert.equal(a.summary.awaitingStageVerification,731);
 assert.equal(a.summary.raasRatingsAssignedByQueue,0);
 assert.equal(a.summary.sourceCensusDate,"2026-10-26");
 assert.equal(a.summary.issuerReadoutEvidenceAsOf,"2026-11-01");
 assert.equal(a.rows.length,731);
 assert.equal(new Set(a.rows.map(r=>r.nctId)).size,731);
 assert.equal(a.csv.trimEnd().split("\r\n").length,732);
});
test("every unclassified row is a research task with no assigned stage or RAAS grade",()=>{
 const a=queue(data);
 const assigned=new Set([...data.pre,...data.post].map(r=>r.nctId));
 for(const row of a.rows){
  assert.ok(/^NCT\d{8}$/.test(row.nctId));
  assert.equal(row.registrySourceUrl,"https://clinicaltrials.gov/study/"+row.nctId);
  assert.equal(row.stage,"UNVERIFIED");
  assert.equal(row.topRaasScore,null);
  assert.equal(row.bottomRaasScore,null);
  assert.equal(row.sourceDate,null);
  assert.equal(row.issuerEvidenceUrl,null);
  assert.equal(row.exactNctToIssuerProgramConfirmed,false);
  assert.equal(row.latestDatedIssuerReadoutOrNegativeCheckVerified,false);
  assert.equal(row.reviewStatus,"NEEDS_ISSUER_READOUT_IDENTITY_EVIDENCE");
  assert.ok(!assigned.has(row.nctId));
  assert.match(row.requiredProof,/Exact NCT\+issuer\+treatment\+indication/);
  assert.match(row.nextAction,/Do not infer a stage from ClinicalTrials\.gov/);
 }
 assert.match(a.csv.split("\r\n")[0],/topRaasScore,bottomRaasScore$/);
 assert.ok(!a.csv.includes("PASS/CRL probability"));
});
test("duplicated or mismatched research identities fail closed",()=>{
 const n=data.unverified[0],c=data.pre[0];
 const mutate=x=>({ ...data, unverified:[x,...data.unverified.slice(1)] });
 for(const row of [
  {...n,ticker:"other untrusted"},
  {...n,nctId:"NOT-A-REAL-NCT"},
  {...n,sourceUrl:"https://example.test/not-the-nct"},
  {...n,evidence:c.evidence},
  {...n,company:""},
 ]){
  assert.throws(()=>queue(mutate(row)),/RAAS_TOP_BOTTOM_STAGE_REVIEW_/);
 }
 assert.throws(()=>queue({...data,unverified:[...data.unverified,c]}),
  /RAAS_TOP_BOTTOM_STAGE_REVIEW_/);
 assert.throws(()=>queue({...data,unverified:data.unverified.slice(1)}),
  /RAAS_TOP_BOTTOM_STAGE_REVIEW_/);
 assert.throws(()=>queue({...data,total:12000}),
  /RAAS_TOP_BOTTOM_STAGE_REVIEW_CENSUS_REQUIRED/);
 assert.throws(()=>queue({...data,total:762}),
  /RAAS_TOP_BOTTOM_STAGE_REVIEW_CENSUS_REQUIRED/);
 assert.throws(()=>queue({...data,censusDate:"2027-12-01"}),
  /RAAS_TOP_BOTTOM_STAGE_REVIEW_CENSUS_REQUIRED/);
});
test("unverified CSV preserves source roster, contains explicit review tasks and never fake grades",()=>{
 const a=queue(data);
 const columns=a.csv.split("\r\n")[0].split(",");
 assert.ok(columns.includes("nctId"));
 assert.ok(columns.includes("exactNctToIssuerProgramConfirmed"));
 assert.ok(columns.includes("latestDatedIssuerReadoutOrNegativeCheckVerified"));
 assert.ok(columns.includes("requiredProof"));
 assert.ok(columns.includes("nextAction"));
 assert.ok(!columns.includes("approvedOverallRaasScore"));
 assert.equal((a.csv.match(/UNVERIFIED/g)||[]).length,731);
 assert.equal((a.csv.match(/NEEDS_ISSUER/g)||[]).length,731);
});
test("direct TOP and BOTTOM route is primary, while POOL and 762 stay separated",()=>{
 const page=source("app/raas-top-bottom/page.tsx");
 const tools=source("app/tools/page.tsx");
 const sheets=source("app/Phase3ReadoutSheets.tsx");
 assert.match(page,/data-raas-primary-score-scope="TOP_BOTTOM_ONLY"/);
 assert.match(page,/<Phase3ReadoutSheets\/>/);
 assert.match(page,/11,000\+ trial POOL/);
 assert.match(tools,/data-tools-primary-raas-top-bottom/);
 assert.match(tools,/href="\/raas-top-bottom"/);
 assert.match(tools,/data-tools-primary-raas-762/);
 assert.ok(tools.indexOf("data-tools-primary-raas-top-bottom")<
   tools.indexOf("data-tools-primary-raas-762"));
 assert.match(sheets,/buildRaasReadoutStageReviewQueue\(data\)/);
 assert.match(sheets,/data-raas-source-review-export="unclassified-no-ratings"/);
 assert.match(sheets,/downloadUnclassifiedSourceReview\(stageReviewQueue.csv\)/);
 assert.match(sheets,/data-raas-stage-gate-summary="top-bottom-only"/);
 assert.match(sheets,/downloadTopBottomRaasWorklist\(bucket,matched\)/);
 assert.doesNotMatch(sheets,/downloadTopBottomRaasWorklist\("unverified"/);
 const output=ts.transpileModule(page,{fileName:"raas-top-bottom/page.tsx",
  reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,
  jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}});
 assert.equal((output.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});
