"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(source.outputText,file);
};
const raw=require("../data/focus-r67-original-phase-source.json");
const {buildR67PhaseSource,FOCUS_R67_PHASE_SOURCE}=
 require("../lib/focus-r67-phase-source.ts");

test("Original immutable R66 source provides 29 source-only trial phase records and 23 provisional applications",()=>{
 const r=FOCUS_R67_PHASE_SOURCE;
 assert.ok(r,"all phase data and source relationships should pass");
 assert.equal(r.schema,"MAIN_R67_VIEW_ONLY_OF_ORIGINAL_R66_PHASE_SOURCE");
 assert.equal(r.run,42720903307);
 assert.equal(r.artifact,13720041195);
 assert.equal(r.ncts,29);
 assert.equal(r.applications,23);
 assert.equal(r.records.length,29);
 assert.equal(new Set(r.records.map(x=>x.nct)).size,29);
 assert.equal(r.sourceReportedPhase3Only,28);
 assert.equal(r.sourceReportedCombinedPhase23,1);
 assert.equal(r.sourceReportedCompleted,19);
 assert.equal(r.sourceReportedActiveNotRecruiting,8);
 assert.equal(r.sourceReportedRecruiting,2);
 assert.equal(r.verifiedPhaseReviews,0);
 assert.equal(r.signedScienceReviews,0);
 assert.equal(r.independentlyValidatedFDAForecasts,0);
 assert.equal(r.futureFDAOutcome,"ABSTAIN");
 assert.equal(r.measuredForecastAccuracy,null);
 assert.equal(r.productionOrClinicalWrites,false);
 assert.ok(r.records.every(x=>x.independentlyVerifiedTrialPhase===false &&
   x.scientificMethodScores===0&&x.independentPhaseReviewEventId===null&&
   x.predictedFDAOutcome==="ABSTAIN"&&x.predictionConfidence===null&&
   x.verifiedFdaApplicationStatus===null&&
   x.reviewFlags.length>=3));
});
test("Savara original Phase 3 is a source date, not a signed forecast",()=>{
 const r=FOCUS_R67_PHASE_SOURCE;
 const trial=r.records.find(x=>x.nct==="NCT04544293");
 assert.ok(trial);
 assert.equal(trial.ticker,"SVRA");
 assert.equal(trial.sourcePhase,"Phase 3");
 assert.equal(trial.sourceStatus,"ACTIVE NOT RECRUITING");
 assert.equal(trial.sourceUpdatedDate,"2026-11-03");
 assert.equal(trial.registryVerifiedMonth,"2026-10");
 assert.equal(trial.enrollment,164);
 assert.equal(trial.allocation,"RANDOMIZED");
 assert.equal(trial.primaryCompletionDate,"2023-11-30");
 assert.equal(trial.originalRegistryUrl,"https://clinicaltrials.gov/study/NCT04544293");
 assert.equal(trial.independentlyCompletedScientificLevel,null);
});
test("Mixed Phase 2/3 and allocation N/A need scientific design review, not automatic failures",()=>{
 const rows=FOCUS_R67_PHASE_SOURCE.records;
 const mixed=rows.find(x=>x.nct==="NCT04871282");
 const nonrandom=rows.find(x=>x.nct==="NCT06331299");
 assert.equal(mixed.sourcePhase,"Combined Phase 2/3");
 assert.equal(nonrandom.allocation,"NA");
 assert.match(mixed.reviewFlags.join(" "),/Combined Phase 2\/3/);
 assert.match(nonrandom.reviewFlags.join(" "),/Allocation N\/A/);
 assert.equal(mixed.predictedFDAOutcome,"ABSTAIN");
 assert.equal(nonrandom.predictedFDAOutcome,"ABSTAIN");
 assert.equal(rows.filter(x=>x.nct==="NCT02500381").length,1);
 assert.equal(rows.find(x=>x.nct==="NCT02500381").applicationCycles.length,2);
});
test("Fabricated source membership, date, status or numerical grade are rejected",()=>{
 const changes=[
  d=>d.rows.pop(),
  d=>d.rows[0][0]="NCT99999999",
  d=>d.rows[0][1]="PHASE1",
  d=>d.rows[0][2]="APPROVED",
  d=>d.rows[0][3]="2099-12-31",
  d=>d.rows[0][4]="2099-12",
  d=>d.rows[0][6]="UNKNOWN_MASKING",
  d=>d.rows[0][7]=-1,
  d=>d.rows[0][9]="not a date",
  d=>d.originalR66Sha256="a".repeat(64),
  d=>d.grade=5,
  d=>d.rows.push(d.rows[0]),
 ];
 for(let i=0;i<changes.length;i++){
  const d=structuredClone(raw);
  changes[i](d);
  assert.equal(buildR67PhaseSource(d),null,"source mutation "+i+" should fail closed");
 }
});
test("Assessment page positions original phase first, original methods then human reviewer readiness then FDA outcome",()=>{
 const p=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
 const view=fs.readFileSync(path.join(root,"app/predictions/assessment/OriginalRegistryPhaseR67.tsx"),"utf8");
 const css=fs.readFileSync(path.join(root,"app/predictions/assessment/OriginalRegistryPhaseR67.module.css"),"utf8");
 const a=p.indexOf("<OriginalRegistryPhaseR67"),b=p.indexOf("<OriginalMethodSourceLadderR64");
 const c=p.indexOf("<IndependentReviewerReadinessR65"),d=p.indexOf("R67 FDA prediction readiness summary");
 assert.ok(a>0&&a<b&&b<c&&c<d,"phase-first science and outcome ordering");
 assert.match(view,/Registry last update posted/);
 assert.match(view,/originalRegistryUrl/);
 assert.match(view,/NOT VERIFIED/);
 assert.match(view,/Study design, enrollment/);
 assert.match(view,/ABSTAIN/);
 assert.match(css,/@media\(max-width:470px\)/);
 assert.doesNotMatch(view,/fetch\(|methodGrade\s*:\s*[1-9]/);
});
