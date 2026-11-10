"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const s=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(s.outputText,file);
};
const snapshot=require("../data/focus-r69-original-pubmed-leads.json");
const {buildR69RegistryPublicationLeads,FOCUS_R69_REGISTRY_PUBLICATION_LEADS}=
 require("../lib/focus-r69-original-publication-leads.ts");

test("R69 original 17 missing-primary NCT source references contain only 11 unverified PubMed leads",()=>{
 const d=FOCUS_R69_REGISTRY_PUBLICATION_LEADS;
 assert.ok(d,"immutable original-source membership and references should pass");
 assert.equal(d.schema,"MAIN_R69_UNREVIEWED_EXACT_SOURCE_PUBLICATION_LEADS");
 assert.equal(d.originalResearchRun,42727350931);
 assert.equal(d.originalResearchArtifact,13723526354);
 assert.equal(d.exactNctsInResearch,29);
 assert.equal(d.provisionalApplications,23);
 assert.equal(d.retainedRegistryPrimaryMissingNcts,17);
 assert.equal(d.casesWithUnverifiedPublicationLeads,7);
 assert.equal(d.casesWithoutPubmedLeadsInArchive,10);
 assert.equal(d.candidateReferenceCount,11);
 assert.equal(d.cases.length,17);
 assert.equal(new Set(d.cases.map(x=>x.nct)).size,17);
 assert.equal(d.cases.reduce((n,x)=>n+x.sourceReferenceLeads.length,0),11);
 assert.equal(d.paperTextIndependentReviews,0);
 assert.equal(d.exactNctPivotalOutcomeVerified,0);
 assert.equal(d.scientificReviewSignoffs,0);
 assert.equal(d.fdaForecastsValidated,0);
 assert.equal(d.measuredForecastAccuracy,null);
 assert.equal(d.futureFdaOutcome,"ABSTAIN");
 assert.equal(d.registryReferenceIsNotOriginalPivotalStudyResults,true);
 assert.equal(d.originalSourceOnlyNoNetworkOrProductionWrites,true);
 assert.ok(d.cases.every(x=>x.independentExactStudyMatchVerified===false&&
   x.independentlyVerifiedPivotalStudyOutcome===null&&
   x.qualifiedReviewerSigned===false&&x.scientificMethodGrade===null&&
   x.futureFDAOutcome==="ABSTAIN"));
 for(const c of d.cases)for(const lead of c.sourceReferenceLeads){
  assert.equal(lead.registryCitationType,"DERIVED");
  assert.equal(lead.pubmedUrl,
   "https://pubmed.ncbi.nlm.nih.gov/"+lead.pmid+"/");
  assert.equal(lead.articleBodyIndependentlyReviewed,false);
  assert.equal(lead.paperContainsPivotalEndpointVerified,false);
  assert.equal(lead.exactNctPaperMatchVerified,false);
  assert.equal(lead.qualifiedScientificReviewerSigned,false);
  assert.equal(lead.clinicalResult,null);
 }
});

test("Exact archived registration reference association is not a claimed efficacy report",()=>{
 const cases=FOCUS_R69_REGISTRY_PUBLICATION_LEADS.cases;
 const rows=new Map(cases.map(x=>[x.nct,x.sourceReferenceLeads.map(p=>p.pmid)]));
 assert.deepEqual(rows.get("NCT02500381"),["40098309","34105177"]);
 assert.deepEqual(rows.get("NCT04871282"),["42848980"]);
 assert.deepEqual(rows.get("NCT05126758"),["42526472"]);
 assert.deepEqual(rows.get("NCT05662241"),["42233621","41840328"]);
 assert.deepEqual(rows.get("NCT06081894"),["42667274","42663312","42663111"]);
 assert.deepEqual(rows.get("NCT06153693"),["40587141"]);
 assert.deepEqual(rows.get("NCT06343779"),["42849489"]);
 assert.deepEqual(rows.get("NCT05059223"),[]);
 assert.equal(rows.size,17);
 const shared=cases.find(x=>x.nct==="NCT02500381");
 assert.equal(shared.applicationCycles.length,2);
});

test("Altered original evidence, inventing publication match or fabricated score fails closed",()=>{
 const mutations=[
  x=>x.rows[0][0]="NCT00000001",
  x=>x.rows.pop(),
  x=>x.rows[3][1].push("12345678"),
  x=>x.rows[7][1][0]="99999999",
  x=>x.rows[7][1].push(x.rows[7][1][0]),
  x=>x.rows[7][1].reverse(),
  x=>x.originalR69Sha256="0".repeat(64),
  x=>x.verifiedPivotalTrials=7,
  x=>x.artifact=1
 ];
 mutations.forEach((change,i)=>{
  const data=structuredClone(snapshot);
  change(data);
  assert.equal(buildR69RegistryPublicationLeads(data),null,
    "tampered publication source input "+i+" should be withheld");
 });
});

test("R69 registry reference panel links real PubMed IDs without scientific inference",()=>{
 const read=f=>fs.readFileSync(path.join(root,f),"utf8");
 const board=read("app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx");
 const panel=read("app/predictions/evidence-gaps/OriginalPublicationLeadsR69.tsx");
 const lib=read("lib/focus-r69-original-publication-leads.ts");
 assert.match(board,/OriginalPublicationLeadsR69/);
 assert.match(board,/FOCUS_R69_REGISTRY_PUBLICATION_LEADS/);
 assert.match(panel,/registry publication leads for/);
 assert.match(panel,/PubMed PMID/);
 assert.match(panel,/exact NCT match/);
 assert.match(panel,/NOT been verified/);
 assert.match(panel,/ABSTAIN/);
 assert.match(lib,/originalRegistrySHA256/);
 assert.doesNotMatch(panel,/fetch\(|signedSuccess|clinicalGrade\s*:\s*[1-9]/);
});
