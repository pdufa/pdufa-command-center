const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true
  }}).outputText,file
);
const {readNightlyHealth,parseNightlyHealth,unavailableNightlyHealth,WORKFLOW_HISTORY_URL,overdueNominalPacificDate,INTEGRITY_STEP}=
  require("../lib/main-phase3-nightly-health.ts");

const when=new Date("2026-10-27T04:10:00.000Z");
const SOURCE_PATH=".github/workflows/main-phase3-evidence-qualification.yml";
const run=(id,at="2026-10-27T03:00:00Z",event="schedule")=>({
  id,event,head_branch:"main",path:SOURCE_PATH,created_at:at,status:"completed",conclusion:"success"
});
const gate=(conclusion="success")=>({name:"pacific-nightly-gate",status:"completed",conclusion});
const integrityStep=(conclusion="success")=>({
  name:INTEGRITY_STEP,
  status:"completed",conclusion
});
const job=(conclusion="success",status="completed")=>({
  name:"research-ledger",status,conclusion,
  completed_at:"2026-10-27T03:20:00Z",
  steps:[integrityStep()]
});
const artifact=(id,expired=false)=>({
  name:"main-phase3-evidence-qualification-research-only",
  size_in_bytes:250000,expired,workflow_run:{id}
});
function provider(runs,{jobs={},artifacts={}}={}){
  const urls=[];
  const get=async url=>{
    urls.push(url);
    if(url.includes("/workflows/main-phase3-evidence-qualification.yml/runs?"))
      return {workflow_runs:runs};
    const match=url.match(/\/actions\/runs\/(\d+)\/(jobs|artifacts)\?/);
    if(!match)throw Error("Unexpected source URL "+url);
    const id=Number(match[1]);
    if(match[2]==="jobs")return {jobs:jobs[id]??[gate(),job()]};
    return {artifacts:artifacts[id]??[artifact(id)]};
  };
  return {get,urls};
}

test("Pacific 10:30 PM grace boundary is exact, no run yet is not failure",async()=>{
  const {get}=provider([]);
  const before=await readNightlyHealth(get,new Date("2026-10-27T05:29:00Z"));
  assert.equal(before.state,"NO_FULL_SCHEDULED_RUN_YET");
  const after=await readNightlyHealth(get,new Date("2026-10-27T05:30:00Z"));
  assert.equal(after.state,"SCHEDULED_SCAN_OVERDUE");
  assert.equal(after.overduePacificDate,"2026-10-26");
  assert.equal(after.runId,null);
  assert.equal(after.artifactConfirmed,false);
  assert.deepEqual(parseNightlyHealth(after),after);
});

test("Before first nominal schedule day, no historic run is incorrectly overdue",async()=>{
  assert.equal(overdueNominalPacificDate(new Date("2026-10-26T05:31:00Z")),null);
  const {get}=provider([]);
  assert.equal((await readNightlyHealth(get,new Date("2026-10-26T05:31:00Z"))).state,
               "NO_FULL_SCHEDULED_RUN_YET");
});

test("Overdue research night persists until the next window, including next morning",async()=>{
  const {get}=provider([]);
  for(const time of ["2026-10-27T05:30:00Z","2026-10-27T16:00:00Z",
                     "2026-10-28T04:00:00Z"]){
    const r=await readNightlyHealth(get,new Date(time));
    assert.equal(r.state,"SCHEDULED_SCAN_OVERDUE");
    assert.equal(r.overduePacificDate,"2026-10-26");
  }
  const next=await readNightlyHealth(get,new Date("2026-10-28T05:31:00Z"));
  assert.equal(next.overduePacificDate,"2026-10-27");
});

test("Pacific overdue windows remain correct after fall and spring DST changes",()=>{
  assert.equal(overdueNominalPacificDate(new Date("2026-11-01T05:29:00Z")),"2026-10-30");
  assert.equal(overdueNominalPacificDate(new Date("2026-11-01T05:31:00Z")),"2026-10-31");
  assert.equal(overdueNominalPacificDate(new Date("2026-11-02T06:31:00Z")),"2026-11-01");
  assert.equal(overdueNominalPacificDate(new Date("2027-03-15T05:31:00Z")),"2027-03-14");
});

