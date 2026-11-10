"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const route=fs.readFileSync(path.join(root,"app/predictions/scientific-reconciliation/priority-gates/ctis-text-index/route.ts"),"utf8");
test("R100 uses only R99 original PDF checksum-gated retrieval; never arbitrary external URL",()=>{
 assert.match(route,/GET as originalPdf/);
 assert.match(route,/R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS/);
 assert.match(route,/originalPdf\(new Request/);
 assert.match(route,/sha!==item\.sha256/);
 assert.match(route,/bytes\.length!==item\.byteCount/);
 assert.match(route,/SOURCE_PDF_SHA256_MISMATCH/);
 assert.match(route,/ORIGINAL_CTIS_DOCUMENT_NOT_ALLOWLISTED/);
});
test("R100 labels PDF operator diagnostics as incomplete, no page reference and no signed SAP",()=>{
 assert.match(route,/BOUNDED_PDF_TEXT_OPERATORS_WITH_FLATE_ONLY/);
 assert.match(route,/scientificPageReferencesCertified:false/);
 assert.match(route,/completePdfTextExtracted:false/);
 assert.match(route,/originalDocumentTextScientificallyReviewed:false/);
 assert.match(route,/controlledSignedFinalSAPAuthenticated:false/);
 assert.match(route,/independentScienceSignoff:false/);
 assert.match(route,/FDAForecast:"ABSTAIN"/);
 assert.match(route,/MAX_STREAMS=3000/);
 assert.match(route,/MAX_DECOMPRESSED=20_000_000/);
});
