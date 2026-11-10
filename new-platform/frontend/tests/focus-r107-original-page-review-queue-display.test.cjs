"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
test("R107 renders the real original-source review queue with explicit uncertainty",()=>{
 assert.match(s,/R106_REVIEW_QUEUE/);
 assert.match(s,/candidatePageObjectIndices\.join/);
 assert.match(s,/sourceSha256/);
 assert.match(s,/not verified printed page numbers/);
 assert.match(s,/openScienceGates/);
 assert.match(s,/FDAForecast/);
 assert.match(s,/ctis-page-evidence\?doc=/);
});
