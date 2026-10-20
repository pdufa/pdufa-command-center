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
  gemJrSavedRows:saved,gemJrScan:null,completedScan:null,stageSavedRows:saved,manualStageList:{},
  onAddToStageList:()=>{},onRemoveFromStageList:()=>{},...props,
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
  assert.match(page,/\(0 active scan checks\)/);
  assert.equal(pickGemResearchRows({pipeline:dataset,savedStage:saved}).length,694);
 }
});
test("Only an explicit VIEW SAVED MEMBERS selects the 11-member stage list",()=>{
 assert.deepEqual(pickGemResearchRows({pipeline:dataset,savedStage:saved,savedOnly:true}),saved);
 assert.equal(pickGemResearchRows({pipeline:dataset,savedStage:saved,savedOnly:false}).length,694);
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(src,/VIEW SAVED MEMBERS/);
 assert.match(src,/function gemCandidateRows\(stage: "GEM_JR" \| "GEM"\)/);
 assert.match(src,/const rows=sortByAssessment\(gemPageRows\[stage\],assessmentRecords,stage,assessmentOrder\[stage\]\)/);
 assert.match(src,/pickGemResearchRows\(\{\s*pipeline,\s*savedStage: snapshot\?\.members\[stage\]\.rows \|\| \[\],/);
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

test("Current top workflow totals appear below navigation in Pipeline, GEM JR, GEM, WT order",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
 const nav=src.indexOf('id="pdufa-section-navigation"');
 const counters=src.indexOf('className="workflow-counts"');
 const overview=src.indexOf('className="workspace-overview"');
 assert.ok(nav>=0 && counters>nav && overview>counters,"totals are directly after navigation and before overview");
 const totals=src.slice(counters,overview);
 const ids=['id:"PIPELINE" as Nav','id:"GEM_JR" as Nav','id:"GEM" as Nav','id:"WT" as Nav'];
 let previous=-1;
 for(const id of ids){ const at=totals.indexOf(id);assert.ok(at>previous,"out-of-order count: "+id);previous=at; }
 assert.match(totals,/publishedCounts/);
 assert.match(totals,/count:snapshot \? verifiedStageCount\("GEM_JR"\) : publishedCounts\?\.gemJr \?\? null/);
 assert.match(totals,/count:snapshot \? verifiedStageCount\("GEM"\) : publishedCounts\?\.gem \?\? null/);
 assert.match(totals,/count:tagsReady \? pageTotals\.WT : null/);
 assert.match(totals,/count:snapshot \? pageTotals\.PIPELINE : publishedCounts\?\.pipeline \?\? null/);
 assert.match(totals,/item\.count===null\?"—":item\.count\.toLocaleString\("en-US"\)/);
 assert.match(css,/\.workflow-counts\s*\{[\s\S]*?grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);
 assert.match(css,/@media\(max-width:750px\)\s*\{\s*\.workflow-counts\s*\{\s*grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
});

test("Each top count is exactly the number displayed on its stage page",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 const totals=src.slice(src.indexOf('const pageTotals:'),src.indexOf('function wtButton'));
 assert.match(totals,/PIPELINE: possible\.length/);
 assert.match(totals,/GEM_JR: gemPageRows\.GEM_JR\.length/);
 assert.match(totals,/GEM: gemPageRows\.GEM\.length/);
 assert.match(totals,/WT: tags\.watch\.length \+ tags\.trade\.length/);
 assert.match(src,/const rows=sortByAssessment\(gemPageRows\[stage\],assessmentRecords,stage,assessmentOrder\[stage\]\)/);
 assert.match(src,/className="gem-count">\{pageTotals\[stage\]\.toLocaleString\("en-US"\)\}/);
 assert.match(src,/className="counter">\{pageTotals\.PIPELINE\.toLocaleString\("en-US"\)\}/);
 assert.match(src,/className="counter">\{tagsReady \? pageTotals\.WT\.toLocaleString\("en-US"\) : "—"\} total W\/T programs/);
 assert.match(src,/const gemPageRows = \{ GEM_JR: gemCandidateRows\("GEM_JR"\), GEM: gemCandidateRows\("GEM"\) \}/);
});

test("Four illustrated top boxes match the reference colors and icons",()=>{
 const src=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 const css=fs.readFileSync(path.join(__dirname,"../app/globals.css"),"utf8");
 const iconSource=fs.readFileSync(path.join(__dirname,"../app/WorkflowStageIcon.tsx"),"utf8");
 assert.match(src,/import WorkflowStageIcon from "\.\/WorkflowStageIcon"/);
 assert.match(iconSource,/function WorkflowStageIcon\(\{stage\}/);
 assert.match(src,/workflow-count-icon/);
 assert.match(src,/workflow-count-copy/);
 assert.match(src,/className=\{"workflow-count workflow-count--"\+item\.id\.toLowerCase\(\)/);
 for(const color of ["pipeline","gem_jr","gem","wt"]){
   assert.ok(css.includes(".migration-workspace .workflow-count--"+color+" {"),"missing color variant: "+color);
 }
 for(const color of ["#eaf3ff","#e6f9ef","#f1e9ff","#fff7e1"]){
   assert.ok(css.includes(color),"missing reference color "+color);
 }
 assert.match(src,/label:"PIPELINE", count:snapshot \? pageTotals\.PIPELINE : publishedCounts\?\.pipeline \?\? null/);
 assert.match(src,/label:"GEM JR", count:snapshot \? verifiedStageCount\("GEM_JR"\) : publishedCounts\?\.gemJr \?\? null/);
 assert.match(src,/label:"GEM", count:snapshot \? verifiedStageCount\("GEM"\) : publishedCounts\?\.gem \?\? null/);
 assert.match(src,/label:"WT", count:tagsReady \? pageTotals\.WT : null/);
 assert.match(css,/\.workflow-count-icon svg/);
 assert.match(css,/\.workflow-counts\s*\{\s*display:grid;\s*grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);
});
