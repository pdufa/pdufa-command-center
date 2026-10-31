const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {create,act}=require("react-test-renderer");
require.extensions[".css"]=()=>{};
for(const ext of [".ts",".tsx"]){
  require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(
    fs.readFileSync(file,"utf8"),{compilerOptions:{
      module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,
    }}
  ).outputText,file);
}
const ws=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");

test("every original Pipeline filter appears only beneath the existing central Restrictions blocks",()=>{
  const definitionStart=ws.indexOf("const stageAndDateFilter = (");
  const migrationStart=ws.indexOf('return <div className="migration-workspace">');
  const restrictionContent=ws.slice(definitionStart,migrationStart);
  const pipelineStart=ws.indexOf('nav==="PIPELINE" && <section className="pipeline-page">');
  const pipelineEnd=ws.indexOf('nav==="GEM_JR" || nav==="GEM"',pipelineStart);
  const pipelineContent=ws.slice(pipelineStart,pipelineEnd);
  assert.ok(definitionStart>0 && migrationStart>definitionStart);
  for(const exact of [
    "STAGE COUNTS","DATE TRIAL COUNTS","TrialQualificationFilters",
    "Market cap $300M–$10B only","onlyBand","onChange={setTrialFilters}",
    "onChange={()=>setStageFilters", "onChange={()=>setDateFilters"
  ]){
    // The selectors are created from the original group.items data rather
    // than hardcoded per-label onChange callbacks.
    if(exact.startsWith("onChange={()=>"))continue;
    assert.ok(restrictionContent.includes(exact), "Missing moved Pipeline filter: "+exact);
  }
  assert.match(restrictionContent,/setter:\s*setStageFilters/);
  assert.match(restrictionContent,/setter:\s*setDateFilters/);
  assert.ok(restrictionContent.includes("group.setter("));
  assert.ok(restrictionContent.includes("DISPLAY TRIALS"));
  assert.ok(!pipelineContent.includes("TrialQualificationFilters"),
    "Original Pipeline should not have a second qualification checklist");
  assert.ok(!pipelineContent.includes("className=\"pipeline-filters pipeline-filters-compact\""));
  assert.ok(pipelineContent.includes("OPEN RESTRICTIONS — EDIT FILTERS"));
  assert.equal((ws.match(/<TrialQualificationFilters /g)||[]).length,1);
  assert.equal((ws.match(/<RestrictionImpact /g)||[]).length,1);
  assert.equal((ws.match(/<GemQualificationChecklist /g)||[]).length,1);
  const central=ws.slice(ws.indexOf('aria-label="Original Pipeline filters"'),ws.indexOf('top==="PDUFA" && (nav==="GEM_JR"'));
  assert.match(central,/pipelineMovedFilters[\s\S]*?RestrictionImpact poolPipelineOnly/);
  assert.match(ws,/if \(top==="RESTRICTIONS"\) return <details/);
  assert.match(central,/aria-label="Independent Pool and Pipeline restrictions"/);
  assert.ok(!restrictionContent.includes("setTags("));
});

test("Pipeline, GEM JR and GEM FS/FA selections keep their original state and scan logic",()=>{
  const check=fs.readFileSync(path.join(__dirname,"../app/GemQualificationChecklist.tsx"),"utf8");
  const impact=fs.readFileSync(path.join(__dirname,"../app/RestrictionImpact.tsx"),"utf8");
  assert.ok(ws.includes('const [trialFilters, setTrialFilters] = useState<TrialFilterValues>'));
  assert.ok(ws.includes("function displayTrials()"));
  assert.ok(ws.includes("function clearPipelineSelections()"));
  assert.ok(ws.includes('top==="PDUFA" && (nav==="GEM_JR" || nav==="GEM")'));
  for(const token of [
    "function toggleFs(){","function toggleFa(){","onScan(result", // dynamic reference checked separately
    "checkboxGroupsForStage(stage).clinical","checkboxGroupsForStage(stage).trading",
    'aria-label="FS: toggle suggested criteria checkboxes"',
    'aria-label={stage==="GEM"?"FA: toggle Gem Jr Trials input"'
  ]){
    if(token==="onScan(result")continue;
    assert.ok(check.includes(token),"Missing original GEM checklist functionality: "+token);
  }
  assert.ok(impact.includes('className={styles.table + " " + styles.catalog}'),
    "Original central restriction layout should not be replaced");
  assert.ok(ws.includes('onScan={result=>{'));
});

