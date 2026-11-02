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
require.extensions[".css"]=mod=>{mod.exports=new Proxy({},{get:(_,key)=>key==="__esModule"?false:String(key)});};
const {filterAndSortPostingRows,postingFilterCount,EMPTY_POSTING_FILTERS,INITIAL_POSTING_SORT}=
 require("../lib/phase3-registry-posting-filters.ts");
const Component=require("../app/Phase3RegistryPostingSheets.tsx").default;
const snapshot=require("../public/phase3-registry-postings-current.json");
const rows=snapshot.records.map(r=>({
 nctId:r.nctId,ticker:r.ticker,company:r.company,registryStatus:r.registryStatus,
 resultsCount:r.resultsCount,resultsFirstPostedDate:r.resultsFirstPostedDate,
 sourceUrl:"https://clinicaltrials.gov/study/"+r.nctId
}));
const before=rows.filter(r=>r.resultsCount===0),after=rows.filter(r=>r.resultsCount>0);
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):
 node?.children?.map(textOf).join("")||"";

test("column filters combine with the global search and don't mutate saved NCT rows",()=>{
 const original=rows.map(r=>r.nctId);
 const target=before[0],same=before.filter(r=>r.ticker===target.ticker&&r.registryStatus===target.registryStatus);
 const filters={...EMPTY_POSTING_FILTERS,ticker:target.ticker,registryStatus:target.registryStatus};
 const result=filterAndSortPostingRows(before,"",filters,INITIAL_POSTING_SORT);
 assert.equal(result.length,same.length);
 assert.ok(result.every(r=>r.ticker===target.ticker&&r.registryStatus===target.registryStatus));
 const partial=filterAndSortPostingRows(before,target.nctId.toLowerCase(),filters,INITIAL_POSTING_SORT);
 assert.deepEqual(partial.map(r=>r.nctId),[target.nctId]);
 assert.equal(postingFilterCount(filters),2);
 assert.deepEqual(rows.map(r=>r.nctId),original);
});
test("posted-date filter uses exact dates; missing dates never pass a range",()=>{
 const dated=after.find(r=>r.resultsFirstPostedDate);
 assert.ok(dated);
 const f={...EMPTY_POSTING_FILTERS,from:dated.resultsFirstPostedDate,to:dated.resultsFirstPostedDate};
 const exact=filterAndSortPostingRows(after,"",f,INITIAL_POSTING_SORT);
 assert.ok(exact.length>=1);
 assert.ok(exact.every(r=>r.resultsFirstPostedDate===dated.resultsFirstPostedDate));
 const range={...EMPTY_POSTING_FILTERS,from:"2035-01-01"};
 assert.equal(filterAndSortPostingRows(after,"",range,INITIAL_POSTING_SORT).length,0);
 assert.equal(filterAndSortPostingRows(before,"",{...EMPTY_POSTING_FILTERS,resultsPosted:"yes"},INITIAL_POSTING_SORT).length,0);
 assert.equal(filterAndSortPostingRows(after,"",{...EMPTY_POSTING_FILTERS,resultsPosted:"no"},INITIAL_POSTING_SORT).length,0);
});
test("sort toggles date descending and NCT ascending without changing source",()=>{
 const sorted=filterAndSortPostingRows(after,"",EMPTY_POSTING_FILTERS,{key:"resultsFirstPostedDate",direction:"desc"});
 for(let i=1;i<sorted.length;i++){
   assert.ok((sorted[i-1].resultsFirstPostedDate||"") >= (sorted[i].resultsFirstPostedDate||""));
 }
 const asc=filterAndSortPostingRows(before,"",EMPTY_POSTING_FILTERS,{key:"nctId",direction:"asc"});
 assert.deepEqual(asc.map(r=>r.nctId),[...before].sort((a,b)=>a.nctId.localeCompare(b.nctId,"en-US",{numeric:true,sensitivity:"base"})).map(r=>r.nctId));
});
test("both tables filter independently and paginate only matching NCTs",async()=>{
 global.IS_REACT_ACT_ENVIRONMENT=true;
 const previous=global.fetch;
 global.fetch=async()=>({ok:true,json:async()=>snapshot});
 let renderer;
 try{
   await act(async()=>{renderer=create(React.createElement(Component));});
   const get=(type,label)=>renderer.root.findAllByType(type).find(n=>n.props["aria-label"]===label);
   const sections=()=>renderer.root.findAllByType("section").filter(s=>/registry results trial spreadsheet/.test(s.props["aria-label"]||""));
   assert.equal(sections().length,2);
   const first=before[0];
   await act(async()=>get("select","Before filter ticker").props.onChange({target:{value:first.ticker}}));
   const b=sections()[0],p=sections()[1];
   assert.equal(b.findAllByType("tbody")[0].findAllByType("tr").length,Math.min(50,before.filter(x=>x.ticker===first.ticker).length));
   assert.equal(p.findAllByType("tbody")[0].findAllByType("tr").length,Math.min(50,after.length));
   assert.match(textOf(b),new RegExp(before.filter(x=>x.ticker===first.ticker).length+" matching"));
   await act(async()=>get("input","Before filter NCT").props.onChange({target:{value:first.nctId}}));
   assert.equal(b.findAllByType("tbody")[0].findAllByType("tr").length,1);
   assert.ok(textOf(b).includes(first.nctId));
   await act(async()=>get("button","Sort Before by NCT / Trial, not sorted").props.onClick());
   assert.equal(b.findAllByType("th").find(th=>th.props["aria-sort"]==="ascending"&&textOf(th).includes("NCT")).props["aria-sort"],"ascending");
   await act(async()=>b.findAllByType("button").find(x=>textOf(x)==="Clear column filters").props.onClick());
   assert.equal(b.findAllByType("tbody")[0].findAllByType("tr").length,Math.min(50,before.length));
   // A shared search works across both tables without dropping independent filters.
   const target=after[0];
   await act(async()=>get("input","Past filter NCT").props.onChange({target:{value:target.nctId}}));
   await act(async()=>renderer.root.findByProps({id:"phase3-postings-query"}).props.onChange({target:{value:target.nctId}}));
   assert.match(textOf(sections()[1]),/1 matching/);
   await act(async()=>renderer.root.findByProps({id:"phase3-postings-query"}).props.onChange({target:{value:""}}));
   assert.match(textOf(sections()[1]),/1 matching/);
 }finally{
   if(renderer)await act(async()=>renderer.unmount());
   global.fetch=previous;
 }
});
