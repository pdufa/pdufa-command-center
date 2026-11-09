"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
 fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const code=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(code.outputText,file);
};
const source=require("../data/focus-r64-original-method-pages.json");
const {buildR64OriginalMethodPageView,FOCUS_R64_METHOD_PAGE_VIEW,EIGHT_SOURCE_DOMAINS}=
 require("../lib/focus-r64-original-method-page-view.ts");
const clone=x=>structuredClone(x);

test("exact R63 29 NCT, 23 applications, 8 ungraded domains and 466 cited PDF page leads",()=>{
 const x=FOCUS_R64_METHOD_PAGE_VIEW;
 assert.ok(x);
 assert.equal(x.uniqueNctCount,29);
 assert.equal(x.applicationGroups,23);
 assert.equal(x.sourceReviewDimensions,8);
 assert.equal(x.unscoredSourceReviewSlots,232);
 assert.equal(x.originalCurrentAttachedDocuments,23);
 assert.equal(x.documentFilesWithMachinePageLeads,22);
 assert.equal(x.sourcePageLeadCount,466);
 assert.equal(x.trials.length,29);
 assert.equal(new Set(x.trials.map(t=>t.nct)).size,29);
 assert.equal(x.trials.reduce((n,t)=>n+t.totalPageLeads,0),466);
 assert.equal(x.trials.filter(t=>t.totalPageLeads>0).length,12);
 assert.equal(x.trials.filter(t=>t.totalPageLeads===0).length,17);
 assert.equal(x.trials.reduce((n,t)=>n+t.domains.length,0),232);
 assert.equal(EIGHT_SOURCE_DOMAINS.length,8);
 assert.equal(x.clinicalMethodScores,0);
 assert.equal(x.qualifiedReviewerSignoffs,0);
 assert.equal(x.independentlyValidatedFdaForecasts,0);
 assert.equal(x.measuredForecastAccuracy,null);
 assert.equal(x.officialFutureFdaOutcome,"ABSTAIN");
 assert.equal(x.not800CompletedScientificAssessments,true);
 assert.equal(x.noProductionWritesOrModelTraining,true);
 assert.ok(x.trials.every(t=>t.installedScientificResearchStage===4&&
    t.independentlyCompletedAssessmentLevel===null&&t.signedScientificGrades===0&&
    t.officialFdaOutcome==="ABSTAIN"&&
    t.domains.every(d=>d.level==="UNASSESSED_SOURCE_ONLY"&&
      d.scientificScore===null&&d.qualifiedReviewerSigned===false&&
      d.originalSourceVersionBeforeUnblindingVerified===false)));
});

test("Savara has exactly its originally cited protocol and SAP pages, not an efficacy grade",()=>{
 const x=FOCUS_R64_METHOD_PAGE_VIEW.trials.find(t=>t.nct==="NCT04544293");
 assert.equal(x.ticker,"SVRA");
 assert.equal(x.sourcePdfDocumentsWithPageLeads,2);
 assert.equal(x.totalPageLeads,47);
 assert.equal(x.domains[0].references[0].filename,"Prot_000.pdf");
 assert.equal(x.domains[0].references[0].pdfPageOneBased,2);
 assert.equal(x.domains[3].references[0].pageUrl,
  "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf#page=5");
 assert.equal(x.domains[3].level,"UNASSESSED_SOURCE_ONLY");
});

test("missing current registry attached document page leads are not scientific failures",()=>{
 const x=FOCUS_R64_METHOD_PAGE_VIEW.trials.find(t=>t.nct==="NCT05126758");
 assert.equal(x.totalPageLeads,0);
 assert.equal(x.sourcePdfDocumentsWithPageLeads,0);
 assert.equal(x.domains.length,8);
 assert.ok(x.domains.every(d=>d.references.length===0&&d.scientificScore===null));
 assert.equal(x.officialFdaOutcome,"ABSTAIN");
});

test("source coverage duplicated in two application cycles never creates a duplicate method assessment",()=>{
 const x=FOCUS_R64_METHOD_PAGE_VIEW.trials.find(t=>t.nct==="NCT02500381");
 assert.deepEqual(x.applicationCycles,["srpt-casimersen","srpt-golodirsen"]);
 assert.equal(FOCUS_R64_METHOD_PAGE_VIEW.trials.filter(t=>t.nct===x.nct).length,1);
});

test("forged source links, NCT IDs, extra forecast field, misleading page totals fail closed",()=>{
 const cases=[
  x=>x.originalR63Sha256="0".repeat(64),
  x=>x.originalArtifact=0,
  x=>x.docs.pop(),
  x=>x.docs[0][0]="NCT99999999",
  x=>x.docs[0][1]="fake-file.pdf",
  x=>x.trialPageLeads.pop(),
  x=>x.trialPageLeads[0][0]="NCT99999999",
  x=>x.trialPageLeads[1][0]=x.trialPageLeads[0][0],
  x=>x.trialPageLeads[0][1][0][0]=[21,1],
  x=>x.trialPageLeads[0][1][0][0]=[0,9000],
  x=>x.trialPageLeads[0][1][0].push([0,14]),
  x=>x.trialPageLeads[0][1][0].pop(),
  x=>x.trialPageLeads[0][1].pop(),
  x=>x.trialPageLeads[0][1][0][0]=[-1,14],
  x=>x.independentlyValidatedFdaForecasts=23,
  x=>x.fdaApprovalProbability=.95
 ];
 cases.forEach((f,i)=>{
   const x=clone(source);
   f(x);
   assert.equal(buildR64OriginalMethodPageView(x),null,"forged input "+i);
 });
});

test("assessment page visibly mounts the original PDF domain-by-domain ladder",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
 const view=fs.readFileSync(path.join(root,"app/predictions/assessment/OriginalMethodSourceLadderR64.tsx"),"utf8");
 const style=fs.readFileSync(path.join(root,"app/predictions/assessment/OriginalMethodSourceLadderR64.module.css"),"utf8");
 assert.match(page,/import OriginalMethodSourceLadderR64/);
 assert.match(page,/<OriginalMethodSourceLadderR64/);
 assert.match(view,/UNASSESSED · SOURCE ONLY/);
 assert.match(view,/Research installation stage/);
 assert.match(view,/Trial assessment level/);
 assert.match(view,/PDF page/);
 assert.match(view,/original public protocol/);
 assert.match(style,/@media\(max-width:480px\)/);
 assert.doesNotMatch(view,/fetch\(|submitGrade|POST\s*\/api|setReviewerSignoff/);
});
