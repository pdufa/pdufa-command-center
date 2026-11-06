const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const data=(x)=>JSON.parse(fs.readFileSync(path.join(__dirname,"../data/",x),"utf8"));
const e=data("phase3CompanyWebsiteEvidence20261105.json");
const a=data("phase3EndpointAdjudications20261105.json");
const q=data("phase3InvestorRelationsResearchQueue20261106.json");
const cases=[["NCT00477672","PRIMARY_ENDPOINT_NOT_MET"],["NCT01174004","PRIMARY_ENDPOINT_MET"],["NCT00550238","NO_BINARY_PASS_FAIL"],["NCT00156923","NO_BINARY_PASS_FAIL"],["NCT00156936","NO_BINARY_PASS_FAIL"]];
test("Exact Acadia/Alkermes historical outcomes are unique, crosswalked, and correctly qualified",()=>{
 for(const [nct,outcome] of cases){
  const matches=a.records.filter(x=>x.nctId===nct);assert.equal(matches.length,1,nct);
  assert.equal(matches[0].endpointOutcome,outcome);
  assert.ok(matches[0].identityEvidenceUrl.startsWith("https://"));
  assert.ok(e.records.some(x=>x.nctId===nct));
 }
 assert.ok(!a.records.some(x=>x.nctId==="NCT00658567"),"Early stopped 014 is not a confirmatory efficacy success/failure");
 const stopped=e.assessmentRecords.find(x=>x.nctId==="NCT00658567"&&x.assessmentNumber===1);
 assert.equal(stopped?.classification,"REQUIRES_INTERPRETATION");
 assert.match(stopped.evidence,/N\/A/);
});
test("Historical FDA application links are trial-specific and never upcoming PDUFA events",()=>{
 for(const nct of ["NCT00477672","NCT00658567","NCT01174004"]){
  const r=e.records.find(x=>x.nctId===nct);assert.equal(r.regulatoryProgramId,"NDA_207318_NUPLAZID_PARKINSON_PSYCHOSIS");
  assert.equal(r.regulatoryEvidenceStatus,"FDA_APPROVED_HISTORICAL");
  assert.ok(!r.pdufaGoalDate,"Historical 2016 target should not become upcoming catalyst");
  assert.match(r.regulatoryEvidence,/May 1, 2016/);
 }
 assert.equal(e.regulatoryApplicationLinkCount,e.records.filter(r=>r.regulatoryEvidenceStatus).length);
 assert.equal(e.regulatoryApplicationProgramCount,new Set(e.records.filter(r=>r.regulatoryProgramId).map(r=>r.regulatoryProgramId)).size);
});
test("Question-level research facts do not create RAAS scores or duplicate slots",()=>{
 const slots=e.assessmentRecords.map(r=>r.nctId+":"+r.assessmentNumber);
 assert.equal(new Set(slots).size,slots.length);
 for(const nct of ["NCT00477672","NCT00658567","NCT01174004","NCT00550238","NCT00156923","NCT00156936"]){
  const records=e.assessmentRecords.filter(r=>r.nctId===nct);
  assert.ok(records.length>=4);
  assert.ok(records.every(r=>r.evidenceScope==="HISTORICAL_SOURCE_FACT_NOT_PREDICTION"&&r.sourceUrl.startsWith("https://")));
  const match=q.companies.find(c=>c.trials.some(t=>t.nctId===nct));
  assert.ok(match.trials.find(t=>t.nctId===nct)?.identityMatched);
 }
 assert.equal(a.totalReviewed,a.records.length);
 for(const outcome of ["PRIMARY_ENDPOINT_MET","PRIMARY_ENDPOINT_NOT_MET","NO_BINARY_PASS_FAIL"])
  assert.equal(a.counts[outcome],a.records.filter(r=>r.endpointOutcome===outcome).length);
});
