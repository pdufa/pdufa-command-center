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
require.extensions[".css"]=mod=>{mod.exports=new Proxy({}, {get:(_x,key)=>String(key)});};

const {goalDailyHistory}=require("../lib/goal-daily-history.ts");
const History=require("../app/GoalDailyHistory.tsx").default;
const todayDate=new Date("2026-10-24T04:00:00Z"); // Oct 23 Pacific
const root="https://github.com/pdufa/pdufa-command-center/actions/runs/";
const day=(date,id,status="PARTIAL",sections={})=>({
  date_pacific:date,run_id:id,run_url:root+id,status,sections
});
const ledger=()=>({schema_version:1,days:[
  day("2026-10-23",40057578041,"PARTIAL",{
    master:{total:11598,new:null,updated:68},pipeline:{total:null,new:null},
    gem_jr:{total:11,new:0},gem:{total:6,new:0},designations:{total:null,new:null},
  }),
  day("2026-10-22",39895404578,"PARTIAL",{
    master:{total:11594,new:null,updated:49},gem_jr:{total:11,new:0},gem:{total:6,new:0},
  }),
  day("2026-10-21",39722233373,"PARTIAL",{
    master:{total:11583,new:null,updated:null},gem_jr:{total:11,new:0},gem:{total:6,new:0},
  }),
]});

test("GOAL daily history preserves each saved date and independently scoped counts",()=>{
  const rows=goalDailyHistory(ledger(),todayDate);
  assert.deepEqual(rows.map(r=>r.date),["2026-10-23","2026-10-22","2026-10-21"]);
  assert.equal(rows[0].today,true);
  assert.equal(rows[0].master.total,11598);
  assert.equal(rows[0].master.updated,68);
  assert.equal(rows[1].master.updated,49);
  assert.equal(rows[0].master.new,null);
  assert.equal(rows[0].pipeline.total,null);
  assert.equal(rows[0].gemJr.total,11);
  assert.equal(rows[0].gemJr.new,0);
  assert.equal(rows[0].gem.total,6);
  assert.equal(rows[0].designations.total,null);
  assert.equal(rows[0].runUrl,root+"40057578041");
  assert.equal(goalDailyHistory(ledger(),todayDate,2).length,2);
});

test("Malformed, duplicated, forged, future and failed publication records fail closed",()=>{
  const input=ledger();
  input.days.push(day("2026-10-24",40057999999,"COMPLETE",{master:{total:99}}));
  input.days.push(day("2026-02-30",40057888888,"COMPLETE",{master:{total:999}}));
  input.days.push(day("2026-10-20",40057777777,"COMPLETE",{master:{total:999}}));
  input.days[input.days.length-1].run_url="https://evil.example/steal";
  assert.equal(goalDailyHistory(input,todayDate).length,3);
  input.days.push(day("2026-10-23",40057578042,"COMPLETE",{master:{total:100000}}));
  assert.equal(goalDailyHistory(input,todayDate).some(row=>row.date==="2026-10-23"),false);
  const failed=ledger();failed.days[0].status="RUN_FAILED";
  const newest=goalDailyHistory(failed,todayDate)[0];
  assert.equal(newest.master.updated,null);
  assert.equal(newest.gemJr.total,null);
  assert.equal(goalDailyHistory({...ledger(),schema_version:9},todayDate).length,0);
  assert.equal(goalDailyHistory({schema_version:1,days:Array(401).fill({})},todayDate).length,0);
  assert.equal(goalDailyHistory(null,todayDate).length,0);
});

test("Collapsed GOAL history shows valid run links and never invents unknown values",async()=>{
  let view;
  try {
    await act(async()=>{view=create(React.createElement(History,{
      daily:ledger(),loading:false,error:""
    }));});
    const rendered=JSON.stringify(view.toJSON());
    assert.match(rendered,/Daily scan history/);
    assert.match(rendered,/published days/);
    assert.match(rendered,/11,598/);
    assert.match(rendered,/11,594/);
    assert.doesNotMatch(rendered,/11 \/ 0/);
    assert.doesNotMatch(rendered,/6 \/ 0/);
    assert.match(rendered,/not new trials/);
    assert.match(rendered,/—/);
    const links=view.root.findAllByType("a");
    assert.equal(links.length,3);
    assert.ok(links.every(a=>a.props.href.startsWith(root) && a.props.rel==="noopener noreferrer"));
    assert.equal(view.root.findAllByType("button").length,0);
  } finally {if(view)await act(async()=>view.unmount());}
});

test("The history panel uses only existing GET source and fits iPhone",()=>{
  const source=fs.readFileSync(path.join(__dirname,"../app/GoalDashboard.tsx"),"utf8");
  const component=fs.readFileSync(path.join(__dirname,"../app/GoalDailyHistory.tsx"),"utf8");
  const css=fs.readFileSync(path.join(__dirname,"../app/GoalDailyHistory.module.css"),"utf8");
  assert.match(source,/setDailyLedger\(data && typeof data/);
  assert.match(source,/setDailyLedger\(null\)/);
  assert.match(source,/<GoalDailyHistory daily=\{dailyLedger\} loading=\{scanLoading\}/);
  assert.match(css,/@media\(max-width:650px\)/);
  assert.match(css,/overflow:auto/);
  assert.doesNotMatch(component,/fetch\(|localStorage|sessionStorage|method: ?["']POST|dispatchWorkflow|Twilio|placeOrder/i);
});
