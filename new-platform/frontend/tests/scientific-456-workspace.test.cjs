const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(
 ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,f
);
const {NextRequest}=require('next/server');
const auth=require('../lib/auth.ts');
const api=require('../app/api/assessments/runtime/route.ts');
const Workspace=require('../app/Scientific456Workspace.tsx').default;
process.env.DASHBOARD_PASSWORD='SYNTHETIC_RUNTIME_PASSWORD';
process.env.SESSION_SIGNING_KEY='SYNTHETIC_RUNTIME_KEY_01234567890123456789';
const base='https://owner.example.test',nct='NCT04576949',runId='a'.repeat(8)+'-'+['a'.repeat(4),'a'.repeat(4),'a'.repeat(4),'a'.repeat(12)].join('-');
function post(body,extra={}){
 return new NextRequest(base+'/api/assessments/runtime',{method:'POST',headers:{
  origin:base,'content-type':'application/json',cookie:auth.COOKIE_NAME+'='+auth.makeSession(),...extra
 },body:JSON.stringify(body)});
}
function get(query){
 return new NextRequest(base+'/api/assessments/runtime?'+new URLSearchParams(query),{
  headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}
 });
}
test('four independent page mounts expose the 456 scientific workspace',()=>{
 for(const [page,cohort] of [['focus','FOCUS'],['past','PAST'],['pool','POOL'],['assessments','ASSESSMENTS']]){
  const text=fs.readFileSync(path.join(__dirname,'../app',page,'page.tsx'),'utf8');
  assert.match(text,new RegExp('<Scientific456Workspace cohort="'+cohort+'"'));
 }
 const focus=fs.readFileSync(path.join(__dirname,'../app/focus/page.tsx'),'utf8');
 assert.match(focus,/L04–L06 saved scientific research/);
 assert.match(focus,/assessments\?nct=/);
});
test('456 workspace lists correct evidence domains, exact-NCT selection and blind history',()=>{
 const current=renderToStaticMarkup(React.createElement(Workspace,{cohort:'FOCUS',initialNct:nct}));
 const historical=renderToStaticMarkup(React.createElement(Workspace,{cohort:'PAST'}));
 for(const s of ['Safety and benefit-risk','Indication-specific clinical assessment','FDA regulatory readiness'])
  assert.ok(current.includes(s));
 assert.match(current,/SCIENTIFIC|Scientific L04–L06/);
 assert.match(current,/NCT04576949/);
 assert.match(current,/NOT VALIDATED/);
 assert.match(current,/No validated scientific score/);
 assert.match(historical,/Pre-decision cutoff/);
 assert.match(historical,/Blind historical cutoff/);
});
test('456 requests use dedicated HTTPS credentials, never production 123 credentials',async()=>{
 const vars=['PDUFA_LEVEL456_API_BASE_URL','PDUFA_LEVEL456_INTERNAL_API_KEY','PDUFA_LEVEL123_API_BASE_URL','PDUFA_LEVEL123_INTERNAL_API_KEY'];
 const originals=Object.fromEntries(vars.map(x=>[x,process.env[x]]));
 const old=global.fetch,urls=[];
 process.env.PDUFA_LEVEL456_API_BASE_URL='https://isolated-456.example.test';
 process.env.PDUFA_LEVEL456_INTERNAL_API_KEY='ISOLATED_SECRET';
 process.env.PDUFA_LEVEL123_API_BASE_URL='https://production-123.example.test';
 process.env.PDUFA_LEVEL123_INTERNAL_API_KEY='PRODUCTION_SECRET';
 global.fetch=async(url,init)=>{
  urls.push(String(url));
  assert.match(String(url),/^https:\/\/isolated-456\.example\.test\/api\/assessment-runtime\//);
  assert.equal(init.headers['X-Pdufa-Internal-Key'],'ISOLATED_SECRET');
  if(init.method==='POST')return Response.json({status:'QUEUED',runId},{status:202});
  return Response.json({nct,runs:[],hasMore:false});
 };
 try{
  for(const level of [4,5,6]){
   const response=await api.POST(post({nct,level,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_6'}));
   assert.equal(response.status,202);
  }
  const history=await api.GET(get({nct,contract:'SCIENTIFIC_1_6'}));
  assert.equal(history.status,200);
  assert.deepEqual((await history.json()).runs,[]);
  assert.equal(urls.length,4);
  assert.equal((await api.POST(post({nct,level:4,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_3'}))).status,422);
  assert.equal((await api.POST(post({nct,level:4,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_6',score:88}))).status,422);
  assert.equal((await api.POST(post({nct,level:4,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_6'},{origin:'https://evil.example.test'}))).status,403);
  assert.equal((await api.GET(get({nct,contract:'SPOOFED'}))).status,422);
  delete process.env.PDUFA_LEVEL456_API_BASE_URL;
  delete process.env.PDUFA_LEVEL456_INTERNAL_API_KEY;
  assert.equal((await api.POST(post({nct,level:4,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_6'}))).status,503);
  assert.equal((await api.GET(get({nct,contract:'SCIENTIFIC_1_6'}))).status,503);
  assert.equal(urls.length,4,'No fallback to the configured 123 backend');
 }finally{
  global.fetch=old;
  for(const v of vars)if(originals[v]===undefined)delete process.env[v];else process.env[v]=originals[v];
 }
});
