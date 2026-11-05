"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const dir=path.resolve(__dirname,"..");
test("one-row-per-trial matrix provides five clinical factor score columns for 741 trials",()=>{
 const lines=fs.readFileSync(path.join(dir,"public/raas-741-five-clinical-score-matrix.csv"),"utf8").trim().split(/\r?\n/);
 assert.equal(lines.length,742);
 assert.match(lines[0],/efficacy_0_100/);
 assert.match(lines[0],/safety_0_100/);
});
test("registry results research stage is not mislabeled issuer-verified Phase3 outcome",()=>{
 const v=JSON.parse(fs.readFileSync(path.join(dir,"data/raas-active-741-coverage.json"),"utf8"));
 assert.equal(v.registryResearchPreview.unclassifiedWithPostedResults,325);
 assert.equal(v.registryResearchPreview.unclassifiedWithoutPostedResults,404);
 assert.equal(v.registryResearchPreview.unclassifiedMissingFromSavedIndex,2);
 assert.equal(v.registryResearchPreview.issuerStageStillUnclassified,731);
 assert.equal(v.classifiedSourceAcceptedGrades,45);
 assert.equal(v.classifiedMissingGrades,5);
});
