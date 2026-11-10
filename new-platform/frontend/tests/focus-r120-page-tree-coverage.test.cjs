"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R120 explicitly reports page-tree traversal coverage mismatch without scientific certification",()=>{
 for(const x of ["provisionalNestedPageTreeCoverageMatchesDetectedPages","provisionalNestedPageTreeCoverageMismatch","provisionalNestedPageTreeOrder.length!==pages.length","sourcePageCitationsScientificallyCertified:false",'FDAForecast:"ABSTAIN"'])assert.ok(s.includes(x),x);
});
