const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");
require.extensions[".css"]=()=>{};
for(const ext of [".ts",".tsx"]){
 require.extensions[ext]=(module,filename)=>module._compile(ts.transpileModule(
  fs.readFileSync(filename,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,
   target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}
 ).outputText,filename);
}
const {validatePipelinePage}=require("../lib/workspace-pages.ts");
const version="a".repeat(64);
const all=Array.from({length:150},(_,i)=>({id:"TRIAL|"+i,ticker:"T"+i,drug:"Drug "+i}));
function page(rows,offset=0){
 return {version,total:rows.length,offset,limit:50,rows:rows.slice(offset,offset+50),
  nextOffset:offset+50<rows.length?offset+50:null};
}

test("Pipeline pages reject mixed versions, wrong offsets, duplicates and missing rows",()=>{
 assert.equal(validatePipelinePage(page(all),0,50).rows.length,50);
 assert.equal(validatePipelinePage(page([]),0,50).total,0);
 assert.throws(()=>validatePipelinePage(page(all),50,50));
 assert.throws(()=>validatePipelinePage(page(all),0,50,"b".repeat(64)));
 assert.throws(()=>validatePipelinePage({...page(all),rows:[all[0],all[0]]},0,50));
 assert.throws(()=>validatePipelinePage({...page(all),nextOffset:100},0,50));
 assert.throws(()=>validatePipelinePage({...page(all),total:-1},0,50));
});

test("Quick view shows the third page, stays bounded and searches records outside loaded pages",async()=>{
 global.IS_REACT_ACT_ENVIRONMENT=true;
 const Workspace=require("../app/Workspace.tsx").default;
 const prior={fetch:global.fetch,window:global.window,localStorage:global.localStorage};
 const storage={getItem:()=>null,setItem(){}};
 global.localStorage=storage;
 global.window={location:{search:""},localStorage:storage};
 const requests=[];
 global.fetch=async url=>{
  requests.push(url);
  const parsed=new URL(url,"https://example.test");
  if(parsed.pathname==="/api/workspace/page"){
   const query=parsed.searchParams.get("query");
   const rows=query?all.filter(row=>row.ticker===query):all;
   return Response.json(page(rows,Number(parsed.searchParams.get("offset"))));
  }
  if(parsed.pathname==="/api/workspace")return new Promise(()=>{});
  if(parsed.pathname==="/api/workspace/summary")return Response.json({pipeline:150,gemJr:11,gem:6});
  if(parsed.pathname==="/api/program-watch-trade")return Response.json({watch:[],trade:[],version:0});
  return Response.json({});
 };
 let root;
 const tick=()=>new Promise(resolve=>setImmediate(resolve));
 const quickViewCells=()=>root.root.findByProps({"aria-label":"Pipeline quick view"}).findAllByType("td");
 const cellText=()=>quickViewCells().map(cell=>cell.children.join(""));
 const button=text=>root.root.findAllByType("button").find(x=>x.children.join("")===text);
 try{
  await act(async()=>{root=create(React.createElement(Workspace,{onInspect(){}}));await tick();});
  assert.ok(cellText().includes("T0"));
  assert.equal(quickViewCells().length,100);
  assert.ok(requests.indexOf("/api/workspace")>requests.indexOf("/api/workspace/page?offset=0&limit=50"));
  await act(async()=>{button("NEXT 50 CANDIDATES").props.onClick();await tick();});
  assert.ok(cellText().includes("T50"));assert.ok(!cellText().includes("T0"));
  await act(async()=>{button("NEXT 50 CANDIDATES").props.onClick();await tick();});
  assert.ok(cellText().includes("T100"));assert.ok(cellText().includes("T149"));
  assert.equal(quickViewCells().length,100);
  assert.equal(button("NEXT 50 CANDIDATES").props.disabled,true);
  await act(async()=>{button("PREVIOUS 50").props.onClick();await tick();});
  assert.ok(cellText().includes("T50"));
  await act(async()=>root.root.findByProps({id:"early-pipeline-search"}).props.onChange({target:{value:"T149"}}));
  await act(async()=>{root.root.findByType("form").props.onSubmit({preventDefault(){}});await tick();});
  assert.deepEqual(cellText(),["T149","Drug 149"]);
 }finally{
  if(root)await act(async()=>root.unmount());
  Object.assign(global,prior);
 }
});

test("Standalone count cards use published memberships without a full candidate download",async()=>{
 global.IS_REACT_ACT_ENVIRONMENT=true;
 const Counts=require("../app/TrialWorkflowCounts.tsx").default;
 const prior={fetch:global.fetch,localStorage:global.localStorage,self:global.self};
 global.self=global;
 global.localStorage={getItem:()=>null};
 const requests=[];
 global.fetch=async url=>{
  requests.push(url);
  return Response.json(url==="/api/workspace/summary"
   ?{asOf:"2026-10-19",pipeline:11775,gemJr:11,gem:6}
   :{watch:["PDUFA-000001"],trade:["PDUFA-000002"]});
 };
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Counts));await new Promise(resolve=>setImmediate(resolve));});
  const numbers=root.root.findAllByProps({className:"workflow-count-number"}).map(x=>x.children.join(""));
  assert.deepEqual(numbers,["11,775","11","6","2"]);
  assert.deepEqual(requests,["/api/workspace/summary","/api/program-watch-trade"]);
 }finally{
  if(root)await act(async()=>root.unmount());
  Object.assign(global,prior);
 }
});
