const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");

// The same TypeScript/JXS transpiler used by existing frontend tests.
for(const ext of [".ts",".tsx"]){
  require.extensions[ext]=(loaded,file)=>{
    const output=ts.transpileModule(fs.readFileSync(file,"utf8"),{
      compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
        jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
    }).outputText;
    loaded._compile(output,file);
  };
}
const Checklist=require("../app/GemQualificationChecklist.tsx");
const {checkboxGroupsForStage,resolveGemJrSource,buildGemJrLivePreview}=Checklist;
function page(stage){
  return renderToStaticMarkup(React.createElement(Checklist.default,{
    stage,initiallyExpanded:true,pipeline:[],asOf:"2026-10-18",stageTotal:0,gemJrScan:null,gemJrSavedRows:[],
    completedScan:null,stageSavedRows:[],manualStageList:{},
    onAddToStageList:()=>{},onRemoveFromStageList:()=>{},
    onScan:()=>{},onReset:()=>{}
  }));
}

test("Both stages preserve their previous checkbox identities with no duplicates",()=>{
  for(const [stage,count] of [["GEM_JR",17],["GEM",11]]){
    const groups=checkboxGroupsForStage(stage);
    const all=[...groups.clinical,...groups.trading];
    assert.equal(all.length,count);
    assert.equal(new Set(all.map(([key])=>key)).size,count);
    assert.ok(groups.trading.length>0);
    assert.ok(groups.clinical.length>0);
  }
  const jr=checkboxGroupsForStage("GEM_JR");
  const gem=checkboxGroupsForStage("GEM");
  const keys=items=>new Set(items.map(([key])=>key));
  assert.ok(keys(jr.clinical).has("phase3"));
  assert.ok(keys(jr.clinical).has("registry"));
  assert.ok(keys(jr.trading).has("marketcap"));
  assert.ok(keys(jr.trading).has("cash"));
  assert.ok(keys(gem.clinical).has("pdufa"));
  assert.ok(keys(gem.trading).has("volume"));
  for(const key of ["phase3","registry","issuer","cash","marketfresh","marketcap"])
    assert.equal([...gem.clinical,...gem.trading].some(([k])=>k===key),false);
});

test("Actual GEM JR renders ORIGINAL clinical and Trading checkbox areas with FS/FA",()=>{
  const html=page("GEM_JR");
  const clinical=html.match(/<section class="gem-original-clinical"[\s\S]*?<\/section>/)?.[0];
  const trading=html.match(/<details class="gem-original-trading"[\s\S]*?<\/details>/)?.[0];
  assert.ok(clinical,"Clinical original checkboxes group present");
  assert.ok(trading,"Trading original checkboxes group present");
  assert.match(clinical,/Successful Phase 3 independently verified/);
  assert.match(clinical,/Phase 3 trial status recorded/);
  assert.doesNotMatch(clinical,/Market cap \$300M/);
  assert.match(trading,/Market cap \$300M/);
  assert.match(trading,/SEC cash runway/);
  assert.match(trading,/Relative volume/);
  assert.match(html,/aria-label="FS: toggle suggested criteria checkboxes"/);
  assert.match(html,/aria-label="FA: toggle Phase 3 trial status recorded and market cap qualification checkboxes"/);
  assert.match(html,/Optional GEM JR evidence alerts/);
  assert.match(html,/TOTAL COMBINED RESULTS/);
  assert.match(html,/DESELECT ALL/);
  assert.match(html,/aria-label="GEM JR SCAN"/);
  assert.equal((clinical+trading).match(/type="checkbox"/g)?.length,17);
});

test("Actual GEM keeps its input checkbox and 11 downstream controls, never FS/FA duplicates",()=>{
  const html=page("GEM");
  const clinical=html.match(/<section class="gem-original-clinical"[\s\S]*?<\/section>/)?.[0];
  const trading=html.match(/<details class="gem-original-trading"[\s\S]*?<\/details>/)?.[0];
  assert.ok(clinical&&trading);
  assert.match(clinical,/Gem Jr Trials/);
  assert.match(clinical,/Verified PDUFA date source/);
  assert.match(trading,/Second financing verified/);
  assert.match(trading,/Relative volume/);
  assert.match(trading,/No unresolved dilution/);
  assert.match(html,/aria-pressed="false" aria-label="FA: toggle Gem Jr Trials input"/);
  assert.equal((html.match(/>FA<\/button>/g)||[]).length,1,"GEM shows exactly one FA button");
  assert.match(html,/aria-label="FS: toggle suggested criteria checkboxes"/);
  assert.match(html,/TOTAL COMBINED RESULTS/);
  assert.match(html,/aria-label="GEM SCAN"/);
  assert.equal((clinical+trading).match(/type="checkbox"/g)?.length,12);
});

