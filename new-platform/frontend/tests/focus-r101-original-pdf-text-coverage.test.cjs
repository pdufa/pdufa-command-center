"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const base=path.resolve(__dirname,"..");
const d=require("../data/focus-r101-acacia-pdf-text-diagnostic-readback-20261110.json");
test("R101 real readbacks have only 263 partial text operator fragments; not a signed SAP",()=>{
 assert.equal(d.exactNct,"NCT06081894");
 assert.equal(d.protocol,"CY 6033");
 assert.equal(d.euct,"2023-505797-15-00");
 assert.equal(d.originalDocuments.length,4);
 assert.deepEqual(d.originalDocuments.map(x=>x.textOperatorChunks),[250,13,0,0]);
 assert.equal(d.originalDocuments.reduce((s,x)=>s+x.textOperatorChunks,0),263);
 assert.equal(d.completeOriginalDocumentTextExtracted,false);
 assert.equal(d.originalPageMappingAvailable,false);
 assert.equal(d.sourcePageCitationsVerified,false);
 assert.equal(d.originalSAPSignaturesAuthenticated,0);
 assert.equal(d.independentScientificSignoffs,0);
 assert.equal(d.acaciaEvidenceGatesStillOpen,4);
 assert.equal(d.launchEvidenceGatesStillOpen,7);
 assert.equal(d.FDAForecast,"ABSTAIN");
});
test("R101 UI never promotes zero PDF operator matches to absence of text or scientific signoff",()=>{
 const p=fs.readFileSync(path.join(base,"app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
 assert.match(p,/R101_TEXT_DIAGNOSTICS/);
 assert.match(p,/zero extracted fragments is not proof/);
 assert.match(p,/Original page-level endpoint comparison/);
 assert.match(p,/FDA forecast: ABSTAIN/);
});
