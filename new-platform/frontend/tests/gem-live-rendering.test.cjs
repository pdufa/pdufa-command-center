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

test("GEM JR FS and FI are independent toggles that retain visible original checkboxes",async()=>{
 let root;
 function Workspace(){
  const [draft,setDraft]=React.useState(null);
  return React.createElement(Checklist,{
   stage:"GEM_JR",pipeline:pipeline.slice(0,6),asOf,stageTotal:11,
   completedScan:null,stageSavedRows:[],manualStageList:{},
   onAddToStageList(){},onRemoveFromStageList(){},
   gemJrScan:null,gemJrSavedRows:[],gemJrDraft:draft,
   onGemJrDraftChange:setDraft,onScan(){},onReset(){}
  });
 }
 const getButton=(label)=>root.root.findAllByType("button").find(button=>
  button.children.some(child=>child===label));
 const original=(name)=>root.root.findAllByType("label").find(label=>
  label.findAllByType("span").some(span=>span.children.includes(name)));
 const fiCheckbox=()=>root.root.findAllByType("input").find(input=>
  input.props["aria-label"]==="FI: Successful Phase 3 independently verified");
 const check=()=>({
  fs:getButton("FS").props["aria-pressed"],
  fi:getButton("FI").props["aria-pressed"],
  fa:getButton("FA").props["aria-pressed"],
  original:original("Successful Phase 3 independently verified").findByType("input").props.checked,
  fiBox:fiCheckbox().props.checked
 });
 const click=async(label)=>{await act(async()=>{getButton(label).props.onClick();});};
 try{
  await act(async()=>{root=create(React.createElement(Workspace));});
  assert.deepEqual(check(),{fs:false,fi:false,fa:false,original:false,fiBox:false});
  await click("FI");
  assert.deepEqual(check(),{fs:false,fi:true,fa:false,original:true,fiBox:true},
   "FI must not enable FS or FA");
  await click("FS");
  assert.deepEqual(check(),{fs:true,fi:true,fa:false,original:true,fiBox:true});
  await click("FI");
  assert.deepEqual(check(),{fs:true,fi:false,fa:false,original:true,fiBox:false},
   "switching off FI must preserve FS and visible original checkbox");
  await click("FI");
  await click("FS");
  assert.deepEqual(check(),{fs:false,fi:true,fa:false,original:true,fiBox:true},
   "switching off FS must preserve FI and visible original checkbox");
  await click("FI");
  assert.deepEqual(check(),{fs:false,fi:false,fa:false,original:false,fiBox:false},
   "both presets off leaves original unchecked");
 }finally{if(root)await act(async()=>root.unmount());}
});