test("Original FS, FA, and combined AND scan evaluator remain in place",()=>{
  const content=fs.readFileSync(path.join(__dirname,"../app/GemQualificationChecklist.tsx"),"utf8");
  for(const unchanged of ["const suggestedByStage:","const FA_CRITERIA=",
    "const GEM_JR_OWNED_CRITERIA=","const sourceRows=useGemJrSource?gemJrRows:pipeline;",
    "const liveCounts=useMemo(", "function toggleFs(){", "function toggleFa(){",
    "function toggle(key:string){", "for(const [, , evaluate] of chosen)",
    "for(let rowIndex=0;rowIndex<scanRows.length;rowIndex++)", "result.audits.length"]){
    assert.ok(content.includes(unchanged),unchanged+" changed unexpectedly");
  }
});

test("GEM JR saved membership remains independent of the research input fallback",()=>{
  const rows=Array.from({length:11},(_,i)=>({
    id:"APPLICATION|PROGRAM-"+i,ticker:"TICK"+i,drug:"Distinct program "+i
  }));
  const pipeline=Array.from({length:694},(_,i)=>({id:"PIPELINE|"+i,ticker:"T"+i}));
  const result=resolveGemJrSource(null,null,pipeline);
  assert.equal(result.sourceKind,"GEM_JR_UNSCREENED");
  assert.equal(result.rows.length,694);
  assert.equal(result.reviewIds.size,694);
  assert.equal(result.scanAvailable,false);
  assert.match(result.label,/no GEM JR screen yet/);
  assert.deepEqual(result.rows.map(x=>x.id),pipeline.map(x=>x.id));
  assert.equal(rows.length,11,"Saved stage membership still has 11, without restricting the research input");
});

test("If GEM JR scan exists, use its exact filtered set rather than merging all saved programs",()=>{
  const saved=Array.from({length:11},(_,i)=>({id:"SAVED|"+i,ticker:"SAVE"+i}));
  const passed={id:"APP|PASS",ticker:"GOOD"};
  const review={id:"APP|REVIEW",ticker:"VERIFY"};
  const scan={passes:[passed],needsReview:[review],fails:[{id:"APP|FAIL",ticker:"FAIL"}]};
  const result=resolveGemJrSource(scan,null,saved);
  assert.equal(result.sourceKind,"GEM_JR");
  assert.deepEqual(result.rows,[passed,review]);
  assert.deepEqual([...result.reviewIds],["APP|REVIEW"]);
  assert.equal(result.scanAvailable,true);
  assert.equal(result.rows.some(row=>row.id.startsWith("SAVED|")),false);
});

test("Absent both JR sources, GEM never fabricates a candidate list",()=>{
  const result=resolveGemJrSource(null,null,[]);
  assert.deepEqual(result.rows,[]);
  assert.equal(result.reviewIds.size,0);
});

test("The current GEM JR combined 694 program checkbox screen feeds GEM, not the unrelated 11-member saved stage ledger",()=>{
 const pipeline=Array.from({length:700},(_,i)=>({
  id:"TRIAL|"+i,ticker:"T"+i,drug:"Drug "+i,
  trialFilters:{registeredPhase:i<694?"Phase 3":"Phase 2"}
 }));
 const checks=[["registry","Phase 3 trial status recorded",
  x=>x.trialFilters?.registeredPhase==="Phase 3"]];
 const preview=buildGemJrLivePreview(pipeline,checks,"2026-10-18T16:10:00Z",700);
 assert.equal(preview.passes.length,694);
 assert.equal(preview.needsReview.length,0);
 const saved=Array.from({length:11},(_,i)=>({id:"STAGE|"+i,ticker:"S"+i}));
 const GEM=resolveGemJrSource(null,preview,pipeline);
 assert.equal(GEM.sourceKind,"GEM_JR_LIVE");
 assert.equal(GEM.rows.length,694);
 assert.equal(GEM.reviewIds.size,0);
 assert.equal(GEM.scanAvailable,false);
 assert.match(GEM.label,/checkbox screen/);
 const JR=renderToStaticMarkup(React.createElement(Checklist.default,{
  stage:"GEM_JR",pipeline,asOf:"2026-10-18T16:10:00Z",stageTotal:11,
  gemJrScan:null,gemJrSavedRows:saved,completedScan:null,stageSavedRows:saved,manualStageList:{},
  onAddToStageList:()=>{},onRemoveFromStageList:()=>{},gemJrDraft:{
   asOf:"2026-10-18T16:10:00Z",sourceTotal:700,
   selected:["registry"],showSuggestions:false,faActive:false,
   optionalGoals:{},twoTrialIds:["",""]
  },onScan:()=>{},onReset:()=>{}
 }));
 assert.match(JR,/TOTAL COMBINED RESULTS/);
 assert.match(JR,/>694</);
});

