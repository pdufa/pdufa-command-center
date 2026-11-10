"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const crypto=require("node:crypto");
require.extensions[".ts"]=(mod,file)=>{
 const compiled=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(compiled.outputText,file);
};
const {R88_SOURCE_CHRONOLOGY}=require("../lib/focus-r88-source-chronology-triage.ts");
const {R89_HISTORICAL_SOURCE_RECOVERY,buildR89HistoricalSourceRecovery}=
 require("../lib/focus-r89-historical-source-recovery.ts");
const {GET}=require("../app/predictions/source-recovery/history/route.ts");
const {R89_ARCHIVED_ACACIA_SOURCE_HISTORY}=require("../lib/focus-r89-acacia-prior-original-history.ts");

test("R89 reconciles exactly 17 current registry original gaps with all 29/23 originals",()=>{
 const d=R89_HISTORICAL_SOURCE_RECOVERY;assert.ok(d);
 assert.equal(d.exactFocusTrialCount,29);
 assert.equal(d.provisionalApplicationCycles,23);
 assert.equal(d.rows.length,17);
 assert.equal(d.missingPublicProtocolSapListingNcts,17);
 assert.equal(new Set(d.rows.map(r=>r.nct)).size,17);
 assert.deepEqual(new Set(d.rows.map(r=>r.nct)),
  new Set(R88_SOURCE_CHRONOLOGY.rows.filter(r=>r.sourcePdfFiles.length===0).map(r=>r.nct)));
 assert.equal(d.originalPivotalPublisherLeadsInFiveStudyIndex,5);
 assert.equal(d.unindexedPivotalPublicationInFiveStudyIndex,12);
 assert.equal(d.rows.filter(r=>r.originalIndexedPivotalPublication).length,5);
 assert.equal(d.rows.filter(r=>!r.originalIndexedPivotalPublication).length,12);
 assert.equal(d.independentlyAuthenticatedSignedProspectiveSAPs,0);
 assert.equal(d.independentQualifiedScienceReviews,0);
 assert.equal(d.validatedFutureFDAForecasts,0);
 assert.ok(d.rows.every(r=>r.currentRegistryProtocolSapFiles===0&&
  r.historicalVersionsInspectedInThisNewR89Run===0&&
  r.historicalSourceRecordsIndependentlyAuthenticated===0&&
  r.independentQualifiedScienceReview===false&&
  r.prospectivelyAuthenticatedSignedSAP===false&&r.validatedFDAOutcome==="ABSTAIN"));
});
test("R89 reuses only the five authentic recorded journal leads and prioritizes two scientific blockers",()=>{
 const d=R89_HISTORICAL_SOURCE_RECOVERY;
 const five=["NCT05126758","NCT05662241","NCT06081894","NCT06153693","NCT06343779"];
 assert.deepEqual(new Set(d.rows.filter(x=>x.originalIndexedPivotalPublication).map(x=>x.nct)),
  new Set(five));
 for(const row of d.rows){
  const paper=row.originalIndexedPivotalPublication;
  if(!paper)continue;
  assert.ok(paper.articleUrl.startsWith("https://"));
  assert.match(paper.pmid,/^\d+$/);
  assert.equal(paper.originalSignedSapChronologyIndependentlyVerified,false);
  assert.equal(paper.qualifiedReviewerSigned,false);
 }
 assert.deepEqual(new Set(d.rows.slice(0,2).map(r=>r.nct)),
  new Set(["NCT06081894","NCT06153693"]));
});
test("R89 reuses four R36 exact original ACACIA bytes and SHA receipts, never forges a signed SAP",()=>{
 const d=R89_ARCHIVED_ACACIA_SOURCE_HISTORY;
 assert.equal(d.nct,"NCT06081894");
 assert.equal(d.exactOriginalVersionsCaptured,4);
 assert.equal(d.liveIndexAvailableFromR89Preview,false);
 assert.equal(d.scientificReviewSigned,false);
 assert.equal(d.prospectiveSAPFinalSignatureAuthenticated,false);
 assert.equal(d.actualUnblindingDateIndependentlyVerified,false);
 assert.equal(d.FDAForecast,"ABSTAIN");
 const repoRoot=path.resolve(root,"../..");
 const validated=JSON.parse(fs.readFileSync(path.join(repoRoot,
  d.sourceResearchDirectory,"validated_comparison.json"),"utf8"));
 const priorReceipt=JSON.parse(fs.readFileSync(path.join(repoRoot,
  d.sourceResearchDirectory,"public_browser_receipt.json"),"utf8"));
 assert.equal(validated.nct,d.nct);
 assert.equal(validated.clinicalSignoff,false);
 assert.equal(validated.gradedMethods,0);
 assert.equal(priorReceipt.versions.length,4);
 for(const v of d.previousVersionFiles){
  const originalBytes=fs.readFileSync(path.join(repoRoot,v.originalRepoPath));
  const actualDigest=crypto.createHash("sha256").update(originalBytes).digest("hex");
  const evidence=validated.versionData["v"+v.uiVersion];
  assert.equal(actualDigest,v.sourceSha256,"original "+v.uiVersion);
  assert.equal(evidence.sourceSha256,v.sourceSha256);
  assert.equal(evidence.apiIndex,v.apiIndex);
  assert.equal(evidence.submitted,v.submittedDate);
  assert.equal(evidence.outcomes.primary.length,v.primaryEndpointsListed);
  assert.equal(priorReceipt.versions.find(x=>x.version===v.uiVersion).sha256,
   v.sourceSha256);
 }
 assert.deepEqual(d.previousVersionFiles.map(v=>v.primaryEndpointsListed),[1,2,2,2]);
});
test("R89 fails closed on altered 17-file source state, fake original signoff and roster",()=>{
 const forged=structuredClone(R88_SOURCE_CHRONOLOGY);
 forged.rows.find(r=>r.nct==="NCT05059223").sourcePdfFiles.push({
  filename:"fake.pdf",sha256:"a".repeat(64)
 });
 assert.equal(buildR89HistoricalSourceRecovery(forged),null);
 const wrong=structuredClone(R88_SOURCE_CHRONOLOGY);
 wrong.rows[0].FDAForecast="APPROVAL";
 assert.equal(buildR89HistoricalSourceRecovery(wrong),null);
 const missing=structuredClone(R88_SOURCE_CHRONOLOGY);
 missing.rows.pop();
 assert.equal(buildR89HistoricalSourceRecovery(missing),null);
});
function req(query){return new Request("https://preview.test/predictions/source-recovery/history"+query);}
function index(nct){
 return {study:{protocolSection:{identificationModule:{nctId:nct}}},
 history:{changes:[{version:0,date:"2024-01-01"},{version:1,date:"2025-02-03"}]}};
}
function version(nct){
 return {studyVersion:1,study:{
  protocolSection:{
   identificationModule:{nctId:nct},
   statusModule:{lastUpdateSubmitDate:"2025-02-03",overallStatus:"COMPLETED"},
   outcomesModule:{primaryOutcomes:[{measure:"Test endpoint",timeFrame:"Week 24"}]}
  },
  documentSection:{largeDocumentModule:{largeDocs:[
   {filename:"Prot_000.pdf",typeAbbrev:"Prot",hasProtocol:true,hasSap:false,
    size:350000,date:"2024-12-01",uploadDate:"2025-04-02T10:41"}
  ]}}
 }};
}
async function withOfficialSource(fake,run){
 const saved=global.fetch;global.fetch=fake;
 try{return await run();}
 finally{global.fetch=saved;}
}
test("R89 official history index validates actual exact NCT and returns original submission dates only",async()=>{
 const nct=R89_HISTORICAL_SOURCE_RECOVERY.rows[0].nct;
 await withOfficialSource(async url=>{
   assert.equal(url,"https://clinicaltrials.gov/api/int/studies/"+nct+"?history=true");
   return Response.json(index(nct));
  },async()=>{
   const response=await GET(req("?nct="+nct));
   assert.equal(response.status,200);
   const d=await response.json();
   assert.equal(d.historyVersionCount,2);
   assert.deepEqual(d.versions,[{apiIndex:0,uiVersion:1,submittedDate:"2024-01-01"},
    {apiIndex:1,uiVersion:2,submittedDate:"2025-02-03"}]);
   assert.equal(d.authenticatedSignedSAPs,0);
   assert.equal(d.FDAForecast,"ABSTAIN");
  });
});
test("R89 exact history version requires official index membership, NCT and submitted-date match",async()=>{
 const nct=R89_HISTORICAL_SOURCE_RECOVERY.rows[0].nct;
 await withOfficialSource(async url=>Response.json(
    String(url).endsWith("/history/1")?version(nct):index(nct)
 ),async()=>{
   const res=await GET(req("?nct="+nct+"&version=1"));
   assert.equal(res.status,200);
   const body=await res.json();
   assert.equal(body.originalPrimaryOutcomeCount,1);
   assert.equal(body.listedProtocolOrSapDocuments.length,1);
   assert.equal(body.listedProtocolOrSapDocuments[0].filename,"Prot_000.pdf");
   assert.equal(body.prospectivelyAuthenticatedSignedSAP,false);
   assert.equal(body.FDAForecast,"ABSTAIN");
 });
 await withOfficialSource(async url=>Response.json(
    String(url).endsWith("/history/1")?
     {...version(nct),studyVersion:0}:index(nct)
 ),async()=>{
   const res=await GET(req("?nct="+nct+"&version=1"));
   assert.equal(res.status,502);
   assert.equal((await res.json()).verifiedSignedProspectiveSAPs,0);
 });
});
test("R89 history failures and invalid/outside NCT never infer absent documents",async()=>{
 const nct=R89_HISTORICAL_SOURCE_RECOVERY.rows[0].nct;
 assert.equal((await GET(req("?nct=oops"))).status,400);
 assert.equal((await GET(req("?nct=NCT00000000"))).status,404);
 assert.equal((await GET(req("?nct="+nct+"&version=9999"))).status,400);
 await withOfficialSource(async()=>new Response("Forbidden",{status:403}),async()=>{
  const res=await GET(req("?nct="+nct));
  assert.equal(res.status,502);
  const d=await res.json();
  assert.equal(d.unknownHistoricalSourceNotAbsent,true);
  assert.equal(d.FDAForecast,"ABSTAIN");
 });
 await withOfficialSource(async()=>Response.json(index("NCT00000000")),async()=>{
  const res=await GET(req("?nct="+nct));
  assert.equal(res.status,502);
 });
 await withOfficialSource(async()=>Response.json(index(nct)),async()=>{
  const res=await GET(req("?nct="+nct+"&version=300"));
  assert.equal(res.status,404);
 });
});
test("R89 read-only page, UI and original historical host remain scoped",()=>{
 const route=fs.readFileSync(path.join(root,
  "app/predictions/source-recovery/history/route.ts"),"utf8");
 const page=fs.readFileSync(path.join(root,
  "app/predictions/source-recovery/page.tsx"),"utf8");
 const client=fs.readFileSync(path.join(root,
  "app/predictions/source-recovery/OriginalHistoryRecoveryR89Client.tsx"),"utf8");
 const previous=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/chronology/page.tsx"),"utf8");
 assert.match(route,/clinicaltrials\.gov\/api\/int\/studies\//);
 assert.match(route,/HISTORY_ORIGINAL_IDENTITY_OR_INDEX_INVALID/);
 assert.match(route,/OFFICIAL_HISTORY_NOT_ACCESSIBLE_CHECK_PUBLIC_UI_OR_RETRY/);
 assert.match(route,/redirect:"error"/);
 assert.match(route,/cache:"no-store"/);
 assert.match(route,/FDAForecast:"ABSTAIN"/);
 assert.match(page,/17 original-source recovery cases/);
 assert.match(client,/Check original registry version index/);
 assert.match(client,/Original signoff: NOT VERIFIED/);
 assert.match(client,/Open official public study record history/);
 assert.match(client,/Four original ACACIA-HCM registry versions already preserved/);
 assert.match(previous,/\/predictions\/source-recovery/);
 assert.doesNotMatch(route,/method:"POST"|submitClinicalScore|setGrade\(/);
});
