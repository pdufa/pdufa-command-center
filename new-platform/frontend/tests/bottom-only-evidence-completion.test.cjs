const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,f);
const {bottomOnlyReport,bottomSourceReviewIsCurrent}=require('../lib/bottom-only-completion.ts');
const {bottomTrialHistory,bottomExport,csvCell}=require('../lib/bottom-only-exports.ts');
const baseline=require('../data/bottomOnlyBaseline20261107.json');
const active=require('../data/p3PostDataActive.json');
const grades=require('../data/bottomOnlyReviewedGradeIncrement20261107.json');
const report=bottomOnlyReport();
test('every saved BOTTOM exact NCT has a complete disposition, never company-matched',()=>{
 assert.deepEqual(report.trials.map(t=>t.nctId),baseline.records.map(t=>t.nctId));
 assert.equal(new Set(report.trials.map(t=>t.nctId)).size,report.trialCount);
 for(const t of report.trials){
  assert.equal(t.registryReview.identity.nctId,t.nctId);
  assert.ok(t.registryReview.phase.includes('PHASE3'));
  assert.equal(t.clinicalFactors.length,5);assert.equal(t.fields.length,190);
  assert.equal(t.metrics.filter(m=>m.activeClinicalWeightPercent===20).length,5);
  assert.ok(t.metrics.filter(m=>!m.activeInClinicalModel).every(m=>m.activeClinicalWeightPercent===0));
  assert.ok(t.clinicalFactors.every(f=>f.grade!==null||f.blocker));
 }
});
test('partial results and genuine negative evidence receive distinct assessments',()=>{
 const rise=report.trials.find(t=>t.nctId==='NCT05031780');
 assert.equal(rise.clinicalFactors[0].grade,50);assert.equal(rise.clinicalFactors[1].grade,25);
 assert.match(rise.clinicalFactors[0].observedResult,/0.1213/);
 const kids=report.trials.find(t=>t.nctId==='NCT05144256');
 assert.equal(kids.clinicalFactors[0].grade,25);assert.equal(kids.clinicalFactors[4].grade,null);
 assert.equal(kids.clinicalFullScore,null);
});
test('unreported tables and absent PK-to-efficacy rule stay null, never midpoint or zero',()=>{
 const apex=report.trials.find(t=>t.nctId==='NCT05453968');
 assert.equal(apex.clinicalFactors[0].grade,null);
 assert.equal(apex.clinicalFactors[0].evidenceState,'BLOCKED_RULE');
 assert.equal(apex.metrics.find(m=>m.id==='post-1-1').state,'BLOCKED_RULE');
 const fusion=report.trials.find(t=>t.nctId==='NCT04768972');
 assert.ok(fusion.clinicalFactors.every(f=>f.grade===null));assert.equal(fusion.clinicalFullScore,null);
 assert.equal(report.activeFactorsScored,203);assert.equal(report.completeClinicalOverallScores,26);
});
test('combined score uses all five supported factors at 20 percent and does not include archived metrics',()=>{
 for(const t of report.trials){
  const scored=t.clinicalFactors.filter(f=>f.grade!==null);
  assert.ok(scored.every(f=>[0,25,50,75,100].includes(f.grade)));
  assert.equal(t.clinicalFullScore,scored.length===5?Math.round(scored.reduce((n,f)=>n+f.grade,0)/5*10)/10:null);
  for(const f of scored)assert.ok(f.sourceUrl&&f.benchmarkSourceUrl&&f.observedResult&&f.uncertaintyReview);
 }
});
test('source revision requires review while score histories remain exact-NCT and append-only',()=>{
 const nct='NCT04849741';assert.equal(bottomSourceReviewIsCurrent(nct,'changed'),false);
 assert.equal(bottomSourceReviewIsCurrent(nct,grades.evidenceReviewHashes[nct]),true);
 const history=bottomTrialHistory(nct);assert.ok(history.length>=2);
 assert.ok(history.every(h=>h.nctId===nct));
 assert.ok(history.some(h=>h.recordedAt==='2026-11-06'));
 assert.ok(history.some(h=>h.clinicalScoredFactors===5));
 const all=require('../data/bottomOnlyScoreHistory20261107.json').records;
 assert.equal(new Set(all.map(x=>x.eventId)).size,all.length);
});
test('active API respects live roster and exact NCT; archived same-company studies cannot leak',async()=>{
 const {GET}=require('../app/api/p3-post-data-research/route.ts');
 const list=await GET(new Request('http://localhost/api/p3-post-data-research')).json();
 assert.equal(list.rows.length,active.records.length);assert.equal(list.activeFactorCount,active.records.length*5);assert.equal(list.activeFactorsScored,128);
 assert.ok(list.rows.every(r=>active.records.some(t=>t.nct===r.nctId)));
 assert.equal(GET(new Request('http://localhost/api/p3-post-data-research?nctId=NCT05257408')).status,404);
 assert.equal(GET(new Request('http://localhost/api/p3-post-data-research?nctId=CORT')).status,422);
 assert.ok(!list.rows.some(t=>t.nctId==='NCT05257408'));
 const detail=await GET(new Request('http://localhost/api/p3-post-data-research?nctId=NCT04544293')).json();
 assert.equal(detail.trial.clinicalFullScore,report.trials.find(t=>t.nctId==='NCT04544293').clinicalFullScore);
 assert.ok(detail.history.every(h=>h.nctId==='NCT04544293'));
});
test('exports preserve numeric missingness and formula-safe source text',()=>{
 assert.equal(csvCell(null),'""');assert.equal(csvCell('=1+1'),'"\'=1+1"');
 const csv=bottomExport('rating-evidence');assert.ok(csv.includes('BLOCKED_RULE'));
 assert.ok(csv.includes('NCT04768972'));assert.equal(csv.trim().split('\r\n').length,report.trialCount*5+1);
 const allowed=new Set(active.records.map(t=>t.nct));
 assert.equal(bottomExport('rating-evidence',allowed).trim().split('\r\n').length,active.records.length*5+1);
});

