"use strict";
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{fileName:f,compilerOptions:{module:1,target:9,esModuleInterop:true}}).outputText,f);
const {topOnlyReport}=require('../lib/top-only-completion.ts');
const {GET}=require('../app/api/top-only-completion/route.ts');
const base=require('../data/topOnlyBaseline20261107.json'),matrix=require('../data/topOnly190Baseline20261107.json'),history=require('../data/topOnlyResearchHistory20261107.json');
const report=topOnlyReport(),ids=new Set(base.records.map(r=>r.nctId));
test('every frozen TOP identity has 190 accounted fields and 30 explicit metric dispositions',()=>{
 assert.equal(report.trialCount,ids.size);assert.equal(new Set(report.trials.map(t=>t.nctId)).size,ids.size);
 assert.deepEqual(new Set(report.trials.map(t=>t.nctId)),ids);assert.deepEqual(report.headers,matrix.headers);
 assert.equal(report.allFieldsAccounted,ids.size);assert.equal(report.allMetricsEvaluated,ids.size);
 for(const t of report.trials){assert.equal(t.worksheet,'TOP');assert.equal(t.membership,'UNCHANGED_FROZEN_TOP');assert.equal(t.fields.length,190);assert.equal(t.metrics.length,30);assert.equal(new Set(t.metrics.map(m=>m.id)).size,30);assert.ok(t.fields.every(f=>f.exportValue!==''));assert.equal(t.registryVerified,true);assert.match(t.phase,/PHASE3/);}
});
test('verified original facts, original scores and predictions remain verbatim',()=>{
 const old=new Map(matrix.rows.map(r=>[r[0],r]));let verified=0;
 for(const t of report.trials){const r=old.get(t.nctId);for(let q=0;q<30;q++){const p=40+q*5;
  if(/SOURCE_FACT|OBSERVED_|DOCUMENTED_/.test(r[p])&&/^https:\/\//.test(r[p+4])){verified++;for(let j=0;j<5;j++)if(r[p+j].trim())assert.equal(t.fields[p+j].exportValue,r[p+j]);}
  for(const j of [1,2])if(r[p+j].trim())assert.equal(t.fields[p+j].exportValue,r[p+j]);
 }}assert.ok(verified>2000);
});
test('facts do not create grades, full overalls require existing complete inputs and weights remain canonical',()=>{
 const {clinicalFiveForTrial}=require('../lib/raas-clinical-five.ts');const grades=[...require('../data/raas-reviewed-metric-assessments.json').records,...require('../data/raas-clinical-five-reviewed-increment.json').records];
 for(const t of report.trials){const programs=[...new Map(grades.filter(g=>g.nctId===t.nctId&&g.ticker===t.ticker&&g.stage==='pre').map(g=>[JSON.stringify([g.drug,g.indication]),g])).values()];const p=programs.length===1?programs[0]:null;
  const canonical=clinicalFiveForTrial({nctId:t.nctId,ticker:t.ticker,drug:p?.drug??t.drug,indication:p?.indication??t.indication},'pre',true);
  assert.equal(t.clinicalFullScore,canonical.researchScore);assert.equal(t.clinicalFullScore===null,t.clinicalScoredFactors!==5);
  assert.equal(t.metrics.reduce((n,m)=>n+m.activeClinicalWeightPercent,0),100);assert.ok(Math.abs(t.metrics.reduce((n,m)=>n+m.originalWeightPercent,0)-100)<1e-8);
  for(const m of t.metrics){if(m.score!==null){assert.ok(m.sourceUrl&&m.benchmarkSourceUrl&&m.sourceDate&&m.assessedAt&&m.observedResult&&m.uncertaintyReview&&m.criticalRiskReview);}else assert.ok(m.blocker);}
  assert.equal(t.prospectivePrediction,null);assert.equal(t.predictionEligibility,'ABSTAIN');
 }assert.equal(report.completeThirtyMetricOverallScores,0);
});
test('pending and later-stage evidence never lower the expected-evidence denominator',()=>{
 let excluded=0;
 for(const t of report.trials){const expected=t.questions.filter(q=>!['PENDING','NOT YET EXPECTED','NOT APPLICABLE'].includes(q.state));excluded+=30-expected.length;
  assert.equal(t.sourceCompleteness,expected.length?Math.round(expected.filter(q=>q.state==='VERIFIED').length/expected.length*1000)/10:null);
 }assert.ok(excluded>0);assert.equal(Object.values(report.sourceStateCounts).reduce((a,b)=>a+b,0),ids.size*30);
});
test('known Essential3 results stay component-specific, observational and inside unchanged TOP membership',()=>{
 const t=report.trials.find(t=>t.nctId==='NCT06087276');assert.equal(t.knownPublicResults,true);assert.equal(t.worksheet,'TOP');assert.equal(t.prospectivePrediction,null);
 const facts=t.additionalReviewedFacts.map(f=>f.evidence).join(' ');assert.match(facts,/Study1/);assert.match(facts,/Study2/);assert.match(facts,/27.0%/);assert.match(facts,/1.7%/);
});
test('every TOP trial and company received a recorded source search; document access failures remain explicit',()=>{
 for(const t of report.trials){assert.equal(t.sourceDiscovery.exactNctSearch.nctId,t.nctId);assert.equal(t.sourceDiscovery.companySearch.ticker,t.ticker);assert.match(t.sourceDiscovery.exactNctSearch.q,new RegExp(t.nctId));}
 assert.equal(report.exactNctSearches,ids.size);assert.equal(report.companiesSearched,new Set(base.records.map(r=>r.ticker)).size);assert.equal(report.documentsAttempted,report.documentsRetrieved+report.documentsBlocked);
});
test('Phase II dose-finding and conflicting or pooled publications never become current Phase III outcomes',()=>{
 const t=report.trials.find(t=>t.nctId==='NCT04871282');assert.equal(t.knownPublicResults,false);assert.equal(t.prospectivePrediction,null);assert.match(t.additionalReviewedFacts.find(f=>f.question===5).evidence,/Phase II dose-finding/);assert.equal(t.questions[4].state,'VERIFIED');
 const triage=require('../data/topOnlyPublicationTriage20261107.json').records;assert.equal(triage.find(p=>p.pmid==='42641848').state,'CONFLICTING_NCT_IN_ABSTRACT');assert.equal(triage.find(p=>p.pmid==='40285763').state,'POOLED_MULTI_TRIAL_FIGURES_NOT_ATTRIBUTED');
 const forest=report.trials.find(t=>t.nctId==='NCT04848506');assert.ok(forest.publicationLeads.some(p=>p.classification==='CONFLICTING_NCT_IN_ABSTRACT'));assert.ok(!forest.additionalReviewedFacts.some(f=>f.sourceUrl.endsWith('/42641848/')));
});
test('new history contains only frozen TOP identities and unique append-only fingerprints',()=>{
 assert.equal(new Set(history.records.map(r=>r.eventId)).size,history.records.length);assert.deepEqual(new Set(history.records.map(r=>r.nctId)),ids);
 for(const h of history.records){assert.ok(h.eventId.endsWith(h.evidenceFingerprint));assert.equal(h.summary.fieldsAccounted,190);assert.equal(h.summary.metricsEvaluated,30);}
});
function csvParse(input){const out=[];let row=[],cell='',quoted=false;for(let i=0;i<input.length;i++){const c=input[i];if(c==='"'){if(quoted&&input[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));out.push(row);row=[];cell='';}else cell+=c;}return out;}
test('TOP API exports exact 190-column CSV, all metric rows, and rejects out-of-scope records',async()=>{
 const r=await GET(new Request('http://localhost/api/top-only-completion?format=csv'));assert.equal(r.status,200);const csv=csvParse((await r.text()).replace(/^\uFEFF/,''));assert.equal(csv.length,ids.size+1);assert.deepEqual(csv[0],matrix.headers);assert.ok(csv.every(r=>r.length===190));assert.ok(csv.slice(1).every(r=>r.every(c=>c!=='')));assert.deepEqual(new Set(csv.slice(1).map(r=>r[0])),ids);
 const metrics=await GET(new Request('http://localhost/api/top-only-completion?format=metrics'));assert.equal(csvParse((await metrics.text()).replace(/^\uFEFF/,'')).length,1+ids.size*30);
 assert.equal((await GET(new Request('http://localhost/api/top-only-completion?nctId=NCT00000000'))).status,404);assert.equal((await GET(new Request('http://localhost/api/top-only-completion?nctId=invalid'))).status,400);
 const detail=await(await GET(new Request('http://localhost/api/top-only-completion?nctId='+base.records[0].nctId))).json();assert.equal(detail.trial.fields.length,190);assert.ok(detail.history.length);
});
test('TOP UI and TOP scoring modules remain intact while BOTTOM has its own independent renderer',()=>{
 const ui=fs.readFileSync(path.join(__dirname,'../app/Phase3SourceOnlySheets.tsx'),'utf8');assert.match(ui,/<TopOnlyCompletionSheet query=\{query\}\/>/);assert.match(ui,/<BottomOnlyCompletionSheet query=\{query\}\/>/);
 const model=fs.readFileSync(path.join(__dirname,'../lib/top-only-completion.ts'),'utf8');assert.doesNotMatch(model,/writeFile|sendTelegram|GEM_JR|streamlit|updatePipeline/);
});
