"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   esModuleInterop:true,jsx:ts.JsxEmit.ReactJS
 }});
 mod._compile(source.outputText,file);
};
const {FOCUS_SOURCE_R40:r,sourceStatusForCycle,verifyR40ResearchReadiness}=
  require("../lib/focus-source-access-rev40.ts");
const {FOCUS_PRELIMINARY_R39:research}=require("../lib/focus-preliminary-application-research.ts");
test("R40 exact 29/23 source retrieval receipt and archive digest",()=>{
  assert.equal(verifyR40ResearchReadiness(),r);
  assert.equal(r.trials,29);
  assert.equal(r.trialRegistryFetched,29);
  assert.equal(r.trialResultsModulePresent,12);
  assert.equal(r.trialResultsModuleNotPresent,17);
  assert.equal(r.provisionalApplicationGroups,23);
  assert.equal(r.groupsWithAtLeastOnePublicSourceRetrieved,23);
  assert.equal(r.canonicalApplicationUrls,21);
  assert.equal(r.additionalOfficialSecFallbackUrls,1);
  assert.equal(r.totalUniqueUrlsAttempted,22);
  assert.equal(r.totalUniqueUrlsFetched,21);
  assert.equal(r.jsonReceiptSha256,"0601058cd65f62380c3f3242b408f95ca13408f21d2845e589e9e4f5faf7d32c");
  assert.equal(r.exactGithubRun,42654460905);
  assert.equal(r.artifactId,13691348436);
  assert.equal(r.artifactExpiryUtc,"2027-02-07T16:24:36Z");
  assert.equal(r.sourceBodiesSavedToRepo,false);
  assert.equal(r.permanentOriginalSourceVault,false);
});
test("reported results module is not a successful or signed clinical test",()=>{
  assert.equal(r.resultsPostedNcts.length,12);
  assert.equal(new Set(r.resultsPostedNcts).size,12);
  assert.equal(r.singlePhase3RegistryRecords+r.combinedPhase2Phase3RegistryRecords,29);
  assert.equal(r.combinedPhaseRecordNct,"NCT04871282");
  assert.equal(r.sourceVersionsIndependentlyAuthenticated,0);
  assert.equal(r.qualifiedClinicalReviews,0);
  assert.equal(r.scientificGradesWritten,0);
  assert.equal(r.independentlyValidatedApplicationForecasts,0);
  assert.equal(r.verifiedHistoricalBacktests,0);
  assert.equal(r.measuredAccuracy,null);
  assert.equal(r.predictionProbability,null);
  assert.equal(r.officialFdaModelOutcome,"ABSTAIN");
});
test("Achieve only exception has official SEC fallback not new FDA review label",()=>{
  const abnormal=research.applications.filter(a=>
    sourceStatusForCycle(a.id)==="ISSUER_LINK_REDIRECTED_OFFICIAL_SEC_FALLBACK_FETCHED");
  assert.deepEqual(abnormal.map(x=>x.id),["achv-cytisinicline"]);
  assert.equal(r.blockedCanonicalSource.originalIssuerHttpStatus,301);
  assert.ok(r.blockedCanonicalSource.fallback.startsWith("https://www.sec.gov/Archives/edgar/data/949858/"));
  assert.equal(r.blockedCanonicalSource.fallbackFetched,true);
  assert.throws(()=>sourceStatusForCycle("cytk-aficamten-unknown"),/APPLICATION_ID_OR_ROSTER_MISMATCH/);
});
test("PREDICTIONS keeps R40 public retrieval distinct from 23 research leans and actual FDA model",()=>{
  const ui=fs.readFileSync(path.join(root,"app/predictions/FocusPreliminaryApplicationBoard.tsx"),"utf8");
  assert.ok(ui.includes("Revision 40 live source-access audit"));
  assert.ok(ui.includes("FOCUS_SOURCE_R40.blockedCanonicalSource.fallback"));
  assert.ok(ui.includes("byCycle.get(a.id)"));
  assert.ok(ui.includes("does not establish"));
  assert.ok(ui.includes("Official FDA prediction"));
  assert.ok(ui.includes("Review delay/extension prediction"));
  assert.equal(research.summary.sourceBasedPreliminaryResearchProfiles,23);
  assert.equal(research.summary.independentlyValidatedFDAForecasts,0);
});
