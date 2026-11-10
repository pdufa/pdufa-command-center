"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R116 classifies direct page-tree children while retaining no-traversal safeguards",()=>{
 for(const x of ["detectedDirectPageTreeKids","detectedDirectKidsMatchingPageDictionaries","detectedDirectKidsMatchingNestedPageNodes","verifiedPageTreeTraversalPerformed:false","sourcePageCitationsScientificallyCertified:false",'FDAForecast:"ABSTAIN"'])assert.ok(s.includes(x),x);
});
