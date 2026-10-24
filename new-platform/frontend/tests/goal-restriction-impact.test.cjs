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
