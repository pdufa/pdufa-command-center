const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const location=path.join(__dirname,"../lib/medical-intelligence-reviewed-findings.ts");
const source=fs.readFileSync(location,"utf8");
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const m={exports:{}};
vm.runInNewContext(compiled,{module:m,exports:m.exports});
const {REVIEWED_FINDINGS,REVIEW_COVERAGE,REVIEW_AS_OF,findingsForNct}=m.exports;
const roster=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
const ncts=new Set(roster.records.map(r=>r.nct));
test("reviewed findings map only to exact FOCUS NCTs and trace to valid sources",()=>{
  assert.ok(REVIEWED_FINDINGS.length>=12);
  assert.equal(new Set(REVIEWED_FINDINGS.map(f=>f.id)).size,REVIEWED_FINDINGS.length);
  for(const f of REVIEWED_FINDINGS){
    assert.match(f.sourceUrl,/^https:\/\//);
    assert.match(f.published,/^\d{4}-\d{2}-\d{2}$/);
    assert.ok(f.published<=REVIEW_AS_OF,"future-dated source: "+f.id);
    assert.ok(f.relatedNcts.length>=1);
    for(const nct of f.relatedNcts)assert.ok(ncts.has(nct),f.id+" has unknown NCT "+nct);
    for(const k of ["headline","detail","fdaRelevance","counterpoint","remainingQuestion"])
      assert.ok(typeof f[k]==="string"&&f[k].length>10,f.id+" missing "+k);
  }
  assert.equal(REVIEW_COVERAGE.reviewedNcts,new Set(REVIEWED_FINDINGS.flatMap(f=>f.relatedNcts)).size);
  assert.equal(REVIEW_COVERAGE.reviewedNcts,roster.records.length,"Every NCT requires at least one sourced finding; this is NOT full adjudication");
  for(const nct of ncts)assert.ok(findingsForNct(nct).length>=1,"Source research gap for "+nct);
});
test("FDA objections, prior CRL and extension remain separate from predictions",()=>{
  assert.ok(findingsForNct("NCT05126758").some(f=>f.type==="REGULATORY_OBJECTION"&&f.evidence==="FDA_PRIMARY"));
  assert.ok(findingsForNct("NCT05126758").some(f=>f.type==="EXTENSION_CONFIRMED"));
  assert.ok(findingsForNct("NCT03697109").some(f=>f.type==="PREVIOUS_CRL"));
  assert.ok(findingsForNct("NCT04308590").some(f=>f.type==="PREVIOUS_CRL"));
  assert.ok(findingsForNct("NCT04544293").some(f=>f.type==="EXTENSION_CONFIRMED"));
  assert.ok(!findingsForNct("NCT04544293").some(f=>f.type==="REGULATORY_OBJECTION"));
  assert.equal(findingsForNct("NCT00000000").length,0);
  assert.equal(findingsForNct("random string").length,0);
  assert.equal(findingsForNct("NCT05208047").some(f=>f.company!=="Cogent"),false);
});
