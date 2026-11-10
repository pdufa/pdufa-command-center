"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const output=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
 }});
 mod._compile(output.outputText,file);
};
const manifest=require("../data/focus-r79-launch-htn-sap-lock-evidence-gates.json");
const {buildR79AuthenticSapLockGates,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES}=
 require("../lib/focus-r79-launch-htn-sap-lock-evidence-gates.ts");

test("Original SAP/DB-lock chronology proof remains 0/7, no authorized keys, no FDA forecast",()=>{
 const out=FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES;
 assert.ok(out);
 assert.equal(out.nct,"NCT06153693");
 assert.equal(out.cycleId,"mlys-lorundrostat");
 assert.equal(out.sourceRequirements.length,7);
 assert.equal(out.requirementsIndependentlyVerified,0);
 assert.equal(out.requiredBeforeProspectiveSapChronologyCertified,7);
 assert.equal(out.sourceBytesSha256Authenticated,0);
 assert.equal(out.productionApprovedTrustAnchors,0);
 assert.equal(out.authenticPlanFinalizedBeforeBlindBreak,false);
 assert.equal(out.firstUnblindedAccessTimestampAuthenticated,false);
 assert.equal(out.actualFinalDatabaseLockTimestampAuthenticated,false);
 assert.equal(out.originalSourceAttestationsVerified,false);
 assert.equal(out.qualifiedIndependentReviewersSigned,0);
 assert.equal(out.validatedFDAApplicationForecasts,0);
 assert.equal(out.scientificGrade,null);
 assert.equal(out.FDAOutcome,"ABSTAIN");
 assert.equal(out.futureTiming,"UNKNOWN");
 assert.equal(out.modelTrainingOrProductionWrites,false);
 assert.equal(out.scientificReadiness,"BLOCKED_AUTHENTIC_PROSPECTIVE_SOURCE");
});
test("Scientific protection of original ICH guidance references and print-only chronology",()=>{
 const out=FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES;
 assert.deepEqual(out.reviewStandards.map(x=>x.kind),["ICH_E9_5_1","ICH_E6_R3_3_16_2"]);
 assert.equal(out.observedPrintedMainSapDate,"2025-02-13");
 assert.equal(out.observedPrintedWindowingAddendumDate,"2025-02-23");
 assert.equal(out.observedPublishedFirstToplineDate,"2025-03-10");
 assert.deepEqual(out.sourceRequirements.map(x=>x.status),[
  "PUBLISHED_IMPRINT_ONLY","NOT_OBTAINED","NOT_OBTAINED","NOT_OBTAINED",
  "NOT_OBTAINED","UNRESOLVED_PRINTED_YEAR_CONFLICT","NOT_OBTAINED"]);
 assert.ok(out.sourceRequirements.every(x=>x.independentReceipt===null));
});
test("Attacker cannot turn source preview into a signed plan or calibrated FDA decision",()=>{
 const attacks=[
  x=>x.sourceRequirements.pop(),
  x=>x.sourceRequirements.reverse(),
  x=>x.sourceRequirements[0].status="VERIFIED",
  x=>x.sourceRequirements[1].status="VERIFIED",
  x=>x.sourceRequirements[1].independentReceipt="fake",
  x=>x.sourceRequirements[5].status="RESOLVED",
  x=>x.sourceRequirements[5].independentReceipt="fake",
  x=>x.productionApprovedTrustAnchors=2,
  x=>x.sourceBytesSha256Authenticated=7,
  x=>x.authenticPlanFinalizedBeforeBlindBreak=true,
  x=>x.firstUnblindedAccessTimestampAuthenticated=true,
  x=>x.actualFinalDatabaseLockTimestampAuthenticated=true,
  x=>x.originalSourceAttestationsVerified=true,
  x=>x.qualifiedIndependentReviewersSigned=2,
  x=>x.requirementsIndependentlyVerified=7,
  x=>x.validatedFDAApplicationForecasts=1,
  x=>x.scientificGrade=20,
  x=>x.FDAOutcome="APPROVAL",
  x=>x.futureTiming="ON_TIME",
  x=>x.modelTrainingOrProductionWrites=true,
  x=>x.nct="NCT00000001",
  x=>x.cycleId="mlys-advance-htn",
  x=>x.observedPrintedMainSapDate="2025-01-24",
  x=>x.reviewStandards[0].url="https://forged.invalid/fda.pdf"
 ];
 attacks.forEach((attack,i)=>{
  const cloned=structuredClone(manifest);
  attack(cloned);
  assert.equal(buildR79AuthenticSapLockGates(cloned),null,"tamper "+i);
 });
});
test("The R79 source-authenticity panel is read-only and only for original MLYS trial",()=>{
 const host=fs.readFileSync(path.join(root,
  "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
  "app/predictions/evidence-gaps/LaunchHtnProspectiveSapGateR79.tsx"),"utf8");
 assert.match(host,/nct==="NCT06153693"&&<LaunchHtnProspectiveSapGateR79\/>/);
 assert.match(panel,/0\/23/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/unblinding/i);
 assert.match(panel,/original source bytes/i);
 assert.match(panel,/seven source-level verification blocks/i);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
