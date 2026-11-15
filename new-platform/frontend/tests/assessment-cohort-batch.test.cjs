const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,f);
const React=require('react'),{act,create}=require('react-test-renderer');
const Launcher=require('../app/AssessmentLauncher.tsx').default;
const {NextRequest}=require('next/server'),auth=require('../lib/auth.ts'),api=require('../app/api/assessments/runtime/route.ts');
globalThis.IS_REACT_ACT_ENVIRONMENT=true;
const base='https://owner.example.test',bid='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
process.env.DASHBOARD_PASSWORD='SYNTHETIC_PASSWORD';process.env.SESSION_SIGNING_KEY='SYNTHETIC_SIGNING_KEY_01234567890123456789';
function req(body){return new NextRequest(base+'/api/assessments/runtime',{method:'POST',headers:{origin:base,'content-type':'application/json',cookie:auth.COOKIE_NAME+'='+auth.makeSession()},body:JSON.stringify(body)});}
const button=(tree,name)=>tree.root.findAllByType('button').find(b=>React.Children.toArray(b.props.children).join('')===name);

test('whole inventory loads beyond fifty and submits server snapshot, with no caller evidence or partial membership',async()=>{
 const old=global.fetch;let tree,posted;const pages=[];
 const records=Array.from({length:61},(_,i)=>({key:'NCT'+String(i+1).padStart(8,'0'),nct:'NCT'+String(i+1).padStart(8,'0'),blocker:null}));
 global.fetch=async(url,init={})=>{
  if(init.method==='POST'){posted=JSON.parse(init.body);return Response.json({batchId:bid,population:'FOCUS',mode:'CURRENT_EVIDENCE',createdAt:'2026-11-15',status:'RESUMABLE',totalTrials:61,totalItems:183,counts:{completed:0,blocked:0,failed:0,scored:0},items:[],canResume:true,terminal:false});}
  const q=new URL('https://fixture.test'+url).searchParams;if(q.has('batches'))return Response.json({batches:[]});
  const offset=Number(q.get('offset'));pages.push(offset);return Response.json({population:'FOCUS',total:61,blocked:0,inventoryHash:'b'.repeat(64),source:{status:'SYNTHETIC_FIXTURE'},records:records.slice(offset,offset+50),nextOffset:offset===0?50:null});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Launcher));});await act(async()=>button(tree,'Assess Trials · Levels 1–3').props.onClick());
  await act(async()=>tree.root.findByProps({'aria-label':'Assessment scope'}).props.onChange({target:{value:'all'}}));
  await act(async()=>{button(tree,'Load complete FOCUS inventory').props.onClick();});
  assert.deepEqual(pages,[0,50]);assert.equal(button(tree,'Submit assessments').props.disabled,false);
  await act(async()=>button(tree,'Submit assessments').props.onClick());
  assert.equal(posted.scope,'all');assert.deepEqual(posted.ncts,[]);assert.equal(posted.inventoryHash,'b'.repeat(64));assert.equal(posted.action,'COHORT_BATCH_CREATE');
  assert.match(JSON.stringify(tree.toJSON()),/183/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('stale or truncated inventory cannot enable whole-list execution',async()=>{
 const old=global.fetch;let tree;
 global.fetch=async url=>String(url).includes('batches=')?Response.json({batches:[]}):Response.json({population:'FOCUS',total:61,blocked:0,inventoryHash:'b'.repeat(64),source:{status:'SYNTHETIC_FIXTURE'},records:[{key:'NCT00000001',nct:'NCT00000001',blocker:null}],nextOffset:null});
 try{
  await act(async()=>{tree=create(React.createElement(Launcher));});await act(async()=>button(tree,'Assess Trials · Levels 1–3').props.onClick());
  await act(async()=>tree.root.findByProps({'aria-label':'Assessment scope'}).props.onChange({target:{value:'all'}}));
  await act(async()=>button(tree,'Load complete FOCUS inventory').props.onClick());
  assert.equal(button(tree,'Submit assessments').props.disabled,true);assert.match(JSON.stringify(tree.toJSON()),/Incomplete source inventory/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('PAST uses historical mode and restores blocked checkpoints after reload without executing them',async()=>{
 const old=global.fetch;let tree,posts=0;
 const saved={batchId:bid,population:'HISTORICAL',mode:'BLIND_HISTORICAL',createdAt:'2026-11-15',status:'COMPLETED_WITH_BLOCKERS',totalTrials:20,totalItems:60,counts:{completed:0,blocked:60,failed:0,scored:0},items:[],canResume:false,terminal:true};
 global.fetch=async(url,init={})=>{if(init.method==='POST'){posts++;throw Error('No execution on saved-history reads');}return Response.json(String(url).includes('batchId=')?saved:{batches:[{batchId:bid,createdAt:'2026-11-15'}]});};
 try{
  await act(async()=>{tree=create(React.createElement(Launcher,{source:'HISTORICAL'}));});await act(async()=>button(tree,'Assess Trials · Levels 1–3').props.onClick());
  assert.equal(tree.root.findByProps({'aria-label':'Batch evidence mode'}).props.value,'BLIND_HISTORICAL');
  await act(async()=>tree.root.findByProps({'aria-label':'Saved assessment batches'}).props.onChange({target:{value:bid}}));
  assert.match(JSON.stringify(tree.toJSON()),/60/);assert.equal(posts,0);assert.equal(button(tree,'Resume saved batch'),undefined);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('cohort proxy preserves authentication and accepts only bounded selection and exact resume requests',async()=>{
 const old=global.fetch;process.env.PDUFA_API_BASE_URL='https://backend.example.test';process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';const urls=[];
 global.fetch=async(url,init)=>{urls.push(url);assert.equal(init.headers['X-Pdufa-Internal-Key'],'SYNTHETIC_INTERNAL_KEY');return Response.json({batchId:bid});};
 const selection={action:'COHORT_BATCH_CREATE',requestKey:bid,population:'FOCUS',scope:'selected',ncts:['NCT04576949'],levels:[1,2,3],mode:'CURRENT_EVIDENCE'};
 try{
  assert.equal((await api.POST(req(selection))).status,200);
  assert.equal((await api.POST(req({...selection,score:100}))).status,422);
  assert.equal((await api.POST(req({...selection,levels:[4]}))).status,422);
  assert.equal((await api.POST(req({action:'COHORT_BATCH_RESUME',batchId:bid}))).status,200);
  assert.equal((await api.POST(req({action:'COHORT_BATCH_RESUME',batchId:'../runs'}))).status,422);
  const get=new NextRequest(base+'/api/assessments/runtime?inventory=true&population=FOCUS&offset=50&limit=100',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
  assert.equal((await api.GET(get)).status,200);
  assert.deepEqual(urls,['https://backend.example.test/api/assessment-runtime/batches','https://backend.example.test/api/assessment-runtime/batches/'+bid+'/resume','https://backend.example.test/api/assessment-runtime/cohort-inventory?population=FOCUS&offset=50&limit=100']);
 }finally{global.fetch=old;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});
