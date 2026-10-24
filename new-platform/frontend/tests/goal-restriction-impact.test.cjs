const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,
  }}).outputText,file);
require.extensions[".css"]=m=>{m.exports=new Proxy({},{get:(_x,key)=>String(key)});};
const catalog=require("../lib/restriction-catalog.ts");
const {fullGoalRestrictionEvidence,calculateGoalRestrictionImpact}=require("../lib/goal-restriction-impact.ts");
const GoalDashboard=require("../app/GoalDashboard.tsx").default;
const sourceName=["company_registry.csv","phase_pipeline_market_caps.csv","all_phase_trials.csv"];
const evidence=()=>({
  fetchedAt:"2026-10-23T20:00:00Z",issues:[],sources:sourceName.map(name=>({
    name,rows:3,url:"https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/"+name,
  })),
  issuers:{
    AA:{listed:"PASS",marketCap:500e6,capAsOf:"2026-10-23"},
    BB:{listed:"FAIL",marketCap:null,capAsOf:"2026-10-23"},
    CC:{listed:"UNKNOWN",marketCap:null,capAsOf:"2026-10-23"},
  },
  trialTypes:{}
});
const baseline=[
  {id:"TRIAL|NCT00000001",ticker:"AA",stage:"Phase 3"},
  {id:"TRIAL|NCT00000002",ticker:"BB",stage:"Phase 2"},
  {id:"TRIAL|NCT00000003",ticker:"CC"},
];
const empty=()=>catalog.defaultCatalogEntries().map(x=>({...x,enabled:false,
  stage:"",priority:"",additionalStages:[],stagePriorities:{}}));

