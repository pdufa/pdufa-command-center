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
 assert.match(page,/<AssessmentWorkbench\s+selectedNct=\{nct\}\s*\/>/);
 assert.match(home,/href="\/assessments"/);
 assert.match(page,/Levels 1–3/);
});

test('scientific contract relays selected Levels 1–3 and rejects higher-level substitution',async()=>{
 const old=global.fetch;process.env.PDUFA_API_BASE_URL='https://backend.example.test';process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';let calls=0;
 global.fetch=async(url,init)=>{calls++;const b=JSON.parse(init.body);assert.equal(b.contract,'SCIENTIFIC_1_3');assert.ok(b.level<=3);return Response.json({status:'QUEUED'},{status:202});};
 try{for(let level=1;level<=3;level++)assert.equal((await api.POST(req({nct,level,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_3'}))).status,202);
  assert.equal((await api.POST(req({nct,level:4,mode:'CURRENT_EVIDENCE',contract:'SCIENTIFIC_1_3'}))).status,422);assert.equal(calls,3);
 }finally{global.fetch=old;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});
test('shared FOCUS records relay through owner authentication and bounded batch rejects evidence injection',async()=>{
 const old=global.fetch;process.env.PDUFA_API_BASE_URL='https://backend.example.test';process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';const urls=[];
 global.fetch=async(url,init)=>{urls.push(url);return Response.json(url.endsWith('/focus/batch')?{status:'BOUNDED_BATCH_QUEUED'}:{total:32,trials:[]});};
 try{
  const get=new NextRequest(base+'/api/assessments/runtime?focus=true',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
  assert.equal((await api.GET(get)).status,200);assert.equal((await api.POST(req({action:'FOCUS_BATCH'}))).status,200);
  assert.equal((await api.POST(req({action:'FOCUS_BATCH',score:99}))).status,422);assert.deepEqual(urls,['https://backend.example.test/api/assessment-runtime/focus','https://backend.example.test/api/assessment-runtime/focus/batch']);
 }finally{global.fetch=old;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});
test('saved scientific findings render actual source passages and contrasts without an invented score',()=>{
 const React=require('react'),{renderToString}=require('react-dom/server'),Findings=require('../app/ScientificTrialFindings.tsx').default;
 const source={source_url:'https://clinicaltrials.gov/api/v2/studies/'+nct,published_at:'2026-01-01',captured_at:'2026-11-15T01:00:00Z',raw_sha256:'b'.repeat(64),locator:'Synthetic fixture page 11',excerpt:'Synthetic source states 80% power.'};
 const html=renderToString(React.createElement(Findings,{value:{kind:'EXECUTED_SCIENTIFIC_TRIAL_ASSESSMENT',executionStatus:'COMPLETED_WITH_LIMITATIONS',trialIdentity:{nct,company:'Synthetic',candidate:'Synthetic drug',ticker:null},checks:[{id:'power_rationale',state:'DOCUMENT_REPORTED',explanation:'Original statement; not independently validated.',citations:[source]}],observations:[{endpointEvaluations:[{title:'Synthetic endpoint',endpointType:'PRIMARY',calculatedContrasts:[{treatmentGroup:'Active',controlGroup:'Placebo',absoluteDifferencePercentagePoints:20.9,limitation:'Descriptive only'}],statisticalAnalyses:[{reported:{paramValue:'3',ciPctValue:'95',ciLowerLimit:'1',ciUpperLimit:'5',pValue:'<0.01'}}],citation:source}]}]}}));
 assert.match(html,/20\.90/);assert.match(html,/SOURCE|DOCUMENT_REPORTED/);assert.match(html,/Synthetic source states 80% power/);assert.match(html,/NOT VERIFIED/);assert.doesNotMatch(html,/approval probability|Evidence coverage: 100/);
});
test('shared saved FOCUS table renders persisted independent levels and explicit unscorable values',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Saved=require('../app/FocusSavedAssessments.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch,oldSelf=global.self;global.self=globalThis;let tree;const levels={};for(let level=1;level<=3;level++)levels[level]={state:'COMPLETED',attempts:1,error:null,missingEvidence:[{id:'unresolved',state:'UNVERIFIED',explanation:'Synthetic missing evidence'}],report:{runId:'synthetic-'+level,nct,level,executionStatus:'COMPLETED_WITH_LIMITATIONS',executedAt:'2026-11-15',engineVersion:'synthetic/level-'+level,score:{value:null,kind:'NOT_VALIDATED',method:'No validated formula'},fdaPrediction:{outcome:'ABSTAIN',probability:null,confidence:'NOT_VALIDATED'},trialIdentity:{candidate:'Synthetic drug'},context:{phases:['PHASE3']}}};
 global.fetch=async url=>{assert.equal(url,'/api/assessments/runtime?focus=true');return Response.json({total:1,fullyProcessed:1,status:'SYNTHETIC_SAVED_FIXTURE',counts:{},source:null,trials:[{nct,ticker:'SYN',company:'Synthetic',pdufaDate:null,levels}]});};
 try{await act(async()=>{tree=create(React.createElement(Saved));});const rendered=JSON.stringify(tree.toJSON());for(let l=1;l<=3;l++)assert.ok(tree.root.findAllByType('th').some(th=>React.Children.toArray(th.props.children).join('')==='L'+l+' Score'));assert.match(rendered,/NOT VALIDATED \/ UNSCORABLE/);assert.match(rendered,/ABSTAIN/);assert.equal(tree.root.findAllByType('tbody')[0].findAllByType('tr').length,1);}
 finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;if(oldSelf===undefined)delete global.self;else global.self=oldSelf;}
});

test('FOCUS columns show the same saved scientific records as the shared assessment table',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer');globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old={fetch:global.fetch,self:global.self,window:global.window};global.self=globalThis;global.window={addEventListener(){},removeEventListener(){}};let tree;
 global.fetch=async url=>{assert.equal(url,'/api/assessments/runtime?focus=true');return Response.json({trials:[{nct,levels:Object.fromEntries([1,2,3].map(level=>[String(level),{report:{runId:'saved-'+level,nct,level,mode:'CURRENT_EVIDENCE',executedAt:'2026-11-15',score:{value:null,kind:'NOT_VALIDATED'},fdaPrediction:{outcome:'ABSTAIN',confidence:'NOT_VALIDATED'}}}]))}]});};
 try{const Cells=require('../app/FocusLevelColumns.tsx').FocusLevelCells;await act(async()=>{tree=create(React.createElement(Cells,{nct}));});const json=JSON.stringify(tree.toJSON());assert.equal((json.match(/NOT VALIDATED \/ UNSCORABLE/g)||[]).length,3);assert.equal((json.match(/ABSTAIN · not predicted/g)||[]).length,3);for(let l=1;l<=3;l++)assert.match(json,new RegExp('Saved assessment saved-'+l));}
 finally{if(tree)await act(async()=>tree.unmount());Object.assign(global,old);}
});

test('launcher uses the scientific contract and cannot count an unpersisted completion',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Launcher=require('../app/AssessmentLauncher.tsx').default;globalThis.IS_REACT_ACT_ENVIRONMENT=true;const old=global.fetch;let tree,posted;
 global.fetch=async(url,init={})=>{if(init.method==='POST'){posted=JSON.parse(init.body);return Response.json({runId:'a'.repeat(8)+'-'+'a'.repeat(4)+'-'+'a'.repeat(4)+'-'+'a'.repeat(4)+'-'+'a'.repeat(12)});}return Response.json({status:'COMPLETED',report:null});};
 try{
  await act(async()=>{tree=create(React.createElement(Launcher));});await act(async()=>{tree.root.findAllByType('button')[0].props.onClick();});
  const textInput=tree.root.findAllByType('textarea')[0]||tree.root.findAllByType('input').find(i=>i.props.type!=='checkbox'&&i.props.type!=='date');
  await act(async()=>{textInput.props.onChange({target:{value:nct}});});
  for(const input of tree.root.findAllByType('input').filter(i=>i.props.type==='checkbox').slice(3))assert.equal(input.props.disabled,true);
  await act(async()=>{tree.root.findAllByType('button').find(b=>['Submit assessments','Run PAST audit and eligible assessments'].includes(b.props.children)).props.onClick();await new Promise(resolve=>setTimeout(resolve,6500));});
  assert.equal(posted.contract,'SCIENTIFIC_1_3');const rendered=JSON.stringify(tree.toJSON());assert.match(rendered,/FAILED/);assert.doesNotMatch(rendered,/3\/3 completed/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('both FOCUS and ASSESSMENTS mount the shared saved scientific records',()=>{for(const file of ['focus/page.tsx','assessments/page.tsx']){const source=fs.readFileSync(require('node:path').join(__dirname,'../app',file),'utf8');assert.match(source,/<FocusSavedAssessments\s*\/>/);}});


test('PAST saved blind records display on PAST and ASSESSMENTS without fabricated scores',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Saved=require('../app/PastSavedAssessments.tsx').default;
 globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch;
 let tree;
 const level=level=>({runId:'saved-'+level,executedAt:'2026-11-15',name:'Synthetic level '+level,executionStatus:'COMPLETED_WITH_LIMITATIONS',score:{value:null,kind:'NOT_VALIDATED',method:'No validated scale'},fdaPrediction:{outcome:'ABSTAIN',confidence:'NOT_VALIDATED'},scientificStatus:'SOURCE_BOUND_ANALYSIS_NOT_VALIDATED',unresolved:2,sourceUrl:'https://clinicaltrials.gov/api/v2/studies/'+nct});
 global.fetch=async url=>{
  assert.equal(url,'/api/assessments/runtime?past=true');
  return Response.json({status:'SAVED_BLIND_HISTORY_NOT_PAST_QUEUE_RECONCILED',truncated:false,trials:[{nct,cutoffDate:'2025-06-01',eventLinkage:'NOT_RECONCILED_TO_PAST_QUEUE',levels:{'1':level(1),'2':level(2),'3':level(3)}}]});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Saved));});
  const rendered=JSON.stringify(tree.toJSON());
  for(const l of [1,2,3])assert.ok(tree.root.findAllByType('th').some(th=>React.Children.toArray(th.props.children).join('')==='L0'+l+' scientific score'));
  const cells=tree.root.findAllByType('tbody')[0].findAllByType('td');
  assert.equal(cells.length,7);
  for(const position of [1,3,5])assert.equal(cells[position].findAllByType('strong')[0].props.children,'NOT VALIDATED / UNSCORABLE');
  assert.match(rendered,/ABSTAIN/);
  assert.match(rendered,/not yet reconciled/);
  for(const page of ['past/page.tsx','assessments/page.tsx','predictions/assessment/page.tsx']){
   const source=fs.readFileSync(require('node:path').join(__dirname,'../app',page),'utf8');
   assert.match(source,/<PastSavedAssessments\s*\/>/);
  }
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('authenticated PAST summary relays only to persistent backend without outcome parameters',async()=>{
 const old=global.fetch;
 process.env.PDUFA_API_BASE_URL='https://backend.example.test';
 process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';
 global.fetch=async(url,init)=>{
  assert.equal(url,'https://backend.example.test/api/assessment-runtime/past');
  assert.equal(init.headers['X-Pdufa-Internal-Key'],'SYNTHETIC_INTERNAL_KEY');
  return Response.json({status:'NO_SAVED_BLIND_SCIENTIFIC_RUNS',trials:[],truncated:false});
 };
 try{
  const req=new NextRequest(base+'/api/assessments/runtime?past=true',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
  const response=await api.GET(req);
  assert.equal(response.status,200);
  assert.deepEqual((await response.json()).trials,[]);
 }finally{global.fetch=old;delete process.env.PDUFA_API_BASE_URL;delete process.env.PDUFA_INTERNAL_API_KEY;}
});

test('dedicated production Level 1–3 API credentials are scoped and fail closed on partial configuration',async()=>{
 const prior=global.fetch;
 process.env.PDUFA_API_BASE_URL='https://old-backend.example.test';
 process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_OLD_BACKEND_KEY';
 process.env.PDUFA_LEVEL123_API_BASE_URL='https://assessments.example.test';
 process.env.PDUFA_LEVEL123_INTERNAL_API_KEY='SYNTHETIC_LEVEL123_KEY';
 const req=new NextRequest(base+'/api/assessments/runtime?focus=true',{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
 let calls=0;
 global.fetch=async(url,init)=>{
  calls++;
  assert.equal(url,'https://assessments.example.test/api/assessment-runtime/focus');
  assert.equal(init.headers['X-Pdufa-Internal-Key'],'SYNTHETIC_LEVEL123_KEY');
  return Response.json({status:'DATABASE_SAVED_RECONCILED_OWNER_ROSTER',total:32,fullyProcessed:32,trials:[]});
 };
 try{
  const response=await api.GET(req);
  assert.equal(response.status,200);
  assert.equal((await response.json()).total,32);
  assert.equal(calls,1);
  delete process.env.PDUFA_LEVEL123_INTERNAL_API_KEY;
  const blocked=await api.GET(req);
  assert.equal(blocked.status,503);
  assert.equal(calls,1,'Must not fallback to the older backend when dedicated API configuration is incomplete');
 }finally{
  global.fetch=prior;
  delete process.env.PDUFA_API_BASE_URL;
  delete process.env.PDUFA_INTERNAL_API_KEY;
  delete process.env.PDUFA_LEVEL123_API_BASE_URL;
  delete process.env.PDUFA_LEVEL123_INTERNAL_API_KEY;
 }
});


test('FOCUS and PAST use the same assessment launcher for single, selected and whole-list scopes',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Launcher=require('../app/AssessmentLauncher.tsx').default;
 globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const originalFetch=global.fetch;
 global.fetch=async url=>{
  if(String(url).includes('pastRoster=2026')){
   const events=require('../data/level4BlindAssessmentQueue20261112.json').historical2026;
   return Response.json({year:2026,total:events.length,linked:0,ready:false,status:'PAST_RECONCILIATION_INCOMPLETE',events:events.map(e=>({eventKey:e.eventKey,status:'MISSING_VERIFIED_LINK'})),tasks:[],eligibleTasks:[]});
  }
  throw Error('Unexpected request');
 };
 try{
 for(const page of ['focus/page.tsx','past/page.tsx']){
  const source=fs.readFileSync(require('node:path').join(__dirname,'../app',page),'utf8');
  assert.match(source,/<AssessmentLauncher source="(?:FOCUS|HISTORICAL)"(?:\s+historicalYear=\{year\})?\s*\/>/);
 }
 for(const source of ['FOCUS','HISTORICAL']){
  let tree;
  try{
   await act(async()=>{tree=create(React.createElement(Launcher,{source}));});
   await act(async()=>{tree.root.findAllByType('button')[0].props.onClick();});
   const scope=()=>tree.root.findByProps({'aria-label':'Assessment scope'});
   const options=scope().findAllByType('option').map(option=>option.props.value);
   assert.deepEqual(options,['single','selected','all']);
   const submit=()=>tree.root.findAllByType('button').find(button=>['Submit assessments','Run PAST audit and eligible assessments'].includes(button.props.children));
   await act(async()=>{scope().props.onChange({target:{value:'single'}});});
   assert.equal(submit().props.disabled,true);
   await act(async()=>{tree.root.findByProps({'aria-label':'Single trial NCT'}).props.onChange({target:{value:nct}});});
   assert.equal(submit().props.disabled,false);
   await act(async()=>{scope().props.onChange({target:{value:'selected'}});});
   assert.equal(submit().props.disabled,true);
   await act(async()=>{tree.root.findAllByType('textarea')[0].props.onChange({target:{value:nct}});});
   assert.equal(submit().props.disabled,false);
   await act(async()=>{scope().props.onChange({target:{value:'all'}});});
   assert.equal(submit().props.disabled,true);
   if(source==='HISTORICAL'){
    const audit=tree.root.findAllByType('button').find(button=>button.props.children==='Audit whole PAST 2026 list');
    assert.equal(audit.props.disabled,false);
    await act(async()=>{await audit.props.onClick();});
    assert.equal(submit().props.disabled,false,'whole PAST can be audited without fabricated trial links');
    await act(async()=>{await submit().props.onClick();});
    assert.ok(tree.root.findAllByType('h3').some(h=>React.Children.toArray(h.props.children).join('').includes('20 events not assessed')));
    assert.match(JSON.stringify(tree.toJSON()),/NOT_ASSESSED_UNVERIFIED/);
    assert.ok(tree.root.findAllByType('summary').some(node=>React.Children.toArray(node.props.children).join('')==='20 PAST events requiring verified linkage or evidence'));
    assert.match(JSON.stringify(tree.toJSON()),/Whole PAST reports every event/);
   }
   await act(async()=>{tree.root.findByProps({'aria-label':'Clear assessment popup'}).props.onClick();});
   assert.equal(scope().props.value,'selected');
  }finally{if(tree)await act(async()=>tree.unmount());}
 }
 }finally{global.fetch=originalFetch;}
});

test('whole-list assessment requires exact verification against saved FOCUS total, not a partial catalog',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Launcher=require('../app/AssessmentLauncher.tsx').default;
 globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const old=global.fetch;let tree,summaryTotal=3,summaryNcts=[nct,'NCT01234567'];
 global.fetch=async url=>{
  if(String(url).includes('focus=true'))return Response.json({status:'DATABASE_SAVED_RECONCILED_OWNER_ROSTER',source:{roster_id:'owner-roster-1'},total:summaryTotal,trials:summaryNcts.map(nct=>({nct}))});
  return Response.json({population:'FOCUS',trials:[{nct},{nct:'NCT01234567'}]});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Launcher,{source:'FOCUS'}));});
  await act(async()=>{tree.root.findAllByType('button')[0].props.onClick();});
  const scope=tree.root.findByProps({'aria-label':'Assessment scope'});
  await act(async()=>{scope.props.onChange({target:{value:'all'}});});
  const load=()=>tree.root.findAllByType('button').find(button=>button.props.children==='Verify and load whole FOCUS list');
  const submit=()=>tree.root.findAllByType('button').find(button=>['Submit assessments','Run PAST audit and eligible assessments'].includes(button.props.children));
  await act(async()=>{await load().props.onClick();});
  assert.equal(submit().props.disabled,true);
  assert.match(JSON.stringify(tree.toJSON()),/FOCUS roster could not be verified as complete/);
  summaryTotal=2;summaryNcts=[nct,'NCT99999999'];
  await act(async()=>{await load().props.onClick();});
  assert.equal(submit().props.disabled,true,'matching counts with different NCTs must fail');
  summaryNcts=[nct,'NCT01234567'];
  await act(async()=>{await load().props.onClick();});
  assert.equal(submit().props.disabled,false);
  assert.match(JSON.stringify(tree.toJSON()),/Full FOCUS roster confirmed/);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});


test('PAST candidate NCT entries never masquerade as verified FDA event prediction links',()=>{
 const past=fs.readFileSync(require('node:path').join(__dirname,'../app/past/page.tsx'),'utf8');
 assert.match(past,/candidateNctByEvent/);
 assert.doesNotMatch(past,/verifiedNctByEvent/);
 assert.match(past,/<PredictionCells\s*\/>/);
 assert.doesNotMatch(past,/<PredictionCells\s+nct=\{candidateNctByEvent/);
});


test('PAST whole-list audit follows selected year and never uses the 2026 cohort for other years',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Launcher=require('../app/AssessmentLauncher.tsx').default;
 globalThis.IS_REACT_ACT_ENVIRONMENT=true;let tree;
 const originalFetch=global.fetch;
 global.fetch=async url=>{
  assert.match(String(url),/pastRoster=2025/);
  return Response.json({status:'PAST_YEAR_NOT_IMPORTED',year:2025,total:null,linked:0,ready:false,events:[],tasks:[]});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Launcher,{source:'HISTORICAL',historicalYear:'2025'}));});
  await act(async()=>{tree.root.findAllByType('button')[0].props.onClick();});
  await act(async()=>{tree.root.findByProps({'aria-label':'Assessment scope'}).props.onChange({target:{value:'all'}});});
  const audit=tree.root.findAllByType('button').find(button=>button.props.children==='Audit whole PAST 2025 list');
  await act(async()=>{await audit.props.onClick();});
  assert.match(JSON.stringify(tree.toJSON()),/roster incomplete or inconsistent/);
  assert.ok(!JSON.stringify(tree.toJSON()).includes('20 PAST events requiring verified linkage or evidence'));
  assert.equal(tree.root.findAllByType('button').find(button=>['Submit assessments','Run PAST audit and eligible assessments'].includes(button.props.children)).props.disabled,true);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=originalFetch;}
});


test('ASSESSMENTS shows independently pinned FOCUS and year-selectable PAST launchers',()=>{
 const page=fs.readFileSync(require('node:path').join(__dirname,'../app/assessments/page.tsx'),'utf8');
 const past=fs.readFileSync(require('node:path').join(__dirname,'../app/PastAssessmentYearLauncher.tsx'),'utf8');
 assert.match(page,/<AssessmentLauncher source="FOCUS" lockSource\s*\/>/);
 assert.match(page,/<PastAssessmentYearLauncher\s*\/>/);
 assert.match(past,/<AssessmentLauncher source="HISTORICAL" historicalYear=\{year\} lockSource\s*\/>/);
 assert.match(past,/PAST assessment year/);
});

test('whole PAST activates only for an exact complete verified year and carries event-specific cutoffs',async()=>{
 const React=require('react'),{act,create}=require('react-test-renderer'),Launcher=require('../app/AssessmentLauncher.tsx').default;
 globalThis.IS_REACT_ACT_ENVIRONMENT=true;
 const events=require('../data/level4BlindAssessmentQueue20261112.json').historical2026;
 const tasks=events.map((e,i)=>({eventKey:e.eventKey,nct:'NCT'+String(i+1).padStart(8,'0'),cutoffDate:'2025-12-'+String((i%20)+1).padStart(2,'0')}));
 const old=global.fetch;let tree,complete=false;
 global.fetch=async url=>{
  assert.match(String(url),/pastRoster=2026/);
  return Response.json({year:2026,total:20,linked:complete?20:19,ready:complete,
   status:complete?'VERIFIED_WHOLE_PAST_COHORT':'PAST_RECONCILIATION_INCOMPLETE',
   events:events.map((e,i)=>({eventKey:e.eventKey,status:complete||i!==19?'READY':'MISSING_VERIFIED_LINK'})),
   tasks:complete?tasks:[],eligibleTasks:complete?tasks:tasks.slice(0,19)});
 };
 try{
  await act(async()=>{tree=create(React.createElement(Launcher,{source:'HISTORICAL',lockSource:true}));});
  await act(async()=>{tree.root.findAllByType('button')[0].props.onClick();});
  await act(async()=>{tree.root.findByProps({'aria-label':'Assessment scope'}).props.onChange({target:{value:'all'}});});
  const audit=()=>tree.root.findAllByType('button').find(b=>b.props.children==='Audit whole PAST 2026 list');
  const submit=()=>tree.root.findAllByType('button').find(b=>['Submit assessments','Run PAST audit and eligible assessments'].includes(b.props.children));
  await act(async()=>{await audit().props.onClick();});
  assert.equal(submit().props.disabled,false,'partial year can report gaps and assess the 19 source-verified trials');
  complete=true;
  await act(async()=>{await audit().props.onClick();});
  assert.equal(submit().props.disabled,false);
  assert.match(JSON.stringify(tree.toJSON()),/Whole PAST audit loaded: 20 verified trials/);
  assert.equal(tree.root.findAllByType('select').find(sel=>sel.props.value==='BLIND_HISTORICAL').props.disabled,true,'whole PAST must enforce predecision historical mode');
  assert.equal(submit().props.disabled,false,'per-event pre-decision dates remove need for one global cutoff');
  assert.equal(tree.root.findAllByProps({type:'date'}).length,0,'each historical event has its own predecision cutoff');
  assert.equal(tree.root.findAllByType('select').find(sel=>sel.props.value==='HISTORICAL').props.disabled,true);
 }finally{if(tree)await act(async()=>tree.unmount());global.fetch=old;}
});

test('PAST preview can audit all unverified events if old backend lacks roster endpoint without forging trial links',async()=>{
 const old=global.fetch;
 process.env.PDUFA_API_BASE_URL='https://backend.example.test';
 process.env.PDUFA_INTERNAL_API_KEY='SYNTHETIC_INTERNAL_KEY';
 let calls=0;
 global.fetch=async(url,init)=>{
  assert.equal(url,'https://backend.example.test/api/assessment-runtime/past/roster?year=2026');
  assert.equal(init.headers['X-Pdufa-Internal-Key'],'SYNTHETIC_INTERNAL_KEY');
  calls++;
  return Response.json({detail:'Not Found'},{status:404});
 };
 const get=path=>new NextRequest(base+path,{headers:{cookie:auth.COOKIE_NAME+'='+auth.makeSession()}});
 try{
  const response=await api.GET(get('/api/assessments/runtime?pastRoster=2026'));
  assert.equal(response.status,200);
  const report=await response.json();
  assert.equal(report.year,2026);
  assert.equal(report.total,20);
  assert.equal(report.linked,0);
  assert.equal(report.ready,false);
  assert.deepEqual(report.eligibleTasks,[]);
  assert.ok(report.events.every(row=>row.status==='BACKEND_ROSTER_ENDPOINT_NOT_INSTALLED'&&!row.ncts.length));
  assert.equal(calls,1);
  assert.equal((await api.GET(new NextRequest(base+'/api/assessments/runtime?pastRoster=2026'))).status,401);
  assert.equal(calls,1,'No unauthenticated fallback to original research queue');
 }finally{
  global.fetch=old;
  delete process.env.PDUFA_API_BASE_URL;
  delete process.env.PDUFA_INTERNAL_API_KEY;
 }
});

test('historical 2026 FDA goal dates and actual actions have independent source provenance and remain outside scientific scoring',()=>{
 const queue=require('../data/level4BlindAssessmentQueue20261112.json').historical2026;
 const ledger=require('../data/past2026RegulatoryResearch20261115.json');
 assert.equal(ledger.records.length,20);
 assert.equal(new Set(ledger.records.map(r=>r.eventKey)).size,20);
 assert.deepEqual(new Set(ledger.records.map(r=>r.eventKey)),new Set(queue.map(r=>r.eventKey)));
 for(const item of ledger.records){
  const queued=queue.find(q=>q.eventKey===item.eventKey);
  assert.equal(item.targetDate,queued.cutoffDate);
  assert.match(item.targetEvidenceUrl,/^https:\/\//);
  assert.match(item.actionEvidenceUrl,/^https:\/\//);
  assert.equal(typeof item.targetSourcePreActionVerified,'boolean');
  if(!item.targetSourcePreActionVerified)assert.equal(item.targetSourcePublishedDate,null);
  if(item.targetSourcePreActionVerified){
   assert.match(item.targetSourcePublishedDate,/^20\d{2}-\d{2}-\d{2}$/);
   assert.ok(item.targetSourcePublishedDate<item.actualFdaActionDate,'pre-action source must precede FDA decision');
  }
  assert.equal(item.exactNctApplicationReviewCycleVerified,false);
  assert.equal(item.scientificPrediction,null);
  assert.equal(item.scientificScore,null);
  assert.match(item.fdaAction,/^(APPROVED|CRL)$/);
  if(item.actualFdaActionDate)assert.match(item.actualFdaActionDate,/^2026-\d{2}-\d{2}$/);
  assert.equal('nct' in item,false,'target and action dates do not independently link an NCT');
 }
 const m=ledger.records.find(r=>r.eventKey.startsWith('MNKD|2026-07-26|'));
 assert.match(m.product,/NOT sBLA/);
 assert.match(m.applicationDescription,/sNDA, not sBLA/);
 assert.equal(ledger.records.find(r=>r.eventKey.startsWith('RGNX|')).actualFdaActionDate,'2026-02-07');
 assert.equal(ledger.records.find(r=>r.eventKey.startsWith('ARVN|')).actualFdaActionDate,'2026-05-01');
 assert.equal(ledger.records.find(r=>r.eventKey.startsWith('DNLI|')).actualFdaActionDate,'2026-03-24');
 assert.equal(ledger.records.find(r=>r.eventKey.startsWith('TLX|')).actualFdaActionDate,'2026-09-11');
 const past=fs.readFileSync(require('node:path').join(__dirname,'../app/past/page.tsx'),'utf8');
 assert.match(past,/regulatoryByEvent\.get\(r\.eventKey\)/);
 assert.match(past,/!reveal\?"Hidden"/);
 assert.match(past,/Actual FDA action date/);
 assert.match(past,/regulatory\.targetSourcePreActionVerified\?/);
 assert.match(past,/Target source withheld until outcome reveal/);
 const launcher=fs.readFileSync(require('node:path').join(__dirname,'../app/AssessmentLauncher.tsx'),'utf8');
 assert.doesNotMatch(launcher,/past2026RegulatoryResearch20261115/);
});

test('FOCUS per-trial survey display shows 3 persisted source-backed reports on both pages without scoring unvalidated research',()=>{
 const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
 const {FocusSurveyRowDetails,FocusLevelCells}=require('../app/FocusLevelColumns.tsx');
 const id='NCT04576949';
 const levels=Object.fromEntries([1,2,3].map(level=>[String(level),{
  state:'COMPLETED',missingEvidence:[{id:'criterion_'+level,state:'MISSING',explanation:'Protocol not yet supplied'}],
  report:{runId:String(level).repeat(36),nct:id,level,mode:'CURRENT_EVIDENCE',
   executedAt:'2026-11-15T01:00:00Z',score:{kind:'NOT_VALIDATED',value:null},
   fdaPrediction:{outcome:'ABSTAIN',confidence:'UNVALIDATED'}}}]));
 let rendered=renderToStaticMarkup(React.createElement('table',null,React.createElement('tbody',null,
  React.createElement('tr',null,React.createElement(FocusSurveyRowDetails,{nct:id,levels}),
   React.createElement(FocusLevelCells,{nct:id,levels})))));
 assert.match(rendered,/3\/3 surveys saved/);
 for(const term of ['L1','L2','L3','Clinical trial design','Efficacy and statistics','MISSING','NOT VALIDATED','ABSTAIN']){
  assert.ok(rendered.includes(term),term);
 }
 assert.match(rendered,/assessments\?nct=NCT04576949/);
 assert.doesNotMatch(rendered,/FDA approval: 100|predicted approval 100/);
 levels['3'].report.score={kind:'LEVEL_SPECIFIC_EVIDENCE_COVERAGE',value:81};
 rendered=renderToStaticMarkup(React.createElement('table',null,React.createElement('tbody',null,
  React.createElement('tr',null,React.createElement(FocusLevelCells,{nct:id,levels})))));
 assert.doesNotMatch(rendered,/>81</,'documentation coverage is not a validated scientific score');
 const focus=fs.readFileSync(require('node:path').join(__dirname,'../app/focus/page.tsx'),'utf8');
 const assessments=fs.readFileSync(require('node:path').join(__dirname,'../app/assessments/page.tsx'),'utf8');
 const saved=fs.readFileSync(require('node:path').join(__dirname,'../app/FocusSavedAssessments.tsx'),'utf8');
 assert.match(focus,/new Set\(members\.map\(t=>t\.nct\)\)\.size!==expected\.size/);
 assert.match(focus,/<FocusSurveyRowDetails nct=\{t\.nct\}/);
 assert.match(focus,/<FocusLevelCells nct=\{t\.nct\}/);
 assert.match(assessments,/<FocusSavedAssessments selectedNct=\{nct\}\/>/);
 assert.match(saved,/\?nct='\+encodeURIComponent\(t\.nct\)/);
 assert.match(saved,/data\.fullyProcessed===data\.total/);
});
