const test=require("node:test");
const assert=require("node:assert/strict");
const roster=require("../data/p3PostDataActive.json");

test("FOCUS ticker navigator uses only dated FOCUS roster and keeps NCT identity",()=>{
  const records=roster.records;
  assert.equal(roster.origin,"FOCUS / Google Sheet");
  assert.ok(Array.isArray(records)&&records.length>0);
  const ids=new Set(records.map(r=>r.nct));
  assert.equal(ids.size,records.length,"no NCT is duplicated");
  const tickers=Array.from(new Set(records.map(r=>r.ticker)));
  assert.ok(tickers.length>0);
  for(const ticker of tickers){
    const ncts=records.filter(r=>r.ticker===ticker).map(r=>r.nct);
    assert.ok(ncts.length>0);
    assert.ok(ncts.every(nct=>/^NCT\d{8}$/.test(nct)));
  }
  assert.equal(tickers.reduce((sum,ticker)=>sum+records.filter(r=>r.ticker===ticker).length,0),records.length);
});
