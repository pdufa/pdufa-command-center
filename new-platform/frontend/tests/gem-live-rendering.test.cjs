const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");

for(const ext of [".ts",".tsx"]){
 require.extensions[ext]=(module,filename)=>module._compile(ts.transpileModule(
  fs.readFileSync(filename,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,
   target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}
 ).outputText,filename);
}
const Checklist=require("../app/GemQualificationChecklist.tsx").default;
global.IS_REACT_ACT_ENVIRONMENT=true;
const pipeline=Array.from({length:12000},(_,i)=>({id:"TRIAL|"+i,ticker:"T"+i,
 trialFilters:{registeredPhase:"Phase 3",primaryOutcome:i%2?"FAIL":"SUCCESS",resultsReleased:true}}));
const asOf="2026-10-19";

test("GEM JR settles after publishing its preview and still responds to qualification changes",async()=>{
 let publications=0,latest,root;
 function Workspace(){
  const [preview,setPreview]=React.useState(null);
  const [draft,setDraft]=React.useState(null);
  const publish=React.useCallback(value=>{
   if(++publications>5)throw Error("GEM JR preview keeps feeding its own render");
   latest=value;
   setPreview(value);
  },[]);
  return React.createElement(Checklist,{stage:"GEM_JR",pipeline,asOf,stageTotal:11,
   gemJrScan:null,gemJrSavedRows:[],completedScan:null,stageSavedRows:[],manualStageList:{},
   onAddToStageList(){},onRemoveFromStageList(){},gemJrLivePreview:preview,gemJrDraft:draft,
   onGemJrLivePreviewChange:publish,onGemJrDraftChange:setDraft,onScan(){},onReset(){}});
 }
 try{
  await act(async()=>{root=create(React.createElement(Workspace));});
  assert.equal(publications,1,"unchanged parent preview must not trigger another publication");
  assert.equal(latest.passes.length,12000);
  assert.equal(latest.needsReview.length,0);
  const successfulPhase3=root.root.findAllByType("label").find(label=>
   label.findAllByType("span").some(span=>span.children.includes("Successful Phase 3 independently verified")));
  assert.ok(successfulPhase3);
  await act(async()=>successfulPhase3.findByType("input").props.onChange());
  assert.equal(publications,2,"changing a requirement publishes one new result");
  assert.equal(latest.passes.length,6000);
  assert.deepEqual(latest.selected,["phase3"]);
 }finally{if(root)await act(async()=>root.unmount());}
});

test("GEM retains unknown evidence inherited from its GEM JR input",async()=>{
 const upstream={asOf,sourceTotal:pipeline.length,selected:[],
  passes:pipeline.slice(0,3),needsReview:pipeline.slice(3,4)};
 let latest,publications=0,root;
 function Workspace(){
  const [preview,setPreview]=React.useState(null);
  const [draft,setDraft]=React.useState({asOf,sourceTotal:pipeline.length,
   selected:["gem_jr_source"],showSuggestions:false,faActive:false,optionalGoals:{},twoTrialIds:["",""]});
  const publish=React.useCallback(value=>{
   if(++publications>5)throw Error("GEM preview did not settle");
   latest=value;setPreview(value);
  },[]);
  return React.createElement(Checklist,{stage:"GEM",pipeline,asOf,stageTotal:6,
   gemJrScan:null,gemJrSavedRows:[],completedScan:null,stageSavedRows:[],manualStageList:{},
   onAddToStageList(){},onRemoveFromStageList(){},gemJrLivePreview:upstream,gemDraft:draft,
   onGemLivePreviewChange:publish,onGemDraftChange:setDraft,onScan(){},onReset(){}});
 }
 try{
  await act(async()=>{root=create(React.createElement(Workspace));});
  assert.equal(publications,1);
  assert.equal(latest.passes.length,3);
  assert.deepEqual(latest.needsReview.map(row=>row.id),[pipeline[3].id]);
 }finally{if(root)await act(async()=>root.unmount());}
});
