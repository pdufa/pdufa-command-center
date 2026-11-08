const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const cache=new Map();
function load(name){
 if(cache.has(name))return cache.get(name);
 const src=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
 const mod={exports:{}};
 vm.runInNewContext(js,{module:mod,exports:mod.exports,require:specifier=>{
  if(specifier.endsWith(".json"))return JSON.parse(fs.readFileSync(path.resolve(__dirname,"../lib",specifier),"utf8"));
  assert.match(specifier,/^\.\//);
  return load(specifier.slice(2));
 }});
 cache.set(name,mod.exports);
 return mod.exports;
}
const {buildInstallationProgress}=load("main-install-progress");
const external={
 observedAt:"2026-11-08T00:00:00Z",
 deployment:{state:"READY",sha:"1234567890123456789012345678901234567890",url:"https://preview.example"},
 medicalQa:"unknown",overallCi:"unknown",
 apiReachable:false,scheduledScans:{state:"unknown",at:null,url:null}
};
const at="2026-11-08T00:00:00Z";
test("monitored progress only counts verified installation checkpoints",()=>{
 const snapshot=buildInstallationProgress(null,external,at);
 assert.equal(snapshot.schemaVersion,1);
 assert.equal(snapshot.stages.length,20);
 assert.equal(snapshot.stages.filter(x=>x.id.startsWith("advanced-")).length,12);
 const all=snapshot.stages.flatMap(x=>x.checks);
 assert.equal(snapshot.overall.total,all.length);
 assert.equal(snapshot.overall.verified,all.filter(x=>x.status==="VERIFIED").length);
 assert.equal(snapshot.overall.percent,Math.floor(snapshot.overall.verified*100/all.length));
 assert.ok(snapshot.overall.blocked>0);
 assert.ok(snapshot.overall.unknown>0);
 assert.equal(snapshot.facts.advancedLevelDefinitions,12);
 assert.equal(snapshot.facts.historicalCalibrationRows,0);
 assert.equal(snapshot.facts.productionModified,false);
 assert.ok(snapshot.nextUnfinished);
});
test("backend blocked and absent CI proof cannot be counted as success",()=>{
 const m=buildInstallationProgress({schemaVersion:1,observedAt:at,storage:{
  state:"BLOCKED",kind:"sqlite",postgresRequired:true},errors:["database missing"]},external,at);
 assert.equal(m.stages.find(x=>x.id==="infrastructure").checks.find(x=>x.id==="infra.storage").status,"BLOCKED");
 assert.equal(m.stages.find(x=>x.id==="infrastructure").checks.find(x=>x.id==="infra.medical-ci").status,"UNKNOWN");
 assert.equal(m.stages.find(x=>x.id==="predictions").checks.find(x=>x.id==="prediction.history").status,"BLOCKED");
 assert.equal(m.health.level,"BLOCKED");
});
test("fresh DB, saved revisions and exact-commit tests advance only their own gates",()=>{
 const fresh={...external,apiReachable:true,medicalQa:"success",overallCi:"failure",scheduledScans:{state:"success",at,url:null}};
 const live={schemaVersion:1,observedAt:at,storage:{state:"READY",kind:"postgresql",postgresRequired:true},
  scans:{phase3Ingestion:{state:"COMPLETE",lastSuccessAt:at},
    nctStream:{state:"OBSERVED",totalRuns:2,failedRuns:0},
    registryWatch:{state:"OBSERVED",enabled:true,lastCheckedAt:at}},
  research:{state:"OBSERVED",finishedSourceRuns:1,savedSourceStages:12,immutableRevisions:1,failedSourceRuns:0},
  alerts:{telegramConfigured:true,lastDelivery:{state:"SENT"}},
  errors:[]};
 const m=buildInstallationProgress(live,fresh,at);
 const infrastructure=m.stages.find(x=>x.id==="infrastructure");
 assert.equal(infrastructure.checks.find(x=>x.id==="infra.storage").status,"VERIFIED");
 assert.equal(infrastructure.checks.find(x=>x.id==="infra.medical-ci").status,"VERIFIED");
 assert.equal(infrastructure.checks.find(x=>x.id==="infra.full-ci").status,"FAILED");
 assert.equal(m.stages.find(x=>x.id==="medical").checks.find(x=>x.id==="medical.complete").status,"VERIFIED");
 assert.equal(m.stages.find(x=>x.id==="operations").checks.find(x=>x.id==="ops.telegram").status,"VERIFIED");
 assert.equal(m.stages.find(x=>x.id==="predictions").checks.find(x=>x.id==="prediction.forecast").status,"PENDING");
 assert.equal(m.stages.find(x=>x.id==="certainty").checks.find(x=>x.id==="certainty.calibrated").status,"PENDING");
 assert.equal(m.health.level,"DEGRADED");
 assert.equal(m.stages.filter(s=>s.id.startsWith("advanced-")).every(s=>s.verified===1),true);
});
test("MAIN monitor UI is protected, refreshing, expandable, and does not alter acceptance gate IDs",()=>{
 const main=fs.readFileSync(path.join(__dirname,"../app/main/page.tsx"),"utf8");
 const component=fs.readFileSync(path.join(__dirname,"../app/main/InstallationProgressDashboard.tsx"),"utf8");
 const api=fs.readFileSync(path.join(__dirname,"../app/api/main/installation-progress/route.ts"),"utf8");
 const nav=fs.readFileSync(path.join(__dirname,"../app/GlobalNavigation.tsx"),"utf8");
 assert.match(main,/<InstallationProgressDashboard\s*\/>/);
 assert.match(main,/MAIN_ACTIVE_GATE_IDS/);
 assert.match(component,/data\.stages\.map\(stage=><StagePanel/);
 assert.match(component,/<details/);
 assert.match(component,/45000/);
 assert.match(component,/data\.nextUnfinished/);
 assert.match(component,/data\.signals\.alerts/);
 assert.match(api,/hasSession/);
 assert.match(api,/PDUFA_INTERNAL_API_KEY/);
 assert.match(api,/PDUFA_GITHUB_READ_TOKEN/);
 assert.match(api,/head_sha/);
 assert.match(api,/event=schedule/);
 assert.match(nav,/label:"MAIN",href:"\/main"/);
 assert.doesNotMatch(component,/<button[^>]+(?:sendMessage|startScan|placeOrder)/);
});
