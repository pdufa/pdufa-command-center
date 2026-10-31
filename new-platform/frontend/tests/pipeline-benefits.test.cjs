"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file
);
const ranked=require("../lib/pipeline-benefit-assessments.ts");
const row={nctId:"NCT12345678",ticker:"EXAM",company:"Example Inc",drug:"Research Therapy",indication:"Disease A",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",censusStatus:"COMPLETED",capUsd:550000000,capAsOf:"2026-10-01",poolStatus:"EXACT_MATCH",postPhase3Evidence:"REGISTRY_COMPLETED",qualification:"NEEDS_REVIEW",reasons:[],timeline:{phase3DataRelease:null,pdufaTarget:null}};
const comparator=(patch={})=>({
 programNctId:row.nctId,programTicker:row.ticker,programTherapy:row.drug,verificationStatus:"VERIFIED",lastVerified:"2026-10-30",indication:row.indication,id:"cmp-a",kind:"APPROVED",therapy:"Existing A",manufacturer:"Maker A",regulatorOrTrialId:"NDA-12345",approvalOrPhase:"FDA approved",lineOfTherapy:"second line",patientPopulation:"marker positive adults",
 sourceUrl:"https://www.fda.gov/example",sourceDate:"2026-10-20",sourceType:"FDA",
 outcome:"Responder rate",effectSize:"5 percentage points",duration:"12 months",safety:"Not assessed",convenience:"Not assessed",firstYearPrice:"Not assessed",payerAccess:"Not assessed",
 comparisonBasis:"INDIRECT",finding:"INSUFFICIENT_EVIDENCE",reason:"Missing treatment-line matched comparative trial",confidence:"LOW",...patch
});
test("original 20 assessment ranking maps each of 38 original research fields exactly once",()=>{
 const a=ranked.auditAssessmentFieldMapping();
 assert.equal(a.rankedAssessments,20);assert.equal(a.originalFields,38);assert.equal(a.assignedFields,38);assert.equal(a.crossCuttingFields,9);
 assert.deepEqual(a.duplicates,[]);assert.deepEqual(a.unassigned,[]);assert.deepEqual(a.unknown,[]);
 assert.equal(ranked.RANKED_BENEFIT_ASSESSMENTS[5].title,"Competitive Advantage");
});
test("unpopulated assessments abstain and do not create survival, financial or adoption facts",()=>{
 const items=ranked.assessmentCoverage(row,"2026-10-31");
 assert.equal(items.length,20);
 for(const item of items){assert.equal(item.state,"NOT_ASSESSED");assert.equal(item.verified,0)}
 for(const item of items)assert.ok(item.required>0,"Every assessment has real defined inputs");
});
test("approved versus pipeline comparator identity is strict and missing competitor data remains unknown",()=>{
 const a=comparator();
 const b=comparator({id:"cmp-b",kind:"PIPELINE",therapy:"Pipeline B",manufacturer:"Sponsor B",regulatorOrTrialId:"NCT87654321",approvalOrPhase:"Phase 3",sourceUrl:"https://clinicaltrials.gov/study/NCT87654321",sourceType:"CLINICAL_TRIALS"});
 const good=ranked.validateComparatorInventory(row,[a,b]);
 assert.equal(good.approved,1);assert.equal(good.pipeline,1);assert.equal(good.rankingAllowed,false);
 assert.equal(ranked.validateComparatorInventory(row,[a,a]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({indication:"Different disease"})]).accepted.length,0);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({regulatorOrTrialId:""})]).accepted.length,0);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({sourceUrl:"http://unverified"})]).accepted.length,0);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({kind:"PIPELINE",regulatorOrTrialId:row.nctId})]).accepted.length,0);
});
test("unsupported directional findings and invalid future dates are rejected",()=>{
 assert.equal(ranked.validateComparatorInventory(row,[comparator({finding:"BETTER",comparisonBasis:"NOT_COMPARABLE"})]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({finding:"BETTER",effectSize:""})]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({sourceDate:"2099-01-01"})]).rejected,1);
});
test("20 primary website headings and comparator subcolumns are wired without replacing four views",()=>{
 const source=fs.readFileSync(path.join(__dirname,"../app/PipelineFourViews.tsx"),"utf8");
 assert.ok(source.includes("RANKED_BENEFIT_ASSESSMENTS.map"));
 assert.ok(source.includes("Existing Approved Therapies"));
 assert.ok(source.includes("Competing Pipeline Therapies"));
 assert.ok(source.includes("Comparative Advantage"));
 assert.ok(source.includes("mode===\"dossier\""));
 assert.ok(source.includes("mode===\"analytics\""));
 assert.ok(source.includes("mode===\"kanban\""));
 assert.ok(source.includes("mode===\"table\""));
 assert.ok(source.includes("PIPELINE_RESEARCH_SECTIONS.map"));
});


test("different product, duplicate therapy, unreviewed and indirect superiority claims fail closed",()=>{
 assert.equal(ranked.validateComparatorInventory(row,[comparator({programTherapy:"Wrong drug"})]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({verificationStatus:undefined})]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({finding:"BETTER",comparisonBasis:"INDIRECT"})]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator({finding:"BETTER",comparisonBasis:"DIRECT_HEAD_TO_HEAD"})]).rejected,1);
 assert.equal(ranked.validateComparatorInventory(row,[comparator(),comparator({id:"another",regulatorOrTrialId:"NDA-99999"})]).accepted.length,1);
});
