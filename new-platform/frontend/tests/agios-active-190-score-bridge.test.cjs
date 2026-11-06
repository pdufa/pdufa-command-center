"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=(p)=>fs.readFileSync(path.join(root,p),"utf8");
const evidence=JSON.parse(read("data/agiosPhase3Evidence20261106.json"));
const census=JSON.parse(read("public/phase3-unified-classifications-2026-11-05.json"));
const exportRoute=read("app/api/phase3-unified-190-columns/route.ts");
const scoreRoute=read("app/api/phase3-active-trial-scores/route.ts");
const sheet=read("app/Phase3SourceOnlySheets.tsx");
const active=new Set(["RECRUITING","NOT_YET_RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION"]);

test("All nine exact Agios active NCTs are represented, five post and four pre",()=>{
 const agio=census.rows.filter(r=>r.ticker==="AGIO"&&active.has(r.registryStatus));
 assert.equal(agio.length,9);
 assert.equal(evidence.trials.length,9);
 assert.deepEqual(new Set(evidence.trials.map(t=>t.nctId)),new Set(agio.map(r=>r.nctId)));
 assert.equal(evidence.trials.filter(t=>t.cohort==="PRE_DATA").length,4);
 assert.equal(evidence.trials.filter(t=>t.cohort==="POST_DATA").length,5);
 assert.equal(evidence.trials.find(t=>t.nctId==="NCT05031780").program,"RISE UP");
 assert.equal(evidence.trials.find(t=>t.nctId==="NCT07859423").drug,"AG-236");
});
test("Source facts are date-qualified and cannot introduce numerical clinical scores",()=>{
 assert.equal(evidence.asOf,"2026-11-06");
 assert.equal(evidence.facts.length,31);
 assert.equal(new Set(evidence.facts.map(f=>f.nctId+"#"+f.question)).size,31);
 const ids=new Set(evidence.trials.map(t=>t.nctId));
 for(const f of evidence.facts){
  assert.ok(ids.has(f.nctId));
  assert.ok(Number.isInteger(f.question)&&f.question>=1&&f.question<=30);
  assert.equal(f.score,null);
  assert.equal(f.status,"SOURCE_FACT_ONLY");
  assert.ok(f.evidence.length>=30);
  assert.ok(/^https:\/\/(investor\.agios\.com|clinicaltrials\.gov)\//.test(f.sourceUrl));
  assert.match(f.sourceDate,/^\d{4}-\d{2}-\d{2}$/);
  assert.ok(f.sourceDate<=evidence.asOf);
 }
});
test("Export reuses corrected 762 ledger and preserves 190 fields with source-aware selectors",()=>{
 assert.match(exportRoute,/const ledger=activePhase3Cohorts\.snapshot;/);
 assert.match(exportRoute,/HEADERS\.length!==190/);
 assert.match(exportRoute,/const questionHeaders = UNIVERSAL_PHASE3_QUESTIONS\.flatMap/);
 assert.match(exportRoute,/const includedCount=ledger\.rows\.filter\(included\)\.length/);
 assert.match(exportRoute,/if\(included\(r\)\)rows\.push\(writeRow\(values\)\)/);
 assert.match(exportRoute,/const agiosFact=agiosFacts\.get/);
 assert.match(exportRoute,/\(NCT\\d\{8\}\)/);
});
test("TOP/BOTTOM clinical and RAAS values are read only from established phase-first ratings",()=>{
 assert.match(scoreRoute,/phaseFirstReport\("census"\)/);
 assert.match(scoreRoute,/const clinicalRating=scored>0\?trial\.overallRating:null/);
 assert.match(scoreRoute,/raasScore:trial\.raasScore/);
 assert.match(scoreRoute,/return Response\.json/);
 assert.match(sheet,/\/api\/phase3-active-trial-scores/);
 assert.match(sheet,/\/api\/phase3-unified-190-columns\?nctId=/);
});
