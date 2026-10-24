const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for(const ext of [".ts",".tsx"]) require.extensions[ext] = (mod,file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
  }}).outputText,file);
const {researchBackendBase} = require("../lib/research-backend.ts");
const {verifiedMarketEnrichment} = require("../lib/verified-market-enrichment.ts");
const PID = "PDUFA-000001";
const EXACT = "TRIAL|NCT01234567|ABC";
function verifiedMarket() {
  return {
    programId: PID, exactKey: EXACT, ticker: "ABC", provider: "ALPACA",
    status: "OK", researchOnly: true, orderExecutionEnabled: false,
    qualificationChanges: false, restrictionChanges: false, fsFaChanges: false,
    feed: "IEX", latestDailyClose: 10.25, latestIexVolume: 200,
    marketSignals: {status:"OK",validBars:98,return20Pct:3.1,
      averageVolume20:150,volumeRatio20:1.33},
    marketEvidenceReview: {programId:PID,exactKey:EXACT,status:"RESEARCH_ONLY",
      observations:[{metric:"20-bar price change",value:3.1,unit:"%"},
        {metric:"Latest IEX volume / 20-bar average",value:1.33,unit:"ratio"}],
      recommendation:null,assessmentScoreChange:false,qualificationChange:false,fsFaChange:false},
  };
}
test("read-only market facts must retain program identity and disabled order boundaries",()=>{
  const good=verifiedMarket();
  assert.equal(verifiedMarketEnrichment(good, PID),good);
  for (const change of [
    x=>x.programId="PDUFA-000002", x=>x.exactKey="", x=>x.orderExecutionEnabled=true,
    x=>x.researchOnly=false, x=>x.restrictionChanges=true, x=>x.fsFaChanges=true,
    x=>x.marketEvidenceReview.programId="PDUFA-000002",
    x=>x.marketEvidenceReview.exactKey="OTHER",
    x=>x.marketEvidenceReview.recommendation="BUY",
    x=>x.marketEvidenceReview.assessmentScoreChange=true,
    x=>x.marketEvidenceReview.observations=[{metric:"x",value:Infinity,unit:"ratio"}],
    x=>x.marketSignals.return20Pct=Infinity,
    x=>x.marketSignals.validBars=0,
    x=>x.latestDailyClose=-5,
  ]) {
    const bad=structuredClone(good);change(bad);
    assert.throws(()=>verifiedMarketEnrichment(bad, PID));
  }
  const offline=verifiedMarket();
  offline.status="ALPACA_AUTH_FAILED";
  offline.latestDailyClose=null;offline.latestIexVolume=null;
  offline.marketSignals={status:"INSUFFICIENT_DATA",validBars:0,return20Pct:null,averageVolume20:null,volumeRatio20:null};
  offline.marketEvidenceReview={...offline.marketEvidenceReview,status:"INSUFFICIENT_EVIDENCE",observations:[]};
  assert.equal(verifiedMarketEnrichment(offline, PID),offline);
});


