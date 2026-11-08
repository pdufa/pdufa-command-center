const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const code=fs.readFileSync(path.join(__dirname,"../lib/medical-intelligence-preview.ts"),"utf8");
const transformed=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};
vm.runInNewContext(transformed,{module:mod,exports:mod.exports});
const {reconcileRegistryBatch}=mod.exports;
const requested=["NCT00123456","NCT00987654"];
function study(nct){return {protocolSection:{identificationModule:{nctId:nct,briefTitle:"Controlled clinical study"},conditionsModule:{conditions:["Test condition"]},designModule:{phases:["PHASE3"],enrollmentInfo:{count:100}},statusModule:{overallStatus:"COMPLETED"},outcomesModule:{primaryOutcomes:[{measure:"Change from baseline"}]}}};}
test("Batch retains only requested exact NCT IDs, identifies incomplete coverage",()=>{
 const response={studies:[study("NCT00123456"),study("NCT00123456"),study("NCT99999999")]};
 const audit=reconcileRegistryBatch(response,requested);
 assert.equal(audit.responseCount,3);
 assert.equal(audit.byNct["NCT00123456"].nct,"NCT00123456");
 assert.equal(audit.byNct["NCT00987654"],undefined);
 assert.deepEqual([...audit.missingNcts],["NCT00987654"]);
 assert.deepEqual([...audit.duplicateNcts],["NCT00123456"]);
 assert.deepEqual([...audit.unexpectedNcts],["NCT99999999"]);
});
test("No false absence when registry response contains valid records",()=>{
 const audit=reconcileRegistryBatch({studies:requested.map(study)},requested);
 assert.equal(audit.missingNcts.length,0);
 assert.equal(Object.keys(audit.byNct).length,2);
});
test("Invalid IDs and unexpectedly wide batch are rejected",()=>{
 assert.throws(()=>reconcileRegistryBatch({studies:[]},["invalid"]),/Invalid/);
 assert.throws(()=>reconcileRegistryBatch({studies:[]},Array.from({length:101},(_,i)=>"NCT"+String(i).padStart(8,"0"))),/Invalid/);
});
