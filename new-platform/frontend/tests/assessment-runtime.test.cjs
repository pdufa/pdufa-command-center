const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,f);
const {NextRequest}=require('next/server'),auth=require('../lib/auth.ts'),api=require('../app/api/assessments/runtime/route.ts');
process.env.DASHBOARD_PASSWORD='SYNTHETIC_RUNTIME_PASSWORD';process.env.SESSION_SIGNING_KEY='SYNTHETIC_RUNTIME_KEY_01234567890123456789';
const base='https://owner.example.test',nct='NCT04576949';
function req(body,extra={}){return new NextRequest(base+'/api/assessments/runtime',{method:'POST',headers:{origin:base,'content-type':'application/json',cookie:auth.COOKIE_NAME+'='+auth.makeSession(),...extra},body:JSON.stringify(body)});}
test('six levels relay only their selected engine request with private server credential',async()=>{
 const old=global.fetch;process.env.PDUFA_API_BASE_URL='https://backend.example.test';process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';
 global.fetch=async(url,init)=>{assert.equal(url,'https://backend.example.test/api/assessment-runtime/runs');assert.equal(init.headers['X-Pdufa-Internal-Key'],'SYNTHETIC_INTERNAL_KEY');const b=JSON.parse(init.body);assert.ok(b.level>=1&&b.level<=6);return Response.json({runId:'a'.repeat(36),nct,status:'QUEUED'},{status:202});};
 try{for(let level=1;level<=6;level++){const response=await api.POST(req({nct,level,mode:'CURRENT_EVIDENCE'}));assert.equal(response.status,202);assert.equal((await response.json()).status,'QUEUED');assert.match(response.headers.get('cache-control'),/no-store/);}}
 finally{global.fetch=old;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});
test('unauthorized, cross-origin, body injection and invalid historical dates fail before backend access',async()=>{
 const old=global.fetch;let count=0;global.fetch=async()=>{count++;throw Error('No network expected');};
 try{
  const body={nct,level:1,mode:'CURRENT_EVIDENCE'};
  assert.equal((await api.POST(req(body,{cookie:'invalid'}))).status,401);assert.equal((await api.POST(req(body,{origin:'https://other.test'}))).status,403);
  for(const b of [{...body,score:99},{...body,level:0},{...body,mode:'BLIND_HISTORICAL',cutoffDate:'2025-02-30'},{...body,mode:'BLIND_HISTORICAL'},{...body,cutoffDate:'2020-01-01'}])assert.equal((await api.POST(req(b))).status,422);
  assert.equal((await api.POST(req({...body,padding:'x'.repeat(2000)}))).status,413);assert.equal(count,0);
 }finally{global.fetch=old;}
});
test('valid historical mode relays cutoff to source-isolated backend; no frontend source retrieval',async()=>{
 const old=global.fetch;process.env.PDUFA_API_BASE_URL='https://backend.example.test';process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';
 global.fetch=async(url,init)=>{assert.match(url,/\/api\/assessment-runtime\/runs$/);assert.deepEqual(JSON.parse(init.body),{nct,level:5,mode:'BLIND_HISTORICAL',cutoffDate:'2020-01-01'});return Response.json({status:'QUEUED'},{status:202});};
 try{assert.equal((await api.POST(req({nct,level:5,mode:'BLIND_HISTORICAL',cutoffDate:'2020-01-01'}))).status,202);}
 finally{global.fetch=old;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});
test('workbench uses real progress and persisted reports, and allows historical submission with a cutoff',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Workbench=require('../app/AssessmentWorkbench.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch;let tree,posts=[];
 const report={runId:'a'.repeat(36),nct,level:1,name:'Source identity',mode:'CURRENT_EVIDENCE',cutoffDate:null,executedAt:'2026-11-14',engineVersion:'test/level-1',reportHash:'a'.repeat(64),scientificStatus:'EVIDENCE_GAPS',activationStatus:'NOT_ACTIVE_SCIENTIFIC_GAPS',ownerReviewStatus:'OWNER_NOT_REVIEWED',score:{value:100,available:4,applicable:4,kind:'LEVEL_SPECIFIC_EVIDENCE_COVERAGE',method:'Evidence checks, not efficacy'},fdaPrediction:{outcome:'ABSTAIN',confidence:'UNCALIBRATED',calibration:'NO_VALIDATED_FDA_MODEL'},context:{phases:['PHASE3'],phaseVerification:'OFFICIAL_REGISTRY_DECLARATION',registryStatus:'COMPLETED',regulatoryStatus:'UNVERIFIED',indicationAnalysis:[]},checks:[],observations:[],risks:[],recommendations:[],limitations:[],evidence:{source_url:'https://clinicaltrials.gov/api/v2/studies/'+nct}};
 global.fetch=async(url,init={})=>{if(init.method==='POST'){posts.push(JSON.parse(init.body));return Response.json({runId:report.runId,status:'QUEUED'},{status:202});}return Response.json(String(url).includes('runId=')?{status:'COMPLETED',progress:[{stage:'PERSISTING_IMMUTABLE_RESULT',at:'2026-11-14'}],report}:{runs:[report],hasMore:false});};
 try{
  await act(async()=>{tree=create(React.createElement(Workbench,{selectedNct:nct}));});assert.equal(posts.length,0);assert.equal(tree.root.findByProps({'aria-label':'Assessment level'}).type,'select');assert.equal(tree.root.findByProps({'aria-label':'Evidence mode'}).type,'select');
  const button=()=>tree.root.findAllByType('button').find(b=>b.props.children==='Run Assessment');
  await act(async()=>{button().props.onClick();await new Promise(r=>setImmediate(r));});assert.equal(posts[0].level,1);assert.match(JSON.stringify(tree.toJSON()),/immutable result saved and retrieved/);
  await act(async()=>{tree.root.findAllByType('select').find(s=>s.props.value==='CURRENT_EVIDENCE').props.onChange({target:{value:'BLIND_HISTORICAL'}});});assert.equal(button().props.disabled,true);
  await act(async()=>{tree.root.findByProps({type:'date'}).props.onChange({target:{value:'2020-01-01'}});});assert.equal(button().props.disabled,false);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('SSR assessment controls stay disabled until client handlers are ready',()=>{
 const React=require('react'),{renderToString}=require('react-dom/server'),Workbench=require('../app/AssessmentWorkbench.tsx').default;
 const html=renderToString(React.createElement(Workbench,{selectedNct:nct}));
 assert.match(html,/data-assessment-ready="false"/);assert.equal((html.match(/<fieldset disabled=""/g)||[]).length,2);
});

test('parent-selected trial changes clear old evidence and switch the exact NCT',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Workbench=require('../app/AssessmentWorkbench.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 let tree;const second='NCT01234567';
 try{
  await act(async()=>{tree=create(React.createElement(Workbench,{selectedNct:nct}));});
  assert.equal(tree.root.findByProps({placeholder:'NCT04576949'}).props.value,nct);
  await act(async()=>{tree.update(React.createElement(Workbench,{selectedNct:second}));});
  assert.equal(tree.root.findByProps({placeholder:'NCT04576949'}).props.value,second);
  assert.equal(tree.root.findAllByProps({'aria-label':'Level 1 saved assessment'}).length,0);
 }finally{if(tree)await act(async()=>tree.unmount());}
});

test('saved assessment history is isolated when the parent changes trial',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Workbench=require('../app/AssessmentWorkbench.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch,second='NCT01234567';let tree;
 const report={runId:'b'.repeat(36),nct,level:1,name:'Source identity',mode:'CURRENT_EVIDENCE',executedAt:'2026-11-14',engineVersion:'test',reportHash:'b'.repeat(64),scientificStatus:'EVIDENCE_GAPS',activationStatus:'NOT_ACTIVE',ownerReviewStatus:'OWNER_NOT_REVIEWED',score:{value:null,available:0,applicable:0,method:'Evidence only'},fdaPrediction:{outcome:'ABSTAIN',confidence:'UNCALIBRATED',calibration:'NONE'},context:{phases:[],phaseVerification:'UNVERIFIED',registryStatus:null,regulatoryStatus:'UNVERIFIED',indicationAnalysis:[]},checks:[],observations:[],risks:[],recommendations:[],limitations:[],evidence:{source_url:'https://clinicaltrials.gov/api/v2/studies/'+nct}};
 global.fetch=async()=>Response.json({runs:[report],hasMore:false});
 try{
  await act(async()=>{tree=create(React.createElement(Workbench,{selectedNct:nct}));});
  await act(async()=>{tree.root.findAllByType('button').find(b=>b.props.children==='Load saved assessment history').props.onClick();});
  assert.equal(tree.root.findAllByProps({'aria-label':'Level 1 saved assessment'}).length,1);
  await act(async()=>{tree.update(React.createElement(Workbench,{selectedNct:second}));});
  assert.equal(tree.root.findByProps({placeholder:'NCT04576949'}).props.value,second);
  assert.equal(tree.root.findAllByProps({'aria-label':'Level 1 saved assessment'}).length,0);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('outdated POOL search cannot overwrite FOCUS search results',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Workbench=require('../app/AssessmentWorkbench.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch;let resolveFirst;let tree;
 const stale=new Promise(resolve=>{resolveFirst=resolve;});
 let calls=0;
 global.fetch=async()=>{calls++;if(calls===1)return stale;return Response.json({trials:[{nct:'NCT01234567',ticker:'NEW',title:'Current cohort',population:'POOL'}]});};
 try{
  await act(async()=>{tree=create(React.createElement(Workbench,{selectedNct:nct}));});
  const search=()=>tree.root.findAllByType('button').find(b=>b.props.children==='Search trials');
  let first;
  await act(async()=>{first=search().props.onClick();});
  await act(async()=>{tree.root.findByProps({'aria-label':'Trial population'}).props.onChange({target:{value:'POOL'}});});
  await act(async()=>{search().props.onClick();});
  await act(async()=>{resolveFirst(Response.json({trials:[{nct:'NCT00000001',ticker:'OLD',title:'Stale cohort',population:'FOCUS'}]}));await Promise.resolve();});
  const display=JSON.stringify(tree.toJSON());
  assert.match(display,/Current cohort/);assert.doesNotMatch(display,/Stale cohort/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('completed assessment with mismatched level is withheld from the selected trial',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Workbench=require('../app/AssessmentWorkbench.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch;let tree;
 const report={runId:'c'.repeat(36),nct,level:2,name:'Registry and phase verification',mode:'CURRENT_EVIDENCE',cutoffDate:null,executedAt:'2026-11-14',engineVersion:'test',reportHash:'c'.repeat(64),scientificStatus:'EVIDENCE_GAPS',activationStatus:'NOT_ACTIVE',ownerReviewStatus:'OWNER_NOT_REVIEWED',score:{value:null,available:0,applicable:0,method:'Evidence only'},fdaPrediction:{outcome:'ABSTAIN',confidence:'UNCALIBRATED',calibration:'NONE'},context:{phases:[],phaseVerification:'UNVERIFIED',registryStatus:null,regulatoryStatus:'UNVERIFIED',indicationAnalysis:[]},checks:[],observations:[],risks:[],recommendations:[],limitations:[],evidence:{source_url:'https://clinicaltrials.gov/api/v2/studies/'+nct}};
 global.fetch=async(url,init={})=>init.method==='POST'?Response.json({runId:report.runId,status:'QUEUED'},{status:202}):Response.json({status:'COMPLETED',progress:[],report});
 try{
  await act(async()=>{tree=create(React.createElement(Workbench,{selectedNct:nct}));});
  await act(async()=>{tree.root.findAllByType('button').find(b=>b.props.children==='Run Assessment').props.onClick();});
  assert.match(JSON.stringify(tree.toJSON()),/Assessment result identity, level, mode or historical cutoff mismatch/);
  assert.equal(tree.root.findAllByProps({'aria-label':'Level 2 saved assessment'}).length,0);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('Levels 1–3 each execute, persist and render exact-NCT evidence reports',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Workbench=require('../app/AssessmentWorkbench.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch;let tree;const posted=[];
 const reports=[1,2,3].map(level=>({runId:String(level).repeat(36),nct,level,name:'Scientific Level '+level,mode:'CURRENT_EVIDENCE',cutoffDate:null,executedAt:'2026-11-14',engineVersion:'test/level-'+level,reportHash:String(level).repeat(64),scientificStatus:'EVIDENCE_GAPS',activationStatus:'NOT_ACTIVE_SCIENTIFIC_GAPS',ownerReviewStatus:'OWNER_NOT_REVIEWED',score:{value:null,available:0,applicable:3,kind:'LEVEL_SPECIFIC_EVIDENCE_COVERAGE',method:'Evidence checks only'},fdaPrediction:{outcome:'ABSTAIN',confidence:'UNCALIBRATED',calibration:'NO_VALIDATED_FDA_MODEL'},context:{phases:['PHASE3'],phaseVerification:'OFFICIAL_REGISTRY_DECLARATION',registryStatus:'COMPLETED',regulatoryStatus:'UNVERIFIED',indicationAnalysis:[]},checks:[{id:'criterion',state:'NOT_VERIFIED',explanation:'Source review pending',locator:'registry'}],observations:[],risks:['Unverified evidence'],recommendations:['Review primary sources'],limitations:[],evidence:{source_url:'https://clinicaltrials.gov/api/v2/studies/'+nct}}));
 global.fetch=async(url,init={})=>{
  if(init.method==='POST'){const body=JSON.parse(init.body);posted.push(body);return Response.json({runId:reports[body.level-1].runId,status:'QUEUED'},{status:202});}
  const run=String(url).match(/runId=([123]{36})/);return Response.json(run?{status:'COMPLETED',progress:[],report:reports.find(r=>r.runId===run[1])}:{runs:reports,hasMore:false});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Workbench,{selectedNct:nct}));});
  for(let level=1;level<=3;level++){
   await act(async()=>{tree.root.findByProps({'aria-label':'Assessment level'}).props.onChange({target:{value:String(level)}});});
   await act(async()=>{tree.root.findAllByType('button').find(b=>b.props.children==='Run Assessment').props.onClick();});
   assert.equal(posted[level-1].level,level);
   assert.equal(posted[level-1].nct,nct);
   assert.equal(tree.root.findAllByProps({'aria-label':'Level '+level+' saved assessment'}).length,1);
  }
  assert.deepEqual(posted.map(x=>x.level),[1,2,3]);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('ASSESSMENTS route mounts the executable workbench and homepage links to it',()=>{
 const page=fs.readFileSync(require('node:path').join(__dirname,'../app/assessments/page.tsx'),'utf8');
 const home=fs.readFileSync(require('node:path').join(__dirname,'../app/page.tsx'),'utf8');
 assert.match(page,/import AssessmentWorkbench from ['"]\.\.\/AssessmentWorkbench['"]/);
 assert.match(page,/<AssessmentWorkbench\s*\/>/);
 assert.match(home,/href="\/assessments"/);
 assert.match(page,/Levels 1–3/);
});
