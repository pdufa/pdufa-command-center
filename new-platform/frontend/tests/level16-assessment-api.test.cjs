const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,f);
const {NextRequest}=require('next/server'),auth=require('../lib/auth.ts'),api=require('../app/api/assessments/levels1-6/route.ts');
process.env.DASHBOARD_PASSWORD='SYNTHETIC_TEST_ONLY_PASSWORD';process.env.SESSION_SIGNING_KEY='SYNTHETIC_TEST_ONLY_SIGNING_KEY_0123456789';
const base='https://owner.example.test';
function req(body,extra={},signed=true){return new NextRequest(base+'/api/assessments/levels1-6',{method:'POST',headers:{origin:base,'content-type':'application/json',...(signed?{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}:{}),...extra},body:JSON.stringify(body)});}
test('options require authentication and do not create a run',async()=>{
 assert.equal((await api.GET(new NextRequest(base+'/api/assessments/levels1-6'))).status,401);
 const response=await api.GET(new NextRequest(base+'/api/assessments/levels1-6',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}}));
 const data=await response.json();assert.equal(data.trials.length,32);assert.equal(data.runId,undefined);assert.match(response.headers.get('cache-control'),/no-store/);
});
test('unauthenticated or forged sessions cannot run assessments',async()=>{
 assert.equal((await api.POST(req({scope:'ALL'},{},false))).status,401);assert.equal((await api.POST(req({scope:'ALL'},{cookie:auth.COOKIE_NAME+'=forged'}))).status,401);
});
test('authenticated one/all API calls execute six or 192 levels',async()=>{
 for(const [body,count] of [[{scope:'ONE',nct:'NCT04576949'},6],[{scope:'ALL'},192]]){const response=await api.POST(req(body));assert.equal(response.status,200);const data=await response.json();assert.equal(data.summary.levelsProcessed,count);assert.equal(data.ownerReviewStatus,'OWNER_NOT_REVIEWED');assert.equal(data.savedToDatabase,false);}
});
test('cross-origin and absent origin requests cannot execute',async()=>{
 assert.equal((await api.POST(req({scope:'ALL'},{origin:'https://other.example.test'}))).status,403);const request=req({scope:'ALL'});request.headers.delete('origin');assert.equal((await api.POST(request)).status,403);
});
test('review flags, arbitrary roles and out-of-FOCUS identities are rejected',async()=>{
 for(const body of [{scope:'ALL',reviewed:true},{scope:'ALL',role:'admin'},{scope:'ONE',nct:'NCT99999999'}])assert.equal((await api.POST(req(body))).status,422);
});
test('request size is bounded independently of content-length',async()=>{
 assert.equal((await api.POST(req({scope:'ALL'},{'content-length':'1025'}))).status,413);assert.equal((await api.POST(req({scope:'ALL',padding:'x'.repeat(2048)}))).status,413);assert.equal((await api.POST(req({scope:'ALL'},{'content-type':'text/plain'}))).status,415);
});
test('malformed JSON and absent bodies cannot claim completion',async()=>{
 const request=req({scope:'ALL'});assert.equal((await api.POST(new NextRequest(request.url,{method:'POST',headers:request.headers,body:'{'}))).status,422);assert.equal((await api.POST(new NextRequest(request.url,{method:'POST',headers:request.headers}))).status,422);
});
test('missing auth configuration fails closed without a fabricated identity provider',async()=>{
 const key=process.env.SESSION_SIGNING_KEY;delete process.env.SESSION_SIGNING_KEY;try{assert.equal((await api.POST(req({scope:'ALL'}))).status,401);}finally{process.env.SESSION_SIGNING_KEY=key;}
});
