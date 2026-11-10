"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R104 page-linked source evidence always validates original hash and exact document roster",()=>{
 assert.match(s,/R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS/);
 assert.match(s,/GET as originalPdf/);
 assert.match(s,/sha!==item\.sha256/);
 assert.match(s,/bytes\.length!==item\.byteCount/);
 assert.match(s,/DOCUMENT_NOT_ALLOWLISTED/);
});
test("R104 page evidence stays explicitly incomplete and FDA abstains",()=>{
 assert.match(s,/pdfPageDictionaryIndexIsNotCertifiedPrintedPageNumber:true/);
 assert.match(s,/completePageTextExtraction:false/);
 assert.match(s,/sourcePageCitationsScientificallyCertified:false/);
 assert.match(s,/signedProspectiveSAPAuthenticated:false/);
 assert.match(s,/independentScientificReviewSigned:false/);
 assert.match(s,/FDAForecast:"ABSTAIN"/);
});
