const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
const {gunzipSync} = require("node:zlib");
for(const ext of [".ts",".tsx"]) require.extensions[ext] = (mod,file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
  }}).outputText,file);
const {fetchReadOnlyWithWarmRetry} = require("../lib/read-only-warm-retry.ts");
const reply=(status,data={status:"ok"})=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json"}});
const noDelay=async()=>{};
test("read-only recovery retries only once for 502/503 and shares caller timeout", async()=>{
  let calls=0;
  const signal=AbortSignal.timeout(30000);
  const f=async(_url,init)=>{calls++;assert.equal(init.signal,signal);assert.equal(init.method,"GET");return reply(calls===1?503:200)};
  const response=await fetchReadOnlyWithWarmRetry("https://example.org/api/score",
    {signal,cache:"no-store"},{fetcher:f,pause:noDelay});
  assert.equal(response.status,200);
  assert.equal(calls,2);
  calls=0;
  const limited=await fetchReadOnlyWithWarmRetry("https://example.org/api/score",
    {signal},{fetcher:async()=>{calls++;return reply(503)},pause:noDelay});
  assert.equal(limited.status,503);assert.equal(calls,2);
});
test("authentication, conflict and malformed statuses never retry, and writes are prohibited",async()=>{
  for(const status of [400,401,403,404,409,422]){
    let calls=0;
    const result=await fetchReadOnlyWithWarmRetry("https://example.org/a",{method:"GET"},{
      fetcher:async()=>{calls++;return reply(status)},pause:noDelay});
    assert.equal(result.status,status);assert.equal(calls,1);
  }
  let calls=0;
  await assert.rejects(()=>fetchReadOnlyWithWarmRetry("https://example.org/a",{method:"POST"},{
    fetcher:async()=>{calls++;return reply(503)},pause:noDelay}),/Only GET/);
  assert.equal(calls,0);
  const ctrl=new AbortController();
  await assert.rejects(()=>fetchReadOnlyWithWarmRetry("https://example.org/a",{signal:ctrl.signal},{
    fetcher:async()=>{calls++;return reply(503)},pause:async()=>ctrl.abort()}),/deadline exceeded/);
  assert.equal(calls,1);
});
test("signed scoring and paginated requests recover once; 409 and auth are fail-closed",async()=>{
  const {NextRequest}=require("next/server");
  const auth=require("../lib/auth.ts");
  const score=require("../app/api/assessments/route.ts");
  const page=require("../app/api/workspace/page/route.ts");
  const vars=["DASHBOARD_PASSWORD","SESSION_SIGNING_KEY","PDUFA_API_BASE_URL","PDUFA_INTERNAL_API_KEY","PDUFA_RESEARCH_API_BASE_URL"];
  const previous=Object.fromEntries(vars.map(k=>[k,process.env[k]])),oldFetch=global.fetch;
  Object.assign(process.env,{
    DASHBOARD_PASSWORD:"test-only-pwd",
    SESSION_SIGNING_KEY:"test-only-long-session-signing-key",
    PDUFA_API_BASE_URL:"https://storage.example",
    PDUFA_RESEARCH_API_BASE_URL:"https://research.example",
    PDUFA_INTERNAL_API_KEY:"test-only-private-key"
  });
  const cookie=auth.COOKIE_NAME+"="+auth.makeSession();
  const req=(pathname,signed=true)=>new NextRequest("http://localhost"+pathname,{headers:signed?{cookie}:{}});
  const pageData={version:"b".repeat(64),total:1,offset:0,limit:50,
    rows:[{id:"TRIAL|EXACT",ticker:"TEST"}],nextOffset:null};
  try{
    let calls=[];
    global.fetch=async(url,options)=>{calls.push({url,options});return reply(calls.length===1?503:200,
      {status:"COMPLETE",total:11795,records:[]})};
    assert.equal((await score.GET(req("/api/assessments",false))).status,401);
    assert.equal(calls.length,0);
    const success=await score.GET(req("/api/assessments"));
    assert.equal(success.status,200);
    assert.equal(calls.length,2);
    assert.ok(calls.every(c=>c.url==="https://storage.example/api/candidate-assessments"));
    assert.equal(calls[0].options.headers["x-pdufa-internal-key"],"test-only-private-key");
    assert.equal(success.headers.get("content-encoding"),"gzip");
    assert.equal(JSON.parse(gunzipSync(Buffer.from(await success.arrayBuffer()))).total,11795);
    calls=[];
    global.fetch=async(url,opts)=>{calls.push({url,opts});return reply(calls.length===1?502:200,pageData)};
    const p=await page.GET(req("/api/workspace/page?offset=0&limit=50"));
    assert.equal(p.status,200);assert.equal((await p.json()).rows[0].ticker,"TEST");assert.equal(calls.length,2);
    assert.ok(calls.every(c=>c.url.startsWith("https://storage.example/api/workspace/page?")));
    calls=[];
    global.fetch=async()=>{calls.push("called");return reply(409)};
    assert.equal((await page.GET(req("/api/workspace/page?offset=0&limit=50"))).status,409);
    assert.equal(calls.length,1);
    calls=[];
    global.fetch=async()=>{calls.push("called");return reply(503)};
    assert.equal((await page.GET(req("/api/workspace/page?offset=0&limit=50"))).status,503);
    assert.equal(calls.length,2);
  }finally{
    global.fetch=oldFetch;
    for(const k of vars)if(previous[k]===undefined)delete process.env[k];else process.env[k]=previous[k];
  }
});
