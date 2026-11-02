"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_,key)=>key==="__esModule"?false:String(key)});};
const {SURVEY_INPUT_COUNT,surveyMissingnessForPosting}=require("../lib/phase3-survey-missingness.ts");
const {postingRatingAudit}=require("../lib/phase3-posting-rating-audit.ts");
const {parseBenefitFeed}=require("../lib/benefit-assessments.ts");
const Phase3=require("../app/Phase3RegistryPostingSheets.tsx").default;
const snapshot=require("../public/phase3-registry-postings-current.json");
global.IS_REACT_ACT_ENVIRONMENT=true;
const before=snapshot.records.find(r=>r.resultsCount===0);
const after=snapshot.records.find(r=>r.resultsCount>0);
const postRow=r=>({...r,sourceUrl:"https://clinicaltrials.gov/study/"+r.nctId});
const fact=(status)=>({value:status==="VERIFIED"?"10%":"Estimated",
 status,sourceUrl:"https://clinicaltrials.gov/study/NCT01234567",sourceDate:"2026-10-01",
 method:"Verified survey input test fixture",confidence:"HIGH"});
const record=(r,facts)=>({nctId:r.nctId,ticker:r.ticker,drug:"TEST THERAPY",
 indication:"TEST INDICATION",facts,advantages:[]});
const feed=(records)=>parseBenefitFeed({schemaVersion:1,sourceAsOf:"2026-10-30",records});
const textOf=n=>typeof n==="string"?n:typeof n==="number"?String(n):n?.children?.map(textOf).join("")||"";
test("M denominator is exactly the 38 canonical benefit-survey questions",()=>{
 assert.equal(SURVEY_INPUT_COUNT,38);
});
test("missing percentage is calculated per exact NCT, not from results-posting status",()=>{
 const f=feed([
  record(before,{eligibleUsPatients:fact("VERIFIED"),clinicalBenefit:fact("MODELED")}),
  record(after,{unmetNeed:fact("VERIFIED")})
 ]);
 const upper=surveyMissingnessForPosting(postRow(before),f);
 const lower=surveyMissingnessForPosting(postRow(after),f);
 assert.deepEqual(
  {total:upper.total,verified:upper.verified,modeled:upper.modeled,missing:upper.missing,missingPercent:upper.missingPercent},
  {total:38,verified:1,modeled:1,missing:36,missingPercent:94.7}
 );
 assert.equal(lower.missingPercent,97.4);
 const up=postingRatingAudit(postRow(before),upper);
 const down=postingRatingAudit(postRow(after),lower);
 assert.equal(up.group.M.label,"94.7% missing");
 assert.equal(up.ingredient.MISS.label,"36/38 (94.7%)");
 assert.equal(down.group.M.label,"97.4% missing");
 assert.match(up.group.M.description,/not recorded.*NOT failed trial outcomes/i);
 assert.equal(up.group.B.label,"Not rated");
 assert.equal(down.group.A.label,"Results posted");
});
test("unmatched, ambiguous, or unavailable survey evidence must not show invented percentages",()=>{
 assert.equal(surveyMissingnessForPosting(postRow(before),null),null);
 assert.equal(surveyMissingnessForPosting(postRow(before),feed([])),null);
 assert.equal(surveyMissingnessForPosting(postRow(before),feed([record(after,{})])),null);
 const wrong={...record(before,{}),ticker:"OTHER"};
 assert.equal(surveyMissingnessForPosting(postRow(before),feed([wrong])),null);
 const one=record(before,{});
 const multi=feed([one,{...one,drug:"SECOND THERAPY"}]);
 assert.equal(surveyMissingnessForPosting(postRow(before),multi),null);
 assert.equal(postingRatingAudit(postRow(before)).group.M.label,"Not assessed");
 assert.equal(postingRatingAudit(postRow(after)).ingredient.MISS.label,"% pending");
});
test("both independent displayed spreadsheets use M percentage and retain 20 horizontal ingredients",async()=>{
 const previous=global.fetch;
 const f=feed([
  record(before,{eligibleUsPatients:fact("VERIFIED"),clinicalBenefit:fact("MODELED")}),
  record(after,{unmetNeed:fact("VERIFIED")})
 ]);
 global.fetch=async url=>({ok:true,json:async()=>String(url).includes("/api/benefit-assessments")?f:snapshot});
 let r;
 try{
  await act(async()=>{r=create(React.createElement(Phase3));});
  const sections=()=>r.root.findAllByType("section").filter(s=>/registry results trial spreadsheet/.test(s.props["aria-label"]||""));
  const [top,bottom]=sections();
  const nctFilter=(section,label)=>section.findAllByType("input").find(x=>x.props["aria-label"]===label);
  await act(async()=>nctFilter(top,"Before filter NCT").props.onChange({target:{value:before.nctId}}));
  await act(async()=>nctFilter(bottom,"Past filter NCT").props.onChange({target:{value:after.nctId}}));
  const rating=(section)=>section.findAllByType("tbody")[0].findAllByType("td").find(x=>x.props["data-rating-group"]==="M");
  assert.match(textOf(rating(top)),/94\.7% missing/);
  assert.match(textOf(rating(bottom)),/97\.4% missing/);
  const topM=top.findAllByType("th").find(x=>x.props["data-rating-group"]==="M");
  await act(async()=>topM.findByType("button").props.onClick());
  const cells=top.findAllByType("tbody")[0].findAllByType("td");
  assert.equal(cells.find(x=>x.props["data-rating-ingredient"]==="MISS").findByType("span").children.join(""),"36/38 (94.7%)");
  assert.equal(bottom.findAllByType("th").filter(x=>x.props["data-rating-ingredient"]).length,0);
  assert.equal(cells.length,top.findAllByType("thead")[0].findAllByType("tr")[0].findAllByType("th").length);
 }finally{
  if(r)await act(async()=>r.unmount());
  global.fetch=previous;
 }
});
