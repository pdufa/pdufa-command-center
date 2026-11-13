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
 assert.equal(snapshot.stages.length,21);
 assert.equal(snapshot.stages.filter(x=>x.id.startsWith("advanced-")).length,12);
 const all=snapshot.stages.flatMap(x=>x.checks);
 assert.equal(snapshot.overall.total,all.length);
 assert.equal(snapshot.overall.verified,all.filter(x=>x.status==="VERIFIED").length);
 assert.equal(snapshot.overall.percent,Math.floor(snapshot.overall.verified*100/all.length));
 assert.ok(snapshot.overall.blocked>0);
 assert.ok(snapshot.overall.unknown>0);
 assert.equal(snapshot.facts.advancedLevelDefinitions,12);
 assert.equal(snapshot.facts.historicalCalibrationRows,0);
 assert.equal(snapshot.facts.sourceDataModified,false);
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
 assert.match(main,/href="\/precision-monitoring"/);
 assert.match(main,/MAIN_ACTIVE_GATE_IDS/);
 assert.match(component,/data\.stages\.map\(stage=><StagePanel/);
 assert.match(component,/data\.trials\.length/);
 assert.match(component,/visibleTrials\.map/);
 assert.match(component,/<details/);
 assert.match(component,/Immutable source revision history/);
 assert.match(component,/45000/);
 assert.match(component,/data\.nextUnfinished/);
 assert.match(component,/data\.signals\.alerts/);
 assert.match(api,/hasSession/);
 assert.match(api,/PDUFA_INTERNAL_API_KEY/);
 assert.match(api,/PDUFA_GITHUB_READ_TOKEN/);
 assert.match(api,/head_sha/);
 assert.match(api,/event=schedule/);
 const home=fs.readFileSync(path.join(__dirname,"../app/page.tsx"),"utf8");
 assert.match(home,/href="\/main"/);
 assert.doesNotMatch(nav,/label:"MAIN",href:"\/main"/);
 assert.doesNotMatch(component,/<button[^>]+(?:sendMessage|startScan|placeOrder)/);
});


test("degraded PostgreSQL never passes database-backed installation gates",()=>{
 const degraded=buildInstallationProgress({schemaVersion:1,observedAt:at,
   storage:{state:"DEGRADED",kind:"postgresql",postgresRequired:true},
   research:{state:"UNKNOWN"},errors:["live telemetry query failed"]},
   {...external,apiReachable:true},at);
 assert.equal(degraded.stages.find(s=>s.id==="infrastructure").checks.find(c=>c.id==="infra.storage").status,"BLOCKED");
 assert.equal(degraded.stages.find(s=>s.id==="medical").checks.find(c=>c.id==="medical.db").status,"BLOCKED");
 assert.equal(degraded.stages.find(s=>s.id==="operations").checks.find(c=>c.id==="ops.ingestion").status,"BLOCKED");
});


test("backend application map requires all 32 exact NCTs before becoming verified",()=>{
 const valid={...external,apiReachable:true};
 const base={schemaVersion:1,observedAt:at,storage:{state:"BLOCKED",kind:"sqlite",postgresRequired:true},
   sourceSnapshots:{applications:{state:"VALID",focusNctCount:32,coveredNctCount:32,applicationCycleCount:23}}};
 const verified=buildInstallationProgress(base,valid,at);
 assert.equal(verified.stages.find(x=>x.id==="medical").checks.find(x=>x.id==="medical.application-map").status,"VERIFIED");
 assert.equal(verified.stages.find(x=>x.id==="medical").checks.find(x=>x.id==="medical.db").status,"BLOCKED");
 const partial=buildInstallationProgress({...base,sourceSnapshots:{applications:{state:"VALID",focusNctCount:32,
   coveredNctCount:29,applicationCycleCount:23}}},valid,at);
 assert.equal(partial.stages.find(x=>x.id==="medical").checks.find(x=>x.id==="medical.application-map").status,"UNKNOWN");
 const corrupt=buildInstallationProgress({...base,sourceSnapshots:{applications:{state:"INVALID"}}},valid,at);
 assert.equal(corrupt.stages.find(x=>x.id==="medical").checks.find(x=>x.id==="medical.application-map").status,"FAILED");
});


test("frontend/backend commit parity is verified only for identical running SHAs",()=>{
 const sha=external.deployment.sha;
 const base={schemaVersion:1,observedAt:at,
   storage:{state:"BLOCKED",kind:"sqlite",postgresRequired:true},
   services:{backendDeployment:{gitSha:sha,branch:"feature/deep-medical-intelligence-preview-20261107"}}};
 const parity=(m)=>m.stages.find(s=>s.id==="infrastructure").checks.find(c=>c.id==="infra.commit-parity").status;
 assert.equal(parity(buildInstallationProgress(base,external,at)),"VERIFIED");
 const mismatched=buildInstallationProgress({...base,services:{backendDeployment:{gitSha:"f".repeat(40)}}},external,at);
 assert.equal(parity(mismatched),"BLOCKED");
 const unknown=buildInstallationProgress({...base,services:{backendDeployment:{gitSha:null}}},external,at);
 assert.equal(parity(unknown),"UNKNOWN");
 assert.equal(mismatched.stages.find(s=>s.id==="infrastructure").status,"BLOCKED");
});