test("GEM JR preview does not elevate unknown trial evidence to verified pass",()=>{
 const rows=[{id:"TRIAL|PASS",ticker:"PASS",phase3Status:"VERIFIED"},
             {id:"TRIAL|UNKNOWN",ticker:"UNKNOWN"},
             {id:"TRIAL|FAIL",ticker:"FAIL",phase3Status:"FAILED"}];
 const preview=buildGemJrLivePreview(rows,[["positive","Phase 3",
  r=>r.phase3Status==="VERIFIED"?true:r.phase3Status==="FAILED"?false:null]],
  "2026-10-18",3);
 assert.deepEqual(preview.passes.map(r=>r.id),["TRIAL|PASS"]);
 assert.deepEqual(preview.needsReview.map(r=>r.id),["TRIAL|UNKNOWN"]);
 const GEM=resolveGemJrSource(null,preview,[]);
 assert.equal(GEM.rows.length,2);
 assert.deepEqual([...GEM.reviewIds],["TRIAL|UNKNOWN"]);
 assert.equal(GEM.rows.some(r=>r.id==="TRIAL|FAIL"),false);
});

test("GEM source fallback cannot silently reduce a 694-row input to 11 saved entries",()=>{
 const saved=Array.from({length:11},(_,i)=>({id:"SAVED|"+i,ticker:"S"+i}));
 const universe=Array.from({length:694},(_,i)=>({id:"PIPELINE|"+i,ticker:"P"+i}));
 const actual=resolveGemJrSource(null,null,universe);
 assert.equal(actual.rows.length,694);
 assert.equal(actual.reviewIds.size,694);
 assert.equal(actual.sourceKind,"GEM_JR_UNSCREENED");
 assert.ok(actual.rows.every(r=>r.id.startsWith("PIPELINE|")));
 assert.equal(saved.length,11);
 const source=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
 assert.match(source,/<GemQualificationChecklist key=\{stage\} stage=\{stage\}/);
 assert.match(source,/GEM JR RESEARCH UNIVERSE INPUT/);
});

test("GEM FA starts off and mirrors only the optional Gem Jr Trials checkbox",()=>{
 const {toggleGemJrTrialsRequirement}=Checklist;
 const initiallyUnselected=[];
 const turnedOn=toggleGemJrTrialsRequirement(initiallyUnselected);
 assert.deepEqual(turnedOn,["gem_jr_source"]);
 assert.deepEqual(toggleGemJrTrialsRequirement(turnedOn),[]);
 const otherCriteria=["volume","pdufa","rsi"];
 const enabled=toggleGemJrTrialsRequirement(otherCriteria);
 assert.deepEqual(enabled,[...otherCriteria,"gem_jr_source"]);
 assert.deepEqual(toggleGemJrTrialsRequirement(enabled),otherCriteria);
 const gemHtml=page("GEM");
 assert.match(gemHtml,/aria-label="Gem Jr Trials \(optional\)"/);
 assert.match(gemHtml,/aria-pressed="false" aria-label="FA: toggle Gem Jr Trials input"/);
 assert.doesNotMatch(gemHtml,/aria-label="Gem Jr Trials \(optional\)"[^>]+checked/);
 const jrHtml=page("GEM_JR");
 assert.match(jrHtml,/aria-label="FA: toggle Phase 3 trial status recorded and market cap qualification checkboxes"/);
 assert.doesNotMatch(jrHtml,/FA: toggle Gem Jr Trials input/);
 const src=fs.readFileSync(path.join(__dirname,"../app/GemQualificationChecklist.tsx"),"utf8");
 assert.ok(src.includes('selectRequirements(toggleGemJrTrialsRequirement(selected))'),"GEM FA uses checkbox selection pathway");
 assert.ok(src.includes('aria-pressed={stage==="GEM"?useGemJrSource:faChecked}'),"FA button state derives from checkbox");
 assert.equal(checkboxGroupsForStage("GEM").clinical.length+checkboxGroupsForStage("GEM").trading.length,11);
});

