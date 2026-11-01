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
const Component=require("../app/ToolsRankingChecklists.tsx").default;
const {BENEFIT_GROUPS}=require("../lib/benefit-assessments.ts");
global.IS_REACT_ACT_ENVIRONMENT=true;
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):
 node&&typeof node==="object"&&Array.isArray(node.children)?node.children.map(textOf).join(""):"";
const button=(tree,id)=>tree.root.findAllByType("button").find(el=>el.props["aria-controls"]===id);
const panel=(tree,index)=>tree.root.findAllByType("div").filter(el=>el.props.className==="panel")[index];
const label=(container,value)=>container.findAllByType("label").find(el=>textOf(el).includes(value));
async function click(tree,id){
 const b=button(tree,id);assert.ok(b,"missing toggle "+id);
 await act(async()=>b.props.onClick());
}
async function check(el,checked){assert.ok(el,"missing checkbox");await act(async()=>el.findByType("input").props.onChange({target:{checked}}));}

test("phone cascade responds to real event handlers, and summary follows either or both lists",async()=>{
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Component));});
  for(const id of ["tools-rank-trials-body","tools-rank-priorities-body","tools-selected-ranking-body"]){
   assert.equal(button(root,id).props["aria-expanded"],false);
  }
  assert.equal(root.root.findAllByType("input").length,0,"both lists must start collapsed");
  await click(root,"tools-rank-trials-body");
  assert.equal(button(root,"tools-rank-trials-body").props["aria-expanded"],true);
  const left=()=>panel(root,0),right=()=>panel(root,1);
  assert.equal(left().findAllByType("input").length,6);
  await check(label(left(),"Patient Health & Clinical Benefit"),true);
  assert.ok(label(left(),"#3"));
  await check(label(left(),"#3"),true);
  const firstField=BENEFIT_GROUPS[2].fields[0].label;
  await check(label(left(),firstField),true);
  await click(root,"tools-selected-ranking-body");
  const summary=()=>root.root.findAllByType("div").find(el=>el.props.id==="tools-selected-ranking-body");
  assert.match(textOf(summary()),/Group #1/);
  assert.match(textOf(summary()),/Assessment #3/);
  assert.ok(textOf(summary()).includes(firstField));
  await click(root,"tools-rank-priorities-body");
  await check(label(right(),"#6"),true);
  await check(label(right(),"#3"),true);
  assert.equal(right().findAllByType("select").length,2);
  const select=right().findAllByType("select").find(el=>el.props["aria-label"]==="Priority of original assessment #3");
  await act(async()=>select.props.onChange({target:{value:"1"}}));
  assert.match(textOf(summary()),/Priority #1:\s*Original #3/);
  assert.match(textOf(summary()),/Priority #2:\s*Original #6/);
  await check(label(left(),"Patient Health & Clinical Benefit"),false);
  assert.doesNotMatch(textOf(summary()),/Group #1/);
  assert.match(textOf(summary()),/Priority #1:\s*Original #3/);
  const details=right().findAllByType("details").find(el=>textOf(el).includes("Choose research fields")&&
   textOf(el).includes(BENEFIT_GROUPS[2].fields[0].label));
  assert.ok(details);
  await check(label(details,firstField),true);
  assert.ok(textOf(summary()).includes(firstField));
  await click(root,"tools-rank-trials-body");
  await click(root,"tools-rank-priorities-body");
  await click(root,"tools-selected-ranking-body");
  assert.equal(button(root,"tools-rank-trials-body").props["aria-expanded"],false);
  assert.equal(button(root,"tools-rank-priorities-body").props["aria-expanded"],false);
  assert.equal(button(root,"tools-selected-ranking-body").props["aria-expanded"],false);
 }finally{if(root)await act(async()=>root.unmount());}
});
