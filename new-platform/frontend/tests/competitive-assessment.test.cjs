"use strict";
const { test }=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const extension of [".ts",".tsx"]) require.extensions[extension]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file
);
const {COMPETITIVE_ASSESSMENT_COLUMNS,verifiedCompetitiveFact}=require("../lib/competitive-assessment.ts");
const {CompetitiveAssessmentHeaders,CompetitiveAssessmentCells,CompetitiveColumnPurposes}=require("../app/CompetitiveAssessmentColumns.tsx");
const React=require("react");
const render=(component,props)=>require("react-dom/server").renderToStaticMarkup(React.createElement(component,props));
const id={nctId:"NCT00000001",ticker:"ABC",indication:"Condition A"};
const fact=value=>({value,status:"VERIFIED",sourceUrl:"https://clinicaltrials.gov/study/NCT00000001",sourceDate:"2026-10-25",method:"Indication-matched review",reason:"Source and denominator reviewed",confidence:"MODERATE"});
const dossier=fields=>({...id,fields});
test("seventeen distinct columns have verbatim purposes and evidence requirements",()=>{
 assert.equal(COMPETITIVE_ASSESSMENT_COLUMNS.length,17);
 assert.equal(new Set(COMPETITIVE_ASSESSMENT_COLUMNS.map(x=>x.id)).size,17);
 const guide=render(CompetitiveColumnPurposes,{});
 for(const x of COMPETITIVE_ASSESSMENT_COLUMNS){
  assert.ok(x.purpose.endsWith("."));
  assert.ok(x.evidence);
  assert.ok(guide.includes(x.purpose));
 }
});
test("fail closed on unmatched study identity and unverified facts",()=>{
 assert.equal(verifiedCompetitiveFact(dossier({approvedCompetitors:fact(0)}),id,"approvedCompetitors").value,0);
 assert.equal(verifiedCompetitiveFact(dossier({adoption:fact(22)}),id,"adoption").value,22);
 assert.equal(verifiedCompetitiveFact(dossier({adoption:fact(103)}),id,"adoption"),null);
 assert.equal(verifiedCompetitiveFact(dossier({approvedCompetitors:fact(-1)}),id,"approvedCompetitors"),null);
 assert.equal(verifiedCompetitiveFact(dossier({eligibleUsPatients:fact(1234)}),{...id,ticker:"OTHER"},"eligibleUsPatients"),null);
 assert.equal(verifiedCompetitiveFact(dossier({eligibleUsPatients:fact(1234)}),{...id,nctId:"NCT99999999"},"eligibleUsPatients"),null);
 assert.equal(verifiedCompetitiveFact(dossier({eligibleUsPatients:{...fact(1234),reason:""}}),id,"eligibleUsPatients"),null);
 assert.equal(verifiedCompetitiveFact(dossier({eligibleUsPatients:{...fact(1234),sourceDate:"2026-02-31"}}),id,"eligibleUsPatients"),null);
});
test("new Pipeline columns are present with explicit reasons but no fabricated estimates",()=>{
 const html=render(CompetitiveAssessmentCells,{row:{...id,sourceUrl:"https://clinicaltrials.gov/study/NCT00000001",reasons:["Pending rights verification"],therapyCostComparison:null}});
 const header=render(CompetitiveAssessmentHeaders,{});
 assert.equal((header.match(/<th/g)||[]).length,13);
 assert.equal((html.match(/<td/g)||[]).length,13);
 assert.ok(html.includes("Not assessed"));
 assert.ok(html.includes("ABSTAIN — not assessed"));
 assert.ok(html.includes("Pending rights verification"));
 assert.ok(html.includes("Ranked priorities 1–10"));
 const sourced=render(CompetitiveAssessmentCells,{row:{...id,sourceUrl:"https://clinicaltrials.gov/study/NCT00000001",reasons:[],commercialAssessment:dossier({approvedCompetitors:fact(0),lateStageCompetitors:fact(2),eligibleUsPatients:fact(20000)})}});
 assert.ok(sourced.includes("20,000"));
 assert.ok(sourced.includes("2 comparable options"));
 assert.ok(sourced.includes("SOURCE-VERIFIED FACT"));
});
