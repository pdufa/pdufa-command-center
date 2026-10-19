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
const {Drilldown}=require("../app/Workspace.tsx");
global.IS_REACT_ACT_ENVIRONMENT=true;
const rows=Array.from({length:12000},(_,i)=>({id:"TRIAL|"+i,programId:"PDUFA-"+(100000+i),
 ticker:"ABC",drug:"Drug "+i,nctId:"NCT"+String(10000000+i)}));
function toggle(node,open){const target={open};node.props.onToggle({target,currentTarget:target});}

test("A 12,000-record evidence table mounts only the opened page and selected trial details",async()=>{
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Drilldown,{rows}));});
  assert.equal(root.root.findAllByProps({className:"drill-program"}).length,0);
  await act(async()=>toggle(root.root.findByProps({className:"nested-expander"}),true));
  const programs=root.root.findAllByProps({className:"drill-program"});
  assert.equal(programs.length,25);
  assert.equal(root.root.findAllByProps({className:"drill-evidence"}).length,0);
  await act(async()=>toggle(programs[0],true));
  assert.equal(root.root.findAllByProps({className:"drill-evidence"}).length,1);
  await act(async()=>toggle(programs[0],false));
  assert.equal(root.root.findAllByProps({className:"drill-evidence"}).length,0);
  await act(async()=>toggle(root.root.findByProps({className:"nested-expander"}),false));
  assert.equal(root.root.findAllByProps({className:"drill-program"}).length,0);
 }finally{if(root)await act(async()=>root.unmount());}
});

test("Evidence pagination reaches every exact program once without creating hidden full records",async()=>{
 const selected=rows.slice(0,61),seen=[];
 let root;
 try{
  await act(async()=>{root=create(React.createElement(Drilldown,{rows:selected}));});
  await act(async()=>toggle(root.root.findByProps({className:"nested-expander"}),true));
  for(;;){
   const programs=root.root.findAllByProps({className:"drill-program"});
   assert.ok(programs.length<=25);
   seen.push(...programs.map(node=>node.findByProps({className:"permanent-id"}).children.join("")));
   const next=root.root.findAllByType("button").find(node=>node.children.includes("NEXT TRIAL PAGE"));
   if(next.props.disabled)break;
   await act(async()=>next.props.onClick());
  }
  assert.deepEqual(seen,selected.map(row=>row.programId));
  assert.equal(new Set(seen).size,61);
  assert.equal(root.root.findAllByProps({className:"drill-evidence"}).length,0);
 }finally{if(root)await act(async()=>root.unmount());}
});
