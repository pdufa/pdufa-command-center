"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const d=require("../data/focus-r103-acacia-original-pdf-structural-census-20261110.json");
test("R103 source page dictionary census has only one structurally consistent original",()=>{
 assert.equal(d.nct,"NCT06081894");
 assert.equal(d.protocol,"CY 6033");
 assert.deepEqual(d.documents.map(x=>x.structuralPageDictionariesFound),[90,102,2,5]);
 assert.deepEqual(d.documents.map(x=>x.objectStreams),[5,0,1,20]);
 assert.deepEqual(d.documents.map(x=>x.structurallyConsistent),[false,true,false,false]);
 assert.equal(d.fullPageTextAvailable,false);
 assert.equal(d.pageCitationsCertified,false);
 assert.equal(d.signedFinalSAPAuthenticated,false);
 assert.equal(d.ACACIAGatesOpen,4);
 assert.equal(d.LaunchGatesOpen,7);
 assert.equal(d.FDAForecast,"ABSTAIN");
});
test("R103 page structure dashboard explicitly rejects page citation certification",()=>{
 const p=fs.readFileSync(path.resolve(__dirname,"../app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
 assert.match(p,/R103_PAGE_CENSUS/);
 assert.match(p,/Do not use these counts as clinical page citations/);
 assert.match(p,/FDA forecast: ABSTAIN/);
});
