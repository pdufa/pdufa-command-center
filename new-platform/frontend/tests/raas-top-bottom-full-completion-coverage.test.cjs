"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const sourceText=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,
  target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {buildRaasTopBottomCompletion:build}
 =require("../lib/raas-top-bottom-completion.ts");
const census=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8");
const evidence=JSON.parse(fs.readFileSync(path.join(root,
 "public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const classified=classifyPhase3Readouts(evidence,parsePhase3CensusCsv(census).rows);
test("all ten exact TOP/BOTTOM NCTs reconcile 300 metric statuses: 30 rated, 270 absent",()=>{
 const result=build(classified),s=result.summary;
 assert.equal(s.scoredScope,"SOURCE_CLASSIFIED_TOP_BOTTOM_ONLY");
 assert.equal(s.researchSourceCensus,741);
 assert.equal(s.unclassifiedResearchRows,731);
 assert.equal(s.classifiedTrialRows,10);
 assert.equal(s.topTrials,2);
 assert.equal(s.bottomTrials,8);
 assert.equal(s.topMetricSlots,60);
 assert.equal(s.bottomMetricSlots,240);
 assert.equal(s.allMetricSlots,300);
 assert.equal(s.provisionalMetricGrades,30);
 assert.equal(s.missingMetricGrades,270);
 assert.equal(s.publishedUngradedMetricLeads,0);
 assert.equal(s.missingWithoutPublishedMetricLead,270);
 assert.equal(s.independentFullScores,0);
 assert.equal(s.calibratedFdaProbabilities,0);
 assert.equal(s.gradingSetupReady,true);
 assert.equal(s.allNumericGradesFinished,false);
 assert.equal(result.tasks.length,300);
 assert.equal(result.trials.length,10);
 assert.deepEqual(Object.fromEntries(result.trials.map(x=>[x.nctId,[x.reviewed,x.missing]])),{
  NCT06445023:[3,27],NCT06455202:[3,27],
  NCT06641076:[0,30],NCT07363577:[5,25],NCT07671911:[5,25],
  NCT05186818:[4,26],NCT05767346:[4,26],NCT06081894:[5,25],
  NCT03697109:[1,29],NCT04308590:[0,30]
 });
 assert.equal(new Set(result.tasks.map(t=>t.nctId+"|"+t.stage+"|"+t.metricId)).size,300);
 assert.equal(result.tasks.filter(x=>x.status==="SOURCE_CHECKED_PROVISIONAL_ONLY").length,30);
 assert.equal(result.tasks.filter(x=>x.status==="NO_SOURCE_REVIEWED_GRADE").length,270);
 assert.ok(result.tasks.every(t=>t.independentValidationStatus==="NOT_COMPLETED"&&
  t.approvedOverallScore===null&&t.calibratedFdaApprovalProbability===null));
});
test("each missing source task carries exact-trial issuer, registry, metric comparator and no fake values",()=>{
 const plan=build(classified);
 for(const task of plan.tasks.filter(x=>x.numericProvisionalGrade===null)){
  assert.match(task.nctId,/^NCT\d{8}$/);
  assert.ok(["TOP","BOTTOM"].includes(task.stage));
  assert.match(task.metricId,/^(pre|post)-[1-6]-[1-5]$/);
  assert.ok(task.metricName);
  assert.ok(task.requiredSourceEvidence.length>10);
  assert.ok(task.requiredIndependentBenchmark.length>5);
  assert.ok(task.criticalRisk.length>5);
  assert.ok(task.nextAction.includes("without a separate human signoff"));
  assert.match(task.issuerDisclosureUrl,/^https:\/\//);
  assert.equal(task.registrySourceUrl,"https://clinicaltrials.gov/study/"+task.nctId);
  assert.equal(task.reviewedPrimarySourceUrl,null);
  assert.equal(task.reviewedComparatorSourceUrl,null);
  assert.equal(task.reviewAssessedAt,null);
  assert.equal(task.primarySourceDated,null);
 }
 const reviewed=plan.tasks.filter(x=>x.numericProvisionalGrade!==null);
 assert.ok(reviewed.every(x=>[0,25,50,75,100].includes(x.numericProvisionalGrade)));
 assert.ok(reviewed.every(x=>x.reviewedPrimarySourceUrl?.startsWith("https://")));
 assert.ok(reviewed.every(x=>x.reviewedComparatorSourceUrl?.startsWith("https://")));
 const all=plan.allCsv.trimEnd().split("\r\n");
 const missing=plan.missingOnlyCsv.trimEnd().split("\r\n");
 assert.equal(all.length,301);
 assert.equal(missing.length,271);
 assert.equal(missing[0],all[0]);
 assert.ok(missing.slice(1).every(x=>x.includes("NO_SOURCE_REVIEWED_GRADE")));
 assert.ok(!plan.allCsv.includes("NCT00000000"));
});
test("unverified inventory and duplicate/incorrect stage data fail closed rather than receiving ratings",()=>{
 assert.throws(()=>build({...classified,
  pre:[...classified.pre,classified.pre[0]],total:742}),
  /RAAS_TOP_BOTTOM_DUPLICATE_CLASSIFIED_NCT/);
 assert.throws(()=>build({...classified,
  post:[...classified.post,classified.pre[0]],total:742}),
  /RAAS_TOP_BOTTOM_DUPLICATE_CLASSIFIED_NCT/);
 assert.throws(()=>build({...classified,
  pre:[...classified.pre,classified.unverified[0]],
  unverified:classified.unverified.slice(1)}),
  /RAAS_CLASSIFIED_COMPONENT_EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>build({...classified,
  post:[...classified.post,classified.unverified[0]],
  unverified:classified.unverified.slice(1)}),
  /RAAS_CLASSIFIED_COMPONENT_EXACT_ISSUER_SOURCE_REQUIRED/);
 assert.throws(()=>build({...classified,total:11000}),
  /RAAS_TOP_BOTTOM_COMPLETION_INVALID_CLASSIFICATION/);
 assert.throws(()=>build({...classified,total:762}),
  /RAAS_TOP_BOTTOM_COMPLETION_INVALID_CLASSIFICATION/);
});
test("iPhone TOP/BOTTOM UI shows full coverage and exports without scoring the unverified queue",()=>{
 const page=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,"app/RaasTopBottomCompletionPanel.tsx"),"utf8");
 const module=fs.readFileSync(path.join(root,"lib/raas-top-bottom-completion.ts"),"utf8");
 assert.match(page,/<RaasTopBottomCompletionPanel data=\{data\}\/>/);
 assert.match(panel,/data-raas-top-bottom-metric-completion/);
 assert.match(panel,/data-raas-missing-review-csv/);
 assert.match(panel,/data-raas-all-150-score-status-csv/);
 assert.match(panel,/data-raas-independent-review-handoff/);
 assert.match(panel,/data-raas-missing-tasks-expand/);
 assert.match(panel,/source-backed|source-classified|source review/i);
 assert.match(panel,/showAll\|\|t\.numericProvisionalGrade===null/);
 assert.match(panel,/task\.numericProvisionalGrade===null\?"Grade N\/A/);
 assert.match(panel,/role="status"/);
 assert.match(module,/buildRaasTopBottomCompletion/);
 assert.match(module,/RAAS_TOP_BOTTOM_UNVERIFIED_LEAKED_INTO_CLASSIFIED/);
 const compiled=ts.transpileModule(panel,{
  fileName:"RaasTopBottomCompletionPanel.tsx",reportDiagnostics:true,
  compilerOptions:{module:ts.ModuleKind.ESNext,
   target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}
 });
 assert.equal((compiled.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});

test("previously published clinical leads are graded, and no ungraded leads remain",()=>{
 const source=JSON.parse(sourceText("data/raas-classified-published-metric-leads.json"));
 assert.equal(source.schemaVersion,1);
 assert.equal(source.scope,"RAAS_EXACT_CLASSIFIED_PUBLISHED_CLINICAL_EVIDENCE_LEADS_UNGRADED");
 assert.equal(source.records.length,0);
 const plan=build(classified);
 const byTask=new Map(plan.tasks.map(x=>[x.nctId+"|"+x.metricId,x]));
 const byTrial=new Map([...classified.pre,...classified.post].map(x=>[x.nctId,x]));
 const seen=new Set();
 for(const lead of source.records){
  const trial=byTrial.get(lead.nctId),task=byTask.get(lead.nctId+"|"+lead.metricId);
  assert.ok(trial&&task);
  assert.equal(trial.ticker,lead.ticker);
  assert.equal(trial.evidence.drug,lead.drug);
  assert.equal(task.stage,lead.stage);
  assert.equal(task.numericProvisionalGrade,null);
  assert.equal(lead.approvedNumericGrade,null);
  assert.ok(lead.sourceUrl.startsWith("https://"));
  assert.ok(lead.referenceUrl.startsWith("https://"));
  assert.ok(lead.reportedResult.length>40);
  assert.ok(lead.reviewNeeded.length>40);
  assert.ok(!seen.has(lead.nctId+"|"+lead.metricId));
  seen.add(lead.nctId+"|"+lead.metricId);
 }
 const panel=sourceText("app/RaasTopBottomCompletionPanel.tsx");
 assert.match(panel,/publishedByMetric/);
 assert.ok(panel.includes("lead.approvedNumericGrade!==null"));
 assert.match(panel,/data-raas-published-ungraded-lead/);
 assert.match(panel,/Published clinical source · not a RAAS grade/);
});

test("external review remains optional for all 300 exact-NCT metrics",()=>{
 const result=build(classified);
 const csv=result.independentReviewHandoffCsv;
 const rows=csv.trimEnd().split("\r\n");
 assert.equal(rows.length,301);
 assert.match(rows[0],/signatureOrAuditReceiptId/);
 assert.match(rows[0],/reviewerIdentity/);
 assert.match(rows[0],/independentlyAdjudicatedMetricGrade/);
 assert.equal(rows.filter(x=>x.includes("PROVISIONAL_NOT_INDEPENDENTLY_VERIFIED")).length,30);
 assert.equal(rows.filter(x=>x.includes("PUBLISHED_UNGRADED_LEAD")).length,0);
 assert.equal(rows.filter(x=>x.includes("UNSCORED_MISSING_EVIDENCE")).length,270);
 assert.equal(rows.filter(x=>x.includes("2_REVIEW_PUBLISHED_SOURCE")).length,0);
 assert.match(csv,/NCT05186818/);
 assert.match(csv,/NEJMoa2401424/);
 assert.match(csv,/NCT03697109/);
 assert.match(csv,/41730814/);
 assert.doesNotMatch(csv,/CERTIFIED_INDEPENDENT_APPROVED/);
 // Every reviewer decision/identity/receipt remains intentionally blank.
 for(const row of rows.slice(1)){
  assert.match(row,/,{9}$/, "No prefilled human reviewer attestation");
 }
});

test("GRACE peer-reviewed efficacy mixed grade is one provisional BOTTOM component, with matching research exports",()=>{
 const feed=JSON.parse(sourceText("data/raas-reviewed-metric-assessments.json"));
 const grade=feed.records.filter(x=>x.nctId==="NCT03697109"&&x.metricId==="post-1-1");
 assert.equal(grade.length,1);
 assert.equal(grade[0].finding,"MIXED_EVIDENCE");
 assert.equal(grade[0].independentReview,"AI_SOURCE_CROSSCHECKED");
 assert.equal(grade[0].sourceUrl,"https://pubmed.ncbi.nlm.nih.gov/41730814/");
 assert.notEqual(grade[0].sourceUrl,grade[0].benchmarkSourceUrl);
 const completion=build(classified);
 const trial=completion.trials.find(x=>x.nctId==="NCT03697109");
 assert.ok(trial);
 assert.equal(trial.reviewed,1);
 assert.equal(trial.missing,29);
 assert.equal(trial.approvedOverallScore,null);
 const task=completion.tasks.find(x=>x.nctId==="NCT03697109"&&x.metricId==="post-1-1");
 assert.equal(task.numericProvisionalGrade,50);
 assert.equal(task.independentValidationStatus,"NOT_COMPLETED");
 const stageCsv=sourceText("public/raas-all-trials-partial-metric-ratings.csv").trimEnd().split(/\r?\n/);
 const post=stageCsv.filter(x=>x.startsWith("NCT03697109,CORT,")&&x.includes(",POST_RESEARCH_ONLY,"));
 assert.equal(post.length,1);
 const cells=post[0].split(",");
 assert.equal(cells[7],"1");assert.equal(cells[8],"1");
 assert.equal(cells[14],"post-1-1:50");assert.equal(cells[15],"29");
 assert.equal(cells[16],"");assert.equal(cells[17],"");
 const ledger=sourceText("public/raas-trial-score-ledger.csv").trimEnd().split(/\r?\n/);
 const record=ledger.filter(x=>x.startsWith("NCT03697109,CORT,"));
 assert.equal(record.length,1);
 assert.equal(record[0].split(",")[14],"1");
 assert.equal(record[0].split(",")[17],"");
 assert.equal(record[0].split(",")[18],"INCOMPLETE_30_METRIC_INDEPENDENT_REVIEW");
});


test("accepted CYTK trial publications become three exact-NCT source-backed research grades without FDA odds",()=>{
 const completion=build(classified);
 const expected=[["NCT05186818","post-1-1"],["NCT05186818","post-1-2"],["NCT05767346","post-1-1"]];
 for(const [nctId,metricId] of expected){
  const task=completion.tasks.find(x=>x.nctId===nctId&&x.metricId===metricId);
  assert.ok(task);
  assert.equal(task.numericProvisionalGrade,75);
  assert.equal(task.independentValidationStatus,"NOT_COMPLETED");
  assert.ok(task.reviewedPrimarySourceUrl?.startsWith("https://"));
  assert.equal(task.approvedOverallScore,null);
  assert.equal(task.calibratedFdaApprovalProbability,null);
 }
 assert.equal(completion.summary.provisionalMetricGrades,30);
 assert.equal(completion.summary.missingMetricGrades,270);
 assert.equal(completion.summary.publishedUngradedMetricLeads,0);
});
