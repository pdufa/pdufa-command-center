"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const source=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(source.outputText,file);
};
const snapshot=require("../data/focus-r64-original-method-pages.json");
const {buildR64OriginalMethodPageView,FOCUS_R64_METHOD_PAGE_VIEW,EIGHT_SOURCE_DOMAINS}=
 require("../lib/focus-r64-original-method-page-view.ts");
const clone=x=>structuredClone(x);

test("All 29 NCTs have exactly eight unscored domains from original R63 page leads",()=>{
 const r=FOCUS_R64_METHOD_PAGE_VIEW;
 assert.ok(r,"archived R63 original page index must pass validation");
 assert.equal(r.schema,"MAIN_R64_VIEW_ONLY_ORIGINAL_R63_EIGHT_DOMAIN_PAGE_LEADS");
 assert.equal(r.originalRun,42713443428);
 assert.equal(r.originalArtifact,13717655352);
 assert.equal(r.uniqueNctCount,29);
 assert.equal(r.applicationGroups,23);
 assert.equal(r.sourceReviewDimensions,8);
 assert.equal(r.unscoredSourceReviewSlots,232);
 assert.equal(r.originalCurrentAttachedDocuments,23);
 assert.equal(r.documentFilesWithMachinePageLeads,22);
 assert.equal(r.trialsWithCurrentPageLeads,12);
 assert.equal(r.trialsWithoutCurrentPageLeads,17);
 assert.equal(r.sourcePageLeadCount,466);
 assert.equal(r.trials.length,29);
 assert.equal(new Set(r.trials.map(t=>t.nct)).size,29);
 assert.equal(r.trials.reduce((n,t)=>n+t.totalPageLeads,0),466);
 assert.ok(r.trials.every(t=>t.domains.length===8&&
   t.domains.every((d,i)=>d.key===EIGHT_SOURCE_DOMAINS[i].key&&
     d.level==="UNASSESSED_SOURCE_ONLY"&&d.scientificScore===null&&
     d.qualifiedReviewerSigned===false&&
     d.originalSourceVersionBeforeUnblindingVerified===false)));
 assert.equal(r.clinicalMethodScores,0);
 assert.equal(r.qualifiedReviewerSignoffs,0);
 assert.equal(r.independentlyValidatedFdaForecasts,0);
 assert.equal(r.measuredForecastAccuracy,null);
 assert.equal(r.officialFutureFdaOutcome,"ABSTAIN");
 assert.equal(r.not800CompletedScientificAssessments,true);
 assert.equal(r.noProductionWritesOrModelTraining,true);
});

test("Savara source PDFs link to their original pages without scientific score",()=>{
 const r=FOCUS_R64_METHOD_PAGE_VIEW;
 const svra=r.trials.find(t=>t.nct==="NCT04544293");
 assert.ok(svra);
 assert.equal(svra.ticker,"SVRA");
 assert.equal(svra.totalPageLeads,47);
 assert.equal(svra.sourcePdfDocumentsWithPageLeads,2);
 assert.deepEqual(svra.applicationCycles,["svra-molgramostim"]);
 const domain=svra.domains.find(d=>d.key==="MULTIPLICITY_CONTROL");
 assert.equal(domain.level,"UNASSESSED_SOURCE_ONLY");
 assert.equal(domain.references.length,6);
 const original=domain.references[0];
 assert.equal(original.pdfPageOneBased,5);
 assert.equal(original.originalUrl,
   "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf");
 assert.equal(original.pageUrl,original.originalUrl+"#page=5");
 assert.equal(svra.independentlyCompletedAssessmentLevel,null);
 assert.equal(svra.officialFdaOutcome,"ABSTAIN");
});

test("Trials lacking currently attached PDF page references are not marked failures",()=>{
 const r=FOCUS_R64_METHOD_PAGE_VIEW;
 const absent=r.trials.find(t=>t.nct==="NCT05126758");
 assert.ok(absent);
 assert.equal(absent.sourcePdfDocumentsWithPageLeads,0);
 assert.equal(absent.totalPageLeads,0);
 assert.equal(absent.domains.length,8);
 assert.ok(absent.domains.every(d=>d.references.length===0 &&
   d.level==="UNASSESSED_SOURCE_ONLY"));
 assert.equal(absent.clinicalMethodScore,undefined);
 assert.equal(absent.officialFdaOutcome,"ABSTAIN");
});

test("Any altered application membership, PDF page, duplicate document, or forged grade fails closed",()=>{
 const mutate=[
  x=>x.originalR63Sha256="a".repeat(64),
  x=>x.originalArtifact=10,
  x=>x.docs.pop(),
  x=>x.docs[0][0]="NCT99999999",
  x=>x.docs[1]=x.docs[0],
  x=>x.trialPageLeads.pop(),
  x=>x.trialPageLeads[0][1].pop(),
  x=>x.trialPageLeads[0][1][0].pop(),
  x=>x.trialPageLeads[0][1][0][0][0]=999,
  x=>x.trialPageLeads[0][1][0][0][1]=0,
  x=>x.validatedForecasts=23,
  x=>x.grade=99,
 ];
 for(let i=0;i<mutate.length;i++){
  const changed=clone(snapshot);
  mutate[i](changed);
  assert.equal(buildR64OriginalMethodPageView(changed),null,
    "mutated research source input "+i+" must fail closed");
 }
});

test("FOCUS assessment page mounts page-linked R64 review above existing 800-method research matrix",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
 const component=fs.readFileSync(
   path.join(root,"app/predictions/assessment/OriginalMethodSourceLadderR64.tsx"),"utf8");
 const css=fs.readFileSync(
   path.join(root,"app/predictions/assessment/OriginalMethodSourceLadderR64.module.css"),"utf8");
 assert.match(page,/import OriginalMethodSourceLadderR64/);
 assert.match(page,/<OriginalMethodSourceLadderR64/);
 assert.ok(page.indexOf("<OriginalMethodSourceLadderR64")<
   page.indexOf("<ScientificMethodMatrix"));
 assert.match(component,/Assessment level: UNASSESSED/);
 assert.match(component,/PDF page/);
 assert.match(component,/NOT CALIBRATED/);
 assert.match(component,/800-test completion/);
 assert.match(css,/@media\(max-width:480px\)/);
 assert.doesNotMatch(component,/fetch\(|setReviewerSignoff|POST\s*\/api/);
});
