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
const {FOCUS_R81_SOURCE_READINESS}=require("../lib/focus-r81-all-focus-source-readiness.ts");
const {FOCUS_R67_PHASE_SOURCE}=require("../lib/focus-r67-phase-source.ts");
const {buildR85PhaseCrosscheckManifest,R85_PHASE_MANIFEST,
 compareR85CurrentRegistry}=require("../lib/focus-r85-registry-phase-crosscheck.ts");

function currentResponse(row){
 return {protocolSection:{
  identificationModule:{nctId:row.nct},
  statusModule:{
   overallStatus:row.registryReportedStatus.replaceAll(" ","_"),
   lastUpdatePostDateStruct:{date:row.archivedSourceUpdatedDate},
   statusVerifiedDate:row.archivedRegistryVerifiedMonth,
   primaryCompletionDateStruct:{date:row.primaryCompletionDate,
     type:row.primaryCompletionType}
  },
  designModule:{
   phases:row.registryReportedPhase==="Phase 3"?
     ["PHASE3"]:["PHASE2","PHASE3"],
   designInfo:{allocation:row.allocation,maskingInfo:{masking:row.masking}},
   enrollmentInfo:{count:row.enrollment,type:row.enrollmentType}
  }
 }};
}
test("R85 retains exact 29 archived original-source SHA identities and 23 groups",()=>{
 const x=R85_PHASE_MANIFEST;
 assert.ok(x);
 assert.equal(x.exactTrials,29);
 assert.equal(x.provisionalCycles,23);
 assert.equal(x.rows.length,29);
 assert.equal(new Set(x.rows.map(r=>r.nct)).size,29);
 assert.equal(new Set(x.rows.flatMap(r=>r.cycleIds)).size,23);
 assert.ok(x.rows.every(r=>/^[0-9a-f]{64}$/.test(r.archivedRegistrySha256)));
 assert.ok(x.rows.every(r=>r.scientificGrade===null&&r.FDAForecast==="ABSTAIN"&&
   r.independentPhaseReview==="NOT_SIGNED"&&r.signedProspectiveSAP==="NOT_AUTHENTICATED"));
 assert.equal(x.independentlySignedPhaseReviews,0);
 assert.equal(x.authenticatedSignedSAPs,0);
 assert.equal(x.validatedFutureFDAPredictions,0);
 assert.equal(x.sourceReportedPhase3,28);
 assert.equal(x.sourceReportedCombinedPhase23,1);
 assert.equal(x.sourceReportedCompleted,19);
 assert.equal(x.sourceReportedActive,8);
 assert.equal(x.sourceReportedRecruiting,2);
 assert.equal(x.sourceReportedNonRandomized,1);
});
test("R85 phase-first order explicitly flags combined Phase 2/3 and nonrandomized design",()=>{
 const x=R85_PHASE_MANIFEST;
 const special=x.rows.filter(r=>r.phaseFirstReviewPriority===
   "DESIGN_REQUIRES_SPECIAL_ADJUDICATION");
 assert.deepEqual(new Set(special.map(r=>r.nct)),
   new Set(["NCT04871282","NCT06331299"]));
 assert.equal(x.rows[0].phaseFirstReviewPriority,
  "DESIGN_REQUIRES_SPECIAL_ADJUDICATION");
 assert.equal(x.rows[1].phaseFirstReviewPriority,
  "DESIGN_REQUIRES_SPECIAL_ADJUDICATION");
 assert.equal(x.rows.find(r=>r.nct==="NCT06445023").primaryCompletionDate,"2026-10");
});
test("R85 live comparator returns matching registry fields without clinical certification",()=>{
 for(const row of R85_PHASE_MANIFEST.rows){
  const result=compareR85CurrentRegistry(row,currentResponse(row));
  assert.ok(result,row.nct);
  assert.equal(result.status,"REGISTRY_FIELDS_MATCH_NOT_INDEPENDENTLY_VERIFIED");
  assert.deepEqual(result.unavailableFields,[]);
  assert.deepEqual(result.differences,[]);
  assert.equal(result.independentPhaseReview,"NOT_SIGNED");
  assert.equal(result.FDAForecast,"ABSTAIN");
  assert.equal(result.prospectiveSAPAuthenticated,false);
 }
});
test("R85 detects exact original-field drift, partial upstream payload, and identity mismatch",()=>{
 const row=R85_PHASE_MANIFEST.rows[0];
 const mutated=currentResponse(row);
 mutated.protocolSection.designModule.phases=["PHASE1"];
 const result=compareR85CurrentRegistry(row,mutated);
 assert.ok(result);
 assert.equal(result.status,"INCOMPLETE_CURRENT_REGISTRY_FIELDS_REQUIRES_REVIEW");
 assert.ok(result.unavailableFields.includes("sourcePhase"));
 const other=currentResponse(row);
 other.protocolSection.designModule.enrollmentInfo.count+=1;
 assert.equal(compareR85CurrentRegistry(row,other).status,
  "REGISTRY_CHANGED_REQUIRES_INDEPENDENT_REVIEW");
 assert.equal(compareR85CurrentRegistry(row,other).differences[0].field,"enrollment");
 const bad=currentResponse(row);
 bad.protocolSection.identificationModule.nctId="NCT00000000";
 assert.equal(compareR85CurrentRegistry(row,bad),null);
 assert.equal(compareR85CurrentRegistry(row,null),null);
});
test("R85 fails closed on wrong 29-NCT roster, missing provenance or forged signoffs",()=>{
 for(const mutate of [
  x=>{x.records.pop();},
  x=>{x.records[0].nct="NCT00000000";},
  x=>{x.records[0].currentOriginalSourceSha256="not-sha";},
  x=>{x.records[0].independentlyVerifiedTrialPhase=true;},
  x=>{x.records[0].sourcePhase="Phase 4";},
  x=>{x.records[0].applicationCycles=["fake-cycle"];}
 ]){
  const changed=structuredClone(FOCUS_R67_PHASE_SOURCE);
  mutate(changed);
  assert.equal(buildR85PhaseCrosscheckManifest(changed,
    FOCUS_R81_SOURCE_READINESS),null);
 }
});
test("R85 server route is exact-NCT, official-host, read-only, and fails safely",()=>{
 const route=fs.readFileSync(path.join(root,
  "app/predictions/phase-verification/check/route.ts"),"utf8");
 const view=fs.readFileSync(path.join(root,
  "app/predictions/phase-verification/page.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
  "app/predictions/evidence-gaps/FocusSourceReadinessR81.tsx"),"utf8");
 assert.match(route,/https:\/\/clinicaltrials\.gov\/api\/v2\/studies\//);
 assert.match(route,/AbortSignal\.timeout/);
 assert.match(route,/redirect:"error"/);
 assert.match(route,/cache:"no-store"/);
 assert.match(route,/status,headers:H/);
 assert.match(route,/R85_PHASE_MANIFEST/);
 assert.match(route,/EXACT_NCT_REQUIRED/);
 assert.match(view,/Check current ClinicalTrials\.gov fields/);
 assert.match(view,/independently signed phase reviews/i);
 assert.match(panel,/\/predictions\/phase-verification/);
 assert.doesNotMatch(route,/method:"POST"|submitClinicalScore|setGrade\(/);
});
