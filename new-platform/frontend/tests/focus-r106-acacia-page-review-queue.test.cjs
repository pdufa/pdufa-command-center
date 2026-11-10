"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const d=require("../data/focus-r106-acacia-source-evidence-review-queue-20261110.json");
test("R106 prioritizes only observed KCCQ page-object indices in verified source",()=>{
 assert.equal(d.nct,"NCT06081894");
 assert.equal(d.protocol,"CY 6033");
 assert.equal(d.sourceSha256,"853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8");
 assert.deepEqual(d.candidatePageObjectIndices,[12,14,20,28,68,84]);
});
test("R106 review queue cannot be interpreted as evidence gate closure",()=>{
 assert.equal(d.status,"PENDING_PRIMARY_PAGE_REVIEW");
 assert.equal(d.sourcePageCitationsCertified,false);
 assert.equal(d.originalSignedProspectiveSAPAuthenticated,false);
 assert.equal(d.independentScienceReviewSigned,false);
 assert.equal(d.openScienceGates,11);
 assert.equal(d.FDAForecast,"ABSTAIN");
});
