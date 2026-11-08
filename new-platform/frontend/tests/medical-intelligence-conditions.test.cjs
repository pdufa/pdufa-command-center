const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
const file=path.join(__dirname,"../lib/medical-intelligence-conditions.ts");
const code=fs.readFileSync(file,"utf8");
const compiled=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};
vm.runInNewContext(compiled,{module:mod,exports:mod.exports});
const {CONDITION_DOSSIERS,conditionForNct}=mod.exports;
const focus=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
const ncts=new Set(focus.records.map(x=>x.nct));
test("Sourced condition dossiers only attach to exact FOCUS trial identities",()=>{
 assert.equal(CONDITION_DOSSIERS.length,4);
 for(const d of CONDITION_DOSSIERS){
  assert.match(d.sourceUrl,/^https:\/\//);
  assert.equal(d.failureFirstQuestions.length,4);
  for(const nct of d.ncts){
   assert.ok(ncts.has(nct));
   assert.equal(conditionForNct(nct)?.id,d.id);
  }
 }
 assert.equal(conditionForNct("NCT99999999"),null);
 assert.equal(conditionForNct("random"),null);
});
