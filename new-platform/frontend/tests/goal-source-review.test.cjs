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
require.extensions[".css"]=module=>{module.exports=new Proxy({}, {get:(_x,key)=>String(key)});};
const {goalSourceReview,filterSourceIssues}=require("../lib/goal-source-review.ts");
const Panel=require("../app/GoalSourceReview.tsx").default;
const runId=40057578041;
const runUrl="https://github.com/pdufa/pdufa-command-center/actions/runs/"+runId;
const scan={date:"2026-10-23",today:false,status:"PARTIAL",runId,runUrl};
const issue=(overrides={})=>({ticker:"SRPT",event_key:"SRPT|CASIMERSEN_DMD45_20270228",
  category:"SEC",claim:"FINANCING_CLOSURE",verification_status:"REVIEW_REQUIRED",
  verification_required:"YES",checked_at:"2026-10-24T03:32:10.703150+00:00",
  reason:"Closing requires a company-matched SEC document and an explicit closing date.",source_url:"",...overrides});
const report=(rows=[issue()])=>({latest_run_id:String(runId),latest_run_url:runUrl,
  execution_status:"COMPLETE",full_coverage_verified:false,
  findings_due:1121,findings_verified:995,findings_unresolved:23,
  findings_unavailable:93,findings_not_applicable:10,
  missing_required_source_families:["FDA","SEC","FINANCIAL"],
  required_findings_unresolved:23,required_issue_examples:rows});

test("Review keeps exact same-ticker programs and different claims distinct without changing the source",()=>{
  const input=report([issue(),issue({event_key:"SRPT|GOLODIRSEN_DMD53_20270228"}),
    issue({category:"FINANCIAL",claim:"CASH_AND_RUNWAY",reason:"Cash evidence needs review."})]);
  const before=JSON.stringify(input);
  const review=goalSourceReview(input,scan);
  assert.equal(review.total,23);
  assert.equal(review.runId,runId);
  assert.equal(review.items.length,3);
  assert.equal(new Set(review.items.map(row=>row.id)).size,3);
  assert.equal(review.items[1].eventKey,"SRPT|GOLODIRSEN_DMD53_20270228");
  assert.equal(review.items[0].sourceUrl,null);
  assert.equal(JSON.stringify(input),before);
  assert.deepEqual(filterSourceIssues(review.items,"FINANCIAL",""),[review.items[2]]);
  assert.deepEqual(filterSourceIssues(review.items,"ALL","golodirsen"),[review.items[1]]);
  assert.equal(filterSourceIssues(review.items,"SEC","matched SEC document").length,2);
});

test("Real SEC company-level filing conflicts do not hide the entire source issue list",async()=>{
  const qncx=issue({ticker:"QNCX",event_key:"REGISTRY:QNCX",
    claim:"FILINGS_INVENTORY",verification_status:"CONFLICT",
    reason:"SEC response does not identify the requested ticker",
    source_url:"https://data.sec.gov/submissions/CIK0001662774.json"});
  const tbph=issue({ticker:"TBPH",event_key:"REGISTRY:TBPH",
    claim:"FILINGS_INVENTORY",verification_status:"CONFLICT",
    reason:"SEC response does not identify the requested ticker",
    source_url:"https://data.sec.gov/submissions/CIK0001583107.json"});
  const dataset=report([qncx,tbph,issue()]);
  const matching=goalSourceReview(dataset,scan);
  assert.ok(matching,"Two exact registry conflicts must not cause review=null");
  assert.equal(matching.total,23);
  assert.equal(matching.items.length,3);
  assert.deepEqual(matching.items.map(x=>x.eventKey),["REGISTRY:QNCX","REGISTRY:TBPH","SRPT|CASIMERSEN_DMD45_20270228"]);
  assert.equal(matching.items.filter(x=>x.status==="CONFLICT").length,2);
  assert.equal(filterSourceIssues(matching.items,"SEC","TBPH").length,1);
  let view;
  try{
    await act(async()=>{view=create(React.createElement(Panel,{review:matching}));});
    const rendered=JSON.stringify(view.toJSON());
    assert.match(rendered,/REGISTRY:QNCX/);
    assert.match(rendered,/REGISTRY:TBPH/);
    assert.match(rendered,/CONFLICT/);
    assert.match(rendered,/bounded sample/);
    assert.equal(view.root.findAllByType("article").length,3);
  }finally{if(view)await act(async()=>view.unmount());}
});

test("Only exactly matched SEC inventory rows may use REGISTRY:TICKER identity",()=>{
  const valid=issue({ticker:"QNCX",event_key:"REGISTRY:QNCX",claim:"FILINGS_INVENTORY",
    verification_status:"CONFLICT"});
  assert.equal(goalSourceReview(report([valid]),scan)?.items.length,1);
  for(const changed of [
    {event_key:"REGISTRY:TBPH"},
    {event_key:"REGISTRY:"},
    {event_key:"REGISTRY:QNCX|FAKE"},
    {event_key:"REGISTRY:qncx"},
    {category:"FINANCIAL"},
    {claim:"FINANCING_CLOSURE"},
    {category:"FDA"},
  ]){
    assert.equal(goalSourceReview(report([{...valid,...changed}]),scan),null,
      "Invalid company identity bypass: "+JSON.stringify(changed));
  }
});