function withEnv(values,fn){
  const keys=["PDUFA_API_BASE_URL","PDUFA_RESEARCH_API_BASE_URL"];
  const saved=Object.fromEntries(keys.map(x=>[x,process.env[x]]));
  try {
    for(const k of keys) delete process.env[k];
    Object.assign(process.env,values);
    return fn();
  } finally {
    for(const k of keys) if(saved[k]===undefined)delete process.env[k];else process.env[k]=saved[k];
  }
}
test("only read-only research routes can override the old backend",()=>{
  withEnv({PDUFA_API_BASE_URL:"https://pdufa-new-api-staging.onrender.com",
    PDUFA_RESEARCH_API_BASE_URL:"https://pdufa-alpaca-enrichment-review.onrender.com"},()=>{
    assert.equal(researchBackendBase(),"https://pdufa-alpaca-enrichment-review.onrender.com");
  });
  withEnv({PDUFA_API_BASE_URL:"https://pdufa-new-api-staging.onrender.com"},()=>{
    assert.equal(researchBackendBase(),"https://pdufa-new-api-staging.onrender.com");
  });
  const regular=fs.readFileSync(require("node:path").join(__dirname,"../app/api/workspace/route.ts"),"utf8");
  assert.doesNotMatch(regular,/PDUFA_RESEARCH_API_BASE_URL|researchBackendBase/);
});
test("only root HTTPS URLs with no credentials or query are accepted",()=>{
  for(const base of ["http://example.org","https://user:password@example.org",
    "https://example.org/path","https://example.org?token=x",
    "https://example.org/#frag","file:///etc/passwd","not a URL"]){
    withEnv({PDUFA_RESEARCH_API_BASE_URL:base},()=>{
      assert.equal(researchBackendBase(),null,base);
    });
  }
});
test("market enrichment proxy uses isolated URL and remains session-protected",async()=>{
  const {NextRequest}=require("next/server");
  const auth=require("../lib/auth.ts");
  const route=require("../app/api/program-market-enrichment/[programId]/route.ts");
  const keys=["PDUFA_API_BASE_URL","PDUFA_RESEARCH_API_BASE_URL","PDUFA_INTERNAL_API_KEY",
    "DASHBOARD_PASSWORD","SESSION_SIGNING_KEY"];
  const previous=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
  const oldFetch=global.fetch;
  Object.assign(process.env,{
    PDUFA_API_BASE_URL:"https://legacy.example",
    PDUFA_RESEARCH_API_BASE_URL:"https://review.example",
    PDUFA_INTERNAL_API_KEY:"test-only-internal-key",
    DASHBOARD_PASSWORD:"test-only-password",
    SESSION_SIGNING_KEY:"test-only-long-enough-signing-key"
  });
  const cookie=auth.COOKIE_NAME+"="+auth.makeSession();
  const ctx={params:Promise.resolve({programId:"PDUFA-000001"})};
  const req=(signed,range="1M")=>new NextRequest("http://localhost/api/program-market-enrichment/PDUFA-000001?range="+range,
    {headers:signed?{cookie}:{}});
  const calls=[];
  global.fetch=async(url,options)=>{
    calls.push({url,options});
    return {ok:true,status:200,json:async()=>verifiedMarket()};
  };
  try{
    assert.equal((await route.GET(req(false),ctx)).status,401);
    assert.equal((await route.GET(req(true,"nope"),ctx)).status,422);
    assert.equal(calls.length,0);
    const reply=await route.GET(req(true),ctx);
    assert.equal(reply.status,200);
    assert.equal(calls.length,1);
    assert.equal(calls[0].url,"https://review.example/api/program-market-enrichment/PDUFA-000001?range=1M");
    assert.equal(calls[0].options.headers["x-pdufa-internal-key"],"test-only-internal-key");
    assert.equal(calls[0].options.redirect,"error");
    assert.equal(reply.headers.get("cache-control"),"private, no-store");
    assert.doesNotMatch(JSON.stringify(await reply.json()),/test-only-internal-key/);
    global.fetch=async()=>({ok:true,status:200,json:async()=>({...verifiedMarket(),orderExecutionEnabled:true})});
    assert.equal((await route.GET(req(true),ctx)).status,503);
    global.fetch=async()=>({ok:true,status:200,json:async()=>({...verifiedMarket(),programId:"PDUFA-000002"})});
    assert.equal((await route.GET(req(true),ctx)).status,503);
    global.fetch=async()=>({ok:false,status:401,json:async()=>({secret:"backend-internal-reason"})});
    const unauthorized=await route.GET(req(true),ctx);
    assert.equal(unauthorized.status,503);
    assert.doesNotMatch(JSON.stringify(await unauthorized.json()),/backend-internal-reason/);
    global.fetch=async()=>({ok:false,status:404,json:async()=>({secret:"backend-internal-reason"})});
    assert.equal((await route.GET(req(true),ctx)).status,404);
  }finally{
    global.fetch=oldFetch;
    for(const key of keys)if(previous[key]===undefined)delete process.env[key];else process.env[key]=previous[key];
  }
});
test("decision readiness proxy inherits separate source without changing assessment writes",()=>{
  const review=fs.readFileSync(require("node:path").join(__dirname,
    "../app/api/review/program-decision-readiness/[programId]/route.ts"),"utf8");
  assert.match(review,/researchBackendBase\(\)/);
  assert.match(review,/researchReadiness\(await response\.json\(\), programId, identity, stage\)/);
  assert.match(review,/redirect: "error"/);
  assert.doesNotMatch(review,/POST|PUT|DELETE/);
});
