"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const d=require("../data/focus-r105-acacia-page-linked-diagnostic-readback-20261110.json");
test("R105 original PDF hashes and six KCCQ candidate page-object indices preserved",()=>{
 assert.equal(d.nct,"NCT06081894");
 assert.equal(d.protocol,"CY 6033");
 assert.equal(d.documents.length,4);
 assert.deepEqual(d.documents.map(x=>x.pagesWithTextFragments),[83,0,2,5]);
 assert.deepEqual(d.documents[0].pageObjectIndices,[12,14,20,28,68,84]);
 assert.equal(d.allSourceHashVerified,true);
 assert.equal(d.allHttpStatus,200);
});
test("R105 page-linked diagnostic never closes original science gates",()=>{
 assert.equal(d.fullPageTextExtraction,false);
 assert.equal(d.clinicalPageCitationsCertified,false);
 assert.equal(d.originalSignedProspectiveSAPAuthenticated,false);
 assert.equal(d.independentScienceReviewSigned,false);
 assert.equal(d.openScienceGates,11);
 assert.equal(d.FDAForecast,"ABSTAIN");
});
