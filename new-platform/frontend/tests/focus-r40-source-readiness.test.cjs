"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
      fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const extension of [".ts",".tsx"])require.extensions[extension]=(mod,file)=>{
  const source=fs.readFileSync(file,"utf8");
  const output=ts.transpileModule(source,{compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
  }});
  mod._compile(output.outputText,file);
};
const pin=require("../data/focus-r40-public-source-audit.json");
const {buildFocusR40SourceStatus,FOCUS_R40_SOURCE_STATUS}=require("../lib/focus-r40-source-readiness.ts");
const {FOCUS_PRELIMINARY_R39}=require("../lib/focus-preliminary-application-research.ts");
const clone=x=>structuredClone(x);
test("all 29 exact NCTs, 23 applications and original retrieved receipt are pinned",()=>{
  const s=FOCUS_R40_SOURCE_STATUS;
  assert.ok(s);
  assert.equal(s.counts.registryRetrieved,29);
  assert.equal(s.counts.applicationGroups,23);
  assert.equal(s.counts.applicationGroupsWithPublicSource,23);
  assert.equal(s.counts.registryResultsSectionPresent,12);
  assert.equal(s.counts.registryResultsSectionNotPresent,17);
  assert.equal(s.trialStatus.length,29);
  assert.equal(s.groupStatus.length,23);
  assert.deepEqual(new Set(s.trialStatus.map(x=>x.nct)),new Set(FOCUS_PRELIMINARY_R39.trials.map(x=>x.nct)));
  assert.deepEqual(new Set(s.groupStatus.map(x=>x.cycleId)),new Set(FOCUS_PRELIMINARY_R39.applications.map(x=>x.id)));
  assert.equal(s.sourceReceiptSha256,"0601058cd65f62380c3f3242b408f95ca13408f21d2845e589e9e4f5faf7d32c");
  assert.match(s.sourceArtifactUrl,/42654460905\/artifacts\/13691348436/);
  assert.equal(s.sourceExpiresAt,"2027-02-07T16:24:36Z");
});
test("resultsSection presence is a source observation and never scientific grading",()=>{
  const s=FOCUS_R40_SOURCE_STATUS;
  assert.equal(s.trialStatus.filter(x=>x.currentRegistryResultsSectionPresent).length,12);
  assert.equal(s.trialStatus.filter(x=>!x.currentRegistryResultsSectionPresent).length,17);
  assert.ok(s.trialStatus.every(x=>x.registryFetchSucceeded&&x.independentlyGradedClinicalMethods===0&&
        x.sourceOriginalPostingDateIndependentlyAuthenticated===false));
  assert.equal(s.trialStatus.find(x=>x.nct==="NCT06081894").currentRegistryResultsSectionPresent,false);
  assert.equal(s.trialStatus.find(x=>x.nct==="NCT04871282").registeredPhase,"PHASE2 / PHASE3");
  assert.equal(s.qualifiedClinicalReviews,0);
  assert.equal(s.independentlyValidatedFdaForecasts,0);
  assert.equal(s.historicalRealBacktests,0);
  assert.equal(s.officialFutureFdaForecast,"ABSTAIN");
  assert.equal(s.accuracy,"NOT_CALIBRATED");
  assert.equal(s.reviewOrScoringWrites,false);
});
test("ACHV official SEC fallback is retained without converting HTTP 301 to scientific failure",()=>{
  const s=FOCUS_R40_SOURCE_STATUS;
  const achv=s.groupStatus.find(x=>x.cycleId==="achv-cytisinicline");
  assert.equal(achv.sourceRoute,"OFFICIAL_SEC_FALLBACK");
  assert.equal(achv.retrievedPublicSource,true);
  assert.equal(achv.regulatorApplicationCycleVerified,false);
  assert.equal(achv.qualifiedReviewerSignoff,false);
  assert.ok(s.groupStatus.filter(x=>x.sourceRoute==="CANONICAL_SOURCE_LINK").length===22);
  assert.ok(s.groupStatus.every(x=>x.retrievedPublicSource===true));
  assert.equal(s.counts.uniqueUrlsFetched,21);
  assert.equal(s.counts.uniqueUrlsAttempted,22);
  assert.equal(pin.canonicalUnavailable.alternateSha256,
    "b0ea5daad7ab6d7682e53348c2158d7e16939ad8c2776a51c2921d25abec3cc2");
});
test("modified source receipt, version or reviewer claims fail closed",()=>{
  const variants=[
    r=>r.counts.registryRetrieved=28,
    r=>r.counts.applicationGroupsWithPublicSource=22,
    r=>r.counts.registryResultsSectionPresent=13,
    r=>r.registryResultsSectionPresent.pop(),
    r=>r.ncts[0]="NCT00000000",
    r=>r.applicationIds[0]="different-group",
    r=>r.source.receiptSha256="0".repeat(64),
    r=>r.source.artifactId=0,
    r=>r.canonicalUnavailable.alternativeFetched=false,
    r=>r.clinicalGradesWritten=1,
    r=>r.modelAuthorized=true,
    r=>r.calibratedAccuracy=.99
  ];
  variants.forEach((change,index)=>{
    const c=clone(pin);
    change(c);
    assert.equal(buildFocusR40SourceStatus(c),null,"tamper case "+index);
  });
});
test("PREDICTIONS displays trial source availability and official forecasts separately",()=>{
  const ui=fs.readFileSync(path.join(root,"app/predictions/FocusPreliminaryApplicationBoard.tsx"),"utf8");
  assert.match(ui,/FOCUS_R40_SOURCE_STATUS/);
  assert.match(ui,/Registry results section/);
  assert.match(ui,/Not in current registry record/);
  assert.match(ui,/23 application groups with source access/);
  assert.match(ui,/sourceArtifactUrl/);
  assert.match(ui,/No original clinical grades/);
  assert.match(ui,/Official FDA prediction/);
  assert.doesNotMatch(ui,/fetch\s*\(|submitGrade|recordOfficialFDAForecast/);
});
