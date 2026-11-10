"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/review-queue/route.ts"),"utf8");
test("R108 review handoff fails closed on source hash and candidate divergence",()=>{
 assert.match(s,/QUEUE\.sourceSha256!==original\.sha256/);
 assert.match(s,/diagnostic\.sha256!==original\.sha256/);
 assert.match(s,/JSON\.stringify\(QUEUE\.candidatePageObjectIndices\)/);
 assert.match(s,/REVIEW_QUEUE_PROVENANCE_MISMATCH/);
});
test("R108 never turns keyword hits into scientific signoff",()=>{
 for(const phrase of ["printedPageNumbersVerified:false","completePageTextVerified:false","sourcePageCitationsCertified:false","originalSignedProspectiveSAPAuthenticated:false","independentScienceReviewSigned:false","openScienceGates:11",'FDAForecast:"ABSTAIN"'])
  assert.ok(s.includes(phrase),phrase);
});