test("GOAL stage impact independently applies each stage's own existing rules",()=>{
  let rules=empty();
  rules=catalog.insertRestrictionIntoList(rules,"public","PIPELINE",0);
  rules=catalog.insertRestrictionIntoList(rules,"phase","GEM_JR",0);
  rules=catalog.insertRestrictionIntoList(rules,"public","GEM",0);
  const before=structuredClone(rules);
  const report=calculateGoalRestrictionImpact(baseline,rules,evidence(),"2026-10-23");
  assert.equal(report.total,3);
  for(const stage of ["PIPELINE","GEM_JR","GEM"]){
    assert.equal(report.stages[stage].total,3,stage);
    assert.equal(report.stages[stage].steps.length,1,stage);
    assert.equal(report.stages[stage].steps[0].before,3,stage);
    assert.equal(report.stages[stage].steps[0].excluded,1,stage);
    assert.equal(report.stages[stage].steps[0].after,2,stage);
    assert.equal(report.stages[stage].remaining,2,stage);
    assert.equal(report.stages[stage].pending,1,stage);
    assert.equal(report.stages[stage].passed,1,stage);
  }
  assert.deepEqual(rules,before);
});
test("entry-time market cap remains UNKNOWN even when present-day caps exist",()=>{
  let rules=empty();
  rules=catalog.insertRestrictionIntoList(rules,"minCap","PIPELINE",0);
  rules=catalog.insertRestrictionIntoList(rules,"public","PIPELINE",1);
  const report=calculateGoalRestrictionImpact(baseline,rules,evidence(),"2026-10-23");
  const stage=report.stages.PIPELINE;
  assert.equal(stage.steps.length,2);
  assert.equal(stage.steps[0].before,3);
  assert.equal(stage.steps[0].excluded,0);
  assert.equal(stage.steps[0].after,3);
  assert.equal(stage.steps[0].pending,3);
  assert.equal(stage.steps[1].before,3);
  assert.equal(stage.steps[1].excluded,1);
  assert.equal(stage.steps[1].after,2);
  assert.equal(stage.pending,2);
  assert.equal(stage.passed,0);
  assert.equal(stage.remaining,stage.pending+stage.passed);
});
test("empty stage rules retain all programs with no fabricated exclusions",()=>{
  const report=calculateGoalRestrictionImpact(baseline,empty(),evidence(),"2026-10-23");
  for(const stage of ["PIPELINE","GEM_JR","GEM"]){
    assert.deepEqual(report.stages[stage].steps,[]);
    assert.equal(report.stages[stage].remaining,3);
    assert.equal(report.stages[stage].excluded,0);
  }
});
test("partial or malformed source evidence never produces numeric impacts",()=>{
  const good=evidence();
  assert.equal(fullGoalRestrictionEvidence(good),true);
  for(const mutate of [
    x=>x.sources.pop(),
    x=>x.sources[1].url="https://evil.example/market.csv",
    x=>x.sources[1].rows=0,
    x=>x.issues.push("cap data unavailable"),
    x=>x.trialTypes=[],
    x=>x.fetchedAt="not a date",
  ]){
    const bad=structuredClone(good);mutate(bad);
    assert.equal(fullGoalRestrictionEvidence(bad),false);
    assert.throws(()=>calculateGoalRestrictionImpact(baseline,empty(),bad,"2026-10-23"));
  }
  assert.throws(()=>calculateGoalRestrictionImpact([],empty(),good,"2026-10-23"));
});
test("GOAL impact button runs read-only GET on demand and shows verified stage counts",async()=>{
  const oldFetch=global.fetch,calls=[];
  const rules=catalog.insertRestrictionIntoList(empty(),"public","PIPELINE",0);
  const restrictions=require("../lib/goal-restrictions.ts").goalRestrictionSummaries(rules);
  global.fetch=async(url,options)=>{
    calls.push({url,options});
    if(url==="/api/restriction-evidence")return {ok:true,json:async()=>evidence()};
    return {ok:false,status:503,json:async()=>({})};
  };
  let view;
  try{
    await act(async()=>{view=create(React.createElement(GoalDashboard,{
      records:baseline,impactRows:baseline,impactEntries:rules,
      restrictions,pipelineCount:3,gemJrCount:0,gemCount:0,
      sourceAsOf:"2026-10-23",onOpen:()=>{}
    }));});
    assert.equal(calls.filter(x=>x.url==="/api/restriction-evidence").length,0,
      "Restriction calculation never runs until explicitly requested");
    const button=view.root.findAllByType("button").find(x=>x.props.children==="CALCULATE SAVED IMPACT");
    assert.ok(button);
    await act(async()=>{await button.props.onClick();});
    assert.equal(calls.filter(x=>x.url==="/api/restriction-evidence").length,1);
    const fetchOptions=calls.find(x=>x.url==="/api/restriction-evidence").options;
    assert.equal(fetchOptions.cache,"no-store");
    assert.equal(fetchOptions.method,undefined);
    const impact=view.root.findByProps({"aria-label":"Pipeline restriction impact"});
    const text=JSON.stringify(view.toJSON());
    assert.match(text,/Starting baseline/);
    assert.match(text,/Confirmed excluded/);
    assert.match(text,/Unknown|require more evidence|pending/i);
    assert.match(text,/3/);
  }finally{if(view)await act(async()=>view.unmount());global.fetch=oldFetch;}
});
test("GOAL cannot claim before/after counts after source outage",async()=>{
  const old=global.fetch;global.fetch=async()=>({ok:false,status:503,json:async()=>({})});
  const rules=empty();let view;
  try{
    await act(async()=>{view=create(React.createElement(GoalDashboard,{
      records:baseline,impactRows:baseline,impactEntries:rules,
      pipelineCount:3,gemJrCount:0,gemCount:0,sourceAsOf:"2026-10-23",
      onOpen:()=>{}
    }));});
    const button=view.root.findAllByType("button").find(x=>x.props.children==="CALCULATE SAVED IMPACT");
    await act(async()=>{await button.props.onClick();});
    assert.match(JSON.stringify(view.toJSON()),/Impact not verified/);
    assert.equal(view.root.findAllByProps({"aria-label":"Pipeline restriction impact"}).length,0);
  }finally{if(view)await act(async()=>view.unmount());global.fetch=old;}
});