test("Yesterday's successful full scan cannot satisfy a missed newer night",async()=>{
  const {get,urls}=provider([run(2001)]);
  const now=new Date("2026-10-28T05:31:00Z");
  const r=await readNightlyHealth(get,now);
  assert.equal(r.state,"SCHEDULED_SCAN_OVERDUE");
  assert.equal(r.overduePacificDate,"2026-10-27");
  assert.equal(r.runId,null);
  assert.equal(r.latestScheduleObservedAtUtc,"2026-10-27T03:00:00Z");
  assert.equal(urls.length,2,"Do not check yesterday's artifact as though it covers tonight");
});

test("A newer deliberately skipped DST alternate is not the expected full scan",async()=>{
  const {get}=provider([run(2005,"2026-10-27T04:00:00Z")],{
    jobs:{2005:[gate(),job("skipped")]}
  });
  const r=await readNightlyHealth(get,new Date("2026-10-27T05:31:00Z"));
  assert.equal(r.state,"SCHEDULED_SCAN_OVERDUE");
  assert.equal(r.overduePacificDate,"2026-10-26");
  assert.equal(r.intentionallySkippedAlternates,1);
});

test("A real full research failure on expected date stays failed, not overdue",async()=>{
  const {get}=provider([run(2001)],{
    jobs:{2001:[gate(),job("failure")]}
  });
  const r=await readNightlyHealth(get,new Date("2026-10-27T05:31:00Z"));
  assert.equal(r.state,"FULL_SCAN_FAILED");
  assert.equal(r.overduePacificDate,null);
  assert.equal(r.runId,2001);
});

test("A real in-progress full research scan is not marked missing",async()=>{
  const {get}=provider([run(2001)],{
    jobs:{2001:[gate(),job(null,"in_progress")]}
  });
  const r=await readNightlyHealth(get,new Date("2026-10-27T05:31:00Z"));
  assert.equal(r.state,"FULL_SCAN_RUNNING");
  assert.equal(r.overduePacificDate,null);
});

test("Extremely delayed GitHub cron started next afternoon belongs to previous night",async()=>{
  const latest=run(2008,"2026-10-27T17:00:00Z");
  const {get}=provider([latest],{
    jobs:{2008:[gate(),job(null,"in_progress")]}
  });
  const observed=await readNightlyHealth(get,new Date("2026-10-27T18:00:00Z"));
  assert.equal(observed.state,"FULL_SCAN_RUNNING"); // late Oct 26 research finally started
  const tomorrow=await readNightlyHealth(get,new Date("2026-10-28T05:31:00Z"));
  assert.equal(tomorrow.state,"SCHEDULED_SCAN_OVERDUE");
  assert.equal(tomorrow.overduePacificDate,"2026-10-27");
});

test("Overdue result cannot be forged with a mismatched date or a completed job",async()=>{
  const {get}=provider([]);
  const original=await readNightlyHealth(get,new Date("2026-10-27T05:31:00Z"));
  for(const change of [
    x=>{x.overduePacificDate=null;},
    x=>{x.overduePacificDate="bad-date";},
    x=>{x.state="FULL_SCAN_CONFIRMED";},
    x=>{x.artifactConfirmed=true;},
    x=>{x.runId=2001;},
  ]){
    const r=structuredClone(original);
    change(r);
    assert.throws(()=>parseNightlyHealth(r));
  }
});

test("Before first scheduled run: no completed nightly scan is invented",async()=>{
  const {get,urls}=provider([]);
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"NO_FULL_SCHEDULED_RUN_YET");
  assert.equal(r.runId,null);
  assert.equal(r.artifactConfirmed,false);
  assert.equal(r.integrityStepConfirmed,false);
  assert.equal(urls.length,1);
  assert.deepEqual(parseNightlyHealth(r),r);
});

test("A recent completed full scheduled research job and exact artifact is confirmed",async()=>{
  const {get,urls}=provider([run(2001)]);
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"FULL_SCAN_CONFIRMED");
  assert.equal(r.runId,2001);
  assert.equal(r.runUrl,"https://github.com/pdufa/pdufa-command-center/actions/runs/2001");
  assert.equal(r.artifactConfirmed,true);
  assert.equal(r.integrityStepConfirmed,true);
  assert.equal(urls.length,3);
  assert.deepEqual(parseNightlyHealth(r),r);
});