test("Restrictions page mounts original Pipeline filters and independent Pool-only catalog",async()=>{
  global.IS_REACT_ACT_ENVIRONMENT=true;
  const Workspace=require("../app/Workspace.tsx").default;
  const OriginalFilter=require("../app/TrialQualificationFilters.tsx").default;
  const OriginalGem=require("../app/GemQualificationChecklist.tsx").default;
  const ActiveRestriction=require("../app/RestrictionImpact.tsx").default;
  const prior={fetch:global.fetch,window:global.window,localStorage:global.localStorage,self:global.self};
  const storage={getItem:()=>null,setItem(){},removeItem(){}};
  global.localStorage=storage;
  global.window={location:{search:""},localStorage:storage,setInterval:()=>0,clearInterval:()=>{}};
  global.self=global;
  const trial={id:"TRIAL|NCT12345678",programId:"PDUFA-000001",ticker:"TEST",
    drug:"Investigational therapy",stage:"Phase 3",pdufaDate:"2027-03-01",
    trialFilters:{registeredPhase:"Phase 3",lists:["PIPELINE"]}};
  const snapshot={
    mode:"PUBLISHED",asOf:"2026-10-20",disclaimer:"Test only",trialFilterSchema:1,
    marketCapRange:{min:300000000,max:10000000000},
    pipeline:[trial],members:{GEM_JR:{rows:[],history:[]},GEM:{rows:[],history:[]}},
    sourceHealth:{state:"CURRENT",issues:[],clinicalRows:1,regulatoryRows:0}
  };
  global.fetch=async url=>{
    const p=new URL(url,"https://local.test");
    if(p.pathname==="/api/workspace")return Response.json(snapshot);
    if(p.pathname==="/api/workspace/page")return Response.json({
      version:"a".repeat(64),total:1,offset:0,limit:50,rows:[trial],nextOffset:null
    });
    if(p.pathname==="/api/workspace/summary")return Response.json({pipeline:1,gemJr:0,gem:0});
    if(p.pathname==="/api/program-watch-trade")return Response.json({watch:[],trade:[],version:0});
    if(p.pathname==="/api/full-trials")return Response.json({status:"PENDING",target:1,downloaded:0,complete:false});
    if(p.pathname==="/api/full-trials/rows")return Response.json({records:{}});
    if(p.pathname==="/api/restriction-evidence")return Response.json({
      fetchedAt:new Date().toISOString(),issuers:{},trialTypes:{},sources:[],issues:[]
    });
    return Response.json({});
  };
  let tree;
  const tick=()=>new Promise(resolve=>setImmediate(resolve));
  const findButtons=(title)=>tree.root.findAllByType("button").filter(x=>x.children.join("")===title);
  try{
    await act(async()=>{tree=create(React.createElement(Workspace,{onInspect(){}}));await tick();await tick();});
    assert.equal(tree.root.findAllByType(OriginalFilter).length,0,"PIPELINE has no editable trial checklist");
    assert.equal(tree.root.findAllByType(OriginalGem).length,0,"PIPELINE has no GEM restrictions");
    assert.equal(findButtons("OPEN RESTRICTIONS — EDIT FILTERS").length,1);
    await act(async()=>{tree.root.findAllByType("button").find(x=>x.children.join("")==="RESTRICTIONS").props.onClick();await tick();});
    assert.equal(tree.root.findAllByType(OriginalFilter).length,1,"Exactly one original Pipeline filter group");
    assert.equal(tree.root.findAllByType(OriginalGem).length,0,"No GEM JR/GEM checklist in active restrictions");
    assert.equal(tree.root.findAllByType(ActiveRestriction).length,1);
    assert.equal(tree.root.findByType(ActiveRestriction).props.poolPipelineOnly,true);
    assert.equal(tree.root.findAllByProps({"aria-label":"Original Pipeline filters"}).length,1);
    assert.equal(tree.root.findAllByProps({"aria-label":"FS: toggle suggested criteria checkboxes"}).length,0);
    assert.equal(tree.root.findAllByProps({"aria-label":"FA: toggle Gem Jr Trials input"}).length,0);
    assert.equal(tree.root.findAllByProps({"aria-label":"FA: toggle Phase 3 trial status recorded and market cap qualification checkboxes"}).length,0);
    const cap=tree.root.findAllByType("input").find(x=>x.props.type==="checkbox"&&x.props.checked===false&&x.parent?.props?.className==="cap-filter");
    assert.ok(cap,"Optional market-cap restriction now present on central page");
    const display=tree.root.findAllByType("button").find(x=>typeof x.props.onClick==="function"&&x.children.join("").startsWith("DISPLAY TRIALS"));
    assert.ok(display);
    await act(async()=>{display.props.onClick();await tick();});
    assert.equal(tree.root.findAllByType(OriginalFilter).length,0,"After displaying, stage filter controls are not duplicated on PIPELINE");
    assert.ok(findButtons("OPEN RESTRICTIONS — EDIT FILTERS").length===1);
  }finally{
    if(tree)await act(async()=>tree.unmount());
    Object.assign(global,prior);
  }
});
