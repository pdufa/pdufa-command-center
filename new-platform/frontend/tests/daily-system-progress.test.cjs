const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for (const extension of [".ts", ".tsx"]) require.extensions[extension] = (module,file) => module._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true},
}).outputText,file);
const {calculateProgress} = require("../lib/daily-system-progress.ts");
const {auditMainDailyEvidence,MAIN_DAILY_EVIDENCE} = require("../lib/main-daily-evidence.ts");
const inventory = require("../data/mainAcceptanceInventory.json");
const observations = require("../data/mainDailyEvidenceSnapshots.json");
const proof = require("../data/mainProductionDeploymentEvidence.json");
const copy = x => structuredClone(x);
const count = (completed,total=31,scope="MAIN/core-platform-gates/v2") => ({completed,total,scope,evidenceUri:"https://example.org/evidence"});
const snapshot = (day,main) => ({asOf:day,systems:{SCIENCE:null,OUTCOME:null,MAIN:main}});

test("the first MAIN baseline reconciles all 31 gates without claiming a completed section",()=>{
  const audit = MAIN_DAILY_EVIDENCE;
  assert.equal(audit.valid,true,audit.reason);
  assert.deepEqual([audit.verified,audit.signals,audit.partial,audit.unverified,audit.total],[1,6,5,19,31]);
  assert.equal(audit.acceptedSections,0);
  assert.equal(audit.sections,8);
  const current = audit.history.at(-1);
  const progress = calculateProgress("MAIN",null,current,audit.history);
  assert.equal(progress.percent,100/31);
  assert.equal(progress.status,"BASELINE_ONLY");
  assert.equal(progress.changePp,null);
  assert.equal(progress.etaDays,null);
  assert.equal(calculateProgress("SCIENCE",null,current).percent,null);
  assert.equal(calculateProgress("OUTCOME",null,current).percent,null);
});

test("correcting the acceptance policy starts v2 without inventing progress or comparing it to v1",()=>{
  assert.equal(inventory.scope,"MAIN/core-platform-gates/v2");
  assert.equal(observations[0].policySource,inventory.policySource);
  const legacy={...inventory,scope:"MAIN/core-platform-gates/v1"};
  assert.equal(auditMainDailyEvidence(legacy,observations,proof).valid,false);
  const previous=snapshot("2026-10-25",count(1,31,"MAIN/core-platform-gates/v1"));
  const current=MAIN_DAILY_EVIDENCE.history.at(-1);
  const result=calculateProgress("MAIN",previous,current);
  assert.equal(result.status,"BASELINE_ONLY");assert.equal(result.changePp,null);
  assert.equal(result.etaDays,null);assert.equal(result.percent,100/31);
  const wrongInventory=copy(inventory);
  wrongInventory.policySource=wrongInventory.policySource.replace("44c2b45a4d5d7b853e1544a31d87cba43fcbbcf4","main");
  assert.equal(auditMainDailyEvidence(wrongInventory,observations,proof).valid,false);
  const wrongSnapshot=copy(observations);
  wrongSnapshot[0].policySource="https://example.org/other-policy";
  assert.equal(auditMainDailyEvidence(inventory,wrongSnapshot,proof).valid,false);
});

test("fixed MAIN identities and original exclusion cannot be removed, duplicated or reassigned",()=>{
  const changes = [
    x=>x.gates.pop(),x=>x.gates.push(x.gates[0]),x=>x.gates[1]=x.gates[0],
    x=>x.gates[0].component="Pipeline",x=>x.scope="new-scope",x=>x.excluded=[],
    x=>x.source=x.source.replace(/dbf786[0-9a-f]+/,"main"),
  ];
  for (const change of changes) {const inv=copy(inventory); change(inv); const r=auditMainDailyEvidence(inv,observations,proof); assert.equal(r.valid,false); assert.deepEqual(r.history,[]);}
});

test("preview, wrong project/commit/alias and undated deployment claims never enter numerator",()=>{
  for (const mutate of [
    x=>x.target="preview",x=>x.state="ERROR",x=>x.branch="feature",x=>x.projectId="other",
    x=>x.commit="a".repeat(40),x=>x.aliases=[],x=>x.evidenceUri="https://example.org/forged",
    x=>x.readyAt="2099-10-26T00:00:00Z",x=>x.observedAt="not-a-date",
  ]) {const p=copy(proof); mutate(p); const r=auditMainDailyEvidence(inventory,observations,p); assert.equal(r.valid,false); assert.equal(r.history.length,0);}
});