test("Successful workflow wrapper but DST alternate skipped cannot be called a scan",async()=>{
  const {get,urls}=provider([run(2002)],{
    jobs:{2002:[gate(),job("skipped")]}
  });
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"NO_FULL_SCHEDULED_RUN_YET");
  assert.equal(r.intentionallySkippedAlternates,1);
  assert.equal(r.latestScheduleObservedAtUtc,"2026-10-27T03:00:00Z");
  assert.equal(r.runId,null);
  assert.equal(urls.length,2);
});

test("Skips newer DST alternate and selects the actual earlier full scan",async()=>{
  const runs=[
    run(2005,"2026-10-27T04:00:00Z"),
    run(2004,"2026-10-27T03:00:00Z")
  ];
  const {get}=provider(runs,{jobs:{2005:[gate(),job("skipped")]}});
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"FULL_SCAN_CONFIRMED");
  assert.equal(r.runId,2004);
  assert.equal(r.intentionallySkippedAlternates,1);
  assert.equal(r.latestScheduleObservedAtUtc,"2026-10-27T04:00:00Z");
});

test("A full research job failure overrides workflow-level source assumptions",async()=>{
  const {get}=provider([run(2001)],{jobs:{2001:[gate(),job("failure")]}});
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"FULL_SCAN_FAILED");
  assert.equal(r.artifactConfirmed,false);
  assert.equal(r.runId,2001);
});

test("Failed DST gate cannot masquerade as intentional skip",async()=>{
  const {get}=provider([run(2001)],{jobs:{2001:[gate("failure"),job("skipped")]}});
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"FULL_SCAN_FAILED");
  assert.equal(r.intentionallySkippedAlternates,0);
});

test("GitHub workflow integrity job name matches exact dashboard validation contract",()=>{
  const workflow=fs.readFileSync(require("node:path").join(__dirname,
    "../../../.github/workflows/main-phase3-evidence-qualification.yml"),"utf8");
  assert.equal(INTEGRITY_STEP,
    "Verify MAIN Phase 3 research integrity manifest [nightly-integrity-v1]");
  assert.ok(workflow.includes("      - name: "+INTEGRITY_STEP+"\n"),
    "Renaming the GitHub source integrity step must fail frontend CI");
  assert.doesNotMatch(INTEGRITY_STEP,/\b(?:14|16|18)\s*(?:file|report)/i,
    "Step names cannot drift when the validated artifact grows");
});

test("Legacy or changed report-count step labels cannot be misreported as success",async()=>{
  for(const oldName of [
    "Reconcile 14 complete source reports and create SHA256 artifact manifest",
    "Reconcile 16 complete source reports and create SHA256 artifact manifest",
    "Verify MAIN Phase 3 research integrity manifest [nightly-integrity-v2]"
  ]){
    const falseJob=job();
    falseJob.steps=[{...integrityStep(),name:oldName}];
    const {get}=provider([run(2001)],{jobs:{2001:[gate(),falseJob]}});
    const found=await readNightlyHealth(get,when);
    assert.equal(found.state,"REPORT_INTEGRITY_UNVERIFIED");
    assert.equal(found.artifactConfirmed,false);
    assert.equal(found.integrityStepConfirmed,false);
  }
});

test("A successful research job without the exact stable integrity step cannot be confirmed",async()=>{
  for(const steps of [
    undefined,
    [],
    [{name:"Ordinary source test",status:"completed",conclusion:"success"}],
    [integrityStep("failure")],
    [integrityStep("skipped")],
    [integrityStep(),integrityStep()],
    [{...integrityStep(),status:"in_progress"}]
  ]) {
    const x=job();
    if(steps===undefined)delete x.steps;
    else x.steps=steps;
    const {get,urls}=provider([run(2001)],{jobs:{2001:[gate(),x]}});
    const status=await readNightlyHealth(get,when);
    assert.equal(status.state,"REPORT_INTEGRITY_UNVERIFIED");
    assert.equal(status.runId,2001);
    assert.equal(status.artifactConfirmed,false);
    assert.equal(status.integrityStepConfirmed,false);
    assert.equal(urls.length,2,"No artifact lookup should turn an unverified report green");
    assert.deepEqual(parseNightlyHealth(status),status);
  }
});

test("Missing source integrity cannot be forged into a passed check in client payload",async()=>{
  const x=job();
  x.steps=[];
  const {get}=provider([run(2001)],{jobs:{2001:[gate(),x]}});
  const status=await readNightlyHealth(get,when);
  const malicious={...status,integrityStepConfirmed:true};
  assert.throws(()=>parseNightlyHealth(malicious));
});

