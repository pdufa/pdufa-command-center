const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
for(const ext of [".ts",".tsx"]){
 require.extensions[ext]=(module,filename)=>{
  const js=ts.transpileModule(fs.readFileSync(filename,"utf8"),{
   compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
     jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText;
  module._compile(js,filename);
 };
}
const {pickGemResearchRows}=require("../lib/gem-screen-rows.ts");
const Checklist=require("../app/GemQualificationChecklist.tsx");
const dataset=Array.from({length:694},(_,i)=>({id:"PDUFA|"+i,ticker:"T"+i,
 drug:"Drug "+i,trialFilters:{registeredPhase:"Phase 3"}}));
const saved=dataset.slice(0,11);
const asOf="2026-10-18";
function html(stage,props={}){
 return renderToStaticMarkup(React.createElement(Checklist.default,{
  stage,pipeline:dataset,asOf,stageTotal:saved.length,
  gemJrSavedRows:saved,gemJrScan:null,...props,
  onScan:()=>{},onReset:()=>{}
 }));
}
test("Zero requirements show all 694 GEM source candidates, not the 11 saved stage members",()=>{
 for(const stage of ["GEM","GEM_JR"]){
  const page=html(stage);
  assert.match(page,/TOTAL COMBINED RESULTS/);
  assert.match(page,/694/);
  assert.match(page,/11/);
  assert.match(page,/saved stage members \(not screened total\)/);
  assert.match(page,/\(0 selected\)/);
  assert.equal(pickGemResearchRows({pipeline:dataset,savedStage:saved}).length,694);
 }
});
test("Only an explicit VIEW SAVED MEMBERS selects the 11-member stage list",()=>{
 assert.deepEqual(pickGemResearchRows({pipeline:dataset,savedStage:saved,savedOnly:true}),saved);
 assert.equal(pickGemResearchRows({pipeline:dataset,savedStage:saved,savedOnly:false}).length,694);
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(src,/VIEW SAVED MEMBERS/);
 assert.match(src,/pickGemResearchRows\(\{pipeline,savedStage:group\?\.rows\|\|\[\],livePreview:stagePreview,completedScan:activeScan,savedOnly\}\)/);
 assert.match(src,/LIVE RESEARCH SCREEN/);
 assert.match(src,/NOT STAGE MEMBER/);
});
test("Live AND-filtering and completed scans determine table rows without adding saved members",()=>{
 const selected=dataset.slice(0,403);
 const preview={passes:selected.slice(0,300),needsReview:selected.slice(300)};
 const result=pickGemResearchRows({pipeline:dataset,savedStage:saved,livePreview:preview});
 assert.equal(result.length,403);
 assert.deepEqual(result.map(r=>r.id),selected.map(r=>r.id));
 const scanned={passes:dataset.slice(0,63),needsReview:dataset.slice(63,88)};
 assert.equal(pickGemResearchRows({pipeline:dataset,savedStage:saved,livePreview:preview,completedScan:scanned}).length,88);
 assert.equal(pickGemResearchRows({pipeline:dataset,savedStage:saved,livePreview:preview,completedScan:scanned,savedOnly:true}).length,11);
});
test("GEM selected GEM JR input preserves 694 live candidates even when saved membership is 11",()=>{
 const preview=Checklist.buildGemJrLivePreview(dataset,[],asOf,dataset.length);
 const source=Checklist.resolveGemJrSource(null,preview,dataset);
 assert.equal(source.rows.length,694);
 const page=html("GEM",{gemJrLivePreview:preview,gemDraft:{
  selected:["gem_jr_source"],sourceTotal:694,asOf,showSuggestions:false,
  faActive:false,optionalGoals:{},twoTrialIds:["",""]
 }});
 assert.match(page,/GEM JR live checkbox results: 694 candidates/);
 assert.match(page,/TOTAL COMBINED RESULTS/);
 assert.match(page,/694/);
});
test("GEM and GEM JR keep original clinical and trading checkboxes",()=>{
 const groups=Checklist.checkboxGroupsForStage("GEM");
 assert.equal(groups.trading.length,10);
 assert.equal(groups.clinical.length,1);
 assert.equal(groups.clinical[0][0],"pdufa");
 const jr=Checklist.checkboxGroupsForStage("GEM_JR");
 assert.equal(jr.trading.length,13);
 assert.equal(jr.clinical.length,4);
});
