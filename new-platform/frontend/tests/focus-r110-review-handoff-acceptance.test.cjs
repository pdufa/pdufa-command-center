"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const receipt=require("../data/focus-r109-acacia-live-review-handoff-acceptance-20261110.json");
const readback=require("../data/focus-r105-acacia-page-linked-diagnostic-readback-20261110.json");
const queue=require("../data/focus-r106-acacia-source-evidence-review-queue-20261110.json");
test("R110 reviewer handoff retains original source identity and candidate indices",()=>{
 assert.equal(receipt.sourceNct,"NCT06081894");
 assert.equal(receipt.sourceProtocol,"CY 6033");
 assert.equal(receipt.sourceSha256,queue.sourceSha256);
 assert.equal(receipt.sourceSha256,readback.documents.find(x=>x.key==="am4-protocol").sha256);
 assert.deepEqual(receipt.candidatePageObjectIndices,queue.candidatePageObjectIndices);
 assert.deepEqual(receipt.candidatePageObjectIndices,readback.documents.find(x=>x.key==="am4-protocol").pageObjectIndices);
 assert.equal(receipt.observedHttpStatus,200);
});
test("R110 live acceptance is not independent scientific signoff",()=>{
 for(const field of ["printedPageNumbersVerified","completePageTextVerified","sourcePageCitationsCertified","originalSignedProspectiveSAPAuthenticated","independentScienceReviewSigned"])
  assert.equal(receipt[field],false,field);
 assert.equal(receipt.openScienceGates,11);
 assert.equal(receipt.FDAForecast,"ABSTAIN");
 assert.equal(queue.FDAForecast,"ABSTAIN");
});
