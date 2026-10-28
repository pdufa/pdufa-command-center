const test=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");const path=require("node:path");const Module=require("node:module");const ts=require("typescript");const root=path.resolve(__dirname,"../lib");const cache={};function load(name){if(cache[name])return cache[name].exports;const file=path.join(root,name+".ts");const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(file,module);cache[name]=m;m.filename=file;m.paths=module.paths;m.require=(id)=>id.startsWith("./")?load(id.slice(2)):require(id);m._compile(js,file);return m.exports;}
const {assessDecisionWithHistory}=load("decision-historical-gate");const now=new Date("2026-10-26T12:00:00Z");const record={programId:"PDUFA-999999",trialId:"NCT12345678",asOf:"2026-10-26T11:00:00Z",status:"COMPLETE",sourceStatus:"VERIFIED",reviewedLevels:20,requiredLevels:20,criticalFindingsResolved:true,calibrationStatus:"VALIDATED"};const target={programId:"PDUFA-999999",asOf:"2026-10-26T11:00:00Z",diseaseSubtype:"A",indication:"B",mechanism:"C",primaryEndpoint:"OS"};const history=Array.from({length:3},(_,i)=>({programId:"PDUFA-"+String(100001+i),decisionAt:"2025-01-01T00:00:00Z",diseaseSubtype:"A",indication:"B",mechanism:"C",primaryEndpoint:"OS",trialPhase:3,outcome:"APPROVED",sourceUrl:"https://example.org/fda",independentlyReviewed:true}));
test("complete synthetic inputs reach review but never trading approval",()=>assert.equal(assessDecisionWithHistory(record,record,target,history,now).status,"EVIDENCE_READY_FOR_REVIEW"));
test("missing analogues block decision readiness",()=>assert.equal(assessDecisionWithHistory(record,record,target,[],now).status,"NOT_READY"));
test("missing science blocks decision readiness",()=>assert.equal(assessDecisionWithHistory(null,record,target,history,now).status,"NOT_READY"));
test("unvalidated outcome blocks decision readiness",()=>assert.equal(assessDecisionWithHistory(record,{...record,calibrationStatus:"UNVALIDATED"},target,history,now).status,"NOT_READY"));
test("program mismatch blocks decision readiness",()=>assert.equal(assessDecisionWithHistory({...record,programId:"PDUFA-888888"},record,target,history,now).status,"NOT_READY"));
test("current science cannot satisfy a different historical prediction cutoff",()=>{
 const r=assessDecisionWithHistory({...record,asOf:"2026-10-26T10:00:00Z"},record,target,history,now);
 assert.equal(r.status,"NOT_READY");assert.ok(r.issues.includes("SCIENCE/target cutoff mismatch"));
});
test("outcome evidence at another cutoff cannot be joined",()=>{
 const r=assessDecisionWithHistory(record,{...record,asOf:"2026-10-26T10:00:00Z"},target,history,now);
 assert.equal(r.status,"NOT_READY");assert.ok(r.issues.includes("OUTCOME/target cutoff mismatch"));
});
