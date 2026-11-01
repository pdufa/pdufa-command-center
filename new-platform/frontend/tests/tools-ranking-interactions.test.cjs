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
const body=(tree,id)=>tree.root.findAllByType("div").find(el=>el.props.id===id);
const label=(container,value)=>container.findAllByType("label").find(el=>textOf(el).includes(value));
async function click(tree,id){
 const b=button(tree,id);assert.ok(b,"missing toggle "+id);
 await act(async()=>b.props.onClick());
}
async function check(el,checked){
 assert.ok(el,"missing checkbox");
 await act(async()=>el.findByType("input").props.onChange({target:{checked}}));
}
test("numbered left cascade opens child assessment and research fields only after each selection",async()=>{
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Component));});
  const leftId="tools-rank-trials-body",rightId="tools-rank-priorities-body",summaryId="tools-selected-ranking-body";
  for(const id of [leftId,rightId,summaryId])assert.equal(button(root,id).props["aria-expanded"],false);
  assert.equal(root.root.findAllByType("input").length,0,"all lists start collapsed");
  await click(root,leftId);
  const left=()=>body(root,leftId);
  assert.ok(left());
  assert.equal(left().findAllByType("input").length,6);
  assert.match(textOf(left()),/1a\/6/);
  assert.match(textOf(left()),/1f\/6/);
  assert.equal(left().findAllByProps({"data-cascade-for":"group-1"}).length,0);
  await check(label(left(),"Patient Health & Clinical Benefit"),true);
  assert.ok(left().findAllByProps({"data-cascade-for":"group-1"}).length===1);
  assert.match(textOf(left()),/2a\/5/);
  assert.equal(left().findAllByProps({"data-cascade-for":"assessment-3"}).length,0);
  await check(label(left(),"#3 — Clinical Benefit"),true);
  const criterion=()=>left().findAllByProps({"data-cascade-for":"assessment-3"})[0];
  assert.ok(criterion());
  assert.match(textOf(criterion()),/3a\/6/);
  const firstField=BENEFIT_GROUPS[2].fields[0].label;
  await check(label(criterion(),firstField),true);
  await click(root,summaryId);
  const summary=()=>body(root,summaryId);
  assert.match(textOf(summary()),/Group #1/);
  assert.match(textOf(summary()),/Assessment #3/);
  assert.ok(textOf(summary()).includes(firstField));
  await check(label(left(),"Patient Health & Clinical Benefit"),false);
  assert.equal(left().findAllByProps({"data-cascade-for":"group-1"}).length,0);
  assert.doesNotMatch(textOf(summary()),/Group #1/);
  await click(root,leftId);
  assert.equal(button(root,leftId).props["aria-expanded"],false);
 }finally{if(root)await act(async()=>root.unmount());}
});

test("right cascade opens two numbered choices and fields immediately, without extra caret",async()=>{
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Component));});
  const leftId="tools-rank-trials-body",rightId="tools-rank-priorities-body",summaryId="tools-selected-ranking-body";
  await click(root,leftId);
  await click(root,rightId);
  assert.equal(button(root,leftId).props["aria-expanded"],false,"other checklist closes to reduce clutter");
  assert.equal(button(root,rightId).props["aria-expanded"],true);
  const right=()=>body(root,rightId);
  assert.equal(right().findAllByType("input").length,20);
  assert.match(textOf(right()),/1a\/20/);
  assert.match(textOf(right()),/1t\/20/);
  assert.equal(right().findAllByProps({"data-cascade-for":"priority-6"}).length,0);
  await check(label(right(),"Original #6 — Competitive Advantage"),true);
  let sub=right().findAllByProps({"data-cascade-for":"priority-6"})[0];
  assert.ok(sub,"checking #6 instantly reveals nested choices");
  assert.match(textOf(sub),/2a\/2/);
  assert.match(textOf(sub),/2b\/2/);
  assert.ok(sub.findAllByType("input").length>0,"research fields are visible without a second click");
  await check(label(right(),"Original #3 — Clinical Benefit"),true);
  assert.match(textOf(label(right(),"Original #6 — Competitive Advantage")),/1f\/20/);
  assert.match(textOf(label(right(),"Original #3 — Clinical Benefit")),/1c\/20/);
  const select=right().findAllByType("select").find(el=>el.props["aria-label"]==="Priority of original assessment #3");
  await act(async()=>select.props.onChange({target:{value:"1"}}));
  assert.match(textOf(label(right(),"Original #6 — Competitive Advantage")),/1f\/20/,
    "option letter for original #6 must not change after priority reordering");
  assert.match(textOf(label(right(),"Original #3 — Clinical Benefit")),/1c\/20/,
    "option letter for original #3 must not change after priority reordering");
  await click(root,summaryId);
  const summary=()=>body(root,summaryId);
  assert.match(textOf(summary()),/Priority #1:\s*Original #3/);
  assert.match(textOf(summary()),/Priority #2:\s*Original #6/);
  const field=BENEFIT_GROUPS[2].fields[0].label;
  await check(label(right().findAllByProps({"data-cascade-for":"priority-3"})[0],field),true);
  assert.ok(textOf(summary()).includes(field));
  await check(label(right(),"Original #6 — Competitive Advantage"),false);
  assert.equal(right().findAllByProps({"data-cascade-for":"priority-6"}).length,0);
  assert.match(textOf(summary()),/Priority #1:\s*Original #3/);
  await click(root,rightId);
  await click(root,summaryId);
  assert.equal(button(root,rightId).props["aria-expanded"],false);
  assert.equal(button(root,summaryId).props["aria-expanded"],false);
 }finally{if(root)await act(async()=>root.unmount());}
});

