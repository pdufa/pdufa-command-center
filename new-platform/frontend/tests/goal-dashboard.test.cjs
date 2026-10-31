const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {act,create}=require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of [".ts",".tsx"]) require.extensions[ext] = (mod,file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file);
require.extensions[".css"]=(mod)=>{mod.exports=new Proxy({}, {get:(_obj,key)=>String(key)});};
const {goalSummary,daysUntilReportedDate,default:GoalDashboard}=require("../app/GoalDashboard.tsx");

test("GOAL is the first top tab, immediately before SCANS, and supports deep link",()=>{
  const source=fs.readFileSync(path.join(__dirname,"../app/Workspace.tsx"),"utf8");
  const typeDeclaration=source.match(/type TopNav = ([^;]+);/);
  assert.ok(typeDeclaration, "top-navigation type is present");
  for(const name of ["GOAL","SCANS","RESULTS"]) assert.ok(typeDeclaration[1].includes(JSON.stringify(name)));
  const navigation=source.slice(source.indexOf('<div className="worktop">'));
  const firstButtons=[...navigation.matchAll(/>([A-Z]+)<\/button>/g)].slice(0,3).map(match=>match[1]);
  assert.deepEqual(firstButtons,["GOAL","SCANS","RESULTS"],"visible tab order is independent of TypeScript union ordering");
  assert.ok(source.includes('if (requested === "GOAL") { setTop("GOAL"); return; }'));
  assert.ok(source.includes('{top==="GOAL" && <GoalDashboard'));
  assert.ok(source.includes('top!=="GOAL" && <div className="workflow-counts"'));
  assert.ok(source.includes('top!=="GOAL" && <div className="workspace-update-row"'));
  assert.ok(source.includes('onOpen={(section:GoalSection)=>'));
});

test("dates use Pacific calendar with strict invalid-date filtering and 180-day boundary",()=>{
  const now=new Date("2026-10-23T20:00:00Z");
  assert.equal(daysUntilReportedDate("2026-10-23",now),0);
  assert.equal(daysUntilReportedDate("2026-10-24",now),1);
  assert.equal(daysUntilReportedDate("2026-10-22",now),-1);
  for(const date of ["2026-02-30","2026-13-01","bad",null,""]){
    assert.equal(daysUntilReportedDate(date,now),null);
  }
  const rows=[
    {id:"A",ticker:"A",drug:"A",pdufaDate:"2026-10-23",checkStatus:"REVIEW"},
    {id:"B",ticker:"B",drug:"B",pdufaDate:"2026-11-01",checkStatus:"UPCOMING"},
    {id:"C",ticker:"C",pdufaDate:"2025-10-01"},
    {id:"D",ticker:"D",pdufaDate:"2028-10-01",checkStatus:"REVIEW"},
  ];
  const result=goalSummary(rows,now);
  assert.equal(result.upcoming,2);
  assert.equal(result.review,2);
  assert.deepEqual(result.dated.map(x=>x.id),["A","B"]);
  assert.equal(goalSummary([],now).review,null);
  assert.equal(goalSummary(null,now).upcoming,null);
});

test("GOAL displays missing evidence as unavailable, never mockup counts",async()=>{
  const navigations=[];
  let renderer;
  try{
    await act(async()=>{renderer=create(React.createElement(GoalDashboard,{
      records:null,pipelineCount:null,gemJrCount:null,gemCount:null,
      sourceState:null,sourceAsOf:null,scanComplete:false,
      onOpen:section=>navigations.push(section)
    }));});
    const rendered=JSON.stringify(renderer.toJSON());
    assert.match(rendered,/GOAL · Dashboard design workspace/);
    assert.match(rendered,/Not confirmed complete/);
    assert.match(rendered,/Not verified/);
    assert.match(rendered,/Daily changes not verified/);
    assert.match(rendered,/Loading the published Pipeline/);
    assert.doesNotMatch(rendered,/11,248|348|128/);
    const buttons=renderer.root.findAllByType("button");
    await act(async()=>{buttons.find(b=>b.props.children==="Open SCANS").props.onClick();});
    await act(async()=>{buttons.find(b=>b.props.children==="View scan RESULTS").props.onClick();});
    assert.deepEqual(navigations,["SCANS","RESULTS"]);
  }finally{if(renderer)await act(async()=>renderer.unmount());}
});

