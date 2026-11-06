const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const vm=require("node:vm");
const lib=path.join(__dirname,"../lib");
function load(name, resolver){const src=fs.readFileSync(path.join(lib,name),"utf8");const code=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;const out={};vm.runInNewContext(code,{exports:out,require:resolver});return out;}
const catalog=load("science-question-catalog.proposed.ts",require);
const published=load("peak-reported-evidence.proposed.ts",require);
const register=load("peak-evidence-register.proposed.ts",id=>id.includes("peak-reported")?published:catalog);
const queue=load("peak-go18-review-queue.proposed.ts",require);
const readiness=load("peak-go19-readiness.proposed.ts",id=>id.includes("peak-go18")?queue:register).PEAK_GO19_READINESS;
test("GO19 reconciles all questions and GO18 review records",()=>{assert.equal(readiness.questionCount,40);assert.equal(readiness.go18ReviewCount,12);assert.equal(readiness.go18PartialCount,6);assert.equal(readiness.go18MissingCount,6);assert.equal(readiness.mappedPublishedQuestions,11);assert.equal(new Set(Array.from(readiness.records,r=>r.assessmentId)).size,40);});
test("GO19 never certifies unadjudicated PEAK evidence",()=>{assert.equal(readiness.scientificReadiness,"INSUFFICIENT_EVIDENCE");assert.equal(readiness.approvalProbability,null);assert.equal(readiness.verifiedQuestionCount,0);for(const row of readiness.records){assert.equal(row.score,null);assert.equal(row.independentlyVerified,false);assert.ok(row.outstanding.length>0);}});
