"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const path=require("node:path");
const Module=require("node:module");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
);
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_,key)=>key==="__esModule"?false:String(key)});};
const {
  TOOLS_FILTERS_STORAGE_KEY,TOOLS_STEP4_STORAGE_KEY,TOOLS_RATINGS_STORAGE_KEY,
  TOOLS_RANKING_STORAGE_KEY,parseToolsFilterSelections,clearToolsPreferences
}=require("../lib/tools-selection-persistence.ts");
const stages=["Phase 2","Phase 3","Phase 3 Results"];
test("saved Phase and FDA selections restore with strict scope validation",()=>{
  assert.equal(parseToolsFilterSelections(null,stages),null);
  const restored=parseToolsFilterSelections({
    selectedStages:["Phase 3","bogus","Phase 3"],
    selectedDesignations:["orphan_drug","not_a_designation","orphan_drug"],
    activeFilter:"phase",query:"test",queryInput:"test",offset:50
  },stages);
  assert.deepEqual(restored.selectedStages,["Phase 3"]);
  assert.deepEqual(restored.selectedDesignations,["orphan_drug"]);
  assert.equal(restored.activeFilter,"phase");
  assert.equal(restored.offset,50);
  assert.equal(parseToolsFilterSelections({
    selectedStages:[],selectedDesignations:[],activeFilter:"invalid",offset:150
  },stages).offset,0);
});
function withBrowser(){
  const map=new Map();
  const handlers=new Map();
  const localStorage={
    getItem:key=>map.get(key)??null,
    setItem:(key,value)=>map.set(key,String(value)),
    removeItem:key=>map.delete(key)
  };
  global.window={localStorage,
    addEventListener:(event,fn)=>{const listeners=handlers.get(event)||new Set();listeners.add(fn);handlers.set(event,listeners);},
    removeEventListener:(event,fn)=>handlers.get(event)?.delete(fn),
    dispatchEvent:event=>{for(const fn of handlers.get(event.type)||[])fn(event);return true;}
  };
  return {map,localStorage};
}
const textOf=node=>typeof node==="string"?node:typeof node==="number"?String(node):
  node?.children?.map(textOf).join("")||"";
function loadPool(){
  const filename="PoolStageExplorer.tsx",original=Module._load;
  const Stub=()=>null;
  const mocks={
    "./PoolDesignationSelector":{__esModule:true,default:({selected,onChange})=>React.createElement("button",{
      onClick:()=>onChange(selected.includes("orphan_drug")?[]:["orphan_drug"])
    },"Toggle FDA")},
    "./ToolsResultsSpreadsheet":{__esModule:true,default:Stub},
    "./ToolsFunnel":{__esModule:true,default:Stub},
    "./ToolsOpeningTrialGrid":{__esModule:true,default:Stub},
    "./ToolsAssessmentSection":{__esModule:true,default:Stub}
  };
  Module._load=function(request,parent,isMain){
    if(parent?.filename.endsWith(filename)&&Object.hasOwn(mocks,request))return mocks[request];
    return original.apply(this,arguments);
  };
  try{return require("../app/"+filename).default;}finally{Module._load=original;}
}
test("reload keeps clicked Phase/FDA filters; scoped clear preserves the other branch; global clear forgets all",async()=>{
  const {map,localStorage}=withBrowser();
  const Pool=loadPool();
  const originalFetch=global.fetch;
  const calls=[];
  global.fetch=async url=>{
    calls.push(String(url));
    return {ok:true,json:async()=>({
      view:"pool",total:0,rows:[],spreadsheetRows:[],nextOffset:null,selectionSummary:{},
      restrictedScope:{scope:"DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN",qualification:"NOT_VERIFIED",
        screenedTrials:0,originalPoolTrials:100,capAsOf:"2026-11-01T03:21:15Z",
        unverifiedCapTrials:20,outsideCapTrials:25,excludedIssuerTrials:10,eligibleIssuers:5,outstanding:[]},
      stageStats:{trials:100,stages:{"Phase 3":{trials:18,standaloneResults:0,regulatoryEvents:0,total:18}}}
    })};
  };
  let root;
  try{
    await act(async()=>{root=create(React.createElement(Pool));});
    let phase=root.root.findByProps({"aria-controls":"tools-first-phase"});
    await act(async()=>phase.props.onClick());
    const phaseBox=root.root.findAllByType("label").find(x=>textOf(x)==="Phase 3"+"18");
    // The stage option is also accessible by its descendant checkbox.
    const option=phaseBox||root.root.findAllByType("label").find(x=>textOf(x).includes("Phase 3")&&!textOf(x).includes("Phase 3 Results"));
    assert.ok(option);
    await act(async()=>option.findByType("input").props.onChange());
    const designation=root.root.findByProps({"aria-controls":"tools-first-designation"});
    await act(async()=>designation.props.onClick());
    await act(async()=>root.root.findAllByType("button").find(x=>textOf(x)==="Toggle FDA").props.onClick());
    assert.deepEqual(JSON.parse(map.get(TOOLS_FILTERS_STORAGE_KEY)).selectedStages,["Phase 3"]);
    assert.deepEqual(JSON.parse(map.get(TOOLS_FILTERS_STORAGE_KEY)).selectedDesignations,["orphan_drug"]);
    assert.ok(calls.some(u=>u.includes("stages=Phase+3")&&u.includes("designations=orphan_drug")));
    await act(async()=>root.unmount());
    root=null;
    await act(async()=>{root=create(React.createElement(Pool));});
    assert.ok(calls.at(-1).includes("stages=Phase+3")&&calls.at(-1).includes("designations=orphan_drug"));
    const restorePhase=root.root.findByProps({"aria-controls":"tools-first-phase"});
    const restoreFDA=root.root.findByProps({"aria-controls":"tools-first-designation"});
    assert.match(textOf(restorePhase),/1 selected/);
    assert.match(textOf(restoreFDA),/1 selected/);
    const clearFDA=root.root.findAllByType("button").find(x=>textOf(x)==="Clear This Section");
    assert.ok(clearFDA);
    await act(async()=>clearFDA.props.onClick());
    assert.deepEqual(JSON.parse(map.get(TOOLS_FILTERS_STORAGE_KEY)).selectedStages,["Phase 3"]);
    assert.deepEqual(JSON.parse(map.get(TOOLS_FILTERS_STORAGE_KEY)).selectedDesignations,[]);
    localStorage.setItem(TOOLS_STEP4_STORAGE_KEY,'{"mode":"all","active":3,"chosen":""}');
    localStorage.setItem(TOOLS_RATINGS_STORAGE_KEY,'["B"]');
    localStorage.setItem(TOOLS_RANKING_STORAGE_KEY,'{"groupIds":[1]}');
    const clearAll=root.root.findAllByType("button").find(x=>textOf(x)==="Clear All Selections");
    assert.ok(clearAll);
    await act(async()=>clearAll.props.onClick());
    assert.deepEqual(JSON.parse(map.get(TOOLS_FILTERS_STORAGE_KEY)).selectedStages,[]);
    assert.deepEqual(JSON.parse(map.get(TOOLS_FILTERS_STORAGE_KEY)).selectedDesignations,[]);
    for(const key of [TOOLS_STEP4_STORAGE_KEY,TOOLS_RATINGS_STORAGE_KEY,TOOLS_RANKING_STORAGE_KEY])
      assert.equal(map.has(key),false);
    clearToolsPreferences();
    assert.equal(map.size,0);
  }finally{
    if(root)await act(async()=>root.unmount());
    global.fetch=originalFetch;
    delete global.window;
  }
});
