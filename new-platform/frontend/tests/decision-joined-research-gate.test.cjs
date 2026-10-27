const test=require("node:test");const assert=require("node:assert/strict");const fs=require("node:fs");const path=require("node:path");const Module=require("node:module");const ts=require("typescript");
const root=path.resolve(__dirname,"../lib"),cache={};
function load(name){if(cache[name])return cache[name].exports;const file=path.join(root,name+".ts");const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(file,module);cache[name]=m;m.filename=file;m.paths=module.paths;m.require=id.startsWith("./")?load(id.slice(2)):require(id);m._compile(js,file);return m.exports;}
const {assessJoinedDecisionResearch}=load("decision-joined-research-gate");
const asOf="2026-10-26T11:00:00Z",now=new Date("2026-10-26T12:00:00Z");
const record={programId:"PDUFA-999999",trialId:"NCT12345678",asOf,status:"COMPLETE",sourceStatus:"VERIFIED",reviewedLevels:20,requiredLevels:20,criticalFindingsResolved:true,calibrationStatus:"VALIDATED"};
const target={programId:record.programId,asOf,diseaseSubtype:"A",indication:"B",mechanism:"C",primaryEndpoint:"OS"};
const history=Array.from({length:3},(_,i)=>({programId:"PDUFA-"+String(100001+i),decisionAt:"2025-01-01T00:00:00Z",diseaseSubtype:"A",indication:"B",mechanism:"C",primaryEndpoint:"OS",trialPhase:3,outcome:"APPROVED",sourceUrl:"https://example.org/fda",independentlyReviewed:true}));
const coverage={asOf,windowStart:"2020-01-01",windowEnd:"2025-01-01",eligibleApplications:10,reviewedDecisions:10,approved:6,crl:3,withdrawn:1,unresolved:0,sourceCoverageConfirmed:true,includesNonApprovals:true};
const chronology=Object.fromEntries(history.map(r=>[r.programId,[{sourceUrl:r.sourceUrl,publishedAt:"2025-01-02T00:00:00Z",observedAt:"2025-01-03T00:00:00Z",decisionAt:r.decisionAt,predictionCutoff:asOf,independentlyReviewed:true}]]));
const assess=(h=history,c=chronology)=>assessJoinedDecisionResearch(record,record,target,h,coverage,c,now);
test("complete synthetic joined research is ready for review, not trading",()=>{const r=assess();assert.equal(r.status,"EVIDENCE_READY_FOR_REVIEW");assert.equal(r.chronologyReviewed,3);});
test("missing matched analogue source blocks joined readiness",()=>{const c={...chronology};delete c[history[0].programId];assert.equal(assess(history,c).status,"NOT_READY");});
test("source observed after cutoff blocks joined readiness",()=>{const c=structuredClone(chronology);c[history[0].programId][0].observedAt="2026-11-01";assert.equal(assess(history,c).status,"NOT_READY");});
test("source decision mismatch blocks joined readiness",()=>{const c=structuredClone(chronology);c[history[0].programId][0].decisionAt="2024-12-31";assert.equal(assess(history,c).status,"NOT_READY");});
test("source URL mismatch blocks joined readiness",()=>{const c=structuredClone(chronology);c[history[0].programId][0].sourceUrl="https://example.org/other";assert.equal(assess(history,c).status,"NOT_READY");});
test("unmatched historic rows do not require chronology",()=>{const extra={...history[0],programId:"PDUFA-777777",mechanism:"unrelated"};const r=assess([...history,extra]);assert.equal(r.status,"EVIDENCE_READY_FOR_REVIEW");assert.equal(r.chronologyRequired,3);});
