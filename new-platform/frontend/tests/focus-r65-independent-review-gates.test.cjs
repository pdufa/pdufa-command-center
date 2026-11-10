"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
  const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
      jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
  mod._compile(source.outputText,file);
};
const {FOCUS_R64_METHOD_PAGE_VIEW}=
  require("../lib/focus-r64-original-method-page-view.ts");
const {FOCUS_R65_REVIEW_GATES,buildR65ReviewGateDisplay,
       R65_DOMAIN_QUESTIONS,R65_REQUIRED_REVIEW_FIELDS}=
  require("../lib/focus-r65-independent-review-gates.ts");
const clone=x=>structuredClone(x);

test("29 trials, 23 groups and 232 independently ungraded source-review tasks",()=>{
 const out=FOCUS_R65_REVIEW_GATES;
 assert.ok(out,"R64 evidence must pass source integrity first");
 assert.equal(out.schema,"MAIN_R65_READ_ONLY_INDEPENDENT_REVIEW_GATE_DISPLAY");
 assert.equal(out.originalReviewRun,42717833879);
 assert.equal(out.originalReviewArtifact,13717848415);
 assert.equal(out.originalSourceSha256,"1238d5a0ed120cd47d05dec12486e59e2bf8dbd6e7b73b989372955db622127a");
 assert.equal(out.uniqueTrials,29);
 assert.equal(out.provisionalApplications,23);
 assert.equal(out.requiredMethodReviews,232);
 assert.equal(out.originalMachinePageLeads,466);
 assert.equal(out.records.length,29);
 assert.equal(new Set(out.records.map(x=>x.nct)).size,29);
 assert.equal(out.records.reduce((n,t)=>n+t.methodTasks.length,0),232);
 assert.equal(out.records.reduce((n,t)=>n+t.sourceLeads,0),466);
 assert.equal(out.signedPhaseReviews,0);
 assert.equal(out.signedScientificReviews,0);
 assert.equal(out.releasedMethodGrades,0);
 assert.equal(out.independentlyValidatedFdaForecasts,0);
 assert.equal(out.predictionAccuracy,null);
 assert.equal(out.officialFutureFdaOutcome,"ABSTAIN");
 assert.equal(out.notAnEnabledReviewerSubmissionEndpoint,true);
 assert.equal(out.productionOrLedgerWrites,false);
 assert.ok(out.records.every(t=>t.reviewedPhaseVerified===false
   &&t.clinicalAssessmentLevel==="UNASSESSED_SOURCE_ONLY"
   &&t.qualifiedSignedGrades===0
   &&t.methodTasks.every(m=>
     m.reviewerAttested===false&&m.secondaryVerifierAttested===false
     &&m.grade===null&&m.failureOrSuccess==="UNDETERMINED"
     &&m.clinicalDisposition==="PENDING_QUALIFIED_HUMAN_ADJUDICATION")));
});

test("Savara 47 source page leads have eight explicit independent method checklists",()=>{
 const r=FOCUS_R65_REVIEW_GATES.records.find(x=>x.nct==="NCT04544293");
 assert.ok(r);
 assert.equal(r.sourceLeads,47);
 assert.equal(r.methodTasks.length,8);
 const multiplicity=r.methodTasks.find(x=>x.domain==="MULTIPLICITY_CONTROL");
 assert.equal(multiplicity.sourcePageLeads,6);
 assert.ok(multiplicity.requiredQuestions.some(x=>x.includes("original family-wise hypothesis")));
 assert.ok(multiplicity.evidenceFields.includes("firstPublicDateEvidence"));
 assert.ok(multiplicity.evidenceFields.includes("secondIndependentVerifier"));
 assert.equal(multiplicity.readyToRecordClinicalMethodGrade,undefined);
 assert.equal(multiplicity.grade,null);
});

test("17 source-free current PDFs become human retrieval tasks, not failed clinical findings",()=>{
 const items=FOCUS_R65_REVIEW_GATES.records.filter(t=>t.sourceLeads===0);
 assert.equal(items.length,17);
 assert.ok(items.every(t=>t.methodTasks.length===8
   &&t.methodTasks.every(d=>d.grade===null
     &&d.sourcePageLeads===0
     &&d.failureOrSuccess==="UNDETERMINED")));
});

test("Every domain has a distinct triad of questions and 17 signed-review requirements",()=>{
 assert.equal(R65_DOMAIN_QUESTIONS.length,8);
 assert.equal(new Set(R65_DOMAIN_QUESTIONS.map(x=>JSON.stringify(x))).size,8);
 assert.ok(R65_DOMAIN_QUESTIONS.every(q=>q.length===3));
 assert.equal(R65_REQUIRED_REVIEW_FIELDS.length,17);
 assert.ok(R65_REQUIRED_REVIEW_FIELDS.includes("originalDocumentContentSha256"));
 assert.ok(R65_REQUIRED_REVIEW_FIELDS.includes("unblindingOrReadoutDateEvidence"));
 assert.ok(R65_REQUIRED_REVIEW_FIELDS.includes("secondIndependentVerifier"));
});

test("Forged score, clinical phase, source membership, missing methods must fail closed",()=>{
 const tamper=[
  x=>x.trials.pop(),
  x=>x.trials[0].independentlyCompletedAssessmentLevel=3,
  x=>x.trials[0].signedScientificGrades=1,
  x=>x.trials[0].officialFdaOutcome="APPROVAL",
  x=>x.trials[0].domains[0].qualifiedReviewerSigned=true,
  x=>x.trials[0].domains[0].scientificScore=4,
  x=>x.trials[0].domains[0].references.pop(),
  x=>x.trials[0].domains.pop(),
  x=>x.independentlyValidatedFdaForecasts=23,
  x=>x.sourcePageLeadCount=0,
 ];
 for(let i=0;i<tamper.length;i++){
  const source=clone(FOCUS_R64_METHOD_PAGE_VIEW);
  tamper[i](source);
  assert.equal(buildR65ReviewGateDisplay(source),null,
    "malicious or stale source "+i+" must fail closed");
 }
 assert.equal(buildR65ReviewGateDisplay(null),null);
});

test("R65 read-only reviewer tasks mounted after original PDF page review",()=>{
 const p=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
 const comp=fs.readFileSync(path.join(root,
   "app/predictions/assessment/IndependentReviewerReadinessR65.tsx"),"utf8");
 assert.match(p,/import IndependentReviewerReadinessR65/);
 assert.match(p,/<IndependentReviewerReadinessR65/);
 assert.ok(p.indexOf("<OriginalMethodSourceLadderR64")<
   p.indexOf("<IndependentReviewerReadinessR65"));
 assert.ok(p.indexOf("<IndependentReviewerReadinessR65")<
   p.indexOf("<ScientificMethodMatrix"));
 assert.match(comp,/UNASSESSED · SOURCE ONLY/);
 assert.match(comp,/REVIEW PENDING/);
 assert.match(comp,/No independent reviewer has signed/);
 assert.match(comp,/ABSTAIN · NOT CALIBRATED/);
 assert.match(comp,/No signoff fields are filled automatically/);
 assert.doesNotMatch(comp,/<form|onSubmit|fetch\(|POST\s*\/api/);
});