test("A confirmed scan must preserve both independent artifact and integrity proofs",async()=>{
  const {get}=provider([run(2001)]);
  const good=await readNightlyHealth(get,when);
  const swapped={...good,state:"REPORT_ARTIFACT_MISSING",artifactConfirmed:false};
  assert.deepEqual(parseNightlyHealth(swapped),swapped);
  assert.throws(()=>parseNightlyHealth({
    ...good,state:"REPORT_INTEGRITY_UNVERIFIED",integrityStepConfirmed:true,
    artifactConfirmed:false
  }));
});

test("Missing or expired source artifact prevents green success",async()=>{
  for(const artifacts of [[],[artifact(2001,true)],[artifact(9999)]]) {
    const {get}=provider([run(2001)],{artifacts:{2001:artifacts}});
    const r=await readNightlyHealth(get,when);
    assert.equal(r.state,"REPORT_ARTIFACT_MISSING");
    assert.equal(r.artifactConfirmed,false);
    assert.equal(r.integrityStepConfirmed,true);
  }
});

test("Scan job still queued or running is not a completed scan",async()=>{
  const {get}=provider([run(2001)],{jobs:{2001:[gate(),job(null,"in_progress")]}});
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"FULL_SCAN_RUNNING");
  assert.equal(r.artifactConfirmed,false);
});

test("A 36-hour-old successful scan cannot conceal subsequent missed nights",async()=>{
  const {get}=provider([run(2001)]);
  const r=await readNightlyHealth(get,new Date("2026-10-29T09:30:00Z"));
  assert.equal(r.state,"SCHEDULED_SCAN_OVERDUE");
  assert.equal(r.overduePacificDate,"2026-10-28");
  assert.equal(r.artifactConfirmed,false);
  assert.equal(r.integrityStepConfirmed,false);
  assert.equal(r.runId,null);
});

test("Unrelated PR workflow runs do not establish a scheduled success",async()=>{
  const {get}=provider([run(2001,undefined,"pull_request")]);
  const r=await readNightlyHealth(get,when);
  assert.equal(r.state,"NO_FULL_SCHEDULED_RUN_YET");
});

test("Malformed GitHub jobs and artifact replies fail closed",async()=>{
  const original=provider([run(2001)]);
  await assert.rejects(()=>readNightlyHealth(async url=>
    url.includes("/jobs?")?{jobs:null}:original.get(url),when));
  await assert.rejects(()=>readNightlyHealth(async url=>
    url.includes("/artifacts?")?{artifacts:"forged"}:original.get(url),when));
});

test("Forged source URL, positive run, scope and artifact claims are rejected",async()=>{
  const {get}=provider([run(2001)]);
  const good=await readNightlyHealth(get,when);
  for(const change of [
    x=>{x.runUrl="https://phishing.example/run";},
    x=>{x.runId=0;},
    x=>{x.scope="LIVE_TRADING_SCAN";},
    x=>{x.artifactConfirmed=false;},
    x=>{x.integrityStepConfirmed=false;},
    x=>{x.state="PRODUCTION_TRADING_APPROVED";},
    x=>{x.checkedAtUtc="not-a-real-date";},
  ]){
    const payload=structuredClone(good);
    change(payload);
    assert.throws(()=>parseNightlyHealth(payload));
  }
});

test("Unavailable source status never reports scan success",()=>{
  const r=unavailableNightlyHealth(when);
  assert.equal(r.state,"SOURCE_UNAVAILABLE");
  assert.equal(r.runId,null);
  assert.equal(r.artifactConfirmed,false);
  assert.equal(r.integrityStepConfirmed,false);
  assert.deepEqual(parseNightlyHealth(r),r);
  assert.match(WORKFLOW_HISTORY_URL,/github\.com\/pdufa\/pdufa-command-center\/actions/);
});

test("Site endpoint is authenticated and cannot mutate live PIPELINE/GEM",()=>{
  const body=fs.readFileSync(require("node:path").join(__dirname,
    "../app/api/main-phase3-nightly-health/route.ts"),"utf8");
  assert.match(body,/authConfigured\(\)/);
  assert.match(body,/hasSession\(/);
  assert.match(body,/readNightlyHealth\(githubJson,now\)/);
  assert.match(body,/private, no-store/);
  assert.doesNotMatch(body,/createOrder|promoteTrial|updateCandidate|setPipeline/);
});