test("excluded IDs are the exact newly removed saved programs, never ticker-based joins",()=>{
  let rules=empty();
  rules=catalog.insertRestrictionIntoList(rules,"public","PIPELINE",0);
  rules=catalog.insertRestrictionIntoList(rules,"phase","PIPELINE",1);
  const rows=[
    {id:"TRIAL|NCT00000001",programId:"PDUFA-000001",ticker:"AA",drug:"Drug A",stage:"Phase 3"},
    {id:"TRIAL|NCT00000002",programId:"PDUFA-000002",ticker:"BB",drug:"Drug B",stage:"Phase 2"},
    {id:"TRIAL|NCT00000003",programId:"PDUFA-000003",ticker:"CC",stage:"Phase 3"},
    {id:"TRIAL|NCT00000004",programId:"PDUFA-000004",ticker:"AA",drug:"Drug D",stage:"Phase 2"},
  ];
  const previous=structuredClone(rows),originalRules=structuredClone(rules);
  const report=calculateGoalRestrictionImpact(rows,rules,evidence(),"2026-10-23");
  const steps=report.stages.PIPELINE.steps;
  assert.equal(steps[0].excluded,1);
  assert.deepEqual(steps[0].excludedPrograms.map(p=>p.id),["TRIAL|NCT00000002"]);
  assert.deepEqual(steps[0].excludedPrograms.map(p=>p.programId),["PDUFA-000002"]);
  assert.equal(steps[0].excludedPrograms[0].nctId,"NCT00000002");
  assert.equal(steps[1].excluded,1,"Phase 2 BB was already removed; AA's Phase 2 record is separate");
  assert.deepEqual(steps[1].excludedPrograms.map(p=>p.id),["TRIAL|NCT00000004"]);
  assert.equal(report.stages.PIPELINE.excluded,2);
  assert.equal(report.stages.PIPELINE.pending,1);
  assert.equal(report.stages.PIPELINE.remaining,2);
  for(const step of steps)assert.equal(step.excludedPrograms.length,step.excluded);
  assert.deepEqual(rows,previous);
  assert.deepEqual(rules,originalRules);
});

test("GOAL's clicked exclusion drilldown searches exact IDs and paginates all excluded programs",async()=>{
  let rules=catalog.insertRestrictionIntoList(empty(),"public","PIPELINE",0);
  const restrictions=require("../lib/goal-restrictions.ts").goalRestrictionSummaries(rules);
  const many=[{id:"TRIAL|NCT90000000",programId:"PDUFA-900000",ticker:"AA",drug:"Retained",
    stage:"Phase 3"},...Array.from({length:27},(_,i)=>{
      const nct="NCT"+String(i+1).padStart(8,"0");
      return {id:"TRIAL|"+nct,programId:"PDUFA-"+String(i+1).padStart(6,"0"),
        nctId:nct,ticker:"BB",drug:i===26?"Distinct patient trial":"Other therapy",
        indication:"Test indication",stage:"Phase 2"};
    })];
  const old=global.fetch;
  global.fetch=async url=>url==="/api/restriction-evidence"
    ? {ok:true,json:async()=>evidence()}
    : {ok:false,status:503,json:async()=>({})};
  let view;
  try{
    await act(async()=>{view=create(React.createElement(GoalDashboard,{
      records:many,impactRows:many,impactEntries:rules,restrictions,
      pipelineCount:28,gemJrCount:0,gemCount:0,
      sourceAsOf:"2026-10-23",onOpen:()=>{}
    }));});
    assert.equal(view.root.findAllByProps({"aria-label":"Pipeline excluded programs for Publicly traded company"}).length,0);
    const calc=view.root.findAllByType("button").find(x=>x.props.children==="CALCULATE SAVED IMPACT");
    await act(async()=>await calc.props.onClick());
    const open=view.root.findAllByType("button").find(x=>
      x.props["aria-label"]==="View 27 excluded programs for Pipeline rule Publicly traded company");
    assert.ok(open);
    await act(async()=>open.props.onClick());
    const detail=view.root.findByProps({"aria-label":"Pipeline excluded programs for Publicly traded company"});
    assert.equal(detail.findAllByType("tbody")[0].findAllByType("tr").length,20);
    assert.deepEqual(detail.findByProps({"aria-label":"Excluded programs pages"})
      .findByType("span").props.children,["Page ",1," of ",2]);
    const next=detail.findAllByType("button").find(x=>x.props.children==="Next →");
    await act(async()=>next.props.onClick());
    assert.equal(detail.findAllByType("tbody")[0].findAllByType("tr").length,7);
    assert.match(JSON.stringify(view.toJSON()),/Distinct patient trial/);
    const input=detail.findByType("input");
    await act(async()=>input.props.onChange({target:{value:"PDUFA-000027"}}));
    assert.equal(detail.findAllByType("tbody")[0].findAllByType("tr").length,1);
    assert.match(JSON.stringify(view.toJSON()),/NCT00000027/);
    assert.doesNotMatch(JSON.stringify(view.toJSON()),/NCT00000026/);
    const link=detail.findAllByType("a")[0];
    assert.equal(link.props.href,"https://clinicaltrials.gov/study/NCT00000027");
    assert.equal(link.props.rel,"noopener noreferrer");
    const close=detail.findAllByType("button").find(x=>x.props.children==="Close details");
    await act(async()=>close.props.onClick());
    assert.equal(view.root.findAllByProps({"aria-label":"Pipeline excluded programs for Publicly traded company"}).length,0);
    assert.equal(many.length,28,"Viewing must not modify source programs");
  }finally{
    if(view)await act(async()=>view.unmount());
    global.fetch=old;
  }
});