test('current roster has every exact NCT while historical research survives active filtering',()=>{
 const originals=new Set(baseline.originalResearchNcts);
 assert.equal(report.trials.filter(t=>originals.has(t.nctId)).length,originals.size);
 assert.ok(active.records.every(r=>report.trials.some(t=>t.nctId===r.nct)));
 assert.equal(report.trials.filter(t=>!active.records.some(r=>r.nct===t.nctId)).length,18);
 assert.ok(report.trials.every(t=>t.clinicalFactors.every(f=>f.grade!==null||f.reviewDisposition)));
 assert.ok(report.trials.every(t=>t.metrics.filter(m=>!m.activeInClinicalModel).every(m=>m.state==='ARCHIVED_NOT_ACTIVE')));
});
test('Essential3 headline, mixed-dose ABTECT and VELA pooled safety are not misassigned',()=>{
 const praxis=report.trials.find(t=>t.nctId==='NCT06087276');
 assert.match(praxis.clinicalFactors[0].observedResult,/-2.6/);
 assert.equal(praxis.clinicalFactors[4].grade,25);
 const vela=report.trials.find(t=>t.nctId==='NCT06411899');
 assert.equal(vela.readoutOutcome,'PRIMARY_ENDPOINT_NOT_MET');
 assert.equal(vela.clinicalFactors[2].grade,25);assert.equal(vela.clinicalFactors[4].grade,null);
 assert.match(vela.clinicalFactors[4].blocker,/pooled/i);
 const abtect=report.trials.find(t=>t.nctId==='NCT05507216');assert.equal(abtect.readoutOutcome,'MIXED_DOSE_RESULTS');
});
test('cross-stage shared history remains linked only by exact NCT',()=>{
 const shared=require('../data/raas-trial-score-history.json').records;
 for(const r of shared){
  assert.ok(bottomTrialHistory(r.nctId).some(h=>h.eventId===r.eventId));
  assert.ok(bottomTrialHistory(r.nctId).every(h=>h.nctId===r.nctId));
 }
});

test('legacy shared metric score snapshots normalize for expandable history without undefined grades',()=>{
 const history=bottomTrialHistory('NCT06445023');
 const legacy=history.filter(h=>h.historyOrigin==='PRESERVED_SHARED_CROSS_STAGE');
 assert.ok(legacy.some(h=>h.metricGrades?.length));
 for(const h of legacy)for(const g of h.metricGrades??[]){assert.equal(typeof g.id,'string');assert.equal(typeof g.grade,'number');assert.equal(g.grade,g.score);}
});
