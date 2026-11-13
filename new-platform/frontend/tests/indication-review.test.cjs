'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,f);
const {buildIndicationReview,indicationReviewSummary}=require('../lib/indication-review.ts');
const trial={nct:'NCT01234567',indicationText:'A specific biomarker-defined cancer',stage:'Phase 1',focus:false};
const details={nctId:'NCT01234567',sourceUrl:'https://clinicaltrials.gov/study/NCT01234567',
 retrievedAt:'2026-11-13T00:00:00Z',
 fields:{eligibility:'Requires prior therapy',enrollment:'24',reportedResults:null,safetyResults:null,
  treatmentArms:'Drug A',documentsPublications:null},
 available:3,total:14};
test('clinical source observations are research leads, never validated efficacy or safety',()=>{
 const rows=buildIndicationReview(trial,details),summary=indicationReviewSummary(rows);
 assert.ok(rows.length>=10);
 assert.equal(rows.find(x=>x.key==='patient-subgroups').state,'SOURCE_OBSERVED_REVIEW_REQUIRED');
 assert.equal(rows.find(x=>x.key==='efficacy').state,'RESEARCH_REQUIRED');
 assert.equal(rows.find(x=>x.key==='safety').state,'RESEARCH_REQUIRED');
 assert.equal(rows.find(x=>x.key==='score-confidence').state,'NOT_SCORED');
 assert.equal(rows.find(x=>x.key==='history').state,'NOT_CONNECTED');
 assert.equal(summary.scored,0);
 assert.equal(summary.clinicallyAdjudicated,0);
});
test('source URLs only attach when the exact registry actually reports a field',()=>{
 const rows=buildIndicationReview(trial,details);
 assert.equal(rows.find(x=>x.key==='existing-therapies').sourceUrl,details.sourceUrl);
 assert.equal(rows.find(x=>x.key==='efficacy').sourceUrl,null);
 assert.equal(rows.find(x=>x.key==='competitive-trials').sourceUrl,null);
});
test('no source record cannot become an automatic scientific result',()=>{
 const rows=buildIndicationReview(trial,null);
 assert.equal(rows.filter(x=>x.state==='SOURCE_OBSERVED_REVIEW_REQUIRED').length,0);
 assert.equal(rows.find(x=>x.key==='score-confidence').evidence,null);
});