test("missing permanent IDs are declared missing, without inventing ticker joins",()=>{
  const rules=catalog.insertRestrictionIntoList(empty(),"public","PIPELINE",0);
  const rows=[{id:"TRIAL|NCT01234567",ticker:"BB",drug:"Test",nctId:"NCT01234567"}];
  const result=calculateGoalRestrictionImpact(rows,rules,evidence(),"2026-10-23");
  const excluded=result.stages.PIPELINE.steps[0].excludedPrograms[0];
  assert.equal(excluded.id,"TRIAL|NCT01234567");
  assert.equal(excluded.programId,null);
  assert.equal(excluded.nctId,"NCT01234567");
  assert.equal(excluded.ticker,"BB");
});


test("GOAL pending IDs are cumulative UNKNOWN survivors, never confirmed excluded trials",()=>{
  let rules=empty();
  rules=catalog.insertRestrictionIntoList(rules,"public","PIPELINE",0);
  rules=catalog.insertRestrictionIntoList(rules,"phase","PIPELINE",1);
  const rows=[
    {id:"TRIAL|NCT00000001",programId:"PDUFA-000001",ticker:"AA",stage:"Phase 3"},
    {id:"TRIAL|NCT00000002",programId:"PDUFA-000002",ticker:"BB",stage:"Phase 2"},
    {id:"TRIAL|NCT00000003",programId:"PDUFA-000003",ticker:"CC"},
  ];
  const ruleCopy=structuredClone(rules);
  const report=calculateGoalRestrictionImpact(rows,rules,evidence(),"2026-10-23");
  for(const step of report.stages.PIPELINE.steps){
    assert.equal(step.pending,1);
    assert.deepEqual(step.pendingPrograms.map(x=>x.id),["TRIAL|NCT00000003"]);
    assert.deepEqual(step.excludedPrograms.map(x=>x.id),
      step.id==="public"?["TRIAL|NCT00000002"]:[]);
    assert.equal(step.pendingPrograms.length,step.pending);
    assert.ok(!step.pendingPrograms.some(p=>step.excludedPrograms.some(x=>x.id===p.id)));
  }
  assert.deepEqual(ruleCopy,rules);
});

test("legacy catalog impact keeps pending ID capture opt-in and outcome unchanged",()=>{
  let rules=catalog.insertRestrictionIntoList(empty(),"public","PIPELINE",0);
  const settings=require("../lib/restriction-impact.ts").defaultRestrictionSettings();
  const legacy=catalog.calculateCatalogImpact(baseline,rules,settings,evidence(),"2026-10-23");
  const observed=legacy.steps.get("public");
  assert.equal(observed.pending,1);
  assert.equal(observed.pendingIds,undefined);
  assert.equal(observed.newlyExcluded,1);
  const inspect=catalog.calculateCatalogImpact(baseline,rules,settings,evidence(),"2026-10-23",true);
  assert.deepEqual([...inspect.steps.get("public").pendingIds],["TRIAL|NCT00000003"]);
  assert.equal(inspect.steps.get("public").pending,observed.pending);
});