test("Analyze Now progress waits for saved pilot and independent rollout switches",()=>{
 const local={...external,analyzeNowAllEnabled:false,apiReachable:true};
 const live={schemaVersion:1,observedAt:at,storage:{state:"READY",kind:"postgresql",postgresRequired:true},
   analysisNow:{state:"OBSERVED",pilotSaved:false,allTrialsEnabled:false,autoRerunEnabled:false,componentWatchBaselines:0}};
 const pilotGate=m=>m.stages.find(x=>x.id==="analyze-now").checks.find(x=>x.id==="analyze-now.pilot").status;
 const enabledGate=m=>m.stages.find(x=>x.id==="analyze-now").checks.find(x=>x.id==="analyze-now.rollout").status;
 assert.equal(pilotGate(buildInstallationProgress(live,local,at)),"PENDING");
 assert.equal(enabledGate(buildInstallationProgress(live,local,at)),"PENDING");
 assert.equal(pilotGate(buildInstallationProgress({...live,analysisNow:{...live.analysisNow,pilotSaved:true}},local,at)),"VERIFIED");
 const mismatched=buildInstallationProgress({...live,analysisNow:{...live.analysisNow,pilotSaved:true,allTrialsEnabled:true}},local,at);
 assert.equal(enabledGate(mismatched),"BLOCKED");
 const all=buildInstallationProgress({...live,analysisNow:{...live.analysisNow,pilotSaved:true,allTrialsEnabled:true}},
   {...local,analyzeNowAllEnabled:true},at);
 assert.equal(enabledGate(all),"VERIFIED");
});

test("all exact 32 FOCUS trials have expandable evidence, no invented verification",()=>{
 const report=buildInstallationProgress(null,external,at);
 assert.equal(report.trials.length,32);
 assert.equal(new Set(report.trials.map(t=>t.nct)).size,32);
 assert.ok(report.trials.every(t=>t.gates.length===7&&t.independentlyVerified===0));
 assert.ok(report.trials.every(t=>t.sourceState==="UNKNOWN"&&t.revisions.length===0));
 assert.ok(report.trials.some(t=>t.missing>0));
});
test("only actual authenticated backend revision telemetry makes a trial history observed",()=>{
 const id="NCT06081894",runId="00000000-0000-4000-8000-000000000023";
 const fake={schemaVersion:1,observedAt:at,storage:{state:"BLOCKED",kind:"sqlite",postgresRequired:true},
  trialHistories:{[id]:{state:"OBSERVED",latestStatus:"COMPLETE",sourceStages:12,failedRuns:1,
   revisions:[{ordinal:1,recordedAt:at,runId,evidenceChanged:true}]}}};
 const report=buildInstallationProgress(fake,external,at);
 const match=report.trials.find(t=>t.nct===id);
 assert.equal(match.sourceState,"OBSERVED");
 assert.equal(match.revisions.length,1);
 assert.equal(match.failedRuns,1);
 assert.equal(report.trials.filter(t=>t.sourceState==="OBSERVED").length,1);
 assert.equal(report.stages.find(s=>s.id==="predictions").checks.find(c=>c.id==="prediction.forecast").status,"PENDING");
});
test("dashboard is read-only, session-gated and distinct from unfinished prediction engine",()=>{
 const component=fs.readFileSync(path.join(__dirname,"../app/main/InstallationProgressDashboard.tsx"),"utf8");
 const page=fs.readFileSync(path.join(__dirname,"../app/precision-monitoring/page.tsx"),"utf8");
 const api=fs.readFileSync(path.join(__dirname,"../app/api/main/installation-progress/route.ts"),"utf8");
 const backend=fs.readFileSync(path.join(__dirname,"../../backend/app/main.py"),"utf8");
 assert.match(page,/PDUFA Precision Monitoring Dashboard/);
 assert.match(api,/hasSession/);
 assert.match(api,/private, no-store/);
 assert.match(api,/export async function GET/);
 assert.doesNotMatch(api,/export async function POST|export async function DELETE/);
 assert.match(component,/45000/);
 assert.match(component,/NOT VALIDATED/);
 assert.match(component,/ABSTAIN/);
 assert.match(backend,/Depends\(require_internal_key\)/);
 assert.match(backend,/api\/internal\/installation-monitor/);
 assert.doesNotMatch(backend,/\bRAASScore\(/);
});

test("production GitHub telemetry reuses configured read-only credential without exposing it",()=>{
 const api=fs.readFileSync(path.join(__dirname,"../app/api/main/installation-progress/route.ts"),"utf8");
 const smoke=fs.readFileSync(path.join(__dirname,"../../../.github/workflows/precision-monitoring-production-smoke.yml"),"utf8");
 assert.match(api,/PDUFA_GITHUB_READ_TOKEN\?\.trim\(\) \|\| process\.env\.PDUFA_GITHUB_TOKEN\?\.trim\(\)/);
 assert.match(api,/head_sha=/);
 assert.match(api,/x=>rec\(x\)\.head_sha===sha/);
 assert.match(api,/hasSession/);
 assert.doesNotMatch(api,/export async function POST|export async function DELETE/);
 assert.match(smoke,/app\/api\/main\/installation-progress\/route\.ts/);
 assert.match(smoke,/status" = "401"/);
 assert.match(smoke,/Sign in required/);
});
