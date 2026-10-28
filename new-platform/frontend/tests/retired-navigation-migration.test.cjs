"use strict";
// Synthetic transport fixtures exercise the supported Next.js workspace. They do
// not certify scientific evidence, trigger scans, or place real/paper orders.
const {test}=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const ts=require("typescript"),React=require("react"),{create,act}=require("react-test-renderer");
require.extensions[".css"]=()=>{};
for(const ext of [".ts",".tsx"])require.extensions[ext]=(m,file)=>m._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
}).outputText,file);
const Workspace=require("../app/Workspace.tsx").default;
global.IS_REACT_ACT_ENVIRONMENT=true;
const flatten=node=>node==null?"":typeof node==="string"?node:Array.isArray(node)?node.map(flatten).join(""):flatten(node.children);

async function withWorkspace(section,check){
 const prior={fetch:global.fetch,window:global.window,localStorage:global.localStorage};
 const values=new Map([["old-streamlit-nav",JSON.stringify({nav:"11. PLAN",pdufa_subtab:"GEM JR + GEM"})]]);
 const storage={getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)};
 const requests=[];
 global.localStorage=storage;global.window={location:{search:section?"?section="+encodeURIComponent(section):""},localStorage:storage,scrollTo(){}};
 global.fetch=async(url,options={})=>{
  requests.push({url,method:options.method??"GET"});
  const pathname=new URL(url,"https://test.invalid").pathname;
  if(pathname==="/api/workspace")return new Promise(()=>{});
  if(pathname==="/api/workspace/page")return Response.json({version:"a".repeat(64),total:0,offset:0,limit:50,rows:[],nextOffset:null});
  if(pathname==="/api/workspace/summary")return Response.json({pipeline:0,gemJr:0,gem:0});
  if(pathname==="/api/program-watch-trade")return Response.json({watch:["PDUFA-000001"],trade:["PDUFA-000002"],version:1});
  return Response.json({error:"Synthetic source unavailable"},{status:503});
 };
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Workspace,{onInspect(){}}));await new Promise(resolve=>setImmediate(resolve));});
  await check(root,requests,values);
  assert.ok(requests.every(r=>r.method==="GET"),"navigation must not dispatch scans, writes or orders");
 }finally{if(root)await act(async()=>root.unmount());Object.assign(global,prior);}
}
const sectionNav=root=>root.root.findByProps({"aria-label":"PDUFA sections"});
const selectedSection=root=>sectionNav(root).findAllByType("button").filter(b=>b.props["aria-current"]==="page").map(b=>flatten(b.props.children));

test("retired Streamlit bookmarks fall back to supported Pipeline without restoring legacy state",async()=>{
 for(const section of ["9. PREDICTION ENGINE","10. MATCH OPTIMIZER","11. PLAN","PRE PHASE 3","PHASE 3 DAILY","GEM JR + GEM"]){
  await withWorkspace(section,async(root,_requests,values)=>{
   assert.deepEqual(selectedSection(root),["PIPELINE"]);
   const labels=root.root.findAllByType("button").map(b=>flatten(b.props.children));
   assert.ok(!labels.includes(section));
   assert.equal(values.get("old-streamlit-nav"),JSON.stringify({nav:"11. PLAN",pdufa_subtab:"GEM JR + GEM"}));
  });
 }
});

test("supported trial-sheet deep links reopen distinct GEM JR, GEM and WT sections",async()=>{
 for(const [section,label] of [["PIPELINE","PIPELINE"],["GEM_JR","GEM JR"],["GEM","GEM"],["WT","WT"]]){
  await withWorkspace(section,async root=>{
   assert.deepEqual(selectedSection(root),[label]);
   const labels=sectionNav(root).findAllByType("button").map(b=>flatten(b.props.children));
   for(const required of ["PIPELINE","GEM JR","GEM","WT","TRADING"])assert.ok(labels.includes(required));
   assert.ok(!labels.includes("GEM JR + GEM"));
  });
 }
});

test("SCANS deep link opens exactly one published report panel, separately from PDUFA",async()=>{
 await withWorkspace("SCANS",async(root,requests)=>{
  const scans=root.root.findAllByType("button").filter(b=>flatten(b.props.children)==="SCANS");
  assert.equal(scans.length,1);assert.equal(scans[0].props["aria-current"],"page");
  assert.equal(root.root.findAllByProps({"aria-label":"PDUFA sections"}).length,0);
  assert.ok(requests.some(r=>r.url.startsWith("/api/published-scans")));
 });
});

test("navigating separate GEM stages and WT preserves permanent program labels without promoting tickers",async()=>{
 await withWorkspace("GEM_JR",async(root,_requests,values)=>{
  const before=values.get("pdufa_new_program_watch_trade_v1");
  assert.deepEqual(JSON.parse(before),{watch:["PDUFA-000001"],trade:["PDUFA-000002"]});
  const buttons=()=>sectionNav(root).findAllByType("button");
  for(const label of ["GEM","WT","GEM JR"]){
   await act(async()=>buttons().find(b=>flatten(b.props.children)===label).props.onClick());
   assert.deepEqual(selectedSection(root),[label]);
  }
  assert.equal(values.get("pdufa_new_program_watch_trade_v1"),before);
  const combined=[...values.values()].join(" ");
  assert.match(combined,/PDUFA-000001/);assert.match(combined,/PDUFA-000002/);
 });
});

test("supported HOP navigation remains research-only and withholds absent approval estimates",async()=>{
 await withWorkspace("PIPELINE",async root=>{
  const prediction=root.root.findAllByType("button").find(b=>flatten(b.props.children)==="PREDICTION");
  await act(async()=>prediction.props.onClick());
  root.root.findByProps({"aria-label":"PREDICTION — HOP"});
  assert.match(JSON.stringify(root.toJSON()),/Research only/);
  assert.match(JSON.stringify(root.toJSON()),/validated approval probabilities are not available yet/);
  assert.match(JSON.stringify(root.toJSON()),/No estimates will be generated/);
 });
});
