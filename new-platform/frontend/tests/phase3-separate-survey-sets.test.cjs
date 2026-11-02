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
const {visiblePostingRatingGroups,visiblePostingTestCount}=require("../lib/phase3-survey-visibility.ts");
const Phase3=require("../app/Phase3RegistryPostingSheets.tsx").default;
const snapshot=require("../public/phase3-registry-postings-current.json");
global.IS_REACT_ACT_ENVIRONMENT=true;
const labelGroups=(kind,all=false)=>visiblePostingRatingGroups(kind,all).map(g=>g.key);
const fields=kind=>visiblePostingRatingGroups(kind).flatMap(g=>g.ingredients.map(v=>v.key));
const sections=r=>r.root.findAllByType("section").filter(s=>/registry results trial spreadsheet/.test(s.props["aria-label"]||""));
const headings=s=>s.findAllByType("thead")[0].findAllByType("tr")[0].findAllByType("th");
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):node?.children?.map(textOf).join("")||"";
const buttons=(s,text)=>s.findAllByType("button").find(v=>textOf(v)===text);
test("the upper and lower posting tables have intentionally distinct, fixed survey profiles",()=>{
 assert.deepEqual(labelGroups("before"),["M","A","C","D"]);
 assert.deepEqual(labelGroups("after"),["M","A","B","C","D","E"]);
 assert.deepEqual(fields("before"),["VER","MOD","MISS","CRIT","ER","FDA","POP","ACCESS","CASH","MOM","CAT"]);
 assert.deepEqual(fields("after"),["VER","MOD","MISS","CRIT","ER","FDA","CL","SAF","COMP","POP","REV","VAL","CASH","MOM","CAT","APP","READY","GRADE"]);
 assert.equal(visiblePostingTestCount("before"),11);
 assert.equal(visiblePostingTestCount("after"),18);
 assert.equal(visiblePostingTestCount("before",true),20);
 assert.equal(visiblePostingTestCount("after",true),20);
});
test("profiles remove irrelevant default columns independently, preserving full review on demand",async()=>{
 const oldFetch=global.fetch;
 global.fetch=async url=>({ok:true,json:async()=>String(url).includes("benefit-assessments")?{schemaVersion:1,sourceAsOf:null,records:[]}:snapshot});
 let r;
 try{
  await act(async()=>{r=create(React.createElement(Phase3));});
  const [top,bottom]=sections(r);
  const g=section=>headings(section).filter(x=>x.props["data-rating-group"]).map(x=>x.props["data-rating-group"]);
  assert.deepEqual(g(top),["M","A","C","D"]);
  assert.deepEqual(g(bottom),["M","A","B","C","D","E"]);
  assert.equal(headings(top).length,13);
  assert.equal(headings(bottom).length,15);
  assert.match(textOf(top),/11 relevant survey tests/);
  assert.match(textOf(bottom),/18 relevant survey tests/);
  await act(async()=>buttons(top,"Show additional surveys").props.onClick());
  assert.deepEqual(g(top),["M","A","B","C","D","E"]);
  assert.deepEqual(g(bottom),["M","A","B","C","D","E"]);
  assert.match(textOf(top),/20 relevant survey tests/);
  assert.match(textOf(bottom),/18 relevant survey tests/);
  await act(async()=>buttons(top,"Expand all ratings").props.onClick());
  assert.equal(headings(top).length,35);
  assert.equal(headings(bottom).length,15);
  assert.equal(top.findAllByType("tbody")[0].findAllByType("tr")[0].findAllByType("td").length,35);
  await act(async()=>buttons(top,"Use relevant surveys only").props.onClick());
  assert.equal(headings(top).length,13);
  assert.deepEqual(g(bottom),["M","A","B","C","D","E"]);
  await act(async()=>buttons(bottom,"Show additional surveys").props.onClick());
  await act(async()=>buttons(bottom,"Expand all ratings").props.onClick());
  assert.equal(headings(bottom).length,35);
  assert.equal(headings(top).length,13);
 }finally{
  if(r)await act(async()=>r.unmount());
  global.fetch=oldFetch;
 }
});
