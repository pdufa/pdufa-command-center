"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
 fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(source.outputText,file);
};
const original=require("../data/focus-r60-original-source-trial-detail.json");
const {validateR60OriginalTrialResearch,FOCUS_R60_ORIGINAL_TRIAL_REVIEW}=
 require("../lib/focus-r60-original-trial-research.ts");
const clone=x=>structuredClone(x);

test("R60 source snap reproduces exactly 29 trial rows and 23 linked application cycles",()=>{
 const r=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
 assert.ok(r);
 assert.equal(r.run,42709199117);
 assert.equal(r.artifact,13715890359);
 assert.equal(r.trials.length,29);
 assert.equal(r.counts.applicationGroups,23);
 assert.equal(r.counts.postedPrimaryTables,16);
 assert.equal(r.counts.reportedStatisticalComparisons,20);
 assert.equal(r.counts.trialsWithCurrentPrimary,12);
 assert.equal(r.counts.trialsWithCurrentSafetyArms,12);
 assert.equal(r.counts.sourceReportedSeriousAeTermRows,244);
 assert.equal(r.counts.sourceReportedOtherAeTermRows,202);
 assert.equal(r.counts.independentlyValidatedFdaForecasts,0);
 assert.equal(r.predictionAccuracy,null);
 assert.equal(r.allOfficialFDAForecasts,"ABSTAIN");
 assert.equal(r.trials.reduce((sum,t)=>sum+t.primaryTables,0),16);
 assert.equal(r.trials.reduce((sum,t)=>sum+t.reportedAnalyses,0),20);
 assert.ok(r.trials.every(t=>
   t.officialApprovalOrCrlForecast==="ABSTAIN"&&
   t.officialReviewTimingForecast==="ABSTAIN"&&
   t.independentlyValidatedScientificReview===false&&t.fdaProbability===null));
});

test("Savara source-reported efficacy and serious adverse-event arm denominators remain ungraded",()=>{
 const r=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
 const t=r.trials.find(x=>x.nct==="NCT04544293");
 assert.equal(t.ticker,"SVRA");
 assert.equal(t.primaryTables,1);
 assert.equal(t.reportedAnalyses,1);
 assert.equal(t.endpoints[0][1][0][0],"0.0007");
 assert.equal(t.endpoints[0][1][0][1],"6.0");
 assert.deepEqual(t.seriousAeArmAffectedAtRisk.map(x=>x[1]),[[14,81],[20,83]]);
 assert.equal(t.independentlyValidatedScientificReview,false);
});

test("Absent current registry source triggers recovery, never a false trial failure",()=>{
 const r=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
 const capr=r.trials.find(t=>t.nct==="NCT05126758");
 assert.equal(capr.primaryTables,0);
 assert.equal(capr.safetyArms,0);
 assert.ok(capr.reviewExceptions.includes("NO_CURRENT_POSTED_PRIMARY_TABLE_CHECK_OTHER_ORIGINALS"));
 assert.ok(capr.reviewExceptions.includes("NO_CURRENT_POSTED_SAFETY_ARM_TABLE_CHECK_OTHER_ORIGINALS"));
 assert.equal(capr.officialApprovalOrCrlForecast,"ABSTAIN");
});

test("One shared trial can support two FDA application groups without double counting",()=>{
 const r=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
 const s=r.trials.find(x=>x.nct==="NCT02500381");
 assert.deepEqual(s.cycles,["srpt-casimersen","srpt-golodirsen"]);
 assert.equal(r.trials.filter(x=>x.nct===s.nct).length,1);
});

test("Forged source hash, statistical fields, fake clinical review and extra members fail closed",()=>{
 const variations=[
  v=>v.run=0,
  v=>v.artifact=0,
  v=>v.utc="2030-01-01",
  v=>v.sourceHashes.r55="0".repeat(64),
  v=>v.trials[0].h="0".repeat(64)+"0",
  v=>v.trials[0].p=8,
  v=>v.trials[0].q=10,
  v=>v.trials[0].a=0,
  v=>v.trials[0].m[0][1]=[["0.01","2"]],
  v=>v.trials[0].s[0][1]=[900,318],
  v=>v.trials[0].n="NCT99999999",
  v=>v.trials[1].n=v.trials[0].n,
  v=>v.trials.push(structuredClone(v.trials[0])),
  v=>v.trials[0].e=["UNVERIFIED_PREDICTION_APPROVED"],
  v=>v.trials[0].fdaProbability=0.98,
  v=>v.validatedFdaForecasts=23,
 ];
 for(let i=0;i<variations.length;i++){
  const changed=clone(original);
  variations[i](changed);
  assert.equal(validateR60OriginalTrialResearch(changed),null,"tamper "+i);
 }
});

test("Prediction screen includes expandable R60 source evidence and zero reviewer write handlers",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 const component=fs.readFileSync(path.join(root,"app/predictions/FocusOriginalSourceChallengeR60.tsx"),"utf8");
 const css=fs.readFileSync(path.join(root,"app/predictions/FocusOriginalSourceChallengeR60.module.css"),"utf8");
 assert.match(page,/import FocusOriginalSourceChallengeR60/);
 assert.ok(page.includes("<FocusOriginalSourceChallengeR60/>"));
 assert.match(component,/Original ClinicalTrials.gov record/);
 assert.match(component,/No deposited statistical comparison/);
 assert.match(component,/Read-only research snapshot/);
 assert.match(component,/Expand all findings/);
 assert.match(component,/Missing current registry results do not establish/);
 assert.match(css,/@media\(max-width:480px\)/);
 assert.doesNotMatch(component,/fetch\(|submitClinicalGrade|POST\s*\/api|setReviewerSignoff/);
});
