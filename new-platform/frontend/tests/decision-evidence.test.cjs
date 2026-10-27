const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const Module=require("node:module");
const ts=require("typescript");
const root=path.resolve(__dirname,"../lib");
const cache={};
function load(name){if(cache[name])return cache[name].exports;const filename=path.join(root,name+".ts");const js=ts.transpileModule(fs.readFileSync(filename,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(filename,module);cache[name]=m;m.filename=filename;m.paths=module.paths;m.require=(id)=>id.startsWith("./")?load(id.slice(2)):require(id);m._compile(js,filename);return m.exports;}
const {evaluateEvidenceDecision}=load("decision-evidence");
const date="2026-10-26T12:00:00Z";
const field=value=>({value,status:"VERIFIED",observedAt:date,sourceUrl:"https://example.org/evidence"});
const evidence={programId:"PDUFA-123456",ticker:"TEST",asOf:date,price:field(10),approvalProbability:field(.7),approvalPrice:field(16),rejectionPrice:field(4),delayProbability:field(.1),delayPrice:field(8),costPct:field(1),calibration:{status:"VALIDATED",sampleSize:100,asOf:date}};
const clock=new Date("2026-10-26T13:00:00Z");
test("complete declared evidence produces research only, never buy",()=>{const r=evaluateEvidenceDecision(evidence,clock);assert.equal(r.status,"RESEARCH_ONLY");assert.ok(Math.abs(r.scenario.expectedReturnPct-27)<1e-9);});
test("unverified source blocks scenario",()=>{const r=evaluateEvidenceDecision({...evidence,price:{...evidence.price,status:"UNVERIFIED"}},clock);assert.equal(r.status,"NOT_READY");assert.equal(r.scenario,null);});
test("stale price evidence blocks scenario",()=>assert.equal(evaluateEvidenceDecision({...evidence,price:{...evidence.price,observedAt:"2026-10-20T12:00:00Z"}},clock).status,"NOT_READY"));
test("missing calibration blocks scenario",()=>assert.equal(evaluateEvidenceDecision({...evidence,calibration:{status:"UNVALIDATED",sampleSize:0,asOf:date}},clock).status,"NOT_READY"));
test("conflicting source blocks scenario",()=>assert.equal(evaluateEvidenceDecision({...evidence,approvalProbability:{...evidence.approvalProbability,status:"CONFLICT"}},clock).status,"NOT_READY"));
