'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,f);
const {evaluatePhaseFirst,verifiedPhase}=require('../lib/phase-first-clinical.ts');
const {phaseFirstReport,phaseFirstContext}=require('../lib/phase-first-report.ts');
const ax=require('../data/axsomePhaseFirstRegistry20261106.json');
const census=require('../public/phase3-unified-classifications-2026-11-05.json');
const fixture=structuredClone(ax.records.find(t=>t.trialId==='NCT07717879'));
const ctx=()=>({...phaseFirstContext(fixture,false),additionalEvidence:{},reviewedFactors:[],regulatory:null,legacyStage:null,stageVerified:false});
const evidence=(t,id)=>t.evidence.find(e=>e.id===id);
const evaluate=(t=fixture,c=ctx())=>evaluatePhaseFirst(t,c,'2026-11-06');

test('exact 762 identities retained; next prevalent company is AXSM with28',()=>{
 const counts=new Map();for(const r of census.rows)counts.set(r.ticker,(counts.get(r.ticker)||0)+1);
 assert.deepEqual([...counts].sort((a,b)=>b[1]-a[1]).slice(0,2),[['ALKS',34],['AXSM',28]]);
 const ids=census.rows.map(t=>t.nctId);assert.equal(new Set(ids).size,762);
 const all=phaseFirstReport('census');assert.deepEqual(all.trials.map(t=>t.trialId).sort(),ids.sort());
 const r=phaseFirstReport('axsome');assert.equal(r.trialCount,28);assert.deepEqual(r.byPhase,{'Phase 3':27,'Phase 2 / Phase 3':1});
});
test('mixed and early phases stay individual-trial phases',()=>{
 assert.equal(verifiedPhase(['PHASE1','PHASE2'],'INTERVENTIONAL').label,'Phase 1 / Phase 2');
 const t={...fixture,phases:['PHASE1']};const r=evaluate(t,{...ctx(),programPhase:'Phase 3'});
 assert.equal(r.phase.label,'Phase 1');assert.equal(evidence(r,'phase3Results').status,'NOT YET EXPECTED');
 assert.equal(evidence(r,'pdufa').status,'NOT YET EXPECTED');assert.equal(r.fdaPrediction.status,'NOT YET ELIGIBLE');
 assert.equal(r.factors.find(f=>f.key==='efficacy').applicability,'NOT YET EXPECTED');assert.equal(r.overallRating,null);
});
test('ongoing applicable results are pending, not missing efficacy',()=>{
 const r=evaluate();assert.equal(evidence(r,'phase3Results').status,'PENDING');assert.equal(evidence(r,'safety').status,'PENDING');
 assert.equal(r.overallRating,null);assert.equal(r.raasPredictionConfidence,null);assert.equal(r.fdaPrediction.probabilities,null);
 const due=r.evidence.filter(e=>['AVAILABLE','MISSING','CONFLICTING'].includes(e.status));
 assert.equal(r.evidenceCompleteness,Math.round(r.evidenceCounts.AVAILABLE/due.length*1000)/10);
});
test('completed trials require results; zero-enrollment withdrawn trials cannot have outcomes',()=>{
 assert.equal(evidence(evaluate({...fixture,status:'COMPLETED'}),'phase3Results').status,'MISSING');
 assert.equal(evidence(evaluate({...fixture,status:'WITHDRAWN',enrollment:{count:0}}),'phase3Results').status,'NOT APPLICABLE');
});
test('phase4 and observational studies do not become pivotal trials',()=>{
 const r=evaluate({...fixture,phases:['PHASE4'],status:'COMPLETED'});
 assert.equal(evidence(r,'phase3Results').status,'NOT APPLICABLE');
 const o=evaluate({...fixture,studyType:'OBSERVATIONAL',phases:[]});assert.equal(o.phase.verified,false);assert.equal(o.overallRating,null);
 assert.equal(evidence(o,'design').status,'AVAILABLE');assert.equal(evidence(o,'power').status,'NOT APPLICABLE');
});
test('partial ratings normalize only dated benchmark-reviewed eligible components',()=>{
 const f=(key,grade)=>({key,grade,sourceUrl:fixture.sourceUrl,sourceDate:'2026-01-01',assessedAt:'2026-11-06',benchmarkSourceUrl:'https://pubmed.ncbi.nlm.nih.gov/35649167/',finding:'Synthetic test grade, never persisted'});
 const c={...ctx(),legacyStage:'pre',stageVerified:true,reviewedFactors:[f('statistics',75),f('safety',25)]};
 const r=evaluate(fixture,c);assert.equal(r.overallRating,50);assert.equal(r.ratingCoverage.scored,2);assert.equal(r.ratingCoverage.eligible,5);assert.equal(r.ratingCoverage.percent,40);assert.equal(r.ratingKind,'PARTIAL_SCORED_COMPONENT_MEAN');
 const future=structuredClone(c);future.reviewedFactors[0].assessedAt='2026-12-01';assert.equal(evaluate(fixture,future).ratingCoverage.scored,1);
 const noBenchmark=structuredClone(c);noBenchmark.reviewedFactors[0].benchmarkSourceUrl=null;assert.equal(evaluate(fixture,noBenchmark).ratingCoverage.scored,1);
 const early={...fixture,phases:['PHASE1']};assert.equal(evaluate(early,c).ratingCoverage.scored,0);
 const explicit={...c,reviewedFactors:[{...f('safety',75),phaseScope:['PHASE1']}]};assert.equal(evaluate(early,explicit).ratingCoverage.scored,1);
});
test('identity and chronology fail closed',()=>{
 assert.throws(()=>evaluate({...fixture,trialId:'NOT_AN_ID'}),/IDENTITY/);
 assert.throws(()=>evaluate({...fixture,nctId:'NCT00000000'}),/IDENTITY/);
 assert.throws(()=>evaluate({...fixture,sourceUrl:'https://clinicaltrials.gov/study/NCT00000000'}),/IDENTITY/);
 assert.throws(()=>evaluate({...fixture,sourceDate:'2026-12-01'}),/CHRONOLOGY/);
 assert.throws(()=>evaluate(fixture,{...ctx(),additionalEvidence:{mechanism:{url:'https://example.org',date:'2026-12-01',text:'Future'}}}),/CHRONOLOGY/);
});
test('Alkermes original reviewed grades remain34 trials115 components; early trials ungraded',()=>{
 const r=phaseFirstReport('alkermes');assert.equal(r.trialCount,128);assert.equal(r.ratedTrials,34);assert.equal(r.scoredComponents,115);
 for(const t of r.trials.filter(t=>t.phase.maturity<3))assert.equal(t.overallRating,null);
 assert.equal(r.fdaPredictions,0);
});
test('Axsome outcomes and endpoint/status conflicts remain visible independently of FDA approval',()=>{
 const r=phaseFirstReport('axsome'),byId=new Map(r.trials.map(t=>[t.trialId,t]));
 assert.equal(evidence(byId.get('NCT02504008'),'status').status,'CONFLICTING');
 assert.match(evidence(byId.get('NCT02504008'),'phase3Results').evidence,/futility/);
 assert.equal(evidence(byId.get('NCT05550207'),'primary').status,'CONFLICTING');
 assert.match(evidence(byId.get('NCT02741791'),'phase3Results').evidence,/did not meet/);
 assert.match(evidence(byId.get('NCT06360419'),'phase3Results').evidence,/did not achieve/);
 assert.match(evidence(byId.get('NCT05557409'),'phase3Results').evidence,/not|fail|signific/i);
 for(const n of ['NCT05059223','NCT05113745']){
  assert.equal(evidence(byId.get(n),'fdaAcceptance').status,'AVAILABLE');
  assert.match(evidence(byId.get(n),'pdufa').evidence,/2027/);assert.equal(evidence(byId.get(n),'fdaOutcome').status,'PENDING');
  assert.notEqual(evidence(byId.get(n),'inspections').status,'AVAILABLE');
 }
 assert.equal(r.ratedTrials,0);assert.equal(r.fdaPredictions,0);
});
test('aggregate evidence counts equal actual records and all trial records have provenance',()=>{
 for(const scope of ['alkermes','axsome','census']){
  const r=phaseFirstReport(scope);let count=0;const actual={};
  for(const t of r.trials){assert.equal(t.evidence.length,36);assert.equal(t.factors.length,5);assert.equal(t.pipeline.automaticTransfer,false);
   for(const e of t.evidence){actual[e.status]=(actual[e.status]||0)+1;count++;assert.equal(e.reviewedAt,'2026-11-06');assert.ok(e.searchedSourceUrl.startsWith('https://'));
    if(e.status==='AVAILABLE'){assert.ok(e.sourceUrl?.startsWith('https://'));assert.ok(e.evidenceDate);}
   }
  }
  assert.equal(count,r.trialCount*36);for(const [s,n] of Object.entries(r.evidenceCounts))assert.equal(n,actual[s]||0);
 }
});
test('API summary fits deployment response budget; details and CSV use exact identifiers',async()=>{
 const {GET}=require('../app/api/phase-first/route.ts');
 for(const scope of ['alkermes','axsome','census']){
  const response=await GET(new Request('https://local/api/phase-first?scope='+scope));assert.equal(response.status,200);
  const text=await response.text();assert.ok(Buffer.byteLength(text)<4_000_000);const r=JSON.parse(text);assert.equal(r.trials[0].evidence.length,0);
 }
 const detail=await (await GET(new Request('https://local/api/phase-first?scope=axsome&trialId=NCT05550207'))).json();assert.equal(detail.trials.length,1);assert.equal(detail.trials[0].evidence.length,36);
 assert.equal((await GET(new Request('https://local/api/phase-first?scope=bad'))).status,400);
 assert.equal((await GET(new Request('https://local/api/phase-first?trialId=bad'))).status,400);
 assert.equal((await GET(new Request('https://local/api/phase-first?scope=axsome&trialId=NCT00000000'))).status,404);
 const csv=await (await GET(new Request('https://local/api/phase-first?scope=axsome&format=csv'))).text();assert.equal(csv.trim().split('\r\n').length,29);
});
test('trial-based history retains separate scope snapshots with stable fingerprints',async()=>{
 const {GET}=require('../app/api/phase-first/history/route.ts');
 const response=GET(new Request('https://local/api/phase-first/history?trialId=NCT05550207'));assert.equal(response.status,200);
 const h=await response.json();assert.deepEqual(new Set(h.records.map(r=>r.sourceScope)),new Set(['axsome','census']));
 const ledger=require('../data/phaseFirstRatingHistory20261106.json');assert.equal(new Set(ledger.records.map(r=>r.eventId)).size,ledger.records.length);
 for(const r of ledger.records){assert.equal(r.continuityKey,r.payload.trialId);assert.match(r.evidenceFingerprint,/^[a-f0-9]{64}$/);}
 assert.equal(GET(new Request('https://local/api/phase-first/history')).status,400);
});
