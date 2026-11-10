"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
  const result=ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
      jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}
  });
  mod._compile(result.outputText,file);
};
const {FOCUS_R81_SOURCE_READINESS}=
  require("../lib/focus-r81-all-focus-source-readiness.ts");
const {buildR83EvidenceGapChecklist,R83_CSV_COLUMNS,R83_SOURCE_SNAPSHOT}=
  require("../lib/focus-r83-evidence-gap-export.ts");
test("R83 exports exactly 29 unique NCTs and 23 provisional groups without double-counting",()=>{
  const src=FOCUS_R81_SOURCE_READINESS;
  assert.ok(src);
  const csv=buildR83EvidenceGapChecklist();
  assert.ok(csv);
  const lines=csv.trimEnd().split("\r\n");
  assert.equal(lines.length,30);
  assert.equal(lines[0].split('","').length,R83_CSV_COLUMNS.length);
  assert.equal((csv.match(/"R81_SOURCE_ONLY_2026-11-09"/gu)||[]).length,29);
  for(const row of src.rows) {
    assert.equal(csv.includes('"'+row.nct+'"'),true,row.nct);
    for(const cycle of row.cycleIds)assert.ok(csv.includes(cycle),cycle);
  }
  assert.equal(new Set(src.rows.map(r=>r.nct)).size,29);
  assert.equal(new Set(src.applicationGroups.map(r=>r.cycleId)).size,23);
  assert.equal(R83_SOURCE_SNAPSHOT,"R81_SOURCE_ONLY_2026-11-09");
});
test("R83 never converts absent retained sources into trial failure or FDA conclusions",()=>{
  const csv=buildR83EvidenceGapChecklist();
  assert.ok(csv.includes("NOT_PRESENT_IN_RETAINED_SNAPSHOT_NOT_EVIDENCE_OF_FAILURE"));
  assert.ok(csv.includes("NOT_INDEXED_IN_FIVE_CASE_SUBSET_OTHER_SOURCES_POSSIBLE"));
  assert.equal((csv.match(/"ABSTAIN_NOT_VALIDATED"/gu)||[]).length,29);
  assert.equal((csv.match(/"NOT_SIGNED"/gu)||[]).length,29);
  assert.ok(!csv.includes("100% probability"));
});
test("R83 export fails closed on fabricated forecasts, dropped cycles and wrong counts",()=>{
  for(const mutate of [
    x=>{x.rows[0].scientificGrade=5;},
    x=>{x.rows[0].officialFDAOutcome="APPROVAL";},
    x=>{x.independentScientificSignoffs=1;},
    x=>{x.applicationGroups.pop();},
    x=>{x.rows[0].cycleIds=["fake-review"];},
    x=>{x.rows[1].nct=x.rows[0].nct;}
  ]) {
    const changed=structuredClone(FOCUS_R81_SOURCE_READINESS);
    mutate(changed);
    assert.equal(buildR83EvidenceGapChecklist(changed),null);
  }
});
test("R83 has a safe read-only route and dashboard download link",()=>{
  const route=fs.readFileSync(path.join(root,
    "app/predictions/evidence-gaps/export/route.ts"),"utf8");
  const panel=fs.readFileSync(path.join(root,
    "app/predictions/evidence-gaps/FocusSourceReadinessR81.tsx"),"utf8");
  assert.match(route,/buildR83EvidenceGapChecklist/);
  assert.match(route,/status:503/);
  assert.match(route,/Content-Disposition/);
  assert.match(route,/no-store/);
  assert.match(panel,/\/predictions\/evidence-gaps\/export/);
  assert.doesNotMatch(route,/fetch\(|POST\s*\/api|submitClinicalScore|setGrade\(/);
});
