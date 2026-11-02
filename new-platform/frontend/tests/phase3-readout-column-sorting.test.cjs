"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
 mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
   esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const {sortPhase3Readouts,readoutResearchCoverage}=require("../lib/phase3-readout-sort.ts");
const component=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
function row(nct,ticker,kind="POST_PUBLIC_READOUT",p,opts={}){
 return {nctId:nct,ticker,company:opts.company||ticker,
  status:opts.status||"COMPLETED",sourceUrl:"https://clinicaltrials.gov/study/"+nct,
  evidence:{nctId:nct,ticker,kind,evidenceDate:opts.date||"2026-10-30",
   evidenceUrl:"https://example.org/"+ticker,
   drug:opts.drug||"Agent "+ticker,
   indication:opts.indication||"Condition "+ticker,
   ...(p?{primaryEndpointP:{display:p,endpoint:"Primary",sourceUrl:"https://example.org/"+ticker}}:{})}};
}
const a=row("NCT00000001","ZED","POST_PUBLIC_READOUT","p < 0.01");
const b=row("NCT00000002","ALFA","POST_PUBLIC_READOUT","p = 0.004");
const c=row("NCT00000003","NOVA","POST_PUBLIC_READOUT",undefined,{date:"2026-11-01"});
const rows=[a,b,c],ids=items=>items.map(r=>r.nctId);
const study=(r,facts={})=>({nctId:r.nctId,ticker:r.ticker,drug:r.evidence.drug,
 indication:r.evidence.indication,facts,advantages:[]});
const fact={value:"Sourced",status:"VERIFIED",sourceUrl:"https://example.org/study",
 sourceDate:"2026-10-30",method:"Exact trial review",confidence:"HIGH"};
const five={eligibleUsPatients:fact,closestCompetitor:fact,adoption:fact,
 peakAnnualSales:fact,valuationImpact:fact};
test("both sheets expose 11/12 independently clickable sortable columns, including surveys",()=>{
 assert.match(component,/sortedHeader\("row","#"/);
 for(const key of ["ticker","nctId","company","survey","synthesis","drug",
  "indication","status","date","source"])
  assert.ok(component.includes('sortedHeader("'+key+'"'),key+" missing header");
 assert.match(component,/bucket==="post"&&sortedHeader\("factorP"/);
 assert.match(component,/onSort=\{setSortColumn\}/);
 assert.match(component,/aria-sort=\{sort===key/);
 assert.equal(component.split("onResearchSort={()=>setResearchSortRequested(true)}").length-1,2);
});
test("row # sorts the original spreadsheet order, never an unstable display index",()=>{
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"row",false,"post",null)),ids(rows));
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"row",true,"post",null)),ids(rows).reverse());
 assert.match(component,/originalNumbers\.get\(row\.nctId\)/);
});
test("ticker, company and clinical identifier have normal reversible ascending/descending order",()=>{
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"ticker",false,"post",null)),[b.nctId,c.nctId,a.nctId]);
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"ticker",true,"post",null)),[a.nctId,c.nctId,b.nctId]);
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"nctId",true,"post",null)),[c.nctId,b.nctId,a.nctId]);
});
test("Factor P sorts numerically with not-reported last in BOTH directions",()=>{
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"factorP",false,"post",null)),[b.nctId,a.nctId,c.nctId]);
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"factorP",true,"post",null)),[a.nctId,b.nctId,c.nctId]);
});
test("trial date sorts newest or oldest, with chronological ISO day values",()=>{
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"date",true,"post",null)),[c.nctId,a.nctId,b.nctId]);
});
test("Survey Ratings sort uses verified facts; unmatched trials remain at bottom",()=>{
 const feed={schemaVersion:1,sourceAsOf:"2026-11-01",records:[
  study(a,{...five}),study(b,{eligibleUsPatients:fact})]};
 assert.equal(readoutResearchCoverage(a,"post",feed).verified,5);
 assert.equal(readoutResearchCoverage(b,"post",feed).verified,1);
 assert.equal(readoutResearchCoverage(c,"post",feed),null);
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"survey",true,"post",feed)),[a.nctId,b.nctId,c.nctId]);
 assert.deepEqual(ids(sortPhase3Readouts(rows,rows,"survey",false,"post",feed)),[b.nctId,a.nctId,c.nctId]);
});
test("SURVEY uses different stage-specific evidence gates, not clinical forecast scores",()=>{
 const pre=row("NCT00000004","PRE","PRE_AS_OF_CHECK");
 const after=row("NCT00000005","POST","POST_PUBLIC_READOUT");
 const sharedFacts={...five};
 const feed={schemaVersion:1,sourceAsOf:"2026-11-01",records:[study(pre,sharedFacts),study(after,sharedFacts)]};
 assert.equal(readoutResearchCoverage(pre,"pre",feed).ready,true);
 assert.equal(readoutResearchCoverage(after,"post",feed).ready,false);
 const clinicalFeed={...feed,records:[study(pre,sharedFacts),
   study(after,{...sharedFacts,clinicalBenefit:fact,magnitude:fact,safetyAdvantage:fact})]};
 assert.equal(readoutResearchCoverage(after,"post",clinicalFeed).ready,true);
});
test("research matching refuses same ticker with the wrong exact program",()=>{
 const other={schemaVersion:1,sourceAsOf:"2026-11-01",records:[
  study({...a,nctId:"NCT99999999"},five)]};
 assert.equal(readoutResearchCoverage(a,"post",other),null);
 const duplicated={schemaVersion:1,sourceAsOf:"2026-11-01",records:[
  study(a,five),{...study(a,five),drug:"Different agent"}]};
 assert.equal(readoutResearchCoverage(a,"post",duplicated),null);
});

test("TOP and BOTTOM sorting resets independently to the default Ticker A–Z",()=>{
 const src=component;
 const reset=/const resetSorting=\(\)=>\{\s*setSort\("ticker"\);\s*setDesc\(false\);\s*\};/;
 assert.match(src,reset);
 assert.match(src,/onClick=\{resetSorting\} disabled=\{sort==="ticker"&&!desc\}/);
 assert.match(src,/aria-label=\{pre\?"Reset TOP spreadsheet sorting to Ticker A to Z":"Reset BOTTOM spreadsheet sorting to Ticker A to Z"\}/);
 assert.equal(src.split('↺ Reset Sorting').length-1,1);
 // A separate Spreadsheet instance holds a distinct sort/direction pair for each bucket.
 assert.match(src,/<Spreadsheet bucket="pre"/);
 assert.match(src,/<Spreadsheet bucket="post"/);
 // Resetting the sort doesn't touch query or filtering, the survey controls or Factor P.
 const fn=src.substring(src.indexOf("const resetSorting=()=>"),src.indexOf("const availableSortColumns"));
 assert.doesNotMatch(fn,/setQuery|setShowSurveys|setShowSynthesis|setBenefitFeed/);
});
