const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const adjud=JSON.parse(fs.readFileSync(path.join(root,"data/phase3EndpointAdjudications20261105.json"),"utf8"));
const issuer=JSON.parse(fs.readFileSync(path.join(root,"data/phase3CompanyWebsiteEvidence20261105.json"),"utf8"));
const queue=JSON.parse(fs.readFileSync(path.join(root,"data/phase3InvestorRelationsResearchQueue20261106.json"),"utf8"));
const studies={
 NCT02384941:"inTandem1",NCT02421510:"inTandem2",NCT02531035:"inTandem3",
 NCT03315143:"SCORED",NCT03521934:"SOLOIST-WHF",NCT03242252:"SOTA-CKD3"
};
const ncts=Object.keys(studies);
test("Lexicon trials retain individual exact-NCT, dose-specific outcome evidence",()=>{
 assert.equal(new Set(adjud.records.map(x=>x.nctId)).size,adjud.records.length);
 assert.equal(new Set(issuer.records.map(x=>x.nctId)).size,issuer.records.length);
 assert.equal(new Set(issuer.assessmentRecords.map(x=>x.nctId+"|"+x.assessmentNumber)).size,issuer.assessmentRecords.length);
 for(const nct of ncts){
  const a=adjud.records.find(x=>x.nctId===nct),s=issuer.records.find(x=>x.nctId===nct);
  assert.equal(a?.endpointOutcome,"PRIMARY_ENDPOINT_MET");
  assert.equal(s?.study,studies[nct]);
  assert.equal(s?.ticker,"LXRX");
  assert.match(a.evidenceUrl,/^https:\/\//);
  for(const q of [1,3,17,29])assert.ok(issuer.assessmentRecords.some(x=>x.nctId===nct&&x.assessmentNumber===q));
 }
 const partial=adjud.records.find(x=>x.nctId==="NCT03242252");
 assert.match(partial.rationale,/400 mg.*not 200 mg|400 mg but not 200 mg|400 mg.*200 mg/);
 assert.match(partial.rationale,/0\.0021/);
 assert.match(partial.rationale,/0\.2095/);
});
test("FDA cardiometabolic approval is not conflated with T1D complete response",()=>{
 for(const nct of ["NCT03315143","NCT03521934"]){
  const x=issuer.records.find(r=>r.nctId===nct);
  assert.equal(x.regulatoryEvidenceStatus,"FDA_APPROVED_HISTORICAL");
  assert.match(x.regulatoryEvidenceUrl,/fda\.gov/);
  assert.equal(x.pdufaGoalDate,undefined);
 }
 for(const nct of ["NCT02384941","NCT02421510","NCT02531035"]){
  const x=issuer.records.find(r=>r.nctId===nct);
  assert.equal(x.regulatoryEvidenceStatus,"FDA_COMPLETE_RESPONSE_HISTORICAL_NOT_APPROVED");
  assert.match(x.regulatoryEvidenceUrl,/investors\.lexpharma\.com/);
  assert.equal(x.pdufaGoalDate,undefined);
 }
 assert.ok(!issuer.records.find(x=>x.nctId==="NCT03242252").regulatoryProgramId);
 assert.equal(issuer.regulatoryApplicationLinkCount,issuer.records.filter(x=>x.regulatoryEvidenceStatus).length);
 assert.equal(issuer.regulatoryApplicationProgramCount,new Set(issuer.records.filter(x=>x.regulatoryProgramId).map(x=>x.regulatoryProgramId)).size);
});
test("Lexicon queue marks six documented trials without pretending all 18 were reviewed",()=>{
 const c=queue.companies.find(x=>x.ticker==="LXRX");
 assert.ok(c);
 assert.equal(c.trials.length,18);
 assert.equal(c.searchStatus,"PARTIALLY_REVIEWED");
 assert.equal(c.trials.filter(x=>x.assessmentReviewStatus==="PARTIALLY_REVIEWED").length,6);
 assert.equal(adjud.totalReviewed,adjud.records.length);
 for(const state of ["PRIMARY_ENDPOINT_MET","PRIMARY_ENDPOINT_NOT_MET","NO_BINARY_PASS_FAIL"])
  assert.equal(adjud.counts[state],adjud.records.filter(x=>x.endpointOutcome===state).length);
});
