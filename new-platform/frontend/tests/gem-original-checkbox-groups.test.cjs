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
const {checkboxGroupsForStage,resolveGemJrSource}=Checklist;
function page(stage){
  return renderToStaticMarkup(React.createElement(Checklist.default,{
    stage,pipeline:[],asOf:"2026-10-18",stageTotal:0,gemJrScan:null,gemJrSavedRows:[],
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
  assert.match(html,/SCAN GEM JR/);
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
  assert.doesNotMatch(html,/aria-label="FA: toggle/);
  assert.match(html,/aria-label="FS: toggle suggested criteria checkboxes"/);
  assert.match(html,/TOTAL COMBINED RESULTS/);
  assert.match(html,/SCAN GEM/);
  assert.equal((clinical+trading).match(/type="checkbox"/g)?.length,12);
});

test("Original FS, FA, and combined AND scan evaluator remain in place",()=>{
  const content=fs.readFileSync(path.join(__dirname,"../app/GemQualificationChecklist.tsx"),"utf8");
  for(const unchanged of ["const suggestedByStage:","const FA_CRITERIA=",
    "const GEM_JR_OWNED_CRITERIA=","const sourceRows=useGemJrSource?gemJrRows:pipeline;",
    "const liveCounts=useMemo(", "function toggleFs(){", "function toggleFa(){",
    "function toggle(key:string){", "for(const [, , evaluate] of chosen)",
    "for(let i=0;i<chosen.length;i++)", "result.audits.length"]){
    assert.ok(content.includes(unchanged),unchanged+" changed unexpectedly");
  }
});

test("GEM's optional GEM JR input uses the real published 11 program memberships before a scan",()=>{
  const rows=Array.from({length:11},(_,i)=>({
    id:"APPLICATION|PROGRAM-"+i,ticker:"TICK"+i,drug:"Distinct program "+i
  }));
  const result=resolveGemJrSource(null,rows);
  assert.equal(result.sourceKind,"GEM_JR_SAVED");
  assert.equal(result.rows.length,11);
  assert.equal(result.reviewIds.size,11);
  assert.equal(result.scanAvailable,false);
  assert.match(result.label,/not re-scanned/);
  assert.deepEqual(result.rows.map(x=>x.id),rows.map(x=>x.id));
});

test("If GEM JR scan exists, use its exact filtered set rather than merging all saved programs",()=>{
  const saved=Array.from({length:11},(_,i)=>({id:"SAVED|"+i,ticker:"SAVE"+i}));
  const passed={id:"APP|PASS",ticker:"GOOD"};
  const review={id:"APP|REVIEW",ticker:"VERIFY"};
  const scan={passes:[passed],needsReview:[review],fails:[{id:"APP|FAIL",ticker:"FAIL"}]};
  const result=resolveGemJrSource(scan,saved);
  assert.equal(result.sourceKind,"GEM_JR");
  assert.deepEqual(result.rows,[passed,review]);
  assert.deepEqual([...result.reviewIds],["APP|REVIEW"]);
  assert.equal(result.scanAvailable,true);
  assert.equal(result.rows.some(row=>row.id.startsWith("SAVED|")),false);
});

test("Absent both JR sources, GEM never fabricates a candidate list",()=>{
  const result=resolveGemJrSource(null,[]);
  assert.deepEqual(result.rows,[]);
  assert.equal(result.reviewIds.size,0);
});
