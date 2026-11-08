"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_,key)=>key==="__esModule"?false:String(key)});};
const Component=require("../app/ToolsOpeningTrialGrid.tsx").default;
global.IS_REACT_ACT_ENVIRONMENT=true;
const row={id:"TRIAL|NCT12345678",nctId:"NCT12345678",ticker:"TEST",company:"Example",
 drug:"Example therapy",indication:"Example indication",stage:"Phase 3",selectedStage:"Phase 3",
 timeline:{phase3DataRelease:null,pdufaTarget:null},designationMatches:{},pdufaApplications:[]};
const props={rows:[row],total:1,offset:0,nextOffset:null,inventoryMode:false,
 loading:false,error:"",selectedStages:1,selectedDesignations:0,noVerifiedNctLinks:false,
 sourceDate:"2026-11-01",sourceState:"SAVED",regulatorySourcesAvailable:true,
 onPrevious:()=>{},onNext:()=>{}};
const heading=(r,id)=>r.root.findAllByType("th").find(x=>x.props["data-rating-group"]===id);
const ingredientHeaders=r=>r.root.findAllByType("th").filter(x=>!!x.props["data-rating-ingredient"]);
const groupButton=(r,id)=>heading(r,id).findByType("button");
const names=r=>r.root.findAllByType("th").map(x=>x.props["data-rating-group"]||x.props["data-rating-ingredient"]).filter(Boolean);
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):
 node?.children?.map(textOf).join("")||"";
test("M–E headings expand ingredients immediately to the right and keep one continuous group outline",async()=>{
 let r;
 try{
  await act(async()=>{r=create(React.createElement(Component,props));});
  assert.deepEqual(names(r),["M","A","B","C","D","E"]);
  for(const id of ["M","A","B","C","D","E"])assert.equal(groupButton(r,id).props["aria-expanded"],false);
  await act(async()=>groupButton(r,"B").props.onClick());
  assert.deepEqual(names(r),["M","A","B","CL","SAF","COMP","C","D","E"]);
  assert.equal(groupButton(r,"B").props["aria-expanded"],true);
  assert.match(heading(r,"B").props.className,/ratingOpen/);
  assert.match(heading(r,"B").props.className,/ratingStart/);
  const ingredientCells=ingredientHeaders(r);
  assert.equal(ingredientCells.length,3);
  assert.deepEqual(ingredientCells.map(x=>x.props["data-rating-ingredient"]),["CL","SAF","COMP"]);
  assert.ok(ingredientCells.every(x=>x.props.className.includes("ratingOpen")));
  assert.match(ingredientCells[2].props.className,/ratingEnd/);
  assert.equal(r.root.findAllByType("td").filter(x=>x.props.title?.includes("source-backed input coverage or explicit unscored status")).length,3);
  await act(async()=>groupButton(r,"A").props.onClick());
  assert.deepEqual(names(r),["M","A","ER","FDA","B","CL","SAF","COMP","C","D","E"]);
  assert.equal(groupButton(r,"B").props["aria-expanded"],true,"B remains open independently");
  const controls=r.root.findAllByType("button");
  await act(async()=>controls.find(x=>textOf(x).includes("Collapse all ratings")).props.onClick());
  assert.deepEqual(names(r),["M","A","B","C","D","E"]);
  await act(async()=>r.root.findAllByType("button").find(x=>textOf(x).includes("Expand all ratings")).props.onClick());
  assert.equal(ingredientHeaders(r).length,20);
  for(const id of ["M","A","B","C","D","E"])assert.equal(groupButton(r,id).props["aria-expanded"],true);
  assert.equal(r.root.findAllByType("td").filter(x=>x.props.title?.includes("source-backed input coverage or explicit unscored status")).length,20,
    "twenty component slots remain present and source-gated");
  assert.match(textOf(r.root.findAllByType("td").filter(x=>x.props.title?.includes("source-backed input coverage or explicit unscored status")).at(-1)),
    /N\/A/,"the unvalidated final opportunity grade must remain unscored");
 }finally{if(r)await act(async()=>r.unmount());}
});

test("Competitive Strategy is after S and D, expands six source-gated subtopics without misaligning trial cells",async()=>{
 let r;
 try{
  await act(async()=>{r=create(React.createElement(Component,props));});
  const headers=()=>r.root.findAllByType("th");
  const labels=()=>headers().map(h=>textOf(h));
  const main=headers().findIndex(h=>h.props["data-competition-group"]==="CS");
  assert.ok(main>0,"Competitive Strategy is a top-level spreadsheet column");
  assert.equal(labels()[main-1].startsWith("D"),true,"CS must follow D immediately");
  assert.match(labels()[main+1],/Drug \/ therapy/,"Drug and the other original columns follow CS");
  const cells=()=>r.root.findAllByType("tbody")[0].findAllByType("td");
  assert.equal(cells().length,headers().length,"One trial row must align with every header");
  const button=headers()[main].findByType("button");
  assert.equal(button.props["aria-expanded"],false);
  await act(async()=>button.props.onClick());
  assert.equal(headers().find(h=>h.props["data-competition-group"]==="CS").findByType("button").props["aria-expanded"],true);
  assert.deepEqual(headers().filter(h=>h.props["data-competition-topic"]).map(h=>h.props["data-competition-topic"]),
    ["SOC","MED","PIPE","COMM","MOAT","STOCK"]);
  assert.equal(cells().length,headers().length,"Expanded trial row stays aligned");
  assert.equal(cells().filter(td=>td.props["data-competition-value"]).length,6);
  assert.ok(cells().filter(td=>td.props["data-competition-value"]).every(td=>/Not assessed|Evidence unavailable/.test(textOf(td))),
    "Missing comparator evidence cannot be converted into unsupported rankings");
  const title=headers().find(h=>h.props["data-competition-topic"]==="MED").props.title;
  assert.match(title,/directly comparable benefit/i);
  await act(async()=>headers().find(h=>h.props["data-competition-group"]==="CS").findByType("button").props.onClick());
  assert.equal(headers().filter(h=>h.props["data-competition-topic"]).length,0);
  assert.equal(cells().length,headers().length);
 }finally{if(r)await act(async()=>r.unmount());}
});