test("incomplete observations, cross-gate proof reuse and fabricated dates fail closed",()=>{
  for (const mutate of [
    x=>x[0].observations.pop(),x=>x[0].observations[1].status="Accepted",
    x=>x[0].observations[2]={...x[0].observations[1],id:x[0].observations[2].id},
    x=>delete x[0].observations[1].proofId,x=>x[0].asOf="2026-10-25",
    x=>x[0].recordedAt="2099-10-26T23:00:00Z",x=>x[0].timezone="UTC",
    x=>x[0].productionCommit="b".repeat(40),x=>x.push(copy(x[0])),
  ]) {const rows=copy(observations); mutate(rows); const r=auditMainDailyEvidence(inventory,rows,proof); assert.equal(r.valid,false); assert.equal(r.history.length,0);}
});

test("recorded daily gate states reconcile with the actual acceptance table",()=>{
  const page=fs.readFileSync(require("node:path").join(__dirname,"../app/installation-audit/page.tsx"),"utf8");
  const rows=page.split("\n").filter(x=>x.startsWith('  { component: "'));
  for (const gate of inventory.gates) {
    const activeComponent=gate.component==="GEM JR / GEM / WT"?"POOL / PIPELINE":gate.component;
    const row=rows.find(x=>x.includes('component: "'+activeComponent+'"'));
    assert.ok(row,"Missing active audit mapping for "+gate.component);
    if(!row){
      assert.equal(gate.component,"GEM JR / GEM / WT","Only retired dated audit categories may be absent from active tracker");
      assert.ok(rows.some(x=>x.includes('component: "POOL / PIPELINE"')));
      assert.ok(MAIN_DAILY_EVIDENCE.observations.some(x=>x.id===gate.id));
      continue;
    }
    const state=row.match(new RegExp(gate.stage+': "([^"]+)"'))[1];
    assert.equal(MAIN_DAILY_EVIDENCE.observations.find(x=>x.id===gate.id).status,state,gate.id);
  }
});

test("missing or malformed measured inputs remain unknown, while a proved zero stays zero",()=>{
  for (const c of [null,count(true),count(NaN),count(32),count(1,0),{...count(1),scope:7},{...count(1),evidenceUri:"https://"}]) {
    assert.equal(calculateProgress("MAIN",null,snapshot("2026-10-26",c)).percent,null);
  }
  assert.equal(calculateProgress("MAIN",null,snapshot("2026-02-30",count(1))).percent,null);
  assert.equal(calculateProgress("MAIN",null,snapshot("2026-10-26",count(0))).percent,0);
  assert.equal(calculateProgress("MAIN",null,{}).percent,null);
});

test("only adjacent same-scope Pacific dates establish daily percentage-point change",()=>{
  const current=snapshot("2026-10-26",count(2));
  assert.equal(calculateProgress("MAIN",snapshot("2026-10-25",count(1)),current).changePp,100/31);
  for (const previous of [snapshot("2026-10-24",count(1)),snapshot("2026-10-26",count(1)),snapshot("2026-10-27",count(1)),snapshot("2026-10-25",count(1,32)),snapshot("2026-10-25",count(1,31,"changed"))]) {
    const result=calculateProgress("MAIN",previous,current);
    assert.equal(result.status,"BASELINE_ONLY"); assert.equal(result.changePp,null); assert.equal(result.etaDays,null);
  }
});

test("ETA requires eight actual comparable daily measurements, not sparse endpoints",()=>{
  const history=Array.from({length:8},(_,i)=>snapshot("2026-10-"+(19+i),count(i+1)));
  const result=calculateProgress("MAIN",history[6],history[7],history);
  assert.equal(result.etaDays,23);
  assert.equal(result.etaDate,"2026-11-18");
  for (const bad of [history.slice(1),[history[0],history[7]],history.map((x,i)=>i===3?{...x,asOf:"2026-10-21"}:x),history.map((x,i)=>i===3?snapshot(x.asOf,count(2)):x),history.map((x,i)=>i===3?snapshot(x.asOf,count(4,32)):x)]) {
    assert.equal(calculateProgress("MAIN",history[6],history[7],bad).etaDays,null);
  }
  const flat=history.map(x=>snapshot(x.asOf,count(2)));
  assert.equal(calculateProgress("MAIN",flat[6],flat[7],flat).etaDays,null);
});

test("rendered cards show sourced MAIN 3.2%, exact denominator, unknown other systems and no invented ETA",()=>{
  const React=require("react");
  const {renderToStaticMarkup}=require("react-dom/server");
  const Component=require("../app/installation-audit/DailySystemProgress.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Component));
  assert.match(html,/3\.2%/);
  assert.match(html,/1\/31 gates verified/);
  assert.match(html,/30\/31.*remain open/);
  assert.match(html,/0\/8.*sections fully accepted/);
  assert.match(html,/2026-10-26/);
  assert.match(html,/Daily change awaits a comparable prior-day snapshot/);
  assert.equal((html.match(/>Not verified<\/p>/g)||[]).length,2);
  assert.match(html,/Not available/);
  assert.match(html,/does not automatically refresh/);
  assert.doesNotMatch(html,/40%|approx\./);
});
