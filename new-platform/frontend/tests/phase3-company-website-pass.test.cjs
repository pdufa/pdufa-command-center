const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript'),fs=require('node:fs');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,f);
const ir=require('../data/phase3CompanyWebsiteEvidence20261105.json');
const endpoints=require('../data/phase3EndpointAdjudications20261105.json');
const sources=require('../data/phase3CompanyBatchRegistrySources20261106.json');
const log=require('../data/phase3CompanyWebsiteSearchLog20261106.json');
const audit=require('../app/api/phase3-missing-data-audit/route.ts');
const fact=(n,q)=>ir.assessmentRecords.find(r=>r.nctId===n&&r.assessmentNumber===q);
test('cumulative manufacturer passes preserve exact identity and do not claim all-company completion',async()=>{
 assert.equal(log.companyUniverse,137);assert.ok(log.companies.length>=8);assert.equal(new Set(log.companies.map(c=>c.ticker)).size,log.companies.length);
 assert.equal(sources.records.length,23);
 for(const r of sources.records){
  assert.equal(r.registry.protocolSection.identificationModule.nctId,r.nctId);
  assert.ok(r.publicationDate<=r.retrievedAt);assert.match(r.sourceSha256,/^[a-f0-9]{64}$/);
 }
 const report=await (await audit.GET(new Request('http://local/api/audit'))).json();
 assert.equal(report.companyWebsiteResearch.companiesSearchedThisBatch,log.companies.length);
 assert.equal(report.companyWebsiteResearch.companiesWithPartialReview+report.companyWebsiteResearch.companiesAwaitingWebsiteReview,137);
 assert.deepEqual(new Set(report.companyWebsiteResearch.hardToResolveCompanies.map(c=>c.ticker)),new Set(['ABVX','ADMA','AGEN','SVA']));
 assert.equal(report.assessment.predicted,61);assert.equal(report.assessment.trialsWithNumericalPredictions,4);
 assert.equal(report.fields.missingAdjudicatedEndpoint,762-endpoints.records.length);
 assert.deepEqual(report.endpointOutcomes,Object.fromEntries(['PRIMARY_ENDPOINT_MET','PRIMARY_ENDPOINT_NOT_MET','NO_BINARY_PASS_FAIL'].map(k=>[k,endpoints.records.filter(r=>r.endpointOutcome===k).length])));
});
test('futility, withdrawn, continuation and pooled program evidence cannot invent efficacy passes',()=>{
 const observed=new Map(endpoints.records.map(r=>[r.nctId,r.endpointOutcome]));
 for(const n of ['NCT02249988','NCT03905109','NCT00126178','NCT04943627','NCT06111014','NCT07795164','NCT06846541','NCT07020819','NCT07807969'])assert.equal(observed.has(n),false);
 assert.equal(observed.get('NCT03428360'),'NO_BINARY_PASS_FAIL');
 assert.equal(observed.get('NCT04374136'),'PRIMARY_ENDPOINT_NOT_MET');
 assert.match(fact('NCT04374136',1).evidence,/biomarker/);
 for(const n of ['NCT06586112','NCT06588738'])assert.doesNotMatch(fact(n,1).evidence,/65%|74%|59%/);
 assert.equal(observed.get('NCT00033904'),'PRIMARY_ENDPOINT_NOT_MET');
 assert.match(fact('NCT00033904',1).evidence,/p=\.506/);
});
test('science archives retain nominal results, negative later PRO and safety contradictions',()=>{
 assert.match(fact('NCT04701164',17).evidence,/nominal/);
 assert.match(fact('NCT04701164',18).evidence,/p=\.2917/);
 assert.match(fact('NCT03428360',18).evidence,/PedsQL/);
 assert.equal(fact('NCT03428360',20).classification,'REQUIRES_INTERPRETATION');
 assert.match(fact('NCT03428360',20).evidence,/18.*17\/130/);
 const newFacts=ir.assessmentRecords.filter(r=>r.recoveryBatch==='COMPANY_WEBSITE_PASS_20261106');
 assert.equal(newFacts.length,241);
 assert.ok(newFacts.every(r=>r.publicationDate&&r.sourceUrl&&r.score===undefined&&r.answer===undefined));
 const ri=ir.records.find(r=>r.nctId==='NCT01814800');assert.equal(ri.regulatorySourceDate,'2019-04-01');
 const aq=ir.records.find(r=>r.nctId==='NCT03428360');assert.equal(aq.regulatoryEvidenceStatus,'FDA_REVIEW_DOCUMENTED_HISTORICAL');
 assert.equal(ri.pdufaGoalDate,undefined);assert.equal(aq.pdufaGoalDate,undefined);
});
