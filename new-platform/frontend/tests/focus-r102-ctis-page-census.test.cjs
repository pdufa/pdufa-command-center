"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const route=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-census/route.ts"),"utf8");
test("R102 page census uses only SHA-matched exact ACACIA original PDF",()=>{
 assert.match(route,/R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS/);
 assert.match(route,/originalPdf\(new Request/);
 assert.match(route,/sha!==item\.sha256/);
 assert.match(route,/bytes\.length!==item\.byteCount/);
 assert.match(route,/UNAUTHORIZED_CTIS_ORIGINAL_DOCUMENT_KEY/);
});
test("R102 does not mislabel page structure as extracted text or signed SAP",()=>{
 assert.match(route,/pageCountStructurallyConsistent/);
 assert.match(route,/objectStreamContainersFound/);
 assert.match(route,/allPagesTextDecoded:false/);
 assert.match(route,/pageLevelEndpointEvidenceExtracted:false/);
 assert.match(route,/pageCitationsScientificallyValidated:false/);
 assert.match(route,/signedFinalSAPAuthenticated:false/);
 assert.match(route,/FDAForecast:"ABSTAIN"/);
});
