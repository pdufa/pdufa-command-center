const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const ledger=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-unified-classifications-2026-11-05.json"),"utf8"));
const route=fs.readFileSync(path.join(root,"app/api/phase3-unified-190-columns/route.ts"),"utf8");
const screen=fs.readFileSync(path.join(root,"app/Phase3UnifiedClassifications.tsx"),"utf8");
const questionDef=fs.readFileSync(path.join(root,"lib/phase3-universal-questions.ts"),"utf8");
const headerCount=(name)=>{
 const m=route.match(new RegExp("const "+name+" = \\[([\\s\\S]*?)\\];"));
 assert.ok(m,"Missing column group "+name);
 return (m[1].match(/"(?:[^"\\]|\\.)*"/g)||[]).length;
};
test("The 762-row assessment has exactly 190 columns (20 legacy + 20 analysis + 30 times 5)",()=>{
 assert.equal(ledger.total,762);
 assert.equal(ledger.rows.length,762);
 assert.equal(new Set(ledger.rows.map(r=>r.nctId)).size,762);
 assert.equal(headerCount("baseHeaders"),20);
 assert.equal(headerCount("extendedHeaders"),20);
 assert.equal((questionDef.match(/\{heading:"/g)||[]).length,30);
 assert.equal(20+20+30*5,190);
 assert.match(route,/HEADERS\.length!==190/);
 assert.match(route,/values\.length!==190/);
 assert.match(route,/rows\.length!==763/);
 assert.match(screen,/api\/phase3-unified-190-columns/);
});
test("Passing classification requires explicit exact-NCT readout; not registry status or a prediction",()=>{
 const observed=ledger.rows.filter(r=>r.classificationVerified&&
  r.readoutOutcome==="PRIMARY_ENDPOINT_MET"&&r.readoutEvidenceUrl);
 assert.equal(observed.length,1);
 assert.equal(observed[0].nctId,"NCT05711940");
 assert.equal(ledger.rows.filter(r=>r.readoutOutcome==="NOT_INDEPENDENTLY_REVIEWED").length,761);
 assert.match(route,/PASS_DOCUMENTED_PRIMARY_ENDPOINT/);
 assert.match(route,/\"UNDETERMINED\"/);
 assert.match(route,/\"PREDICTED_PRE_READOUT\"/);
 assert.match(route,/\"SOURCE_FACT_ONLY\"/);
 assert.match(route,/\"UNSCORED\"/);
 assert.match(screen,/Passing classification/);
 assert.match(screen,/data-passing-classification/);
});
