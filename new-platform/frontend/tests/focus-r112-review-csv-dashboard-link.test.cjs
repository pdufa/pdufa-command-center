"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const page=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
const csv=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/review-queue/csv/route.ts"),"utf8");
test("R112 scientific dashboard links to fail-closed six-row CSV export",()=>{
 assert.match(page,/href="\/predictions\/scientific-reconciliation\/priority-gates\/review-queue\/csv"/);
 assert.match(page,/Export six-row uncertified page-review CSV/);
 assert.match(csv,/REVIEW_QUEUE_PROVENANCE_MISMATCH/);
 assert.match(csv,/QUEUE\.candidatePageObjectIndices\.map/);
 assert.match(csv,/QUEUE\.openScienceGates!==11/);
 assert.match(csv,/FDAForecast/);
});