test("Review withholds another run and malformed or contradictory finding lists",()=>{
  for(const change of [
    {latest_run_id:String(runId-1)}, {latest_run_url:runUrl+"/jobs"},
    {required_findings_unresolved:null}, {required_findings_unresolved:-1},
    {required_findings_unresolved:0}, {required_issue_examples:null},
    {required_issue_examples:Array.from({length:25},(_,n)=>issue({event_key:"SRPT|PROGRAM_"+n}))},
    {required_issue_examples:[issue(),issue()]},
    {required_issue_examples:[issue({ticker:"VRTX"})]},
    {required_issue_examples:[issue({verification_status:"VERIFIED"})]},
    {required_issue_examples:[issue({verification_required:"NO"})]},
    {required_issue_examples:[issue({category:"OTHER"})]},
    {required_issue_examples:[issue({checked_at:"not a date"})]},
    {required_issue_examples:[issue({reason:""})]},
  ])assert.equal(goalSourceReview({...report(),...change},scan),null,JSON.stringify(change));
  assert.equal(goalSourceReview(report(),{...scan,status:"RUN_FAILED"}),null);
  assert.equal(goalSourceReview(report(),null),null);
  assert.equal(goalSourceReview(null,scan),null);
  const empty=goalSourceReview({...report([]),required_findings_unresolved:0},scan);
  assert.deepEqual(empty.items,[]);
  assert.equal(empty.total,0);
});

test("Only recorded safe HTTPS links are clickable; an unavailable link preserves the finding",()=>{
  const good="https://www.sec.gov/Archives/edgar/data/1579428/report.htm";
  for(const source_url of [good,"javascript:alert(1)","http://www.sec.gov/report",
    "https://name:secret@www.sec.gov/report","https://127.0.0.1/report",
    "https://service.internal/report","https://www.sec.gov:8443/report",null,""]){
    const review=goalSourceReview(report([issue({source_url})]),scan);
    assert.equal(review.items.length,1);
    assert.equal(review.items[0].sourceUrl,source_url===good?good:null);
  }
});

test("Search, source-family filter and paging expose saved findings without requests or writes",async()=>{
  const rows=Array.from({length:23},(_,n)=>issue({event_key:"SRPT|PROGRAM_"+n,
    category:n<2?"FDA":"SEC",claim:n<2?"PDUFA_TARGET":"FINANCING_CLOSURE",
    reason:n===22?"Distinct reason on the final evidence page.":"Source evidence needs review."}));
  const review=goalSourceReview(report(rows),scan);
  const oldFetch=global.fetch;
  let calls=0,view;
  global.fetch=async()=>{calls++;throw new Error("Unexpected request");};
  try{
    await act(async()=>{view=create(React.createElement(Panel,{review}));});
    assert.equal(view.root.findAllByType("article").length,10);
    const next=()=>view.root.findAllByType("button").find(x=>x.children.join("")==="Next evidence findings");
    await act(async()=>next().props.onClick());
    await act(async()=>next().props.onClick());
    assert.equal(view.root.findAllByType("article").length,3);
    assert.equal(next().props.disabled,true);
    await act(async()=>view.root.findByType("input").props.onChange({target:{value:"final evidence"}}));
    assert.equal(view.root.findAllByType("article").length,1);
    assert.match(JSON.stringify(view.toJSON()),/PROGRAM_22/);
    await act(async()=>view.root.findByType("input").props.onChange({target:{value:""}}));
    await act(async()=>view.root.findByType("select").props.onChange({target:{value:"FDA"}}));
    assert.equal(view.root.findAllByType("article").length,2);
    assert.equal(view.root.findAllByType("button").length,0);
    assert.match(view.root.findByProps({role:"status"}).children.join(""),/23 required gaps/);
    assert.equal(calls,0);
  }finally{global.fetch=oldFetch;if(view)await act(async()=>view.unmount());}
});

test("Incomplete recorded examples are labelled as a sample, while absent details are unavailable",async()=>{
  let view;
  try{
    await act(async()=>{view=create(React.createElement(Panel,{review:goalSourceReview(report(),scan)}));});
    assert.match(JSON.stringify(view.toJSON()),/bounded sample/);
    await act(async()=>view.update(React.createElement(Panel,{review:null})));
    assert.match(JSON.stringify(view.toJSON()),/details are unavailable/);
    assert.equal(view.root.findAllByType("article").length,0);
  }finally{if(view)await act(async()=>view.unmount());}
});
