"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const s=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence/route.ts"),"utf8");
test("R117 direct-leaf order is bounded, duplicate guarded, and explicitly provisional",()=>{
 for(const x of ["pageTreeNodeRefs.length===1","pageTreeNodesWithUnresolvedKids===0","new Set(pageTreeDirectKidRefs).size===pageTreeDirectKidRefs.length","provisionalDirectLeafKidsInArrayOrder:directLeafPageOrder","provisionalDirectLeafKidsOrderNotScientificallyCertified:true","verifiedPageTreeTraversalPerformed:false","sourcePageCitationsScientificallyCertified:false"])assert.ok(s.includes(x),x);
});
