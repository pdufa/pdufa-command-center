"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(source.outputText,file);
};
const {buildR68EvidenceRecovery,FOCUS_R68_EVIDENCE_RECOVERY}=
 require("../lib/focus-r68-evidence-recovery.ts");
const {FOCUS_R60_ORIGINAL_TRIAL_REVIEW}=
 require("../lib/focus-r60-original-trial-research.ts");
const {FOCUS_R64_METHOD_PAGE_VIEW}=
 require("../lib/focus-r64-original-method-page-view.ts");
const {FOCUS_R65_REVIEW_GATES}=
 require("../lib/focus-r65-independent-review-gates.ts");
const {FOCUS_R67_PHASE_SOURCE}=
 require("../lib/focus-r67-phase-source.ts");

test("R68 reconciles all original immutable 29 trials, 23 cycles and source-coverage counts",()=>{
 const r=FOCUS_R68_EVIDENCE_RECOVERY;
 assert.ok(r);
 assert.equal(r.schema,"MAIN_R68_ORIGINAL_SOURCE_RECOVERY_WORKLIST_ONLY");
 assert.equal(r.uniqueTrials,29);
 assert.equal(r.provisionalApplicationCycles,23);
 assert.equal(r.rows.length,29);
 assert.equal(new Set(r.rows.map(x=>x.nct)).size,29);
 assert.equal(r.postedPrimaryTrials,12);
 assert.equal(r.currentSafetyArmTrials,12);
 assert.equal(r.trialsWithCurrentPdfPageLeads,12);
 assert.equal(r.trialsWithoutCurrentPostedPrimary,17);
 assert.equal(r.trialsWithoutCurrentSafetyArmTables,17);
 assert.equal(r.trialsWithoutCurrentPdfPageLeads,17);
 assert.equal(r.scientificDomainSourcePositions,232);
 assert.equal(r.originalMachinePageLeads,466);
 assert.equal(r.rows.reduce((n,x)=>n+x.machinePageLeads,0),466);
 assert.equal(r.independentPhaseReviews,0);
 assert.equal(r.independentClinicalGrades,0);
 assert.equal(r.qualifiedReviewerSignoffs,0);
 assert.equal(r.validatedFDAForecasts,0);
 assert.equal(r.historicalPredictionAccuracy,null);
 assert.equal(r.allFutureFdaOutcomes,"ABSTAIN");
 assert.equal(r.sourceMissingDoesNotMeanTrialFailure,true);
 assert.equal(r.sourceRecoveryIsNotAClinicalRanking,true);
 assert.equal(r.noWritesToHistoricalOutcomesOrProduction,true);
 assert.ok(r.rows.every(x=>x.scientificAssessmentLevel==="UNASSESSED_SOURCE_ONLY"&&
   x.qualifiedReviewerSigned===false&&x.clinicalScienceScore===null&&
   x.officialFutureFdaOutcome==="ABSTAIN"&&
   x.historicalMeasuredAccuracy===null&&x.sourceRecoveryTasks.length===5));
 assert.ok(r.rows.every((x,i,a)=>i===0||
   a[i-1].missingInRetainedRegistryCopyCount>=x.missingInRetainedRegistryCopyCount),
   "sort only by missing source categories, not prognostic clinical results");
});
test("Current archived source fields identify true work items without interpreting outcome",()=>{
 const r=FOCUS_R68_EVIDENCE_RECOVERY;
 const svra=r.rows.find(x=>x.nct==="NCT04544293");
 assert.equal(svra.ticker,"SVRA");
 assert.ok(svra.currentPostedPrimaryTables>0);
 assert.ok(svra.currentSafetyArms>0);
 assert.equal(svra.currentPdfFilesWithMachinePageLeads,2);
 assert.equal(svra.missingInRetainedRegistryCopyCount,0);
 assert.equal(svra.officialFutureFdaOutcome,"ABSTAIN");
 const capr=r.rows.find(x=>x.nct==="NCT05126758");
 assert.equal(capr.sourcePrimaryTableAvailable,false);
 assert.equal(capr.sourcePdfPageLeadsAvailable,false);
 assert.match(capr.sourceRecoveryTasks[2].detail,/No primary table in this retained current registry copy/);
 assert.equal(capr.officialFutureFdaOutcome,"ABSTAIN");
 const mixed=r.rows.find(x=>x.nct==="NCT04871282");
 assert.ok(mixed.designAndOriginalSourceExceptions.some(x=>x.includes("Combined Phase 2/3")));
 const nonrandom=r.rows.find(x=>x.nct==="NCT06331299");
 assert.ok(nonrandom.designAndOriginalSourceExceptions.some(x=>x.includes("Allocation N/A")));
 const shared=r.rows.find(x=>x.nct==="NCT02500381");
 assert.equal(shared.applicationCycles.length,2);
 assert.equal(r.rows.filter(x=>x.nct===shared.nct).length,1);
});
test("Cross-source mismatch or a fabricated reviewer/forecast state fails closed",()=>{
 const alterations=[
  ()=>{
    const s=structuredClone(FOCUS_R60_ORIGINAL_TRIAL_REVIEW);
    s.trials[0].nct="NCT99999999";
    return [s,FOCUS_R64_METHOD_PAGE_VIEW,FOCUS_R65_REVIEW_GATES,FOCUS_R67_PHASE_SOURCE];
  },
  ()=>{
    const s=structuredClone(FOCUS_R64_METHOD_PAGE_VIEW);
    s.trials[0].sourcePdfDocumentsWithPageLeads=999;
    return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,s,FOCUS_R65_REVIEW_GATES,FOCUS_R67_PHASE_SOURCE];
  },
  ()=>{
    const s=structuredClone(FOCUS_R65_REVIEW_GATES);
    s.records[0].reviewedPhaseVerified=true;
    return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,FOCUS_R64_METHOD_PAGE_VIEW,s,FOCUS_R67_PHASE_SOURCE];
  },
  ()=>{
    const s=structuredClone(FOCUS_R67_PHASE_SOURCE);
    s.records[0].predictedFDAOutcome="APPROVED";
    return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,FOCUS_R64_METHOD_PAGE_VIEW,FOCUS_R65_REVIEW_GATES,s];
  },
  ()=>{
    const s=structuredClone(FOCUS_R67_PHASE_SOURCE);
    s.records.pop();
    return [FOCUS_R60_ORIGINAL_TRIAL_REVIEW,FOCUS_R64_METHOD_PAGE_VIEW,FOCUS_R65_REVIEW_GATES,s];
  },
  ()=>{
    const s=structuredClone(FOCUS_R60_ORIGINAL_TRIAL_REVIEW);
    s.trials[0].cycles=["fake-cycle"];
    return [s,FOCUS_R64_METHOD_PAGE_VIEW,FOCUS_R65_REVIEW_GATES,FOCUS_R67_PHASE_SOURCE];
  }
 ];
 for(let i=0;i<alterations.length;i++){
   const args=alterations[i]();
   assert.equal(buildR68EvidenceRecovery(...args),null,"tampered source "+i+" must fail closed");
 }
});
test("Actual route, filters and exact study links are mounted without reviewer submission",()=>{
 const get=f=>fs.readFileSync(path.join(root,f),"utf8");
 const route=get("app/predictions/evidence-gaps/page.tsx");
 const board=get("app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx");
 const overview=get("app/predictions/page.tsx");
 const assessment=get("app/predictions/assessment/page.tsx");
 assert.match(route,/EvidenceRecoveryBoardR68/);
 assert.match(board,/Search source recovery trials/);
 assert.match(board,/Filter source recovery trials/);
 assert.match(board,/sourceRecoveryTasks/);
 assert.match(board,/trial\.assessmentUrl/);
 assert.match(board,/ABSTAIN/);
 assert.match(board,/NOT CALIBRATED/);
 assert.match(overview,/\/predictions\/evidence-gaps/);
 assert.match(assessment,/\/predictions\/evidence-gaps/);
 assert.doesNotMatch(board,/fetch\(|POST\s*\/api|signClinicalReview|setClinicalScore/);
});
