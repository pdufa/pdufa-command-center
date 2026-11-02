const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const snapshot=JSON.parse(fs.readFileSync(
  path.join(root,"public/phase3-registry-postings-2026-10-18.json"),"utf8"));
test("every one of the 730 historical Phase 3 NCT records is counted exactly once",()=>{
  assert.equal(snapshot.schemaVersion,1);
  assert.equal(snapshot.measure,"CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT");
  assert.equal(snapshot.sourceFile,"data/phase3_730_full_assessment.csv");
  assert.equal(snapshot.records.length,730);
  const ids=new Set();
  let without=0,withResults=0;
  for(const r of snapshot.records){
    assert.match(r.nctId,/^NCT\d{8}$/);
    assert.match(r.ticker,/^[A-Z0-9.-]+$/);
    assert.ok(!ids.has(r.nctId),"duplicate "+r.nctId);
    ids.add(r.nctId);
    assert.ok(Number.isSafeInteger(r.resultsCount)&&r.resultsCount>=0);
    if(r.resultsCount>0)withResults++;else without++;
  }
  assert.equal(ids.size,730);
  assert.equal(without,404);
  assert.equal(withResults,326);
  assert.equal(snapshot.noResultsPosted,without);
  assert.equal(snapshot.resultsPosted,withResults);
});
test("October 18 and October 26 Phase 3 snapshots are not conflated",()=>{
  const csv=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8");
  const ids=new Set(csv.trim().split(/\r?\n/).slice(1).map(x=>x.split(",")[0]));
  const previous=new Set(snapshot.records.map(x=>x.nctId));
  assert.equal(ids.size,741);
  const common=[...previous].filter(x=>ids.has(x));
  assert.equal(common.length,722);
  assert.equal(previous.size-common.length,8);
  assert.equal(ids.size-common.length,19);
});