test("switching left to right preserves both independent checklists and selected summary",async()=>{
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Component));});
  const leftId="tools-rank-trials-body",rightId="tools-rank-priorities-body",summaryId="tools-selected-ranking-body";
  await click(root,leftId);
  await check(label(body(root,leftId),"Patient Health & Clinical Benefit"),true);
  await click(root,rightId);
  assert.equal(body(root,leftId),undefined);
  await check(label(body(root,rightId),"Original #3 — Clinical Benefit"),true);
  await click(root,summaryId);
  assert.match(textOf(body(root,summaryId)),/Group #1/);
  assert.match(textOf(body(root,summaryId)),/Priority #1:\s*Original #3/);
  await click(root,leftId);
  assert.equal(button(root,rightId).props["aria-expanded"],false);
  assert.ok(body(root,leftId).findAllByProps({"data-cascade-for":"group-1"}).length===1);
 }finally{if(root)await act(async()=>root.unmount());}
});


test("Clear This Section preserves the other ranking list, while TOOLS global reset clears both",async()=>{
 const oldWindow=global.window;
 const fakeWindow=new EventTarget();
 const values=new Map();
 fakeWindow.localStorage={
  getItem:key=>values.get(key)||null,
  setItem:(key,value)=>values.set(key,value),
  removeItem:key=>values.delete(key)
 };
 global.window=fakeWindow;
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Component));});
  await click(root,"tools-rank-trials-body");
  await check(label(body(root,"tools-rank-trials-body"),"Patient Health & Clinical Benefit"),true);
  await click(root,"tools-rank-priorities-body");
  await check(label(body(root,"tools-rank-priorities-body"),"Original #3 — Clinical Benefit"),true);
  await click(root,"tools-rank-trials-body");
  const left=body(root,"tools-rank-trials-body");
  const clearLeft=left.findAllByType("button").find(el=>textOf(el)==="Clear This Section");
  assert.ok(clearLeft);
  await act(async()=>clearLeft.props.onClick());
  await click(root,"tools-selected-ranking-body");
  assert.doesNotMatch(textOf(body(root,"tools-selected-ranking-body")),/Group #1/);
  assert.match(textOf(body(root,"tools-selected-ranking-body")),/Priority #1:\s*Original #3/,
    "Scoped clearing must not erase the right ranking");
  await act(async()=>fakeWindow.dispatchEvent(new Event("pdufa-tools-clear-all-selections")));
  assert.match(textOf(body(root,"tools-selected-ranking-body")||""),/^$/,
    "Global clearing should collapse the ranking summary");
  await click(root,"tools-selected-ranking-body");
  assert.match(textOf(body(root,"tools-selected-ranking-body")),/No ranking criteria selected/);
  const stored=JSON.parse(values.get("pdufa-tools-ranking-checklists-v1"));
  assert.deepEqual(stored.groupIds,[]);
  assert.deepEqual(stored.priorities,[]);
 }finally{
  if(root)await act(async()=>root.unmount());
  global.window=oldWindow;
 }
});
