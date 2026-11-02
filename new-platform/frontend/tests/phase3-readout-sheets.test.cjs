const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const manifest=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const census=fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8")
  .trim().split(/\r?\n/).slice(1).map(line=>{
    const [nctId,ticker]=line.split(",",2);
    return {nctId,ticker};
  });
test("741 distinct census NCTs are classified exactly once into pre/post/unknown",()=>{
  const all=new Map(census.map(x=>[x.nctId,x]));
  assert.equal(census.length,741);
  assert.equal(all.size,741);
  const known=new Set();
  for(const entry of manifest.entries){
    assert.equal(known.has(entry.nctId),false);
    assert.equal(all.get(entry.nctId)?.ticker,entry.ticker);
    assert.match(entry.evidenceUrl,/^https:\/\/\S+$/);
    assert.match(entry.evidenceDate,/^\d{4}-\d{2}-\d{2}$/);
    assert.ok(entry.evidenceDate<=manifest.sourceAsOf);
    assert.ok(["POST_PUBLIC_READOUT","PRE_AS_OF_CHECK"].includes(entry.kind));
    known.add(entry.nctId);
  }
  assert.equal(manifest.entries.filter(e=>e.kind==="PRE_AS_OF_CHECK").length,2);
  assert.equal(manifest.entries.filter(e=>e.kind==="POST_PUBLIC_READOUT").length,3);
  assert.equal(census.length-known.size,736);
});
test("pre-release is a dated issuer check, not absence of ClinicalTrials.gov results",()=>{
  assert.deepEqual(new Set(manifest.sourceFiles),new Set([
    "data/phase3_pre_readout_evidence.csv","data/post_phase3_discoveries.csv"
  ]));
  for(const pre of manifest.entries.filter(e=>e.kind==="PRE_AS_OF_CHECK"))
    assert.equal(pre.evidenceDate,"2026-10-11");
});
