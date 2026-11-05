"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const registry=require("../public/raas-registry-evidence-index.json");
const {buildTrialMetricReviewDossier}=require("../lib/raas-trial-metric-review-dossier.ts");
const {
 REVIEW_WORKSHEET_HEADERS,parseReviewerWorksheetCsv,serializeReviewerWorksheet,
 auditReviewerWorksheetCsv
}=require("../lib/raas-review-worksheet-preflight.ts");
const docket=buildTrialMetricReviewDossier(registry,"NCT05208047","COGT");
const original=serializeReviewerWorksheet(docket);
const parse=()=>parseReviewerWorksheetCsv(original);
const print=rows=>rows.map((r,i)=>i===0?r.join(","):
 r.map(s=>'"'+s.replaceAll('"','""')+'"').join(",")).join("\r\n")+"\r\n";
const populateReady=(row)=>{
 row[18]="READY_FOR_EXTERNAL_REVIEW";
 row[19]="50";
 row[20]="https://clinicaltrials.gov/study/NCT05208047";
 row[21]="2026-10-15";
 row[22]="https://pubmed.ncbi.nlm.nih.gov/12345678/";
 row[23]="Independent published randomized benchmark context needs verification.";
 row[24]="Source-reported effect size interpreted from the original study result.";
 row[25]="Statistical confidence bounds and missing-data caveats evaluated.";
 row[26]="Potential adverse effects and protocol deviations require independent review.";
 row[27]="Predeclared methods and population caveats are documented here.";
};
test("unchanged downloaded clinical worksheet has exactly 60 protected rows, no approvals",()=>{
 assert.ok(docket);
 const rows=parse();
 assert.equal(rows.length,61);
 assert.deepEqual(rows[0],REVIEW_WORKSHEET_HEADERS);
 assert.equal(rows[0].length,29);
 assert.equal(rows.filter(r=>r[4]==="pre").length,30);
 assert.equal(rows.filter(r=>r[4]==="post").length,30);
 const audit=auditReviewerWorksheetCsv(original,docket);
 assert.equal(audit.schemaValid,true);
 assert.equal(audit.expectedMetricRows,60);
 assert.equal(audit.receivedMetricRows,60);
 assert.equal(audit.blockedRows,0);
 assert.equal(audit.readyForExternalReview,0);
 assert.equal(audit.completedEvidenceFields,0);
 assert.equal(audit.independentlyAuthenticatedMetrics,0);
 assert.equal(audit.approvedRaasScores,0);
 assert.equal(audit.calibratedFdaPredictions,0);
 assert.ok(audit.metrics.every(m=>m.status==="NOT_STARTED"));
});
test("ready stage-matched clinical evidence is still unapproved even with all fields populated",()=>{
 const rows=parse(),r=rows.find(r=>r[5]==="post-1-1");
 assert.ok(r);
 populateReady(r);
 const audit=auditReviewerWorksheetCsv(print(rows),docket);
 assert.equal(audit.schemaValid,true);
 assert.equal(audit.readyForExternalReview,1);
 assert.equal(audit.completedEvidenceFields,1);
 assert.equal(audit.blockedRows,0);
 assert.equal(audit.independentlyAuthenticatedMetrics,0);
 assert.equal(audit.approvedRaasScores,0);
 assert.equal(audit.calibratedFdaPredictions,0);
});
test("not-ready evidence is blocked, rather than assigned a zero or neutral score",()=>{
 const rows=parse(),r=rows.find(r=>r[5]==="post-1-1");
 r[18]="READY_FOR_EXTERNAL_REVIEW";
 const audit=auditReviewerWorksheetCsv(print(rows),docket);
 assert.equal(audit.blockedRows,1);
 assert.equal(audit.readyForExternalReview,0);
 assert.ok(audit.issues.some(x=>x.code==="REVIEW_FIELDS_INCOMPLETE"));
 assert.equal(audit.approvedRaasScores,0);
});
test("a well-populated wrong TOP stage remains blocked pending dated readout evidence",()=>{
 const rows=parse(),r=rows.find(r=>r[5]==="pre-1-1");
 populateReady(r);
 const audit=auditReviewerWorksheetCsv(print(rows),docket);
 assert.equal(audit.readyForExternalReview,0);
 assert.ok(audit.issues.some(x=>x.code==="STAGE_NOT_SUPPORTED_BY_SNAPSHOT"));
});
test("protected source hash, changed research metric, and missing rows fail closed",()=>{
 const rows=parse();
 rows[1][2]="f".repeat(64);
 rows[2][6]="Unauthorized alternative metric name";
 let audit=auditReviewerWorksheetCsv(print(rows),docket);
 assert.equal(audit.schemaValid,false);
 assert.ok(audit.issues.filter(x=>x.code==="SOURCE_OR_CATALOG_MODIFIED").length>=2);
 const missing=parse();
 missing.pop();
 audit=auditReviewerWorksheetCsv(print(missing),docket);
 assert.equal(audit.schemaValid,false);
 assert.ok(audit.issues.some(x=>x.code==="MISSING_METRIC"));
 assert.ok(audit.issues.some(x=>x.code==="MISSING_OR_EXTRA_METRIC_ROWS"));
});
test("wrong ticker, duplicate metric, and unknown metric never substitute source evidence",()=>{
 const rows=parse();
 rows[1][1]="FAKE";
 rows[2][5]=rows[1][5];
 let audit=auditReviewerWorksheetCsv(print(rows),docket);
 assert.equal(audit.schemaValid,false);
 assert.ok(audit.issues.some(x=>x.code==="SOURCE_OR_CATALOG_MODIFIED"));
 assert.ok(audit.issues.some(x=>x.code==="DUPLICATE_METRIC"));
 const other=parse();other[1][5]="post-9-9";
 audit=auditReviewerWorksheetCsv(print(other),docket);
 assert.equal(audit.schemaValid,false);
 assert.ok(audit.issues.some(x=>x.code==="UNKNOWN_METRIC"));
});
test("invalid reviewer grade, same-source benchmark, non-HTTPS URL and invalid source date are flagged",()=>{
 const rows=parse(),r=rows.find(r=>r[5]==="post-1-1");
 populateReady(r);
 r[19]="95";
 r[21]="2026-02-30";
 r[20]="http://clinicaltrials.gov/study/NCT05208047";
 r[22]=r[20];
 const audit=auditReviewerWorksheetCsv(print(rows),docket);
 for(const code of ["INVALID_PROPOSED_BAND","INVALID_PRIMARY_URL",
  "INVALID_BENCHMARK_URL","INVALID_SOURCE_DATE","SELF_BENCHMARK"])
  assert.ok(audit.issues.some(x=>x.code===code),code);
});
test("quoted commas and line breaks are safely parsed; malformed quoting is rejected",()=>{
 const rows=parse(),r=rows.find(r=>r[5]==="post-1-1");
 r[24]="Reports a positive response, but results are\nnot independently replicated";
 const joined=print(rows);
 const parsed=parseReviewerWorksheetCsv(joined);
 assert.equal(parsed.length,61);
 assert.equal(parsed.find(x=>x[5]==="post-1-1")[24],r[24]);
 assert.throws(()=>parseReviewerWorksheetCsv(original+'\r\n"unclosed'),
  /RAAS_WORKSHEET_UNCLOSED_CSV_QUOTE/);
 assert.throws(()=>auditReviewerWorksheetCsv("bad,header\r\n",docket),
  /RAAS_WORKSHEET_WRONG_SCHEMA_DOWNLOAD_LATEST/);
});
test("preflight is browser-only: no submission route, storage, or scores and page link exists",()=>{
 const ui=fs.readFileSync(path.join(root,
  "app/raas-trial-review/RaasWorksheetPreflight.tsx"),"utf8");
 const page=fs.readFileSync(path.join(root,"app/raas-trial-review/page.tsx"),"utf8");
 assert.match(ui,/data-raas-local-review-worksheet-preflight/);
 assert.match(ui,/auditReviewerWorksheetCsv/);
 assert.match(ui,/\.text\(\)/);
 assert.doesNotMatch(ui,/\bfetch\(/);
 assert.doesNotMatch(ui,/localStorage|sessionStorage/);
 assert.match(page,/RaasWorksheetPreflight/);
 const compiled=ts.transpileModule(ui,{fileName:"RaasWorksheetPreflight.tsx",
  reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,
   module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX}});
 assert.deepEqual(compiled.diagnostics??[],[]);
});
