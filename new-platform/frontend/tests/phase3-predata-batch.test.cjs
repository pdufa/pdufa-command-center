const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,".."),read=p=>fs.readFileSync(path.join(root,p),"utf8");
test("All 253 dated Phase 3 pre-readout candidate rows have unique NCT identities",()=>{
 const a=JSON.parse(read("data/phase3PreDataBatch20261105.json"));
 assert.equal(a.counts.registryActiveCapScreen,257);
 assert.equal(a.counts.knownIssuerReadoutsExcluded,4);
 assert.equal(a.trials.length,253);
 assert.equal(new Set(a.trials.map(x=>x.nctId)).size,253);
 assert.equal(a.trials.filter(x=>x.protocol).length,199);
 assert.equal(a.trials.filter(x=>!x.protocol).length,54);
 assert.ok(a.trials.some(x=>x.nctId==="NCT06641089"));
 for(const x of a.trials){
  assert.match(x.nctId,/^NCT\d{8}$/);
  assert.ok(x.marketCapUsd>=300000000&&x.marketCapUsd<=10000000000);
  assert.ok(!a.excludedKnownIssuerReadouts.some(k=>k.nctId===x.nctId));
 }
});
test("All 30 universal questions avoid inventing efficacy predictions",()=>{
 const q=read("lib/phase3-universal-questions.ts");
 assert.equal((q.match(/\{heading:/g)||[]).length,30);
 assert.match(q,/documentationScore:100/);
 assert.match(q,/sourceObservation/);
 assert.match(q,/Statistical analysis plan/);
 const lib=read("lib/phase3-top-questions.ts");
 assert.match(lib,/UNIVERSAL_PHASE3_QUESTIONS.map/);
 assert.match(lib,/NO OUTCOME SCORE/);
 const page=read("app/Phase3SourceOnlySheets.tsx");
 assert.match(page,/<Phase3PreDataBatch query=\{query\}\/>/);
 const panel=read("app/Phase3PreDataBatch.tsx");
 assert.match(panel,/Export all/);
 assert.match(panel,/phase3AnalysisCsvValues\(t.nctId\)/);
 assert.match(panel,/NOT a verified unreleased roster/);
});
