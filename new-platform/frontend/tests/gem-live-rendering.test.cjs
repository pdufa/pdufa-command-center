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
  return React.createElement(Checklist,{stage:"GEM_JR",initiallyExpanded:true,pipeline,asOf,stageTotal:11,
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
  return React.createElement(Checklist,{stage:"GEM",initiallyExpanded:true,pipeline,asOf,stageTotal:6,
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


test("GEM JR FS toggles the original five restrictions with no FI controls",async()=>{
 let root,draft;
 function Workspace(){
  const [stored,setDraft]=React.useState(null);
  draft=stored;
  return React.createElement(Checklist,{
   stage:"GEM_JR",initiallyExpanded:true,pipeline:pipeline.slice(0,6),asOf,stageTotal:11,
   completedScan:null,stageSavedRows:[],manualStageList:{},
   onAddToStageList(){},onRemoveFromStageList(){},
   gemJrScan:null,gemJrSavedRows:[],gemJrDraft:stored,
   onGemJrDraftChange:setDraft,onScan(){},onReset(){}
  });
 }
 const button=(label)=>root.root.findAllByType("button").find(b=>b.children.includes(label));
 const original=(name)=>root.root.findAllByType("label").find(label=>
  label.findAllByType("span").some(span=>span.children.includes(name))).findByType("input");
 const phase3="Successful Phase 3 independently verified";
 try{
  await act(async()=>{root=create(React.createElement(Workspace));});
  assert.equal(button("FI"),undefined);
  assert.equal(button("FS").props["aria-pressed"],false);
  assert.equal(original(phase3).props.checked,false);
  assert.equal(Boolean(draft?.fiSelected),false);
  await act(async()=>{button("FS").props.onClick();});
  assert.equal(button("FS").props["aria-pressed"],true);
  assert.equal(original(phase3).props.checked,true);
  assert.equal(draft.selected.length,5);
  assert.equal(Boolean(draft.fiSelected),false);
  assert.equal(button("FI"),undefined);
  await act(async()=>{button("FS").props.onClick();});
  assert.equal(button("FS").props["aria-pressed"],false);
  assert.equal(original(phase3).props.checked,false);
  assert.deepEqual(draft.selected,[]);
 }finally{if(root)await act(async()=>root.unmount());}
});

test("Both stage new-trial tables add and remove exact candidates directly in the same row",async()=>{
 for(const stage of ["GEM_JR","GEM"]){
  const candidate={id:"TRIAL|ADD-1",ticker:"TEST",drug:"Trial drug",
   nctId:"NCT12345678",trialFilters:{registeredPhase:"Phase 3"}};
  const completedScan={
   runNumber:1,asOf,evaluatedAt:asOf+"T12:00:00Z",
   sourceTotal:1,baseline:1,sourceKind:"PIPELINE",
   selected:["registry"],audits:[],passes:[candidate],needsReview:[],fails:[]
  };
  let root,savedNow={};
  function Workspace(){
   const [list,setList]=React.useState({});
   savedNow=list;
   return React.createElement(Checklist,{
    stage,initiallyExpanded:true,pipeline:[candidate],asOf,stageTotal:0,
    completedScan,stageSavedRows:[],manualStageList:list,
    onAddToStageList:row=>setList(old=>({...old,[row.id]:"2026-10-19T12:00:00Z"})),
    onRemoveFromStageList:id=>setList(old=>{const next={...old};delete next[id];return next;}),
    gemJrScan:null,gemJrSavedRows:[],onScan(){},onReset(){}
   });
  }
  const button=(value)=>root.root.findAllByType("button").find(btn=>
   btn.children.some(child=>child===value));
  try{
   await act(async()=>{root=create(React.createElement(Workspace));});
   assert.ok(root.root.findAllByType("strong").some(el=>el.children.some(
    txt=>typeof txt==="string"&&txt.includes("CANDIDATES"))));
   assert.equal(button("ADD TO LIST").props.disabled,false);
   assert.equal(button("REMOVE").props.disabled,true);
   await act(async()=>{button("ADD TO LIST").props.onClick();});
   assert.equal(savedNow[candidate.id],"2026-10-19T12:00:00Z",stage+" added exact program");
   assert.equal(button("ADDED ✓").props.disabled,true);
   assert.equal(button("REMOVE").props.disabled,false);
   await act(async()=>{button("REMOVE").props.onClick();});
   assert.equal(savedNow[candidate.id],undefined,stage+" removed same exact program");
   assert.equal(button("ADD TO LIST").props.disabled,false);
   assert.equal(button("REMOVE").props.disabled,true);
  }finally{if(root)await act(async()=>root.unmount());}
 }
});

test("Repeat scans show zero NEW programs and retain the old match under PREVIOUSLY SEEN",async()=>{
 for(const stage of ["GEM_JR","GEM"]){
  const candidate={id:"APPLICATION|EXACT-1",ticker:"SAME",drug:"Single verified program"};
  const scan={runNumber:1,asOf,evaluatedAt:asOf+"T12:00:00Z",sourceTotal:1,baseline:1,
   sourceKind:"PIPELINE",selected:["registry"],audits:[],passes:[candidate,candidate],needsReview:[],fails:[]};
  let root,setFresh,saved={};
  function Wrapper(){
   const [fresh,setFreshIds]=React.useState([candidate.id]);
   const [list,setList]=React.useState({});
   setFresh=setFreshIds;saved=list;
   return React.createElement(Checklist,{
    stage,initiallyExpanded:true,pipeline:[candidate],asOf,stageTotal:0,completedScan:scan,
    stageSavedRows:[],newThisScanIds:fresh,manualStageList:list,
    gemJrScan:null,gemJrSavedRows:[],
    onAddToStageList:row=>setList(current=>current[row.id]?current:
      {...current,[row.id]:"2026-10-20T10:00:00Z"}),
    onRemoveFromStageList:id=>setList(current=>{const next={...current};delete next[id];return next;}),
    onScan(){},onReset(){}
   });
  }
  const buttons=()=>root.root.findAllByType("button");
  const button=(label)=>buttons().find(b=>b.children.includes(label));
  const panelText=()=>root.root.findAllByType("strong").flatMap(b=>b.children.filter(x=>typeof x==="string")).join(" ");
  try{
   await act(async()=>{root=create(React.createElement(Wrapper));});
   assert.match(panelText(),/NEW\s+(GEM JR|GEM)\s+CANDIDATES/);
   assert.ok(button("ADD TO LIST"),"first scan can manually add program");
   // Simulate completed second scan with an unchanged source and filter.
   await act(async()=>{setFresh([]);});
   assert.match(panelText(),/NEW\s+(GEM JR|GEM)\s+CANDIDATES/);
   assert.equal(button("ADD TO LIST"),undefined,"repeat scan should not show existing program as NEW");
   assert.ok(button("PREVIOUSLY SEEN"),"old matches remain accessible");
   await act(async()=>{button("PREVIOUSLY SEEN").props.onClick();});
   assert.ok(button("ADD TO LIST"),"prior program remains manually actionable");
   await act(async()=>{button("ADD TO LIST").props.onClick();});
   assert.equal(Object.keys(saved).length,1);
   await act(async()=>{button("REMOVE").props.onClick();});
   assert.equal(Object.keys(saved).length,0);
  }finally{if(root)await act(async()=>root.unmount());}
 }
});
