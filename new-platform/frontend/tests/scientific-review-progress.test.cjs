"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const { validateScientificPairProgress } = loadTS(
  path.join(__dirname, "../lib/scientific-review-progress.ts"),
);
function loadTS(file, mocks={}) {
  const source = fs.readFileSync(file, "utf8");
  const built = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  const mod = { exports: {} };
  new Function("require", "module", "exports", built)(
    name => {
      if (!(name in mocks)) throw Error("Unexpected dependency: " + name);
      return mocks[name];
    }, mod, mod.exports,
  );
  return mod.exports;
}
const NCT = "NCT02142738";
const GATES = ["protocol_sap","published_results","independent_replication","official_regulatory"];
function fixture() {
  const gates = GATES.map((gateId, i) => ({
    gateId, capturedSourceCount: i === 0 ? 1 : 0,
    reconciliationQuestionCount: i === 0 ? 1 : i === 1 ? 5 : 1,
    eligibleQuestionSourcePairs: i === 0 ? 1 : 0,
    pairingTechnicalPreflightPassed: i === 0 ? 1 : 0,
    twoAuthorizedReviewersRecorded: i === 0 ? 1 : 0,
    disputedTechnicalPairCount: 0,
    historicalAuditCorruptionPairs: 0,
  }));
  return {
    nctId: NCT, mode: "isolated_read_only_technical_reviewer_preflight",
    sourceDocumentCount: 1, questionCount: 8, eligibleQuestionSourcePairs: 1,
    pairingTechnicalPreflightPassedCount: 1, disputedTechnicalPairCount: 0,
    historicalAuditCorruptionPairs: 0, gates,
    capturedBytesRehashed: true, independentClinicalReviewCount: 0,
    verifiedClinicalSourceCount: 0, qualifiedIndependenceAdjudicated: false,
    formalSecondPersonSignoffCount: 0, scientificAdjudicationComplete: false,
    readyForScientificConclusion: false, scientificScore: null,
    fdaApprovalProbability: null, mayPromoteScientificScore: false,
  };
}
test("aggregate accepted only for technically consistent, non-adjudicated pilot rows", () => {
  const input = fixture();
  input.reviewerEmail = "should never be copied";
  input.gates[0].google_subject = "private";
  const result = validateScientificPairProgress(input);
  assert.equal(result.nctId,NCT);
  assert.equal(result.pairingTechnicalPreflightPassedCount,1);
  assert.equal(result.sourceDocumentCount,1);
  assert.equal(result.gates.length,4);
  assert.equal(result.independentClinicalReviewCount,0);
  assert.equal(result.verifiedClinicalSourceCount,0);
  assert.equal(result.scientificScore,null);
  assert.equal(result.fdaApprovalProbability,null);
  assert.equal(result.scientificAdjudicationComplete,false);
  assert.equal(result.mayPromoteScientificScore,false);
  assert.doesNotMatch(JSON.stringify(result), /should never be copied|private|google_subject|reviewerEmail/);
});
test("zero sources or reviewed statements is an incomplete technical preflight", () => {
  const input=fixture();
  input.sourceDocumentCount=0; input.eligibleQuestionSourcePairs=0;
  input.pairingTechnicalPreflightPassedCount=0;
  input.gates[0].capturedSourceCount=0;
  input.gates[0].eligibleQuestionSourcePairs=0;
  input.gates[0].pairingTechnicalPreflightPassed=0;
  input.gates[0].twoAuthorizedReviewersRecorded=0;
  const report=validateScientificPairProgress(input);
  assert.equal(report.scientificAdjudicationComplete,false);
  assert.equal(report.independentClinicalReviewCount,0);
});
test("tampered gate, identity, signing claim, count, or pairing totals fail closed", () => {
  const mutations=[
    x=>{x.nctId="NCT00000001";},x=>{x.mode="clinical_approved";},
    x=>{x.capturedBytesRehashed=false;},
    x=>{x.independentClinicalReviewCount=1;},
    x=>{x.verifiedClinicalSourceCount=1;},
    x=>{x.qualifiedIndependenceAdjudicated=true;},
    x=>{x.formalSecondPersonSignoffCount=1;},
    x=>{x.scientificAdjudicationComplete=true;},
    x=>{x.readyForScientificConclusion=true;},
    x=>{x.scientificScore=88;},x=>{x.fdaApprovalProbability=.91;},
    x=>{x.mayPromoteScientificScore=true;},
    x=>{x.questionCount=7;},x=>{x.sourceDocumentCount=2;},
    x=>{x.eligibleQuestionSourcePairs=20;},
    x=>{x.pairingTechnicalPreflightPassedCount=2;},
    x=>{x.gates[0].gateId="unsafe";},
    x=>{x.gates[0].pairingTechnicalPreflightPassed=2;},
    x=>{x.gates[0].reconciliationQuestionCount=0;},
    x=>{x.gates[0].twoAuthorizedReviewersRecorded=0;},
    x=>{x.gates=[...x.gates,...x.gates];},
    x=>{x.gates[0].disputedTechnicalPairCount=9;},
  ];
  for(const mutation of mutations){
    const x=fixture();mutation(x);
    assert.throws(()=>validateScientificPairProgress(x),/contract unverified/,String(mutation));
  }
});
const routeFile=path.join(__dirname,"../app/api/scientific-assessment/reviewer-progress/route.ts");
function route({ authorized=true,status=200,marker=true,upstream=fixture() }={}){
  const calls=[];
  const api=loadTS(routeFile,{
    "next/server":{NextResponse:{json:(body,options={})=>({
      body,status:options.status??200,headers:options.headers??{},
    })}},
    "../../../../lib/auth":{
      COOKIE_NAME:"cookie",authConfigured:()=>true,
      hasSession:session=>authorized&&session==="allowed",
    },
    "../../../../lib/read-only-warm-retry":{
      fetchReadOnlyWithWarmRetry:async (url,init)=>{
        calls.push({url,init});
        return {ok:status===200,status,
          headers:{get:()=>marker?"science-review-pair-progress-v1":"other-contract"},
          json:async()=>upstream};
      },
    },
    "../../../../lib/scientific-review-progress":{validateScientificPairProgress},
  });
  const request=async(nct=NCT,extra=false)=>{
    const url=new URL("https://example.test/api/scientific-assessment/reviewer-progress");
    url.searchParams.set("nct_id",nct);
    if(extra)url.searchParams.set("extra","true");
    return api.GET({nextUrl:url,cookies:{get:()=>({value:"allowed"})}});
  };
  return {request,calls};
}
async function withEnv(fn){
  const keys=["PDUFA_SCIENTIFIC_API_BASE_URL","PDUFA_SCIENTIFIC_PREVIEW_READ_KEY",
    "PDUFA_INTERNAL_API_KEY","PDUFA_API_BASE_URL"];
  const original=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
  process.env.PDUFA_SCIENTIFIC_API_BASE_URL="https://isolated-science.example.com";
  process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY="TEST_READ_ONLY_KEY_NOT_REAL";
  process.env.PDUFA_INTERNAL_API_KEY="ORDINARY_KEY_MUST_NOT_USE";
  process.env.PDUFA_API_BASE_URL="https://normal-dashboard.example.com";
  try {return await fn();}
  finally {for(const k of keys)if(original[k]===undefined)delete process.env[k];else process.env[k]=original[k];}
}
test("proxy rejects unauthenticated and wrong trial before any backend request",async()=>withEnv(async()=>{
  const denied=route({authorized:false});assert.equal((await denied.request()).status,401);
  assert.equal(denied.calls.length,0);
  const wrong=route();assert.equal((await wrong.request("NCT12345678")).status,422);
  assert.equal((await wrong.request(NCT,true)).status,422);
  assert.equal(wrong.calls.length,0);
}));
test("proxy uses dedicated isolated read key, returns only strictly projected nonclinical counts",async()=>withEnv(async()=>{
  const mock=route();
  const response=await mock.request();
  assert.equal(response.status,200);
  assert.equal(response.headers["Cache-Control"],"private, no-store");
  assert.equal(mock.calls.length,1);
  assert.equal(mock.calls[0].url,"https://isolated-science.example.com/api/scientific-assessment/pilot/reviewer-progress/"+NCT);
  assert.equal(mock.calls[0].init.cache,"no-store");
  assert.equal(mock.calls[0].init.headers["x-pdufa-internal-key"],"TEST_READ_ONLY_KEY_NOT_REAL");
  assert.doesNotMatch(JSON.stringify(response.body),/google_subject|reviewerEmail|clinicalIndependenceVerified/);
}));
test("proxy refuses missing contract, backend denial, and forged clinical conclusions",async()=>withEnv(async()=>{
  assert.equal((await route({status:401}).request()).status,503);
  assert.equal((await route({marker:false}).request()).status,503);
  const forged=fixture();forged.scientificAdjudicationComplete=true;
  assert.equal((await route({upstream:forged}).request()).status,503);
}));
test("the trial UI uses only the protected route and never claims scientific adjudication",()=>{
  const ui=fs.readFileSync(path.join(__dirname,"../app/ScientificAssessment.tsx"),"utf8");
  assert.match(ui,/Check technical A\/B reviewer progress/);
  assert.match(ui,/reviewer-progress\?nct_id=NCT02142738/);
  assert.match(ui,/validateScientificPairProgress\(await response.json\(\)\)/);
  assert.match(ui,/Independent clinical reviews: 0/);
  assert.match(ui,/Qualified clinical adjudication: NOT COMPLETE/);
  assert.match(ui,/setScientificReviewerPairProgress\(null\)/);
  assert.doesNotMatch(ui,/promoteReviewerPair|automaticallyApproveClinicalSources/);
});
