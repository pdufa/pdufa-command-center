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
const {R85_PHASE_MANIFEST}=require("../lib/focus-r85-registry-phase-crosscheck.ts");
const {FOCUS_R81_SOURCE_READINESS}=require("../lib/focus-r81-all-focus-source-readiness.ts");
const {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES}=require(
 "../lib/focus-r79-launch-htn-sap-lock-evidence-gates.ts");
const {R86_ORIGINAL_DOCUMENT_MANIFEST,buildR86OriginalDocumentManifest,
 inspectR86CurrentStudy}=require("../lib/focus-r86-original-document-inventory.ts");

function response(row){
 return {protocolSection:{identificationModule:{nctId:row.nct}},
  hasResults:true,resultsSection:{
    participantFlowModule:{groups:[{id:"A"},{id:"B"}]},
    outcomeMeasuresModule:{outcomeMeasures:[{type:"PRIMARY"}]},
    adverseEventsModule:{seriousEvents:[{term:"sample"}],otherEvents:[]}
   },documentSection:{largeDocumentModule:{largeDocs:[
    {typeAbbrev:"Prot",hasProtocol:true,hasSap:false,hasIcf:false,
      label:"Original trial protocol in registry listing",date:"2025-01-31",
      uploadDate:"2025-02-03",filename:"Prot_000.pdf",size:812496},
    {typeAbbrev:"SAP",hasProtocol:false,hasSap:true,hasIcf:false,
      label:"Study SAP listing",date:"2025-02",uploadDate:"2025-02-10",
      filename:"SAP_001.pdf",size:504746}
   ]}}};
}
test("R86 retains exact 29-NCT/23-cycle source identities and no clinical grades",()=>{
 const d=R86_ORIGINAL_DOCUMENT_MANIFEST;
 assert.ok(d);
 assert.equal(d.exactTrials,29);
 assert.equal(d.provisionalApplications,23);
 assert.equal(d.rows.length,29);
 assert.equal(new Set(d.rows.map(r=>r.nct)).size,29);
 assert.equal(new Set(d.rows.flatMap(r=>r.cycleIds)).size,23);
 assert.equal(d.independentSignedSAPsAuthenticated,0);
 assert.equal(d.qualifiedIndependentScientificReviews,0);
 assert.equal(d.validatedFutureFDAPredictions,0);
 assert.equal(d.rows.filter(r=>r.currentPrimaryTableRetained).length,12);
 assert.equal(d.rows.filter(r=>r.currentSafetyArmsRetained).length,12);
 assert.equal(d.rows.filter(r=>r.publishedMainReportIndexedInFiveCaseSubset).length,5);
 assert.ok(d.rows.every(r=>r.scientificGrade===null&&r.FDAOutcome==="ABSTAIN"&&
  r.authenticatedSignedProspectiveSAP===false&&
  r.signedIndependentScientificReview===false&&/^[0-9a-f]{64}$/.test(
   r.archivedOriginalRegistrySha256)));
});
test("R86 keeps original chronology and source conflicts visible for both pilots",()=>{
 const d=R86_ORIGINAL_DOCUMENT_MANIFEST;
 const launch=d.rows.find(x=>x.nct==="NCT06153693");
 const acacia=d.rows.find(x=>x.nct==="NCT06081894");
 assert.ok(launch&&acacia);
 assert.equal(launch.focusCase,"LAUNCH_HTN");
 assert.equal(acacia.focusCase,"ACACIA_HCM");
 assert.equal(launch.knownBlockers.length,7);
 assert.equal(acacia.knownBlockers.length,4);
 assert.ok(launch.knownBlockers.every(b=>b.verified===false));
 assert.ok(acacia.knownBlockers.every(b=>b.verified===false));
 assert.equal(d.rows[0].sourceFirstPriority,0);
 assert.equal(d.rows[1].sourceFirstPriority,0);
 assert.match(acacia.knownBlockers.map(b=>b.label).join(" "),/516-versus-517/);
});
test("R86 official registry document metadata and posted results do not certify science",()=>{
 for(const row of R86_ORIGINAL_DOCUMENT_MANIFEST.rows){
  const result=inspectR86CurrentStudy(row,response(row));
  assert.ok(result,row.nct);
  assert.equal(result.docsInCurrentRegistry,2);
  assert.equal(result.listedProtocolDocuments,1);
  assert.equal(result.listedSapDocuments,1);
  assert.equal(result.listedConsentDocuments,0);
  assert.equal(result.currentRegistryResultsPosted,true);
  assert.equal(result.postedResultModules.participantFlowGroups,2);
  assert.equal(result.postedResultModules.endpointMeasures,1);
  assert.equal(result.postedResultModules.seriousAdverseEventTerms,1);
  assert.equal(result.prospectivelyLockedSapAuthenticated,false);
  assert.equal(result.qualifiedIndependentScientificReview,false);
  assert.equal(result.independentFDAForecast,"ABSTAIN");
 }
});
test("R86 no public original docs or posted results still means missing source only",()=>{
 const row=R86_ORIGINAL_DOCUMENT_MANIFEST.rows[0];
 const x=inspectR86CurrentStudy(row,{
  protocolSection:{identificationModule:{nctId:row.nct}},
  hasResults:false
 });
 assert.ok(x);
 assert.equal(x.docsInCurrentRegistry,0);
 assert.equal(x.listedProtocolDocuments,0);
 assert.equal(x.listedSapDocuments,0);
 assert.equal(x.currentRegistryResultsPosted,false);
 assert.equal(x.postedResultModules,null);
 assert.match(x.nextEvidenceAction,/absence here does not imply/);
 assert.equal(x.independentFDAForecast,"ABSTAIN");
});
test("R86 rejects cross-NCT, forged source, invalid documents and contradictory result body",()=>{
 const row=R86_ORIGINAL_DOCUMENT_MANIFEST.rows[0];
 for(const mutate of [
  x=>{x.protocolSection.identificationModule.nctId="NCT00000000";},
  x=>{x.documentSection.largeDocumentModule.largeDocs[0].filename="../a.pdf";},
  x=>{x.documentSection.largeDocumentModule.largeDocs[0].size=-1;},
  x=>{x.documentSection.largeDocumentModule.largeDocs[0].hasSap="yes";},
  x=>{x.documentSection.largeDocumentModule.largeDocs[0].date="not-a-date";},
  x=>{x.hasResults="yes";},
  x=>{delete x.resultsSection;}
 ]){
  const forged=response(row);mutate(forged);
  assert.equal(inspectR86CurrentStudy(row,forged),null);
 }
 assert.equal(inspectR86CurrentStudy(row,null),null);
});
test("R86 fails closed on roster drift or forged qualified reviewer actions",()=>{
 for(const mutate of [
  x=>{x.rows.pop();},
  x=>{x.rows[0].nct="NCT00000000";},
  x=>{x.rows[0].archivedRegistrySha256="bad-sha";},
  x=>{x.rows[0].FDAForecast="APPROVAL";},
  x=>{x.rows[0].sourceUpdatedDate="";},
 ]){
  const bad=structuredClone(R85_PHASE_MANIFEST);
  mutate(bad);
  assert.equal(buildR86OriginalDocumentManifest(
   bad,FOCUS_R81_SOURCE_READINESS,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES),null);
 }
 const launch=structuredClone(FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES);
 launch.qualifiedIndependentReviewersSigned=2;
 assert.equal(buildR86OriginalDocumentManifest(
  R85_PHASE_MANIFEST,FOCUS_R81_SOURCE_READINESS,launch),null);
});
test("R86 route is read-only, exact NCT scoped and fails closed",()=>{
 const route=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/check/route.ts"),"utf8");
 const page=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/page.tsx"),"utf8");
 const client=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/OriginalSourceDocumentsR86Client.tsx"),"utf8");
 const phase=fs.readFileSync(path.join(root,
  "app/predictions/phase-verification/page.tsx"),"utf8");
 assert.match(route,/https:\/\/clinicaltrials\.gov\/api\/v2\/studies\//);
 assert.match(route,/NCT_NOT_IN_LOCKED_FOCUS_ROSTER/);
 assert.match(route,/redirect:"error"/);
 assert.match(route,/cache:"no-store"/);
 assert.match(route,/AbortSignal\.timeout/);
 assert.match(route,/REGISTRY_SOURCE_IDENTITY_OR_STRUCTURE_INVALID/);
 assert.match(page,/Original protocols, SAPs and registry results/);
 assert.match(client,/Check all 29 current registry source records/);
 assert.match(client,/start\+=4/);
 assert.match(phase,/\/predictions\/original-documents/);
 assert.doesNotMatch(route,/method:"POST"|submitClinicalScore|setGrade\(/);
});
