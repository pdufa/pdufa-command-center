"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_,key)=>key==="__esModule"?false:String(key)});};
const Component=require("../app/Phase3ReadoutSheets.tsx").default;
const publicRoot=path.resolve(__dirname,"../public");
const census=fs.readFileSync(path.join(publicRoot,"phase3-census-2026-10-26.csv"),"utf8");
const manifest=JSON.parse(fs.readFileSync(path.join(publicRoot,"phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
global.IS_REACT_ACT_ENVIRONMENT=true;
const textOf=node=>typeof node==="string"||typeof node==="number"?String(node):
 (node?.children||[]).map(textOf).join("");
const sheetSections=root=>root.findAllByType("section")
 .filter(s=>["Top pre-release spreadsheet","Bottom post-release spreadsheet"].includes(s.props["aria-label"]));
const press=(sheet,partial)=>sheet.findAllByType("button").find(b=>textOf(b).includes(partial));
test("TOP and BOTTOM sorting and trial rows are collapsed by default and expand independently",async()=>{
 const oldFetch=global.fetch;
 global.fetch=async url=>({
  ok:true,text:async()=>census,json:async()=>manifest
 });
 let view;
 try{
  await act(async()=>{view=create(React.createElement(Component));});
  let [top,bottom]=sheetSections(view.root);
  assert.ok(top&&bottom,"Both spreadsheets should exist");
  for(const sheet of [top,bottom]){
    assert.equal(sheet.findAllByType("table").length,0,"Trial rows should start collapsed");
    assert.equal(sheet.findAllByType("select").length,0,"Sort controls should start collapsed");
    assert.equal(press(sheet,"Sorting controls").props["aria-expanded"],false);
    assert.equal(press(sheet,"Trial rows").props["aria-expanded"],false);
  }
  await act(async()=>{press(top,"Trial rows").props.onClick();});
  [top,bottom]=sheetSections(view.root);
  assert.equal(top.findAllByType("table").length,1);
  assert.equal(bottom.findAllByType("table").length,0);
  assert.equal(top.findAllByType("select").length,0);
  await act(async()=>{press(bottom,"Sorting controls").props.onClick();});
  [top,bottom]=sheetSections(view.root);
  assert.equal(bottom.findAllByType("select").length,1);
  assert.equal(bottom.findAllByType("table").length,0);
  assert.equal(top.findAllByType("select").length,0);
  await act(async()=>{press(top,"Expand all segments").props.onClick();});
  [top,bottom]=sheetSections(view.root);
  assert.equal(top.findAllByType("select").length,1);
  assert.equal(top.findAllByType("table").length,1);
  assert.equal(bottom.findAllByType("table").length,0);
  await act(async()=>{press(top,"Collapse all segments").props.onClick();});
  [top,bottom]=sheetSections(view.root);
  assert.equal(top.findAllByType("table").length,0);
  assert.equal(top.findAllByType("select").length,0);
  assert.equal(bottom.findAllByType("select").length,1,"Other spreadsheet must be unchanged");
  assert.ok(press(bottom,"Reset Sorting"),"Reset sorting must remain available when sorting is expanded");
 }finally{
  if(view)await act(async()=>view.unmount());
  global.fetch=oldFetch;
 }
});

test("every TOOLS page top section and Phase 3 upper control group is closed individually by default",()=>{
 const page=fs.readFileSync(path.resolve(__dirname,"../app/tools/page.tsx"),"utf8");
 const sheets=fs.readFileSync(path.resolve(__dirname,"../app/Phase3ReadoutSheets.tsx"),"utf8");
 const styles=fs.readFileSync(path.resolve(__dirname,"../app/Phase3ReadoutSheets.module.css"),"utf8");
 assert.match(page,/<details data-tools-segment="pool"/);
 assert.match(page,/<details data-tools-segment="phase3"/);
 assert.equal((page.match(/<details/g)||[]).length,3);
 assert.doesNotMatch(page,/<details[^>]*\sopen(?:\s|=|>)/);
 for(const segment of ["overview","search","survey-ratings","survey-synthesis"])
   assert.ok(sheets.includes('data-segment="phase3-'+segment+'"'),"Missing "+segment+" accordion");
 assert.equal((sheets.match(/className=\{css\.topSegment\}/g)||[]).length,4);
 assert.match(sheets,/return <section className=\{css\.sheet\}[^\n]*\n\s*<details className=\{css\.sheetAccordion\}>/);
 assert.doesNotMatch(sheets,/<details[^>]*\sopen(?:\s|=|>)/);
 assert.match(styles,/\.topSegmentSummary\{/);
 assert.match(styles,/\.sheetAccordion\[open\]/);
});
test("each spreadsheet retains two independent default-closed inner segments",async()=>{
 const oldFetch=global.fetch;
 global.fetch=async()=>({ok:true,text:async()=>census,json:async()=>manifest});
 let view;
 try{
  await act(async()=>{view=create(React.createElement(Component));});
  const [top,bottom]=sheetSections(view.root);
  for(const sheet of [top,bottom]){
   const cards=sheet.findAllByType("details");
   assert.equal(cards.length,1);
   assert.equal(cards[0].props.open,undefined);
   assert.equal(cards[0].findAllByType("summary").length,1);
   assert.equal(press(sheet,"Sorting controls").props["aria-expanded"],false);
   assert.equal(press(sheet,"Trial rows").props["aria-expanded"],false);
  }
 }finally{
  if(view)await act(async()=>view.unmount());
  global.fetch=oldFetch;
 }
});
