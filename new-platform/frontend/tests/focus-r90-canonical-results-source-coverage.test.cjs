"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(x.outputText,file);
};
const original=require("../data/focus-r90-nine-existing-result-page-readbacks-20261110.json");
const originalRepoFocus=require("../../backend/app/data/focus_snapshot.json");
const {R89_HISTORICAL_SOURCE_RECOVERY}=require("../lib/focus-r89-historical-source-recovery.ts");
const {R89_NEW_PUBLIC_SOURCE_LEADS}=require("../lib/focus-r89-new-public-source-leads.ts");
const {R90_CANONICAL_RESULTS_RECOVERY,buildR90CanonicalResultsSourceCoverage}=
 require("../lib/focus-r90-canonical-results-source-coverage.ts");

test("R90 restores all nine source URLs that already existed in canonical immutable 29-FOCUS data",()=>{
 const x=R90_CANONICAL_RESULTS_RECOVERY;assert.ok(x);
 assert.equal(x.exactFocusNcts,29);
 assert.equal(x.provisionalCycles,23);
 assert.equal(x.trialsWithoutCurrentRegistryProtocolSAP,17);
 assert.equal(x.existingPriorFivePivotalPublicationResearchLeads,5);
 assert.equal(x.additionalThreeConferenceIssuerResearchLeads,3);
 assert.equal(x.alreadyHeldNineIssuerSecResultsLinksVerified,9);
 assert.equal(x.sourceResultLeadCoverageForSeventeen,17);
 assert.equal(x.rows.length,9);
 assert.equal(new Set(x.rows.map(r=>r.nct)).size,9);
 assert.equal(new Set(x.rows.map(r=>r.url)).size,8);
 assert.equal(x.directExactNctInNineReports,5);
 assert.equal(x.nameAndRegistryCrosswalkInNineReports,4);
 const canonical=new Map(originalRepoFocus.records.map(r=>[r.nct,r]));
 assert.equal(canonical.size,29);
 for(const r of x.rows){
  const baseline=canonical.get(r.nct);
  assert.ok(baseline,"FOCUS source member "+r.nct);
  assert.equal(baseline.ticker,r.ticker);
  assert.equal(baseline.resultsUrl,r.url);
  assert.equal(r.exactRegistryUrl,"https://clinicaltrials.gov/study/"+r.nct);
  assert.equal(r.noSAP,true);assert.equal(r.noScienceReview,true);
  assert.equal(r.FDAForecast,"ABSTAIN");
 }
 assert.equal(x.signedOriginalSAPsAuthenticated,0);
 assert.equal(x.independentClinicalReviewSignoffs,0);
 assert.equal(x.calibratedFDAPredictions,0);
});
test("R90 plus R89 gives 17 unique original result research leads without changing pivotal publication count",()=>{
 const five=new Set(R89_HISTORICAL_SOURCE_RECOVERY.rows.filter(
  r=>r.originalIndexedPivotalPublication).map(r=>r.nct));
 const three=new Set(R89_NEW_PUBLIC_SOURCE_LEADS.rows.map(r=>r.nct));
 const nine=new Set(R90_CANONICAL_RESULTS_RECOVERY.rows.map(r=>r.nct));
 const combined=[...five,...three,...nine];
 assert.equal(combined.length,17);
 assert.equal(new Set(combined).size,17);
 assert.deepEqual(new Set(combined),
  new Set(R89_HISTORICAL_SOURCE_RECOVERY.rows.map(r=>r.nct)));
 assert.equal(R89_NEW_PUBLIC_SOURCE_LEADS.originalFiveStudyPivotalIndexStill,5);
 assert.equal(R90_CANONICAL_RESULTS_RECOVERY.existingPriorFivePivotalPublicationResearchLeads,5);
});
test("R90 checks result-page NCT provenance: five direct NCT, four registry name matches",()=>{
 const rows=R90_CANONICAL_RESULTS_RECOVERY.rows;
 const direct=rows.filter(r=>r.verification==="REPORT_DIRECTLY_NAMES_EXACT_NCT");
 const cross=rows.filter(r=>r.verification===
 "TRIAL_NAME_REGISTRY_CROSSWALK_NOT_EXPLICIT_NCT_ON_REPORT");
 assert.deepEqual(new Set(direct.map(r=>r.nct)),
  new Set(["NCT06445023","NCT06455202","NCT04871282",
   "NCT06669754","NCT06087276"]));
 assert.deepEqual(new Set(cross.map(r=>r.nct)),
  new Set(["NCT05059223","NCT05113745","NCT05244304","NCT05208047"]));
 assert.equal(rows.filter(r=>r.ticker==="CLDX").length,2);
 assert.equal(new Set(rows.filter(r=>r.ticker==="CLDX").map(r=>r.url)).size,1);
});
test("R90 rejects invented source URLs, cross-NCT mappings, upgraded science and changed census",()=>{
 const attacks=[
  x=>{x.records[0].nct="NCT00000000";},
  x=>{x.records[0].url="https://attacker.example/fake";},
  x=>{x.records[0].ticker="WRONG";},
  x=>{x.records[0].publicDate="2026-11-09";},
  x=>{x.records[0].idEvidence="REPORT_DIRECTLY_NAMES_EXACT_NCT";},
  x=>{x.records[0].originalClinicalTrialRegistryUrl="https://other.example";},
  x=>{x.records[0].authenticatedOriginalSignedSAP=true;},
  x=>{x.records[0].qualifiedIndependentClinicalAssessment=true;},
  x=>{x.records[0].FDAOutcome="APPROVAL";},
  x=>{x.records[0].originalResultPageVisitedAndAvailable=false;},
  x=>{x.records.pop();},
  x=>{x.records[1].nct=x.records[0].nct;},
  x=>{x.reportsThatExplicitlyPrintNct=9;},
  x=>{x.peerReviewedFullManuscriptsNewlyAuthenticated=9;}
 ];
 for(const change of attacks){
  const x=structuredClone(original);change(x);
  assert.equal(buildR90CanonicalResultsSourceCoverage(x),null);
 }
});
test("R90 browser view links original issuer/SEC result sources and never confuses them with signed SAPs",()=>{
 const view=fs.readFileSync(path.join(root,
  "app/predictions/source-recovery/page.tsx"),"utf8");
 const cards=fs.readFileSync(path.join(root,
  "app/predictions/source-recovery/OriginalHistoryRecoveryR89Client.tsx"),"utf8");
 assert.match(view,/R90_CANONICAL_RESULTS_RECOVERY/);
 assert.match(view,/sourceResultLeadCoverageForSeventeen/);
 assert.match(cards,/canonicalSourceLeads/);
 assert.match(cards,/Verified accessible issuer\/SEC source already retained in FOCUS/);
 assert.match(cards,/This issuer\/SEC page explicitly prints the exact NCT ID/);
 assert.match(cards,/exact NCT requires separate official registry trial-name match/);
 assert.match(cards,/Final signed SAP: NOT VERIFIED/);
 assert.match(cards,/FDA forecast: ABSTAIN/);
 assert.doesNotMatch(cards,/setGrade\(|submitClinicalScore|probabilityPercent|POST\s*\/api/);
});
