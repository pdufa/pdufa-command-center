const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");const path=require("node:path");const ts=require("typescript");const vm=require("node:vm");
const src=fs.readFileSync(path.join(__dirname,"../lib/peak-go20-document-priorities.proposed.ts"),"utf8");
const compiled=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const output={};vm.runInNewContext(compiled,{exports:output});
const rows=output.PEAK_GO20_DOCUMENT_PRIORITIES;
test("eight document groups cover all forty questions without duplication",()=>{
 assert.equal(rows.length,8);
 assert.deepEqual(Array.from(rows,r=>r.rank),[1,2,3,4,5,6,7,8]);
 const ids=rows.flatMap(r=>Array.from(r.assessmentIds));assert.equal(ids.length,40);assert.equal(new Set(ids).size,40);
 for(let i=1;i<=40;i++)assert.ok(ids.includes("S"+String(i).padStart(2,"0")));
});
test("prioritization does not invent verification, document access or predictions",()=>{
 for(const r of rows){assert.equal(r.status,"NOT_INDEPENDENTLY_REVIEWED");assert.equal(r.availability,"UNKNOWN");}
 const s=output.PEAK_GO20_ACQUISITION_STATUS;assert.equal(s.reviewedDocuments,0);assert.equal(s.independentlyVerifiedAssessments,0);assert.equal(s.readiness,"INSUFFICIENT_EVIDENCE");assert.equal(s.approvalProbability,null);
});
