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
const Phase3=require("../app/Phase3RegistryPostingSheets.tsx").default;
const snapshot=require("../public/phase3-registry-postings-current.json");
const {postingRatingAudit}=require("../lib/phase3-posting-rating-audit.ts");
const {TOOLS_RATING_GROUPS}=require("../lib/tools-rating-groups.ts");
global.IS_REACT_ACT_ENVIRONMENT=true;
const keys=["M","A","B","C","D","E"];
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):
 node?.children?.map(textOf).join("")||"";
const sections=r=>r.root.findAllByType("section").filter(s=>/registry results trial spreadsheet/.test(s.props["aria-label"]||""));
const headers=s=>s.findAllByType("thead")[0].findAllByType("tr")[0].findAllByType("th");
const cells=s=>s.findAllByType("tbody")[0].findAllByType("tr")[0].findAllByType("td");
const groups=s=>headers(s).filter(x=>x.props["data-rating-group"]);
const ingredients=s=>headers(s).filter(x=>x.props["data-rating-ingredient"]);
const button=(s,key)=>groups(s).find(x=>x.props["data-rating-group"]===key).findByType("button");
test("M–E taxonomy is identical to the main TOOLS final trials grid",()=>{
 assert.deepEqual(TOOLS_RATING_GROUPS.map(g=>g.key),keys);
 assert.equal(TOOLS_RATING_GROUPS.flatMap(g=>g.ingredients).length,20);
 const source=fs.readFileSync(require("path").join(__dirname,"../app/ToolsOpeningTrialGrid.tsx"),"utf8");
 assert.match(source,/const RATING_GROUPS=TOOLS_RATING_GROUPS/);
});
test("registry posting alone cannot create medical, commercial or stock ratings",()=>{
 const before=snapshot.records.find(r=>r.resultsCount===0);
 const after=snapshot.records.find(r=>r.resultsCount>0);
 const auditBefore=postingRatingAudit({...before,sourceUrl:"https://clinicaltrials.gov/study/"+before.nctId});
 const auditAfter=postingRatingAudit({...after,sourceUrl:"https://clinicaltrials.gov/study/"+after.nctId});
 for(const key of ["B","C","D","E"]){
  assert.match(auditBefore.group[key].label,/Not rated|Not assessed/);
  assert.match(auditAfter.group[key].label,/Not rated|Not assessed/);
 }
 assert.equal(auditBefore.group.A.label,"Not posted");
 assert.equal(auditAfter.group.A.label,"Results posted");
 assert.equal(auditAfter.ingredient.MISS.label,"38 to review");
 assert.equal(auditAfter.ingredient.GRADE.label,"Not assessed");
 assert.ok(!Object.values(auditAfter.group).some(x=>/% upside|approved|pass grade/i.test(x.label)));
});
test("both registry tables show M–E and independently expand ingredients horizontally",async()=>{
 const previous=global.fetch;
 global.fetch=async()=>({ok:true,json:async()=>snapshot});
 let r;
 try{
  await act(async()=>{r=create(React.createElement(Phase3));});
  const [top,bottom]=sections(r);
  assert.ok(top&&bottom);
  for(const section of [top,bottom]){
   assert.deepEqual(groups(section).map(x=>x.props["data-rating-group"]),keys);
   assert.deepEqual(ingredients(section),[]);
   assert.equal(headers(section).length,15);
   assert.equal(cells(section).length,15);
   assert.ok(groups(section).every(x=>x.findByType("button").props["aria-expanded"]===false));
  }
  await act(async()=>button(top,"B").props.onClick());
  assert.deepEqual(ingredients(top).map(x=>x.props["data-rating-ingredient"]),["CL","SAF","COMP"]);
  assert.deepEqual(ingredients(bottom),[],"second sheet must remain collapsed");
  assert.equal(headers(top).length,18);
  assert.equal(cells(top).length,headers(top).length);
  assert.match(groups(top).find(x=>x.props["data-rating-group"]==="B").props.className,/ratingOpen/);
  assert.match(ingredients(top).at(-1).props.className,/ratingEnd/);
  await act(async()=>button(bottom,"M").props.onClick());
  assert.deepEqual(ingredients(bottom).map(x=>x.props["data-rating-ingredient"]),["VER","MOD","MISS","CRIT"]);
  assert.equal(cells(bottom).length,headers(bottom).length);
  await act(async()=>top.findAllByType("button").find(x=>textOf(x)==="Expand all ratings").props.onClick());
  assert.equal(ingredients(top).length,20);
  assert.equal(headers(top).length,35);
  assert.equal(cells(top).length,35);
  assert.equal(headers(bottom).length,19);
  assert.ok(textOf(top).includes("Not assessed"));
  await act(async()=>top.findAllByType("button").find(x=>textOf(x)==="Collapse all ratings").props.onClick());
  assert.equal(headers(top).length,15);
  assert.equal(cells(top).length,15);
 }finally{
  if(r)await act(async()=>r.unmount());
  global.fetch=previous;
 }
});
test("rating column filters are independent and do not lose original registry totals",async()=>{
 const previous=global.fetch;
 global.fetch=async()=>({ok:true,json:async()=>snapshot});
 let r;
 try{
  await act(async()=>{r=create(React.createElement(Phase3));});
  const [top,bottom]=sections(r);
  const totalTop=top.findAllByType("strong").map(textOf).join(" ");
  const totalBottom=bottom.findAllByType("strong").map(textOf).join(" ");
  assert.match(totalTop,new RegExp(snapshot.noResultsPosted+" total"));
  assert.match(totalBottom,new RegExp(snapshot.resultsPosted+" total"));
  const f=top.findAllByType("input").find(x=>x.props["aria-label"]==="Before filter A rating");
  await act(async()=>f.props.onChange({target:{value:"Results posted"}}));
  assert.equal(top.findAllByType("tbody")[0].findAllByType("tr")[0].findAllByType("td").length,15);
  assert.match(textOf(top),/0 matching/);
  assert.ok(!textOf(bottom).includes("0 matching"));
  await act(async()=>top.findAllByType("button").find(x=>textOf(x)==="Clear column filters").props.onClick());
  assert.equal(top.findAllByType("tbody")[0].findAllByType("tr").length,50);
  assert.equal(bottom.findAllByType("tbody")[0].findAllByType("tr").length,50);
 }finally{
  if(r)await act(async()=>r.unmount());
  global.fetch=previous;
 }
});
