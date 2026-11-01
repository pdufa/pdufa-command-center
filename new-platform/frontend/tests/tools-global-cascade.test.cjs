"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const Module=require("node:module");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
   module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_,k)=>k==="__esModule"?false:String(k)});};
const {toolsOptionCode}=require("../lib/tools-option-code.ts");
const {SPECIAL_DESIGNATION_CATEGORIES}=require("../lib/trial-designations.ts");
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):
 node&&typeof node==="object"&&Array.isArray(node.children)?node.children.map(textOf).join(""):"";
function loadWithMocks(filename,mocks){
 const original=Module._load;
 Module._load=function(request,parent,isMain){
  if(parent?.filename.endsWith(filename)&&Object.hasOwn(mocks,request))return mocks[request];
  return original.apply(this,arguments);
 };
 try{return require("../app/"+filename).default;}finally{Module._load=original;}
}
const Stub=()=>null;
const PoolStageExplorer=loadWithMocks("PoolStageExplorer.tsx",{
 "./PoolDesignationSelector":{default:Stub},
 "./ToolsResultsSpreadsheet":{default:Stub},
 "./ToolsFunnel":{default:Stub}
});
const sampleIndex={
 availableKeys:{fast_track:true,orphan_drug:true},
 trialEvents:{"NCT00000001":["ABC|ONE"]},
 programs:{"ABC|ONE":{eventKey:"ABC|ONE",ticker:"ABC",drug:"Drug",indication:"Disease",
  designations:{fast_track:{status:"GRANTED",verification:"FDA_VERIFIED",source:"https://www.fda.gov/example"}}}},
 linkageCoverage:{verifiedNctCount:1}
};
const PoolDesignationSelector=loadWithMocks("PoolDesignationSelector.tsx",{
 "./TrialDesignations":{useTrialDesignations:()=>({index:sampleIndex,loading:false,error:"",retry:()=>{}})}
});

test("stable circle codes cover every option, reject nonexistent indexes",()=>{
 assert.equal(toolsOptionCode(1,0,2),"1a/2");
 assert.equal(toolsOptionCode(1,1,2),"1b/2");
 assert.equal(toolsOptionCode(2,0,4),"2a/4");
 assert.equal(toolsOptionCode(2,12,13),"2m/13");
 assert.equal(toolsOptionCode(3,4,5),"3e/5");
 assert.equal(toolsOptionCode(1,19,20),"1t/20");
 assert.throws(()=>toolsOptionCode(2,20,13),/TOOLS_OPTION_INDEX_INVALID/);
 assert.equal(SPECIAL_DESIGNATION_CATEGORIES.length,13);
});
test("stage category click reveals choices, checkbox still sets exact API stage filter",async()=>{
 let root;
 const oldFetch=global.fetch;
 const queried=[];
 global.fetch=async url=>{
  queried.push(String(url));
  return {ok:true,json:async()=>({
   view:"pool",total:0,rows:[],spreadsheetRows:[],nextOffset:null,selectionSummary:{},
   stageStats:{trials:100,standaloneResults:0,regulatoryEvents:0,stages:{
    "Phase 2":{trials:12,standaloneResults:0,regulatoryEvents:0,total:12}}}
  })};
 };
 try{
  await act(async()=>{root=create(React.createElement(PoolStageExplorer));});
  const button=()=>root.root.findAllByType("button")
   .find(x=>x.props["aria-controls"]==="tools-stage-group-0");
  assert.ok(button());
  assert.equal(button().props["aria-expanded"],false);
  assert.equal(root.root.findAllByProps({id:"tools-stage-group-0"}).length,0);
  await act(async()=>button().props.onClick());
  assert.equal(button().props["aria-expanded"],true);
  const children=root.root.findAllByProps({id:"tools-stage-group-0"})[0];
  const phase=children.findAllByType("label").find(x=>textOf(x).includes("Phase 2")&&!textOf(x).includes("Phase 2/3"));
  assert.ok(phase);
  assert.ok(textOf(children).includes("3a/5"));
  assert.ok(textOf(children).includes("3e/5"));
  await act(async()=>phase.findByType("input").props.onChange());
  assert.ok(queried.some(x=>x.includes("stages=Phase+2")),"stage selection must still update exact existing API query");
  assert.equal(button().props["aria-expanded"],true);
  await act(async()=>button().props.onClick());
  assert.equal(root.root.findAllByProps({id:"tools-stage-group-0"}).length,0);
 }finally{
  if(root)await act(async()=>root.unmount());
  global.fetch=oldFetch;
 }
});
test("checking FDA category reveals program and linked-trial counts without changing their meanings",async()=>{
 let root;
 function Wrapper(){
  const [selected,setSelected]=React.useState([]);
  return React.createElement(PoolDesignationSelector,{selected,onChange:setSelected,poolTrialCount:100});
 }
 try{
  await act(async()=>{root=create(React.createElement(Wrapper));});
  const first=root.root.findAllByType("label").find(x=>textOf(x).includes("Fast Track Designation"));
  assert.ok(first);
  assert.match(textOf(first),/2a\/13/);
  assert.ok(!root.root.findAllByProps({className:"toolsCascadeFdaEvidence"}).length);
  await act(async()=>first.findByType("input").props.onChange());
  const evidence=root.root.findAllByProps({className:"toolsCascadeFdaEvidence"});
  assert.equal(evidence.length,1);
  assert.match(textOf(evidence[0]),/1 source programs/);
  assert.match(textOf(evidence[0]),/1 linked NCTs/);
  await act(async()=>first.findByType("input").props.onChange());
  assert.equal(root.root.findAllByProps({className:"toolsCascadeFdaEvidence"}).length,0);
  const last=root.root.findAllByType("label").find(x=>textOf(x).includes("Animal Rule"));
  assert.match(textOf(last),/2m\/13/);
  assert.equal(last.findByType("input").props.disabled,true);
 }finally{if(root)await act(async()=>root.unmount());}
});
test("20-assessment selector stays sequential and evidence UI follows active assessment",()=>{
 const matrix=fs.readFileSync(require.resolve("../app/ToolsBenefitMatrix.tsx"),"utf8");
 assert.match(matrix,/toolsOptionCode\(1,g.number-1,BENEFIT_GROUPS.length\)/);
 assert.match(matrix,/<ToolsOptionNumber level=\{1\} index=\{active-1\} total=\{BENEFIT_GROUPS.length\}/);
 const ranking=fs.readFileSync(require.resolve("../app/ToolsRankingChecklists.tsx"),"utf8");
 assert.match(ranking,/data-cascade-for=\{"assessment-"\+id\}/);
 const explorer=fs.readFileSync(require.resolve("../app/PoolStageExplorer.tsx"),"utf8");
 assert.match(explorer,/styles.toolsCascadeChildren/);
 const designation=fs.readFileSync(require.resolve("../app/PoolDesignationSelector.tsx"),"utf8");
 assert.match(designation,/checked&&index&&<div className=\{styles.toolsCascadeFdaEvidence\}/);
});