test("GOAL keeps live saved totals and buttons for existing sections",async()=>{
  const navigation=[];
  const now=new Date();
  const fields=new Intl.DateTimeFormat("en-US",{timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(now);
  const part=name=>fields.find(x=>x.type===name).value;
  const today=[part("year"),part("month"),part("day")].join("-");
  const records=[{id:"TEST|A",ticker:"TEST",drug:"Test drug",indication:"Example",
    pdufaDate:today,checkStatus:"UPCOMING"}];
  let renderer;
  try{
    await act(async()=>{renderer=create(React.createElement(GoalDashboard,{
      records,pipelineCount:11795,gemJrCount:4,gemCount:2,
      sourceAsOf:"2026-10-23T20:00:00Z",sourceState:"PARTIAL",
      scanFinishedAt:"2026-10-24T03:21:00Z",scanComplete:true,
      onOpen:section=>navigation.push(section)
    }));});
    const output=JSON.stringify(renderer.toJSON());
    assert.match(output,/11,795/);
    assert.match(output,/Confirmed complete/);
    assert.match(output,/Test drug/);
    assert.doesNotMatch(output,/Saved stage members/);
    assert.doesNotMatch(output,/Existing GEM JR restrictions/);
    assert.match(output,/Pipeline/);
    const buttons=renderer.root.findAllByType("button");
    const stage=buttons.find(b=>b.props.children==="View all →");
    assert.ok(stage);
    await act(async()=>stage.props.onClick());
    await act(async()=>buttons.find(b=>b.props.children==="Edit RESTRICTIONS").props.onClick());
    assert.deepEqual(navigation,["PIPELINE","RESTRICTIONS"]);
  }finally{if(renderer)await act(async()=>renderer.unmount());}
});

test("GOAL refresh reads only the authenticated scan report and displays actual update counts",async()=>{
  const original=global.fetch;
  const calls=[];
  const payload={daily:{schema_version:1,days:[{
    date_pacific:new Intl.DateTimeFormat("en-US",{timeZone:"America/Los_Angeles",
      year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date())
      .filter(x=>["year","month","day"].includes(x.type))
      .reduce((acc,x)=>{acc[x.type]=x.value;return acc;},{}),
    run_id:40057578041,run_url:"https://github.com/pdufa/pdufa-command-center/actions/runs/40057578041",
    status:"PARTIAL",sections:{master:{new:null,updated:68},designations:{total:null}}
  }]}};
  const date=payload.daily.days[0].date_pacific;
  const dateParts=date;
  payload.daily.days[0].date_pacific=dateParts.year+"-"+dateParts.month+"-"+dateParts.day;
  payload.newFromScan={runId:40057578041,scanPacificDate:payload.daily.days[0].date_pacific,
    pipelineNewPrograms:null,pipelineChangedTrials:68,rows:[]};
  let view;
  try{
    global.fetch=async(url,init)=>{
      calls.push({url,init});
      return {ok:true,json:async()=>payload};
    };
    await act(async()=>{view=create(React.createElement(GoalDashboard,{
      records:[],pipelineCount:11795,gemJrCount:11,gemCount:6,onOpen:()=>{}
    }));});
    let content=JSON.stringify(view.toJSON());
    assert.match(content,/68/);
    assert.match(content,/Partial evidence/);
    assert.match(content,/not verified for today/);
    assert.match(content,/No individually identified new findings were published/);
    const button=view.root.findAllByType("button")
      .find(x=>x.props.children==="Refresh scan findings");
    assert.ok(button);
    await act(async()=>{button.props.onClick();});
    assert.equal(calls.length,2);
    assert.ok(calls.every(x=>x.url==="/api/published-scans" &&
      x.init.cache==="no-store" && !x.init.method));
  } finally{
    if(view)await act(async()=>view.unmount());
    global.fetch=original;
  }
});

test("GOAL desktop and phone layouts are responsive without creating separate routes",()=>{
  const css=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.module.css"),"utf8");
  assert.match(css,/grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.match(css,/\.statusRow\{grid-template-columns:1fr\}/);
  assert.match(css,/\.stageGrid\{grid-template-columns:1fr\}/);
  assert.match(css,/overflow:auto/);
  const source=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.tsx"),"utf8");
  assert.match(source,/fetch\("\/api\/published-scans"/);
  assert.doesNotMatch(source,/localStorage|sessionStorage|method: ?"POST"|runScan|ORDER_EXECUTION/);
});
