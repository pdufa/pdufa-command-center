"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const source=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/review-queue/csv/route.ts"),"utf8");
test("R109 exports provenance-matched six KCCQ candidate rows without science signoff",()=>{
 for(const s of ["candidatePageObjectIndices","sourceSha256","REVIEW_QUEUE_PROVENANCE_MISMATCH","PENDING_PRIMARY_PAGE_REVIEW","ABSTAIN","printed_page_verified","complete_page_text_verified","scientific_citation_certified","text/csv"])assert.ok(source.includes(s),s);
 assert.ok(source.includes('QUEUE.openScienceGates!==11'));
});
