const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,file);
const source=require('../lib/phase3-population-geography.ts');
const ledger=require('../public/phase3-unified-classifications-2026-11-05.json');
const ir=require('../data/phase3CompanyWebsiteEvidence20261105.json');
const endpoints=require('../data/phase3EndpointAdjudications20261105.json');
const audit=require('../app/api/phase3-missing-data-audit/route.ts');

test('all 762 registry identities preserve publication dates, source hashes and unreviewed scientific interpretation',()=>{
 const ncts=new Set(ledger.rows.map(r=>r.nctId));
 assert.equal(source.populationGeographyRecords.length,762);
 assert.ok(source.populationGeographyIntegrity(ncts));
 assert.equal(source.populationGeographyIntegrity(new Set(['NCT00000000'])),false);
 for(const r of source.populationGeographyRecords){
  assert.equal(r.sourceUrl,'https://clinicaltrials.gov/study/'+r.nctId);
  assert.ok(new URL(r.batchApiUrl).searchParams.get('filter.ids').split(',').includes(r.nctId));
  assert.equal(r.criticalReviewStatus,'NOT_YET_REVIEWED');
  assert.equal(r.score,undefined);
  const population=source.populationGeographyFact(r.nctId,6);
  assert.equal(population.classification,'DOCUMENTED_SOURCE_FACT');
  assert.equal(population.assessmentNumber,6);
  assert.match(population.evidence,/not observed participant demographics/);
  assert.match(population.evidence,/NOT been assessed/);
  const geography=source.populationGeographyFact(r.nctId,26);
  assert.equal(Boolean(geography),r.registeredLocationCount>0);
  if(geography)assert.match(geography.evidence,/not confirmed recruiting sites/);
 }
 assert.equal(source.populationGeographyFact('NCT00000000',6),null);
 assert.equal(source.populationGeographyFact(ledger.rows[0].nctId,1),null);
 assert.equal(source.populationGeographyFact(ledger.rows[0].nctId,30),null);
});
test('aggregate audit exposes documentary coverage without scientific completion, FDA promotion or numerical score generation',async()=>{
 const r=await audit.GET(new Request('http://local/audit'));assert.equal(r.status,200);
 const report=await r.json();
 assert.equal(report.fields.populationGeographyRecords,762);
 assert.equal(report.fields.populationEligibilityFacts,762);
 assert.equal(report.fields.registeredGeographyFacts,726);
 assert.equal(report.assessment.predicted,61);
 assert.equal(report.assessment.trialsWithNumericalPredictions,4);
 assert.equal(report.perQuestion[5].predictions,4);
 assert.equal(report.perQuestion[5].sourceFacts,758);
 assert.equal(report.perQuestion[5].unscored,0);
 assert.ok(report.perQuestion[5].documentaryInterpretationPending>750);
 assert.ok(report.perQuestion[5].requiringResearch>750);
 assert.ok(report.assessment.researchPendingIncludingDocumentedDesign>report.assessment.unscored);
 assert.ok(report.populationGeographyScope.includes('not completed numerical'));
 assert.equal(report.investorRelationsCoverage.reduce((a,c)=>a+c.registryIdentityMatchedTrials,0),762);
 assert.equal(report.discoveryAvenues.avenues.length,4);
 assert.match(report.discoveryAvenues.sourcePolicy,/NO_IMPORTED_PROBABILITIES/);
});
test('Ionis dose failures, external controls, failed cardiomyopathy study and post-readout SAP chronology remain explicit',()=>{
 const e=new Map(endpoints.records.map(r=>[r.nctId,r]));
 assert.equal(e.get('NCT04136171').endpointOutcome,'PRIMARY_ENDPOINT_NOT_MET');
 assert.equal(e.get('NCT04136184').endpointOutcome,'PRIMARY_ENDPOINT_MET');
 assert.match(e.get('NCT04136184').rationale,/external placebo/);
 assert.match(e.get('NCT04568434').rationale,/50 mg.*not significant/);
 assert.equal(ir.records.find(r=>r.nctId==='NCT04136171').regulatoryEvidenceStatus,undefined);
 for(const nct of ['NCT04568434','NCT05139810']){
  for(const q of [13,14,15]){
   const fact=ir.assessmentRecords.find(r=>r.nctId===nct&&r.assessmentNumber===q);
   assert.equal(fact.publicationDate,'2025-02-13');
   assert.match(fact.chronologyQualification,/post-readout/);
   assert.equal(fact.classification,'DOCUMENTED_SOURCE_FACT');
   assert.equal(fact.score,undefined);
  }
 }
 const monthDates=ir.assessmentRecords.filter(r=>r.publicationDate.length===7);
 assert.ok(monthDates.length>=3);
 assert.ok(monthDates.every(r=>r.publicationDatePrecision==='MONTH'));
 const savara=ir.records.find(r=>r.nctId==='NCT04544293');
 assert.equal(savara.pdufaGoalDate,'2026-11-22');
 assert.equal(savara.regulatoryEvidenceStatus,'ISSUER_REPORTED_BLA_UNDER_FDA_REVIEW');
 assert.equal(savara.regulatorySourceDate,'2026-08-11');
 assert.match(savara.regulatoryEvidence,/newer source freshness/);
});
