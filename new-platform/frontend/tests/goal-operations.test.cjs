const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
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
const {goalOperationalState}=require("../lib/goal-operations.ts");
const Panel=require("../app/GoalOperationsPanel.tsx").default;
const mockScan={date:"2026-10-23",today:true,status:"PARTIAL",runId:40057578041,
  runUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/40057578041"};
const audit=()=>({
  generated_at_utc:new Date().toISOString(),status:"REVIEW_REQUIRED",
  source_scan:{workflow:"pdufa-overnight-sequential.yml",run_id:40057578041,conclusion:"success"},
  counts:{input_tests:4,data_gaps:3,reviews:1,models_mapped:0,overlaps:0},
  checks:[
    {Test:"Trade score",Status:"DATA GAP",Result:"Missing", "Why it matters":"Evidence"},
    {Test:"Public PoA",Status:"DATA GAP",Result:"Missing", "Why it matters":"Evidence"},
    {Test:"FDA probability",Status:"DATA GAP",Result:"Missing", "Why it matters":"Evidence"},
    {Test:"Finance gate",Status:"REVIEW",Result:"Missing", "Why it matters":"Evidence"}
  ],
  provenance_note:"Saved snapshots only."
});

test("GOAL does not confuse successful scan job with verified FDA/source completeness",()=>{
  const state=goalOperationalState(mockScan,audit());
  assert.equal(state.scan.concern,true);
  assert.equal(state.scan.label,"Partial published evidence");
  assert.equal(state.scoring.gaps,4);
  assert.equal(state.scoring.concern,true);
  assert.match(state.scoring.detail,/Saved stock\/FDA\/financing snapshots only/);
  assert.match(state.scan.url,/\/actions\/runs\/40057578041$/);
});

test("Missing or stale audit cannot be treated as score completion",()=>{
  assert.equal(goalOperationalState(null,null).scoring.concern,true);
  assert.equal(goalOperationalState(null,null).scan.concern,true);
  const stale=audit();
  stale.generated_at_utc="2025-01-01T00:00:00Z";
  const state=goalOperationalState(mockScan,stale,Date.parse("2026-10-24T04:00:00Z"));
  assert.match(state.scoring.detail,/older than 48 hours/);
  assert.equal(state.scoring.concern,true);
  const clear=audit();
  clear.status="NO_INPUT_GAPS_FOUND";
  clear.counts.data_gaps=0;
  clear.counts.reviews=0;
  clear.checks=clear.checks.map(check=>({...check,Status:"OBSERVED"}));
  assert.equal(goalOperationalState({...mockScan,status:"COMPLETE"},clear).scoring.concern,false);
  assert.equal(goalOperationalState({...mockScan,status:"COMPLETE"},clear).scan.concern,false);
});

test("Operational panel lists actual blockers, never starts scans or claims Drive cron",async()=>{
  let view,opened=[];
  try{
    await act(async()=>{view=create(React.createElement(Panel,{
      scan:mockScan,scoring:audit(),loading:false,onOpenScans:()=>opened.push("SCANS")
    }));});
    const output=JSON.stringify(view.toJSON());
    assert.match(output,/Partial published evidence/);
    assert.match(output,/4 scoring-input checks need attention/);
    assert.match(output,/not a Google Drive data backup/);
    assert.match(output,/Recurring backup not verified/);
    assert.match(output,/Delivery not verified/);
    assert.match(output,/Alpaca HTTP 401/);
    const links=view.root.findAllByType("a");
    assert.ok(links.length>=2);
    assert.ok(links.every(x=>x.props.rel==="noopener noreferrer"));
    const button=view.root.findAllByType("button").find(x=>x.props.children==="Inspect SCANS →");
    await act(async()=>button.props.onClick());
    assert.deepEqual(opened,["SCANS"]);
  }finally{if(view)await act(async()=>view.unmount());}
});

test("GOAL operations update from authenticated saved report and mobile rendering",()=>{
  const source=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.tsx"),"utf8");
  const panel=fs.readFileSync(path.join(__dirname,"../app/GoalOperationsPanel.tsx"),"utf8");
  const css=fs.readFileSync(path.join(__dirname,"../app/GoalOperationsPanel.module.css"),"utf8");
  assert.match(source,/setScoringReport\(scoring\)/);
  assert.match(source,/setScoringReport\(null\)/);
  assert.match(source,/GoalOperationsPanel scan=\{scanView\} scoring=\{scoringReport\}/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.doesNotMatch(panel,/fetch\(|method: ?["']POST|dispatchWorkflow\(|localStorage\.setItem|Twilio\.send/i);
});
