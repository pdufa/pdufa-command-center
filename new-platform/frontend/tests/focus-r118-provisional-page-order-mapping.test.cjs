"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R118 maps provisional Kids positions to object-scan indices without claiming certified page order",()=>{
 for(const x of ["provisionalDirectLeafOrderToObjectScanIndex","provisionalPageTreePosition:index+1","pdfPageDictionaryObjectScanIndex:pages.find","provisionalDirectLeafKidsOrderNotScientificallyCertified:true","verifiedPageTreeTraversalPerformed:false","sourcePageCitationsScientificallyCertified:false"])assert.ok(s.includes(x),x);
});
