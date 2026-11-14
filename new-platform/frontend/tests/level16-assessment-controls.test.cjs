const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript'),React=require('react');
const {act,create}=require('react-test-renderer');globalThis.IS_REACT_ACT_ENVIRONMENT=true;
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,f);
const Runner=require('../app/LevelSixAssessmentRunner.tsx').default;
const {NextRequest}=require('next/server'),auth=require('../lib/auth.ts'),api=require('../app/api/assessments/levels1-6/route.ts');
process.env.DASHBOARD_PASSWORD='SYNTHETIC_CONTROL_TEST_ONLY';process.env.SESSION_SIGNING_KEY='SYNTHETIC_CONTROL_TEST_ONLY_KEY_0123456789';
const flush=async()=>{for(let i=0;i<3;i++)await new Promise(resolve=>setImmediate(resolve));};
const buttons=tree=>tree.root.findAllByType('button');
const text=tree=>JSON.stringify(tree.toJSON());

test('actual controls run selected ORCA-2 and all 32 through the authenticated API',async()=>{
 const original=global.fetch,calls=[];let tree;
 global.fetch=async(url,init={})=>{calls.push({url,init});const req=new NextRequest('https://owner.example.test'+url,{method:init.method||'GET',headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession(),origin:'https://owner.example.test','content-type':'application/json'},...(init.body?{body:init.body}:{})});return init.method==='POST'?api.POST(req):api.GET(req);};
 try{
  await act(async()=>{tree=create(React.createElement(Runner,{selectedNct:'NCT04576949'}));await flush();});
  assert.equal(calls.filter(c=>c.init.method==='POST').length,0,'Loading the page must not run an assessment');
  assert.equal(tree.root.findByType('select').findAllByType('option').length,32);
  assert.equal(tree.root.findByType('select').props.value,'NCT04576949');
  await act(async()=>{buttons(tree).find(b=>String(b.props.children).includes('Run selected')).props.onClick();await flush();});
  assert.deepEqual(JSON.parse(calls.find(c=>c.init.method==='POST').init.body),{scope:'ONE',nct:'NCT04576949'});
  assert.match(text(tree),/levels processed/);assert.match(text(tree),/OWNER NOT REVIEWED/);
  assert.equal(tree.root.findAllByType('article').length,1);
  assert.equal(tree.root.findAllByType('h4').filter(h=>h.props.children==='Source observations').length,0,'Closed levels must not mount all source-observation bodies');
  await act(async()=>{tree.root.findAllByType('details').find(d=>d.props.onToggle).props.onToggle({currentTarget:{open:true}});});
  assert.ok(tree.root.findAllByType('h4').some(h=>h.props.children==='Source observations'));
  await act(async()=>{buttons(tree).find(b=>String(b.props.children).includes('Run all 32')).props.onClick();await flush();});
  assert.equal(tree.root.findAllByType('article').length,32);
  const posts=calls.filter(c=>c.init.method==='POST');assert.deepEqual(JSON.parse(posts[1].init.body),{scope:'ALL'});
  assert.match(text(tree),/not saved to the database/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=original;}
});
test('missing login disables runs and provides existing dashboard sign-in link',async()=>{
 const original=global.fetch;let tree;global.fetch=async()=>new Response(JSON.stringify({error:'Sign in required'}),{status:401});
 try{await act(async()=>{tree=create(React.createElement(Runner));await flush();});assert.ok(buttons(tree).every(b=>b.props.disabled));assert.ok(tree.root.findAllByType('a').some(a=>a.props.href==='/'));assert.equal(tree.root.findAllByProps({role:'alert'}).length,1);}
 finally{if(tree)await act(async()=>tree.unmount());global.fetch=original;}
});
test('an unsuccessful run never renders a completed assessment',async()=>{
 const original=global.fetch;let tree;
 global.fetch=async(_url,init={})=>init.method==='POST'?new Response(JSON.stringify({error:'Evidence package unavailable'}),{status:503}):new Response(JSON.stringify({evidenceCutoffDate:'2026-11-14',trials:[{nct:'NCT04576949',ticker:'ACHV',company:'Achieve',indication:'Smoking cessation'}]}));
 try{await act(async()=>{tree=create(React.createElement(Runner));await flush();});await act(async()=>{buttons(tree)[0].props.onClick();await flush();});assert.match(text(tree),/Evidence package unavailable/);assert.equal(tree.root.findAllByType('article').length,0);}
 finally{if(tree)await act(async()=>tree.unmount());global.fetch=original;}
});
test('ASSESSMENTS mounts the runner without importing its evidence payload into client code',()=>{
 const page=fs.readFileSync(require('node:path').join(__dirname,'../app/predictions/assessment/page.tsx'),'utf8');assert.match(page,/<LevelSixAssessmentRunner selectedNct=\{selected\?\.nct\}/);
 const source=fs.readFileSync(require('node:path').join(__dirname,'../app/LevelSixAssessmentRunner.tsx'),'utf8');assert.match(source,/import type \{AssessmentRun,TrialResult,LevelResult\}/);assert.doesNotMatch(source,/import collected|level16AssessmentEvidence\.json|setInterval|localStorage/);
});
test('direct Level 3 selected/all controls show a source-linked lean and preserve insufficient evidence for trial 14',async()=>{
 const original=global.fetch,calls=[];let tree;
 global.fetch=async(url,init={})=>{calls.push(init);const req=new NextRequest('https://owner.example.test'+url,{method:init.method||'GET',headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession(),origin:'https://owner.example.test','content-type':'application/json'},...(init.body?{body:init.body}:{})});return init.method==='POST'?api.POST(req):api.GET(req);};
 try{
  await act(async()=>{tree=create(React.createElement(Runner,{selectedNct:'NCT04576949'}));await flush();});
  const selected=()=>buttons(tree).find(b=>String(b.props.children).includes('Run Level 3 predictor · selected'));
  await act(async()=>{selected().props.onClick();await flush();});
  assert.deepEqual(JSON.parse(calls.find(c=>c.method==='POST').body),{scope:'ONE',nct:'NCT04576949',level:3});assert.match(text(tree),/Approval lean/);assert.match(text(tree),/not a complete FDA application forecast/);
  assert.equal(tree.root.findAllByType('details').filter(d=>d.props.onToggle).length,1,'Only Level 3 runs');
  await act(async()=>{tree.root.findByType('select').props.onChange({target:{value:'NCT06455202'}});});
  await act(async()=>{selected().props.onClick();await flush();});assert.match(text(tree),/Insufficient evidence/);assert.doesNotMatch(JSON.stringify(tree.root.findByProps({'aria-label':'Level 3 prediction for NCT06455202'}).findByType('h4').props.children),/Approval lean/);
  await act(async()=>{buttons(tree).find(b=>String(b.props.children).includes('Run Level 3 predictor · all 32')).props.onClick();await flush();});
  assert.equal(tree.root.findAllByType('article').length,32);assert.equal(tree.root.findAllByType('details').filter(d=>d.props.onToggle).length,32);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=original;}
});
