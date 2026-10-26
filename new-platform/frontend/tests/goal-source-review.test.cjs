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


test("Actual October 25 main nightly SEC/FINANCIAL ledger exposes all 23 source gaps, including both ticker conflicts",()=>{
  const path=require("node:path");
  const source=JSON.parse(fs.readFileSync(
    path.join(__dirname,"../../../data/pdufa_source_report.json"),"utf8"));
  const daily=JSON.parse(fs.readFileSync(
    path.join(__dirname,"../../../data/daily_scan_results.json"),"utf8"));
  const saved=daily.days.find(day=>String(day.run_id)===String(source.latest_run_id));
  assert.ok(saved,"published source must match a dated nightly RESULTS run");
  const sameRun={
    date:saved.date_pacific,today:false,status:saved.status,
    runId:saved.run_id,runUrl:saved.run_url
  };
  assert.equal(saved.date_pacific,"2026-10-25");
  assert.equal(source.findings_due,1121);
  assert.equal(source.findings_unresolved,21);
  assert.equal(source.findings_conflicted,2);
  assert.equal(source.required_findings_unresolved,23);
  const matched=goalSourceReview(source,sameRun);
  assert.ok(matched,"all actual required source issues must display");
  assert.equal(matched.runId,saved.run_id);
  assert.equal(matched.total,23);
  assert.equal(matched.items.length,23);
  assert.equal(new Set(matched.items.map(item=>item.id)).size,23);
  assert.deepEqual(matched.items.filter(item=>item.status==="CONFLICT")
    .map(item=>item.eventKey).sort(),["REGISTRY:QNCX","REGISTRY:TBPH"]);
  assert.equal(matched.items.filter(item=>item.category==="SEC").length,22);
  assert.equal(matched.items.filter(item=>item.category==="FINANCIAL").length,1);
  assert.equal(matched.items.filter(item=>item.status==="REVIEW_REQUIRED").length,21);
  assert.equal(matched.items.every(item=>item.reason.length>0),true);
  assert.equal(goalSourceReview(source,{...sameRun,runId:sameRun.runId-1}),null);
});

test("SEC registry claims are accepted ONLY for their exact conflicted inventory identity",()=>{
  const registry=issue({ticker:"QNCX",event_key:"REGISTRY:QNCX",
    category:"SEC",claim:"FILINGS_INVENTORY",verification_status:"CONFLICT"});
  const matched=goalSourceReview(report([registry]),scan);
  assert.ok(matched);
  assert.equal(matched.items[0].eventKey,"REGISTRY:QNCX");
  for(const forged of [
    {...registry,category:"FINANCIAL"},
    {...registry,claim:"FINANCING_CLOSURE"},
    {...registry,verification_status:"REVIEW_REQUIRED"},
    {...registry,event_key:"REGISTRY:TBPH"},
    {...registry,event_key:"REGISTRY:QNCX:other"},
    {...registry,event_key:"REGISTRY:QNCX|PROGRAM"},
  ]){
    assert.equal(goalSourceReview(report([forged]),scan),null,
      "reject modified SEC source identity without hiding genuine conflicts");
  }
});
