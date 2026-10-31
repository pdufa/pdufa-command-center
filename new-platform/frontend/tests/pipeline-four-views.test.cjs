"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const extension of [".ts",".tsx"])require.extensions[extension]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file
);
const lib=require("../lib/pipeline-research-view.ts");
const React=require("react");
const render=(Component,props)=>require("react-dom/server").renderToStaticMarkup(React.createElement(Component,props));
const fake={nctId:"NCT12345678",ticker:"TEST",company:"Test Research Sponsor",
 drug:"Therapy A",indication:"Indication A",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
 censusStatus:"COMPLETED",capUsd:500000000,capAsOf:"2026-10-26",
 poolStatus:"EXACT_MATCH",postPhase3Evidence:"REGISTRY_COMPLETED",
 qualification:"NEEDS_REVIEW",reasons:["Check current issuer and rights"],timeline:{
  phase3DataRelease:null,pdufaTarget:null,
 }};
const fact=value=>({value,status:"VERIFIED",sourceUrl:"https://example.org/study",
 sourceDate:"2026-10-20",method:"Matched endpoint",reason:"Study report checked",confidence:"MODERATE"});
test("all thirty-eight fields are uniquely assigned once across seven expandable sections",()=>{
 const sections=lib.PIPELINE_RESEARCH_SECTIONS;
 assert.equal(sections.length,7);
 assert.deepEqual(sections.map(x=>x.fields.length),[6,7,9,4,6,3,3]);
 assert.equal(lib.PIPELINE_RESEARCH_FIELDS.length,38);
 assert.equal(new Set(lib.PIPELINE_RESEARCH_FIELDS.map(x=>x.id)).size,38);
 for(const f of lib.PIPELINE_RESEARCH_FIELDS)assert.ok(f.label&&f.purpose&&f.evidence,f.id);
 for(const id of ["trialId","company","daysSinceReadout","daysToPdufa","competitorCount",
  "clinicalBenefit","competitiveStrategy","overallRank"])assert.ok(lib.PIPELINE_RESEARCH_FIELDS.some(f=>f.id===id));
});
test("source data is visible while missing clinical advantages and PDUFA details remain withheld",()=>{
 assert.equal(lib.researchFieldResult(fake,"trialId","2026-10-31").value,"NCT12345678");
 assert.equal(lib.researchFieldResult(fake,"company","2026-10-31").state,"RECORD");
 assert.equal(lib.researchFieldResult(fake,"daysToPdufa","2026-10-31").state,"MISSING");
 assert.equal(lib.researchFieldResult(fake,"daysSinceReadout","2026-10-31").state,"MISSING");
 assert.equal(lib.researchFieldResult(fake,"competitorCount","2026-10-31").state,"MISSING");
 assert.equal(lib.researchFieldResult(fake,"clinicalBenefit","2026-10-31").state,"MISSING");
 assert.equal(lib.researchFieldResult(fake,"overallRank","2026-10-31").state,"MISSING");
 assert.equal(lib.verifiedMetricCount(fake,"2026-10-31"),0);
});
test("extended fields honor exact NCT, ticker, indication and source identity checks",()=>{
 const original={...fake,commercialAssessment:{nctId:fake.nctId,ticker:fake.ticker,
  indication:fake.indication,fields:{approvedCompetitors:fact(0),lateStageCompetitors:fact(3)},
  additionalFields:{closestCompetitor:fact("Approved Drug A")}}};
 assert.equal(lib.researchFieldResult(original,"competitorCount","2026-10-31").value,"3 competitors");
 assert.equal(lib.researchFieldResult(original,"closestCompetitor","2026-10-31").value,"Approved Drug A");
 assert.equal(lib.researchFieldResult({...original,commercialAssessment:{...original.commercialAssessment,indication:"Other"}},"closestCompetitor","2026-10-31").state,"MISSING");
});
test("workflow respects source gaps and the PDUFA minus three cutoff, not arbitrary success grades",()=>{
 assert.equal(lib.workflowColumn(fake,"2026-10-31"),"readout");
 const readout={date:"2026-09-01",sourceUrl:"https://example.org/release",status:"VERIFIED"};
 const pdufa={date:"2026-11-20",sourceUrl:"https://example.org/fda",status:"VERIFIED"};
 const withReadout={...fake,timeline:{...fake.timeline,phase3DataRelease:readout}};
 assert.equal(lib.workflowColumn(withReadout,"2026-10-31"),"pdufa");
 assert.equal(lib.workflowColumn({...withReadout,timeline:{...withReadout.timeline,pdufaTarget:pdufa}},"2026-10-31"),"approaching");
 assert.equal(lib.workflowColumn({...withReadout,timeline:{...withReadout.timeline,pdufaTarget:pdufa}},"2026-11-17"),"cutoff");
 assert.equal(lib.comparableIndication(fake),"indication a");
});
test("all four options render as real selectable controls and share a single research source",()=>{
 const component=require("../app/PipelineFourViews.tsx").default;
 const html=render(component,{});
 for(const title of ["Advanced Table","Cards + Dossier","Research Workflow","Compare + Analytics"])
  assert.ok(html.includes(title),title);
 assert.ok(html.includes('role="tablist"'));
 const source=fs.readFileSync(path.join(__dirname,"../app/PipelineFourViews.tsx"),"utf8");
 assert.ok(source.includes('limit:String(MAX_ROWS)'));
 assert.ok(source.includes('view:"pipeline"'));
 assert.ok(source.includes('"/api/scope-funnel?"'));
 assert.ok(source.includes("PIPELINE_RESEARCH_SECTIONS.map"));
 assert.ok(source.includes("WORKFLOW_COLUMNS.map"));
 assert.ok(source.includes("same recorded indication"));
 const wrapper=fs.readFileSync(path.join(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(wrapper.includes('<PipelineFourViews />'));
 assert.ok(wrapper.includes('section==="pool"||reviewMode'));
 const api=fs.readFileSync(path.join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
 assert.ok(api.includes('view==="pipeline" && limit==="500"'));
 assert.ok(api.includes("hasSession"));
});
