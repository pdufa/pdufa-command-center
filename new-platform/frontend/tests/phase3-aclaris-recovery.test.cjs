const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ir=require('../data/phase3CompanyWebsiteEvidence20261105.json');
const endpoints=require('../data/phase3EndpointAdjudications20261105.json');
const sources=require('../data/phase3AclarisRegistrySources20261106.json');
const queue=require('../data/phase3InvestorRelationsResearchQueue20261106.json');
const byNct=new Map(sources.records.map(r=>[r.nctId,r]));
const fact=(n,q)=>ir.assessmentRecords.find(r=>r.nctId===n&&r.assessmentNumber===q);
test('all six Aclaris source identities, protocols and historical timestamps match',()=>{
 assert.equal(byNct.size,6);
 for(const r of byNct.values()){
  assert.equal(r.registry.protocolSection.identificationModule.nctId,r.nctId);
  assert.equal(r.registry.protocolSection.identificationModule.orgStudyIdInfo.id,r.sponsorProtocol);
  assert.match(r.sourceSha256,/^[a-f0-9]{64}$/);
  assert.ok(r.publicationDate<=r.retrievedAt);
 }
 const facts=ir.assessmentRecords.filter(r=>byNct.has(r.nctId));
 assert.equal(facts.length,102);assert.equal(new Set(facts.map(r=>r.nctId+':'+r.assessmentNumber)).size,102);
 assert.ok(facts.every(r=>r.score===undefined&&r.answer===undefined));
});
test('single-arm safety/clearance outcomes cannot become efficacy passes or inherit wart approval',()=>{
 for(const nct of ['NCT02667288','NCT03812510'])
  assert.equal(endpoints.records.find(r=>r.nctId===nct).endpointOutcome,'NO_BINARY_PASS_FAIL');
 assert.match(fact('NCT03812510',1).evidence,/prior-treatment strata/);
 assert.match(fact('NCT03812510',23).evidence,/1\/376/);
 assert.match(fact('NCT03812510',24).evidence,/426/);
 assert.equal(fact('NCT03812510',20).classification,'REQUIRES_INTERPRETATION');
 for(const nct of ['NCT03687372','NCT03691831','NCT03812510']){
  const r=ir.records.find(r=>r.nctId===nct);assert.equal(r.regulatoryEvidenceStatus,undefined);assert.equal(r.pdufaGoalDate,undefined);
 }
 assert.equal(ir.records.filter(r=>byNct.has(r.nctId)&&r.regulatoryEvidenceStatus).length,3);
 for(const r of ir.records.filter(r=>byNct.has(r.nctId)&&r.regulatoryEvidenceStatus)){
  assert.match(r.regulatoryEvidenceUrl,/appletter/);assert.equal(r.regulatorySourceDate,'2017-12-14');
 }
});
test('SAE denominators, missing-data plans, chronology and unresolved definitions remain explicit',()=>{
 assert.match(fact('NCT02667236',23).evidence,/4\/223/);
 assert.match(fact('NCT02667275',23).evidence,/6\/244/);
 assert.match(fact('NCT02667275',20).evidence,/233\/244/);
 for(const nct of ['NCT03687372','NCT03691831']){
  assert.match(fact(nct,14).evidence,/tipping-point/);
  assert.match(fact(nct,15).evidence,/fixed sequence/);
  assert.equal(fact(nct,13).sourceDocumentDate,'2019-02-14');
  assert.ok(fact(nct,13).publicUploadDate>'2019-10-24');
  assert.match(fact(nct,13).chronologyQualification,/after readout/);
 }
 assert.match(fact('NCT03812510',14).evidence,/changing the protocol ITT/);
 const c=queue.companies.find(c=>c.ticker==='ACRS');
 assert.equal(c.trials.filter(r=>r.identityMatched).length,6);
 assert.ok(c.blockers.some(x=>x.includes('USER_DIRECTION_REQUESTED')));
 assert.ok(c.trials.every(r=>r.questionReview.length===30));
 assert.ok(c.trials.every(r=>r.assessmentReviewStatus==='PARTIALLY_REVIEWED'));
});
