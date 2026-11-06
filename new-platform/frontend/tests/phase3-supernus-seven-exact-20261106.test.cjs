const test=require('node:test');
const assert=require('node:assert/strict');
const ir=require('../data/phase3CompanyWebsiteEvidence20261105.json');
const outcomes=require('../data/phase3EndpointAdjudications20261105.json');
const queue=require('../data/phase3InvestorRelationsResearchQueue20261106.json');
const log=require('../data/phase3CompanyWebsiteSearchLog20261106.json');
const target=['NCT03247530','NCT03247517','NCT03247543','NCT03247556','NCT04016779','NCT02618408','NCT02618434'];
const found=n=>outcomes.records.find(x=>x.nctId===n);
const fact=(n,q)=>ir.assessmentRecords.find(x=>x.nctId===n&&x.assessmentNumber===q);
test('Supernus seven exact NCT/protocol outcomes recorded once, no fabricated RAAS scores',()=>{
 assert.equal(new Set(target).size,7);
 const all=new Set(ir.records.map(x=>x.nctId));
 assert.equal(new Set(outcomes.records.map(x=>x.nctId)).size,outcomes.records.length);
 for(const n of target){
  assert.ok(all.has(n));
  assert.ok(found(n)&&found(n).identityEvidenceUrl&&found(n).evidenceUrl);
  assert.ok(fact(n,1)&&fact(n,29));
  assert.ok(!ir.assessmentRecords.filter(x=>x.nctId===n).some(x=>'score' in x||'answer' in x));
  assert.ok(queue.companies.find(c=>c.ticker==='SUPN').trials.find(x=>x.nctId===n).identityMatched);
 }
 assert.equal(target.filter(n=>found(n).endpointOutcome==='PRIMARY_ENDPOINT_MET').length,5);
 assert.equal(target.filter(n=>found(n).endpointOutcome==='PRIMARY_ENDPOINT_NOT_MET').length,2);
 assert.ok(log.companies.some(x=>x.ticker==='SUPN'));
});
test('P304 600 mg did not meet primary endpoint despite 400 mg meeting it',()=>{
 assert.match(found('NCT03247556').rationale,/600 mg.*p=0\.0712/);
 assert.match(found('NCT03247556').rationale,/did NOT meet/);
});
test('SPN-810 CHIME final efficacy failures not overwritten by positive interim results',()=>{
 assert.match(found('NCT02618408').rationale,/p=0\.092/);
 assert.match(found('NCT02618408').rationale,/interim stage 1 p=0\.029 does not override/);
 assert.match(found('NCT02618434').rationale,/p=0\.961/);
 assert.ok(!found('NCT02691182'));
});
test('Question facts are unique and counts derive from records',()=>{
 const keys=ir.assessmentRecords.map(x=>x.nctId+':'+x.assessmentNumber);
 assert.equal(new Set(keys).size,keys.length);
 assert.equal(outcomes.totalReviewed,outcomes.records.length);
 for(const [k,v] of Object.entries(outcomes.counts)) assert.equal(v,outcomes.records.filter(x=>x.endpointOutcome===k).length);
 assert.equal(ir.trialCount,ir.records.length);
 assert.equal(ir.companyCount,new Set(ir.records.map(x=>x.ticker)).size);
 assert.equal(ir.regulatoryApplicationLinkCount,ir.records.filter(x=>x.regulatoryEvidenceStatus).length);
});
