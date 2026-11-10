"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const src=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(src.outputText,file);
};
const raw=require("../data/focus-r71-five-main-publication-source-review.json");
const {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE,buildR71PivotalEvidenceIntake}=
 require("../lib/focus-r71-pivotal-evidence-intake.ts");

test("Five exact studies, forty unsigned review positions, zero validated future FDA forecasts",()=>{
 const x=FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE;
 assert.ok(x,"valid original source-role, DOI and 29/23 reference crosswalk");
 assert.equal(x.schema,"MAIN_R71_FIVE_SOURCE_LINKED_MAIN_REPORT_SCIENCE_REVIEW_INTAKE");
 assert.equal(x.focusNcts,29);
 assert.equal(x.applicationCycles,23);
 assert.equal(x.candidateMainResultPublications,5);
 assert.equal(x.sourceReviewDomainsPerTrial,8);
 assert.equal(x.sourceResearchPositionsAwaitingAdjudication,40);
 assert.equal(x.casesWithOriginalPublishedJournalProtocolOrAppendixListings,3);
 assert.equal(x.studiesWithOpenPMCFullArticleAndSupplementExcerpts,1);
 assert.equal(x.independentlyValidatedSignedSAPVersions,0);
 assert.equal(x.qualifiedClinicalScienceReviewSignoffs,0);
 assert.equal(x.scientificallyValidatedFutureFDAForecasts,0);
 assert.equal(x.historicalAccuracy,null);
 assert.equal(x.officialFutureFDAOutcome,"ABSTAIN");
 assert.equal(x.noHistoricalOutcomeLookupsOrProductionWrites,true);
 assert.equal(x.sourceSummaryCannotBeUsedAsAClinicalGrade,true);
 assert.equal(x.fiveRecords.length,5);
 assert.equal(new Set(x.fiveRecords.map(r=>r.nct)).size,5);
 assert.deepEqual(x.fiveRecords.map(r=>r.pmid).sort(),
  ["40587141","42233621","42526472","42663312","42849489"]);
 for(const t of x.fiveRecords){
  assert.equal(t.domains.length,8);
  assert.equal(t.sourceMayPostdateBlindPredictionOrigin,true);
  assert.equal(t.originalSignedSapChronologyVerified,false);
  assert.equal(t.completeOriginalArticleAndSupplementsScientificallyAdjudicated,false);
  assert.equal(t.qualifiedReviewerSignoffs,0);
  assert.equal(t.scienceGrade,null);
  assert.equal(t.futureFDAOutcome,"ABSTAIN");
  assert.equal(t.historicalValidationAccuracy,null);
  assert.ok(t.domains.every(d=>d.status==="SOURCE_LEADS_PENDING_SCIENTIFIC_ADJUDICATION"&&
   d.scientificGrade===null&&d.reviewerSigned===false));
 }
});
test("NCT source findings retain distinct endpoint populations and original supplement limitations",()=>{
 const by=new Map(FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE.fiveRecords.map(t=>[t.nct,t]));
 const capr=by.get("NCT05126758");
 assert.match(capr.reportedEffect,/4.55/);
 assert.match(capr.reportedEffect,/0.029/);
 assert.equal(capr.supplementUrl,null);
 const indigo=by.get("NCT05662241");
 assert.match(indigo.reportedEffect,/Hazard ratio 0.44/);
 assert.match(indigo.supplementStatus,/NOT_INDEPENDENTLY_RECONCILED/);
 const acacia=by.get("NCT06081894");
 assert.match(acacia.primaryEndpoint,/Two primary endpoints/);
 assert.match(acacia.safetyObservation,/10.5% vs 0.8%/);
 const htn=by.get("NCT06153693");
 assert.match(htn.reportedEffect,/-9.1 mmHg/);
 assert.match(htn.supplementStatus,/LOCK_CHRONOLOGY_PENDING/);
 assert.match(htn.specificReviewNeeds.join(" "),/1000-imputation/);
 assert.match(htn.specificReviewNeeds.join(" "),/MAR\/MNAR/);
 const rapid=by.get("NCT06343779");
 assert.match(rapid.reportedEffect,/1.28 h/);
 assert.match(rapid.analysisPopulation,/88 patients/);
 assert.match(rapid.specificReviewNeeds.join(" "),/crossover/);
 assert.equal(rapid.supplementUrl,null);
});

test("Tamper trial identity, published effect, source dates, false outcome or source access flags fails closed",()=>{
 const mutators=[
  r=>r.cases.pop(),
  r=>r.cases[0].nct="NCT99999999",
  r=>r.cases[0].pmid="99999999",
  r=>r.cases[0].doi="10.9999/fake",
  r=>r.cases[0].ticker="FAKE",
  r=>r.cases[0].published="2027-12-31",
  r=>r.cases[0].sourceAccess="INDEPENDENTLY_VALIDATED_FULL_SCIENCE",
  r=>r.cases[0].journalUrl="https://attacker.com/fake",
  r=>r.cases[0].specificReviewNeeds=[],
  r=>r.cases[0].fullOriginalPaperIndependentlyRead=true,
  r=>r.originalSignedPreunblindingStatisticalPlansVerified=5,
  r=>r.independentQualifiedScienceReviews=5,
  r=>r.validatedFutureFdaApplicationForecasts=23,
  r=>r.officialFDAForecast="APPROVE",
  r=>r.grade=99,
 ];
 for(let i=0;i<mutators.length;i++){
  const copy=structuredClone(raw);
  mutators[i](copy);
  assert.equal(buildR71PivotalEvidenceIntake(copy),null,
    "fabricated study/source review "+i+" must fail closed");
 }
});

test("True source-review card mounts inside prior original PubMed/FOCUS research dashboard",()=>{
 const c=fs.readFileSync(path.join(root,
 "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const board=fs.readFileSync(path.join(root,
 "app/predictions/evidence-gaps/OriginalPublicationLeadsR69.tsx"),"utf8");
 const css=fs.readFileSync(path.join(root,
 "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.module.css"),"utf8");
 assert.match(board,/ScientificOriginalsIntakeR71/);
 assert.ok(board.indexOf("<ScientificOriginalsIntakeR71")>
  board.indexOf("<OriginalPubmedArticleMetadataR70"));
 assert.match(c,/published primary finding/);
 assert.match(c,/domain-by-domain scientific review requirements/);
 assert.match(c,/ABSTAIN/);
 assert.match(c,/protocol and supplemental materials listing/);
 assert.match(c,/Independent|independent/i);
 assert.match(css,/@media\(max-width:470px\)/);
 assert.doesNotMatch(c,/fetch\(|POST\s*\/api|setGrade\(|userSignedApproval/);
});
