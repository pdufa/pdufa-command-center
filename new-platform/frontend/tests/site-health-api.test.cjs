const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
require.extensions['.ts']=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,filename);
const {NextRequest}=require('next/server');
const auth=require('../lib/auth.ts');
const route=require('../app/api/site-health/route.ts');

test('Unauthenticated health request cannot probe backend, reports, or mailbox data',async()=>{
 const original=global.fetch;
 global.fetch=async()=>assert.fail('Unauthenticated outbound request');
 try{
  const response=await route.GET(new NextRequest('https://dashboard.example/api/site-health'));
  assert.equal(response.status,401);
  assert.equal(route.POST,undefined,'Health endpoint must remain read-only');
 }finally{global.fetch=original;}
});
test('Authenticated health aggregates independent evidence and exposes exact safe-scope zero email count',async()=>{
 const originalFetch=global.fetch;
 const keys=['DASHBOARD_PASSWORD','SESSION_SIGNING_KEY','PDUFA_API_BASE_URL','PDUFA_INTERNAL_API_KEY','VERCEL_GIT_COMMIT_SHA'];
 const originals=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
 Object.assign(process.env,{DASHBOARD_PASSWORD:'test-only-health-password',SESSION_SIGNING_KEY:'test-only-health-signing-key-long-enough',
  PDUFA_API_BASE_URL:'https://backend.example',PDUFA_INTERNAL_API_KEY:'internal-test-value',VERCEL_GIT_COMMIT_SHA:'a'.repeat(40)});
 const dated={updated_at_utc:new Date().toISOString()};
 const requested=[];
 global.fetch=async(url,options)=>{
  requested.push({url,options});
  let result;
  if(url==='https://backend.example/health')result={service:'pdufa-new-backend',storage_ready:true,status:'ok'};
  else if(url==='https://backend.example/api/workspace/summary')result={pipeline:11775,gemJr:11,gem:6};
  else if(url.endsWith('/nightly_scan_report.json'))result={...dated,scans:Array(3).fill({collector_status:'COMPLETE'})};
  else if(url.endsWith('/pdufa_source_report.json'))result={...dated,status:'PARTIAL',required_findings_unresolved:23,full_coverage_verified:false};
  else if(url.endsWith('/nightly_scoring_audit.json'))result={...dated,status:'REVIEW_REQUIRED',counts:{data_gaps:4}};
  else if(url.endsWith('/pdufa_mail_count.json'))result={...dated,scope:'PDUFA_ONLY_EXCLUDING_INBOX_TRASH_SPAM',status:'CHECKED',total_count:0,unread_count:0};
  else if(url.endsWith('/status'))result={statuses:[{context:'Vercel',state:'success'}]};
  else assert.fail('Unexpected destination '+url);
  return {ok:true,json:async()=>result};
 };
 try{
  const request=new NextRequest('https://dashboard.example/api/site-health',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
  const response=await route.GET(request);
  const data=await response.json();
  assert.equal(response.status,200);
  assert.equal(data.checks.length,10);
  const get=id=>data.checks.find(c=>c.id===id);
  assert.equal(get('backend').state,'good');
  assert.equal(get('lists').summary,'11,775');
  assert.equal(get('lists').label,'POOL source inventory');
  assert.equal(get('scans').state,'good');
  assert.equal(get('sources').state,'warning');
  assert.equal(get('scoring').state,'warning');
  assert.equal(get('controls').state,'unknown');
  assert.equal(get('screens').state,'unknown');
  assert.equal(get('email').state,'good');
  assert.equal(get('email').summary,'0 emails · 0 unread');
  assert.ok(requested.every(r=>!r.options.method||r.options.method==='GET'));
  assert.ok(requested.every(r=>!r.url.includes('gmail.com')),'Endpoint reads saved count, never mailbox or Inbox');
  assert.ok(!JSON.stringify(data).includes('internal-test-value'));
 }finally{
  global.fetch=originalFetch;
  for(const [key,value]of Object.entries(originals)){if(value===undefined)delete process.env[key];else process.env[key]=value;}
 }
});