test("GOAL pending drilldown reveals only source-matched UNKNOWN rows, with exact IDs",async()=>{
  const rules=catalog.insertRestrictionIntoList(empty(),"public","PIPELINE",0);
  const restrictions=require("../lib/goal-restrictions.ts").goalRestrictionSummaries(rules);
  const old=global.fetch;
  global.fetch=async url=>url==="/api/restriction-evidence"
    ? {ok:true,json:async()=>evidence()}
    : {ok:false,status:503,json:async()=>({})};
  let view;
  try{
    await act(async()=>{view=create(React.createElement(GoalDashboard,{
      records:baseline,impactRows:baseline,impactEntries:rules,restrictions,
      pipelineCount:3,gemJrCount:0,gemCount:0,sourceAsOf:"2026-10-23",onOpen:()=>{}
    }));});
    const calculate=view.root.findAllByType("button").find(b=>b.props.children==="CALCULATE SAVED IMPACT");
    await act(async()=>await calculate.props.onClick());
    const pending=view.root.findAllByType("button").find(b=>
      b.props["aria-label"]==="View 1 pending programs after Pipeline rule Publicly traded company");
    assert.ok(pending);
    await act(async()=>pending.props.onClick());
    const details=view.root.findByProps({"aria-label":"Pipeline pending programs after Publicly traded company"});
    assert.match(JSON.stringify(view.toJSON()),/retained with UNKNOWN evidence/);
    const tr=details.findByType("tbody").findAllByType("tr");
    assert.equal(tr.length,1);
    assert.match(JSON.stringify(view.toJSON()),/TRIAL\|NCT00000003/);
    assert.doesNotMatch(JSON.stringify(tr[0].children),/TRIAL\|NCT00000002/);
    assert.ok(details.findAllByType("button").some(b=>b.props.children==="Export pending CSV"));
    await act(async()=>pending.props.onClick());
    assert.equal(view.root.findAllByProps({"aria-label":"Pipeline pending programs after Publicly traded company"}).length,0);
  } finally{
    if(view)await act(async()=>view.unmount());
    global.fetch=old;
  }
});

test("GOAL CSV export retains original IDs, distinguishes pending from excluded, and escapes formulas",()=>{
  const {impactSummaryCsv,impactProgramCsv}=require("../lib/goal-impact-export.ts");
  const rules=catalog.insertRestrictionIntoList(empty(),"public","PIPELINE",0);
  const rows=[
    {id:"TRIAL|NCT00000001",programId:"PDUFA-000001",ticker:"AA",drug:"Safe source"},
    {id:"TRIAL|NCT00000002",programId:"PDUFA-000002",ticker:"BB",drug:'=HYPERLINK("url")'},
    {id:"TRIAL|NCT00000003",programId:"PDUFA-000003",ticker:"CC",drug:"Unknown source"},
  ];
  const report=calculateGoalRestrictionImpact(rows,rules,evidence(),"2026-10-23");
  const summary=impactSummaryCsv(report);
  assert.match(summary,/Saved source as of/);
  assert.match(summary,/READ_ONLY_SAVED_SCREENING/);
  const excluded=impactProgramCsv(report,"PIPELINE","public","EXCLUDED");
  const pending=impactProgramCsv(report,"PIPELINE","public","PENDING");
  assert.match(excluded,/PDUFA-000002/);
  assert.match(excluded,/TRIAL\|NCT00000002/);
  assert.match(excluded,/'=HYPERLINK\(""url""\)/);
  assert.doesNotMatch(excluded,/PDUFA-000003/);
  assert.match(pending,/PDUFA-000003/);
  assert.doesNotMatch(pending,/PDUFA-000002/);
  assert.match(excluded,/EXCLUDED/);
  assert.match(pending,/PENDING/);
  assert.throws(()=>impactProgramCsv(report,"PIPELINE","unknown","PENDING"));
  assert.ok(excluded.startsWith("\uFEFF"));
});
