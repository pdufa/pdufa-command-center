"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const src=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R114 structural Pages node count does not imply page-tree traversal or scientific certification",()=>{
 for(const s of ["detectedUncompressedPageTreeNodes:pageTreeNodeCount","verifiedPageTreeTraversalPerformed:false","pageDictionaryIndexIsObjectScanOrderNotVerifiedPageTreeOrder:true","sourcePageCitationsScientificallyCertified:false",'FDAForecast:"ABSTAIN"'])assert.ok(src.includes(s),s);
});
