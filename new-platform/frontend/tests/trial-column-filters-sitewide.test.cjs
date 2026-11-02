"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const React=require("react");
const ts=require("typescript");
const {act,create}=require("react-test-renderer");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_,key)=>key==="__esModule"?false:String(key)});};
const {applyColumnFilters,activeColumnFilters}=require("../app/TrialColumnFilterBar.tsx");
const rows=[
 {ticker:"AAA",nctId:"NCT11111111",company:"Alpha",s:3,d:null,stage:"Phase 3"},
 {ticker:"BBB",nctId:"NCT22222222",company:"Beta",s:31,d:-10,stage:"Phase 3"},
 {ticker:"CCC",nctId:"NCT33333333",company:"Gamma",s:75,d:45,stage:"Phase 2"},
];
const read=(row,key)=>row[key];
test("multiple column filters AND together without modifying source rows",()=>{
 const x=applyColumnFilters(rows,{stage:"Phase 3",s:">=30"},read);
 assert.deepEqual(x.map(r=>r.ticker),["BBB"]);
 assert.equal(activeColumnFilters({stage:"Phase 3",s:">=30",company:""}),2);
 assert.deepEqual(rows.map(r=>r.ticker),["AAA","BBB","CCC"]);
});
test("numeric filter excludes missing evidence instead of treating as zero",()=>{
 assert.deepEqual(applyColumnFilters(rows,{d:"<=0"},read).map(x=>x.ticker),["BBB"]);
 assert.deepEqual(applyColumnFilters(rows,{s:">20"},read).map(x=>x.ticker),["BBB","CCC"]);
});
test("all three existing TOOLS/readout table components include independent filter state",()=>{
 const p=require("node:path");
 const dir=p.resolve(__dirname,"../app");
 for(const file of ["ToolsOpeningTrialGrid.tsx","ToolsResultsSpreadsheet.tsx","Phase3ReadoutSheets.tsx"]){
  const data=fs.readFileSync(p.join(dir,file),"utf8");
  assert.match(data,/TrialColumnFilterBar/);
  assert.match(data,/applyColumnFilters/);
 }
});
test("visible-page filter controls expose inputs, clear action and are responsive",async()=>{
 global.IS_REACT_ACT_ENVIRONMENT=true;
 const Component=require("../app/TrialColumnFilterBar.tsx").default;
 let state={ticker:"A"},view;
 const make=()=>React.createElement(Component,{title:"Test",fields:[{key:"ticker",label:"Ticker"},{key:"s",label:"S"}],
  filters:state,onChange:next=>{state=next;}});
 try{
  await act(async()=>{view=create(make());});
  assert.equal(view.root.findAllByType("input").length,2);
  assert.equal(view.root.findByType("summary").children.some(c=>String(c).includes("Column filters")),true);
  await act(async()=>view.root.findAllByType("button").find(b=>b.children.join("").includes("Clear column filters")).props.onClick());
  assert.deepEqual(state,{});
 }finally{if(view)await act(async()=>view.unmount());}
});
