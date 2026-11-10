"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const src=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R113 PDF object scan index is explicitly not certified page-tree order",()=>{
 assert.match(src,/pageDictionaryIndexIsObjectScanOrderNotVerifiedPageTreeOrder:true/);
 assert.match(src,/NOT verified PDF page-tree order or viewer page numbers/);
 assert.match(src,/sourcePageCitationsScientificallyCertified:false/);
 assert.match(src,/signedProspectiveSAPAuthenticated:false/);
 assert.match(src,/FDAForecast:"ABSTAIN"/);
});