test("FI controls are absent on both stages; original FS/FA checkboxes and candidate tables remain",()=>{
 for(const stage of ["GEM_JR","GEM"]){
  const html=page(stage);
  const clinical=html.match(/<section class="gem-original-clinical"[\s\S]*?<\/section>/)?.[0];
  const trading=html.match(/<details class="gem-original-trading"[\s\S]*?<\/details>/)?.[0];
  assert.ok(clinical && trading);
  assert.doesNotMatch(html,/aria-label="FI:|gem-fi-filter-section|>FI<\/button>|FI — [56] SCAN RESTRICTIONS/);
  assert.match(html,/aria-label="FS: toggle suggested criteria checkboxes"/);
  assert.match(html,/aria-label="FA: toggle/);
  assert.match(html,new RegExp("NEW "+(stage==="GEM_JR"?"GEM JR":"GEM")+" CANDIDATES"));
  assert.match(html,new RegExp("MY "+(stage==="GEM_JR"?"GEM JR":"GEM")+" LIST"));
  assert.match(html,/Run SCAN to populate this table/);
 }
 const jr=checkboxGroupsForStage("GEM_JR");
 const original=new Set([...jr.clinical,...jr.trading].map(([key])=>key));
 for(const id of ["phase3","registry","issuer","cash","marketfresh","marketcap"])assert.ok(original.has(id));
 assert.equal(original.size,17);
 assert.equal([...checkboxGroupsForStage("GEM").clinical,...checkboxGroupsForStage("GEM").trading].length,11);
 const src=fs.readFileSync(path.join(__dirname,"../app/GemQualificationChecklist.tsx"),"utf8");
 for(const forbidden of ["fiSelected","fiActive","fiIndependent","toggleFi","gem-fi-filter-section"]){
  assert.ok(!src.includes(forbidden),"redundant FI state or UI still exists: "+forbidden);
 }
 assert.match(src,/renderOriginalCheckboxes\(checkboxGroupsForStage\(stage\).clinical\)/);
 assert.match(src,/renderOriginalCheckboxes\(checkboxGroupsForStage\(stage\).trading\)/);
 assert.match(src,/onAddToStageList\(row\)/);
 assert.match(src,/onRemoveFromStageList\(row.id\)/,"new candidates table must support inline REMOVE");
 assert.match(src,/onRemoveFromStageList\(item.id\)/,"MY LIST must still support removal");
 assert.match(src,/disabled=\{Boolean\(manualStageList\[row.id\]\)\}/,"already added candidate cannot be added twice");
 assert.match(src,/disabled=\{!manualStageList\[row.id\]\}/,"candidate cannot be removed until added");
 assert.match(src,/Added \{manualStageList\[row.id\]\.slice\(0,10\)\}/);
});

test("A rescanned GEM JR or GEM program is NEW only once per stage, never duplicated",()=>{
 const {newlyObservedProgramIds}=Checklist;
 const trialA={id:"APPLICATION|A-TRIAL",ticker:"BBIO",drug:"Drug A"};
 const trialB={id:"APPLICATION|B-TRIAL",ticker:"BBIO",drug:"Drug B"};
 const alreadySaved={id:"APPLICATION|SAVED",ticker:"SAVED"};
 const scan={selected:["registry"],passes:[trialA,trialA,trialB,alreadySaved],needsReview:[trialB],
   fails:[{id:"APPLICATION|FAIL",ticker:"FAIL"}]};
 const first=newlyObservedProgramIds(scan,new Set(),new Set([alreadySaved.id]));
 assert.deepEqual(first,[trialA.id,trialB.id],"same ticker with different programs is not a duplicate");
 assert.deepEqual(newlyObservedProgramIds(scan,new Set(first),new Set([alreadySaved.id])),[],
   "second identical scan must have zero new trials");
 // One stage's seen history cannot suppress an independent other stage.
 assert.deepEqual(newlyObservedProgramIds(scan,new Set([trialA.id]),new Set([alreadySaved.id])),[trialB.id]);
 assert.deepEqual(newlyObservedProgramIds(scan,new Set(),new Set([alreadySaved.id,trialA.id])),[trialB.id],
   "a program already manually curated is not new");
 assert.deepEqual(newlyObservedProgramIds({...scan,selected:[]},new Set(),new Set()),[],
   "an unrestricted scan cannot mark the entire Pipeline as new");
});

test("managed GEM checklist uses one catalog selection and hides redundant checkboxes",()=>{
  const jr=renderToStaticMarkup(React.createElement(Checklist.default,{
    stage:"GEM_JR",initiallyExpanded:true,pipeline:[],asOf:"2026-10-20",
    stageTotal:0,completedScan:null,stageSavedRows:[],manualStageList:{},
    gemJrScan:null,gemJrSavedRows:[],onAddToStageList:()=>{},onRemoveFromStageList:()=>{},
    onScan:()=>{},onReset:()=>{},managedSelected:["registry","marketcap"],
    managedGoals:{priority_review:"6"},hideChecklistItems:true
  }));
  assert.match(jr,/ONE MASTER RESTRICTIONS LIST/);
  assert.doesNotMatch(jr,/gem-original-clinical|gem-original-trading|Optional GEM JR evidence alerts/);
  assert.match(jr,/aria-pressed="true" aria-label="FA: toggle Phase 3/);
  assert.match(jr,/aria-label="FS: toggle suggested criteria checkboxes"/);
  assert.deepEqual(Checklist.gemPresetAssociations("registry"),["GEM JR FS","GEM JR FA"]);
  assert.deepEqual(Checklist.gemPresetAssociations("gem_jr_source"),["GEM FA"]);
});
