"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const repoRoot=path.resolve(root,"../..");
require.extensions[".ts"]=(mod,file)=>{
 const transpiled=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(transpiled.outputText,file);
};
const {R93_PRIORITY_SCIENTIFIC_GATES,buildR93PriorityScientificGates}=
 require("../lib/focus-r93-priority-scientific-gates.ts");
const {R86_ORIGINAL_DOCUMENT_MANIFEST}=
 require("../lib/focus-r86-original-document-inventory.ts");
const {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES}=
 require("../lib/focus-r79-launch-htn-sap-lock-evidence-gates.ts");
const {FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY}=
 require("../lib/focus-r78-launch-htn-public-chronology.ts");
const {R89_ARCHIVED_ACACIA_SOURCE_HISTORY}=
 require("../lib/focus-r89-acacia-prior-original-history.ts");
const {R89_HISTORICAL_SOURCE_RECOVERY}=
 require("../lib/focus-r89-historical-source-recovery.ts");
const {GET}=require(
 "../app/predictions/scientific-reconciliation/priority-gates/export/route.ts");

test("R93 priority handoff preserves two exact FOCUS trials, 11 original evidence gates and 29/23 unchanged",()=>{
 const x=R93_PRIORITY_SCIENTIFIC_GATES;
 assert.ok(x);
 assert.equal(x.schema,"MAIN_R93_PRIORITY_2_CASE_11_ORIGINAL_SCIENTIFIC_GATES_UNADJUDICATED");
 assert.equal(x.exactFOCUSTrialsUnaffected,29);
 assert.equal(x.provisionalFDAApplicationCyclesUnaffected,23);
 assert.equal(x.priorityOriginalTrialCases,2);
 assert.equal(x.unresolvedAuthenticatedScienceRequirements,11);
 assert.equal(x.cases.length,2);
 assert.deepEqual(x.cases.map(v=>v.nct),["NCT06081894","NCT06153693"]);
 assert.equal(x.cases[0].gates.length,4);
 assert.equal(x.cases[1].gates.length,7);
 assert.equal(new Set(x.cases.flatMap(v=>v.gates.map(g=>v.nct+":"+g.id))).size,11);
 assert.equal(x.independentlyVerifiedSignedProspectiveSAPs,0);
 assert.equal(x.qualifiedIndependentScienceSignoffs,0);
 assert.equal(x.validatedFDAPredictions,0);
 assert.equal(x.FDAForecast,"ABSTAIN");
 assert.ok(x.cases.every(v=>v.signedOriginalSAPAuthenticated===false&&
  v.independentScienceApproved===false&&v.methodGrade===null&&
  v.FDAForecast==="ABSTAIN"));
 assert.ok(x.cases.flatMap(v=>v.gates).every(g=>
  g.resolvedByAuthenticatedOriginals===false&&
  g.signedQualifiedReviewerApproved===false&&
  g.permissibleConclusion==="SOURCE_RECONCILIATION_PENDING_NOT_APPROVAL_PROBABILITY"&&
  g.provenanceClass==="PUBLISHED_RESEARCH_LEAD_REQUIRES_CONTROLLED_ORIGINAL_PROOF"));
});
test("R93 prior original ACACIA registry versions correctly frame one-to-two primary change without retrospective causal conclusion",()=>{
 const packet=JSON.parse(fs.readFileSync(path.join(repoRoot,
  "docs/medical-review-pilot-20261108/revision36-original-history/validated_comparison.json"),"utf8"));
 const d=R93_PRIORITY_SCIENTIFIC_GATES;
 assert.equal(packet.nct,"NCT06081894");
 assert.deepEqual(["v26","v27","v29","v30"].map(v=>
  packet.versionData[v].outcomes.primary.length),[1,2,2,2]);
 assert.equal(packet.versionData.v26.lastUpdatePosted.date,"2025-01-14");
 assert.equal(packet.versionData.v27.lastUpdatePosted.date,"2025-05-20");
 assert.equal(d.acaciaOriginalHistoricalVersions,4);
 assert.equal(d.acaciaRegistryPrimaryEndpointsVersion26,1);
 assert.equal(d.acaciaRegistryPrimaryEndpointsVersion27,2);
 const acacia=d.cases.find(x=>x.nct==="NCT06081894");
 assert.ok(acacia);
 assert.ok(acacia.gates.some(x=>x.id==="DUAL_PRIMARY_HISTORY"));
 assert.match(acacia.timelineSummary,/SAP signature and first-unblinding chronology are NOT/);
 assert.ok(acacia.gates.every(x=>x.resolvedByAuthenticatedOriginals===false));
});
test("R93 original Launch SAP imprint versus public topline does not counterfeit true database lock or unblinding chronology",()=>{
 const d=R93_PRIORITY_SCIENTIFIC_GATES;
 const prior=JSON.parse(fs.readFileSync(path.join(root,
  "data/focus-r78-launch-htn-public-chronology.json"),"utf8"));
 const source=JSON.parse(fs.readFileSync(path.join(root,
  "data/focus-r79-launch-htn-sap-lock-evidence-gates.json"),"utf8"));
 assert.equal(d.launchPublishedSAPImprint,"2025-02-13");
 assert.equal(d.launchPublicToplineDate,"2025-03-10");
 assert.equal(prior.observation.originalActualDatabaseLockDate,null);
 assert.equal(prior.observation.originalActualUnblindingDate,null);
 assert.equal(prior.observation.twoPrintedSAPCoverDateDiscrepanciesUnresolved,true);
 assert.equal(source.requirementsIndependentlyVerified,0);
 assert.equal(source.requiredBeforeProspectiveSapChronologyCertified,7);
 const launch=d.cases.find(x=>x.nct==="NCT06153693");
 assert.ok(launch);
 assert.deepEqual(new Set(launch.gates.map(x=>x.id)),
  new Set(source.sourceRequirements.map(x=>x.id)));
 for(const g of launch.gates){
  const original=source.sourceRequirements.find(x=>x.id===g.id);
  assert.ok(original);
  assert.equal(g.sourceStatus,original.status);
  assert.equal(g.existingEvidence,original.evidence);
 }
});
test("R93 preserves ACACIA original source safety and population discrepancies, without treating safety counts as adjudicated",()=>{
 const packet=JSON.parse(fs.readFileSync(path.join(repoRoot,
  "docs/medical-review-pilot-20261108/revision36-protocol-safety/reviewer-packet.json"),"utf8"));
 assert.equal(packet.identity.nct,"NCT06081894");
 assert.equal(packet.protocolGraph.finalLockedSapVerified,false);
 assert.equal(packet.safeguards.clinicalSignoff,false);
 assert.equal(packet.safeguards.APPROVAL,"ABSTAIN");
 assert.deepEqual(new Set(packet.unresolved.map(x=>x.id)),
  new Set(["FINAL_LOCKED_SAP","CONSORT_516_517",
   "HF_SAE_11_1_12_3","INTERRUPTION_14_2_7"]));
 const acacia=R93_PRIORITY_SCIENTIFIC_GATES.cases[0];
 const h=acacia.gates.find(g=>g.id==="HEART_FAILURE_WINDOWS");
 assert.ok(h);
 assert.match(h.scientificQuestion,/11\/1 and 12\/3/);
 assert.match(h.scientificQuestion,/14 reported interruptions/);
 assert.equal(h.signedQualifiedReviewerApproved,false);
 assert.equal(h.provenanceClass,"PUBLISHED_RESEARCH_LEAD_REQUIRES_CONTROLLED_ORIGINAL_PROOF");
});
test("R93 original gate source mutation and false qualified review assertions fail closed",()=>{
 const scenarios=[
  inv=>{inv.rows.find(x=>x.nct==="NCT06081894").knownBlockers.pop();},
  inv=>{inv.rows.find(x=>x.nct==="NCT06081894").knownBlockers[0].status="COMPLETE";},
  inv=>{inv.rows.find(x=>x.nct==="NCT06153693").signedIndependentScientificReview=true;},
  inv=>{inv.exactTrials=30;},
  inv=>{inv.rows.find(x=>x.nct==="NCT06153693").scientificGrade=100;}
 ];
 for(const mutate of scenarios){
  const copy=structuredClone(R86_ORIGINAL_DOCUMENT_MANIFEST);
  mutate(copy);
  assert.equal(buildR93PriorityScientificGates(copy),null);
 }
 const gates=structuredClone(FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES);
 gates.sourceRequirements[0].status="SIGNED";
 assert.equal(buildR93PriorityScientificGates(R86_ORIGINAL_DOCUMENT_MANIFEST,gates),null);
 const r78=structuredClone(FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY);
 r78.observation.originalActualDatabaseLockDate="2025-02-01";
 assert.equal(buildR93PriorityScientificGates(
  R86_ORIGINAL_DOCUMENT_MANIFEST,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES,
  R89_ARCHIVED_ACACIA_SOURCE_HISTORY,r78),null);
 const original=structuredClone(R89_ARCHIVED_ACACIA_SOURCE_HISTORY);
 original.prospectiveSAPFinalSignatureAuthenticated=true;
 assert.equal(buildR93PriorityScientificGates(
  R86_ORIGINAL_DOCUMENT_MANIFEST,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES,
  original),null);
 const recovered=structuredClone(R89_HISTORICAL_SOURCE_RECOVERY);
 recovered.rows.find(x=>x.nct==="NCT06081894").independentQualifiedScienceReview=true;
 assert.equal(buildR93PriorityScientificGates(
  R86_ORIGINAL_DOCUMENT_MANIFEST,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES,
  R89_ARCHIVED_ACACIA_SOURCE_HISTORY,FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY,
  recovered),null);
});
test("R93 exact eleven gate CSV export is no-store, safe, with no fictional scientific grades",async()=>{
 const r=GET(),csv=await r.text();
 assert.equal(r.status,200);
 assert.match(r.headers.get("Content-Type"),/text\/csv/);
 assert.match(r.headers.get("Cache-Control"),/no-store/);
 assert.match(r.headers.get("Content-Disposition"),/attachment/);
 assert.equal(csv.trim().split("\r\n").length,12);
 assert.match(csv,/NCT06081894/);
 assert.match(csv,/NCT06153693/);
 assert.match(csv,/FINAL_LOCKED_SAP/);
 assert.match(csv,/CONFLICTED_ADDENDUM_YEAR_RECONCILIATION/);
 assert.match(csv,/FDA_forecast/);
 assert.match(csv,/NOT_SIGNED/);
 assert.match(csv,/ABSTAIN/);
 assert.doesNotMatch(csv,/APPROVED|FAILURE|Grade 100/);
});
test("R93 page is linked from previous original scientific work, with original sources, no prediction controls",()=>{
 const page=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
 const prev=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/protocol-crosswalk/page.tsx"),"utf8");
 const route=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/priority-gates/export/route.ts"),"utf8");
 assert.match(page,/Priority original scientific evidence checklist/);
 assert.match(page,/R93_PRIORITY_SCIENTIFIC_GATES/);
 assert.match(page,/NOT AUTHENTICATED/);
 assert.match(page,/Regulatory outcome: ABSTAIN/);
 assert.match(page,/11 original-evidence requirements to CSV/);
 assert.match(prev,/\/predictions\/scientific-reconciliation\/priority-gates/);
 assert.match(route,/safeCell/);
 assert.match(route,/FDAForecast:"ABSTAIN"/);
 assert.doesNotMatch(route,/method:"POST"|modelTraining|setGrade\(/);
});
