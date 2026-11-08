const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}
}).outputText,file);
const {NextRequest}=require("next/server");
const auth=require("../lib/auth.ts");
const {FOCUS_SPECIALTY_ASSESSMENT_QUEUE}=require("../lib/focus-specialty-assessment.ts");
const {GET}=require("../app/api/predictions/medical-phase-handoff/route.ts");
const ids=FOCUS_SPECIALTY_ASSESSMENT_QUEUE.map(x=>x.nct);
const nct=ids[0];
function data(){
  const queue=ids.map((id,i)=>({
    nct:id,category:i===0?"PHASE_RECONCILIATION_REQUIRED":i<=12?
      "POSTED_PRIMARY_RESULTS_NEED_ADJUDICATION":"NO_POSTED_PRIMARY_RESULTS_FIND_ORIGINAL_READOUT",
    reviewPriority:i===0?1:i<=12?2:3,
    phase:i===0?["PHASE2","PHASE3"]:["PHASE3"],
    phaseAgreement:i===0?"MULTIPHASE_REVIEW_REQUIRED":"MATCHED_SINGLE_PHASE",
    phaseReviewerStatus:"NOT_INDEPENDENTLY_ADJUDICATED",
    officialRegistryUrl:"https://clinicaltrials.gov/study/"+id,
    registryLastUpdate:"2026-09-22",primaryOutcomeDefinitions:2,
    primaryOutcomeResultsPosted:i<=12?2:0,
    registrySnapshotId:"source-"+i,sourceRunId:"run-"+i,
    nextEvidenceAction:"Human review of original exact-NCT evidence is pending.",
    reviewQueuePosition:i+1,
  }));
  const current=queue[0];
  return {
    queue:{schema:"EXACT_NCT_EVIDENCE_REVIEW_QUEUE_V1",
      status:"READY_FOR_INDEPENDENT_EVIDENCE_REVIEW",
      canonicalTrials:29,phaseReconciliationRequired:1,
      postedPrimaryResultsNeedReview:12,noPostedPrimaryResults:16,
      reviewItems:queue,clinicalSignoff:false,
      fdaPredictions:{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"},
      certainty:"NOT_VALIDATED"},
    detail:{schema:"REGISTRY_RECONCILIATION_V1",nct,
      snapshotId:current.registrySnapshotId,sourceRunId:current.sourceRunId,
      currentRegistryPhases:current.phase,savedRegistryPhases:["PHASE3"],
      phaseAgreement:current.phaseAgreement,
      phaseAgreementExplanation:"Multiphase requires manual review",
      machineSourceIdentityVerified:true,reviewerVerifiedCurrentPhase:false,
      lastCompletedPhaseIndependentlyVerified:false,
      scientificSignoff:false,scientificGradesWritten:0,
      sourceType:"OFFICIAL_REGISTRY_SPONSOR_SUBMITTED",
      registryUrl:"https://clinicaltrials.gov/study/"+nct,
      sourceHashSha256:"a".repeat(64),savedStageHashSha256:"b".repeat(64),
      sponsor:"Test sponsor",title:"Phase review pilot",overallStatus:"ACTIVE_NOT_RECRUITING",
      latestRecordUpdatePosted:"2026-09-22",savedAt:"2026-11-08T20:11:00Z",
      fdaPredictions:{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"},
      certainty:"NOT_VALIDATED"}
  };
}
function sessionHeaders(){return {cookie:auth.COOKIE_NAME+"="+auth.makeSession()};}
test("read-only phase handoff requires dashboard cookie and isolated server-only credential",async()=>{
  const names=["DASHBOARD_PASSWORD","SESSION_SIGNING_KEY","PDUFA_MEDICAL_REVIEW_API_BASE_URL","PDUFA_MEDICAL_REVIEW_READ_KEY"];
  const saved=Object.fromEntries(names.map(name=>[name,process.env[name]])),oldFetch=global.fetch;
  try{
    process.env.DASHBOARD_PASSWORD="fixture-password-123456";
    process.env.SESSION_SIGNING_KEY="z".repeat(40);
    process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL="https://isolated.example";
    process.env.PDUFA_MEDICAL_REVIEW_READ_KEY="readonly-fixture-key";
    const url="http://localhost/api/predictions/medical-phase-handoff?nct="+nct;
    let calls=0;
    global.fetch=async (target,opts)=>{
      calls++;
      assert.equal(opts.headers["x-pdufa-internal-key"],"readonly-fixture-key");
      assert.equal(opts.redirect,"error");
      assert.equal(opts.cache,"no-store");
      const d=data();
      if(String(target).endsWith("/queue"))return Response.json(d.queue);
      assert.equal(target,"https://isolated.example/api/internal/medical-registry-reconciliation/"+nct+"/latest");
      return Response.json(d.detail);
    };
    assert.equal((await GET(new NextRequest(url))).status,401);
    assert.equal(calls,0);
    assert.equal((await GET(new NextRequest("http://localhost/api/predictions/medical-phase-handoff?nct=NCT99999999",
      {headers:sessionHeaders()}))).status,422);
    assert.equal(calls,0);
    const response=await GET(new NextRequest(url,{headers:sessionHeaders()}));
    assert.equal(response.status,200);
    assert.equal(response.headers.get("cache-control"),"private, no-store");
    const result=await response.json();
    assert.equal(result.canonicalTrials,29);
    assert.equal(result.queue.length,29);
    assert.equal(result.selected.nct,nct);
    assert.equal(result.selected.currentPhaseReviewerVerified,false);
    assert.equal(result.scientificGradesWritten,0);
    assert.equal(result.certainty,"NOT_VALIDATED");
    assert.equal(result.fdaPredictions.APPROVAL,"ABSTAIN");
    assert.ok(!JSON.stringify(result).includes("readonly-fixture-key"));
    assert.equal(calls,2);
    delete process.env.PDUFA_MEDICAL_REVIEW_READ_KEY;
    assert.equal((await GET(new NextRequest(url,{headers:sessionHeaders()}))).status,503);
    assert.equal(calls,2);
  }finally{
    global.fetch=oldFetch;
    for(const [name,value] of Object.entries(saved))
      if(value===undefined)delete process.env[name];else process.env[name]=value;
  }
});
test("phase handoff fails closed on drift, missing identity or fabricated signoff",async()=>{
  const names=["DASHBOARD_PASSWORD","SESSION_SIGNING_KEY","PDUFA_MEDICAL_REVIEW_API_BASE_URL","PDUFA_MEDICAL_REVIEW_READ_KEY"];
  const saved=Object.fromEntries(names.map(name=>[name,process.env[name]])),oldFetch=global.fetch;
  try{
    process.env.DASHBOARD_PASSWORD="fixture-password-123456";
    process.env.SESSION_SIGNING_KEY="z".repeat(40);
    process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL="https://isolated.example";
    process.env.PDUFA_MEDICAL_REVIEW_READ_KEY="readonly-fixture-key";
    const url="http://localhost/api/predictions/medical-phase-handoff?nct="+nct;
    for(const mutate of [
      d=>{d.detail.snapshotId="wrong-snapshot";},
      d=>{d.detail.reviewerVerifiedCurrentPhase=true;},
      d=>{d.queue.reviewItems.pop();},
      d=>{d.queue.reviewItems[0].nct="NCT99999999";},
      d=>{d.queue.clinicalSignoff=true;},
      d=>{d.queue.phaseReconciliationRequired=3;},
      d=>{d.detail.fdaPredictions.APPROVAL=0.6;},
      d=>{d.detail.sourceHashSha256="bogus";},
      d=>{d.detail.registryUrl="https://other.example/study/"+nct;}
    ]){
      const fixture=data();mutate(fixture);
      global.fetch=async target=>Response.json(String(target).endsWith("/queue")?fixture.queue:fixture.detail);
      const response=await GET(new NextRequest(url,{headers:sessionHeaders()}));
      assert.equal(response.status,503);
      assert.match((await response.json()).error,/not/);
    }
  }finally{
    global.fetch=oldFetch;
    for(const [name,value] of Object.entries(saved))
      if(value===undefined)delete process.env[name];else process.env[name]=value;
  }
});
