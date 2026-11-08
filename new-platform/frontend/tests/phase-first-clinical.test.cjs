'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,f);
const {evaluatePhaseFirst,verifiedPhase}=require('../lib/phase-first-clinical.ts');
const {phaseFirstReport,phaseFirstContext}=require('../lib/phase-first-report.ts');
const ax=require('../data/axsomePhaseFirstRegistry20261106.json');
const census=require('../public/phase3-unified-classifications-2026-11-05.json');
const fixture=structuredClone(ax.records.find(t=>t.trialId==='NCT07717879'));
const ctx=()=>({...phaseFirstContext(fixture,false),additionalEvidence:{},regulatory:null,publicReadoutDocumented:false});
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
 assert.equal('overallRating' in r,false);assert.equal('factors' in r,false);
});
test('ongoing applicable results are pending, not missing efficacy',()=>{
 const r=evaluate();assert.equal(evidence(r,'phase3Results').status,'PENDING');assert.equal(evidence(r,'safety').status,'PENDING');
 assert.equal('overallRating' in r,false);assert.equal('raasPredictionConfidence' in r,false);assert.equal(r.fdaPrediction.probabilities,null);
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
 const o=evaluate({...fixture,studyType:'OBSERVATIONAL',phases:[]});assert.equal(o.phase.verified,false);assert.equal('overallRating' in o,false);
 assert.equal(evidence(o,'design').status,'AVAILABLE');assert.equal(evidence(o,'power').status,'NOT APPLICABLE');
});
test('legacy score inputs cannot enter active source analysis',()=>{
 const injected={...ctx(),legacyStage:'pre',stageVerified:true,approvedRaas:100,reviewedFactors:[{key:'safety',grade:100,sourceUrl:fixture.sourceUrl,sourceDate:'2026-01-01',assessedAt:'2026-11-06',benchmarkSourceUrl:'https://pubmed.ncbi.nlm.nih.gov/35649167/',finding:'Synthetic legacy input'}]};
 const clean=evaluate(fixture,ctx()),attempt=evaluate(fixture,injected);
 assert.deepEqual(attempt,clean);
 for(const field of ['factors','overallRating','ratingKind','ratingCoverage','raasScore','raasPredictionConfidence'])assert.equal(field in attempt,false,field);
 assert.equal(attempt.analysisMode,'PHASE_APPROPRIATE_SOURCE_EVIDENCE_ONLY');
});
test('identity and chronology fail closed',()=>{
 assert.throws(()=>evaluate({...fixture,trialId:'NOT_AN_ID'}),/IDENTITY/);
 assert.throws(()=>evaluate({...fixture,nctId:'NCT00000000'}),/IDENTITY/);
 assert.throws(()=>evaluate({...fixture,sourceUrl:'https://clinicaltrials.gov/study/NCT00000000'}),/IDENTITY/);
 assert.throws(()=>evaluate({...fixture,sourceDate:'2026-12-01'}),/CHRONOLOGY/);
 assert.throws(()=>evaluate(fixture,{...ctx(),additionalEvidence:{mechanism:{url:'https://example.org',date:'2026-12-01',text:'Future'}}}),/CHRONOLOGY/);
});
test('all Alkermes trial identities survive without executing historical scores',()=>{
 const r=phaseFirstReport('alkermes');assert.equal(r.trialCount,128);
 assert.equal(r.analysisMode,'PHASE_APPROPRIATE_SOURCE_EVIDENCE_ONLY');
 for(const t of r.trials)assert.equal('overallRating' in t,false);
 for(const k of ['ratedTrials','fullyCoveredRatings','scoredComponents'])assert.equal(k in r,false);
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
 assert.equal('ratedTrials' in r,false);assert.equal(r.fdaPredictions,0);
});
test('aggregate evidence counts equal actual records and all trial records have provenance',()=>{
 for(const scope of ['alkermes','axsome','sinovac','census']){
  const r=phaseFirstReport(scope);let count=0;const actual={};
  for(const t of r.trials){assert.equal(t.evidence.length,36);assert.equal('factors' in t,false);assert.equal(t.pipeline.automaticTransfer,false);
   for(const e of t.evidence){actual[e.status]=(actual[e.status]||0)+1;count++;assert.equal(e.reviewedAt,'2026-11-06');assert.ok(e.searchedSourceUrl.startsWith('https://'));
    if(e.status==='AVAILABLE'){assert.ok(e.sourceUrl?.startsWith('https://'));assert.ok(e.evidenceDate);}
   }
  }
  assert.equal(count,r.trialCount*36);for(const [s,n] of Object.entries(r.evidenceCounts))assert.equal(n,actual[s]||0);
 }
});
test('API summary fits deployment response budget; details and CSV use exact identifiers',async()=>{
 const {GET}=require('../app/api/phase-first/route.ts');
 for(const scope of ['alkermes','axsome','sinovac','census']){
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

test('Sinovac is next by prevalence; all27 individually verified phases retain trading restriction',()=>{
 const counts=new Map();for(const r of census.rows)counts.set(r.ticker,(counts.get(r.ticker)||0)+1);
 assert.deepEqual([...counts].sort((a,b)=>b[1]-a[1]).slice(0,3),[['ALKS',34],['AXSM',28],['SVA',27]]);
 const r=phaseFirstReport('sinovac');assert.equal(r.trialCount,27);assert.deepEqual(r.byPhase,{'Phase 3':27});
 assert.equal(r.trials.filter(t=>t.status==='COMPLETED').length,17);
 assert.equal('ratedTrials' in r,false);assert.equal(r.fdaPredictions,0);
 for(const t of r.trials){assert.match(t.pipeline.companyRestriction,/Excluded|halt/);assert.equal(t.pipeline.automaticTransfer,false);assert.equal('raasScore' in t,false);}
 const all=phaseFirstReport('census');assert.equal(all.trials.filter(t=>t.ticker==='SVA'&&t.pipeline.companyRestriction).length,27);
 assert.equal(phaseFirstReport('axsome').trials.some(t=>t.pipeline.companyRestriction),false);
 const queue=require('../data/phase3InvestorRelationsResearchQueue20261106.json').companies.find(c=>c.ticker==='SVA');
 assert.equal(queue.searchStatus,'PARTIALLY_REVIEWED');
 assert.equal(queue.trials.filter(t=>t.identityMatched).length,27);
 for(const t of queue.trials)assert.equal(new Set(t.questionReview.map(q=>q.number)).size,30);
});
test('Sinovac original SAPs and published immune response do not invent clinical verdicts',()=>{
 const r=phaseFirstReport('sinovac'),byId=new Map(r.trials.map(t=>[t.trialId,t]));
 for(const n of ['NCT05850364','NCT06049927']){
  assert.equal(evidence(byId.get(n),'power').status,'AVAILABLE');assert.match(evidence(byId.get(n),'power').sourceUrl,new RegExp(n));
  assert.match(evidence(byId.get(n),'uncertainty').sourceUrl,/SAP_001.pdf/);
 }
 assert.match(evidence(byId.get('NCT05850364'),'uncertainty').evidence,/LOCF/);
 assert.match(evidence(byId.get('NCT06049927'),'uncertainty').evidence,/Multiple|multiple/);
 assert.match(evidence(byId.get('NCT05850364'),'phase3Results').evidence,/unadjudicated/);
 assert.equal(evidence(byId.get('NCT05245552'),'phase3Results').status,'MISSING');
 assert.equal(evidence(byId.get('NCT07211152'),'phase3Results').status,'MISSING');
 assert.equal(evidence(byId.get('NCT06734832'),'phase3Results').status,'PENDING');
 assert.equal(evidence(byId.get('NCT07611513'),'priorEfficacySafety').confidence,'MODERATE');
 for(const t of r.trials){assert.equal(t.fdaPrediction.probabilities,null);assert.notEqual(evidence(t,'fdaOutcome').status,'AVAILABLE');}
 const adjudications=require('../data/phase3EndpointAdjudications20261105.json').records;
 assert.equal(adjudications.filter(x=>byId.has(x.nctId)).length,14);
 assert.equal(adjudications.some(x=>x.nctId==='NCT05850364'),false);
});
test('nine exact-trial30-question facts are sourced and nonnumeric without duplicate slots',()=>{
 const evidenceData=require('../data/sinovacPhaseFirstEvidence20261106.json');
 const ir=require('../data/phase3CompanyWebsiteEvidence20261105.json').assessmentRecords;
 const slots=ir.map(r=>r.nctId+':'+r.assessmentNumber);assert.equal(new Set(slots).size,slots.length);
 assert.equal(evidenceData.questionFacts.length,9);
 for(const fact of evidenceData.questionFacts){
  const stored=ir.find(r=>r.nctId===fact.nctId&&r.assessmentNumber===fact.assessmentNumber);
  assert.ok(stored);assert.equal(stored.classification,'DOCUMENTED_SOURCE_FACT');assert.equal(stored.evidence,fact.evidence);
  assert.equal(stored.score,undefined);assert.equal(stored.prediction,undefined);
 }
 assert.equal(ir.some(r=>r.nctId==='NCT05245552'&&[13,14,15].includes(r.assessmentNumber)),false);
});
test('released918 history events stay byte-equivalent in their canonical JSON representation',()=>{
 const history=require('../data/phaseFirstRatingHistory20261106.json');
 const hash=require('node:crypto').createHash('sha256').update(JSON.stringify(history.records.slice(0,918))).digest('hex');
 assert.equal(hash,'72f2635c5d228dbd96cc75dcb7a2e5d8fdfbc19278e6859c171550842085f746');
 const sva=history.records.filter(r=>r.sourceScope==='sinovac');assert.ok(sva.length>=27);
 assert.equal(new Set(sva.map(r=>r.continuityKey)).size,27);
});
