const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path"),Module=require("node:module"),ts=require("typescript");
const root=path.resolve(__dirname,"../lib"),cache={};
function load(name){if(cache[name])return cache[name].exports;const file=path.join(root,name+".ts");const js=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;const m=new Module(file,module);cache[name]=m;m.filename=file;m.paths=module.paths;m.require=(id)=>id.startsWith("./")?load(id.slice(2)):require(id);m._compile(js,file);return m.exports;}
const {assessCalibrationCohortAtCutoff}=load("decision-calibration-cohort-gate");
const rows=Array.from({length:30},(_,i)=>({programId:"PDUFA-"+String(100000+i),predictedAt:"2025-01-01T00:00:00Z",decisionAt:"2025-02-01T00:00:00Z",predictionCapturedAt:"2025-01-01T00:00:00Z",decisionObservedAt:"2025-02-02T00:00:00Z",predictionSource:"https://example.org/forecast",decisionSource:"https://example.org/fda",probability:i%2===0?.8:.2,approved:i%2===0,reviewStatus:"INDEPENDENTLY_VERIFIED"}));
test("historical synthetic cohort is research only",()=>{const r=assessCalibrationCohortAtCutoff(rows,"2026-10-26");assert.equal(r.status,"RESEARCH_ONLY");assert.equal(r.tradeAuthorized,false);});
test("outcomes after cutoff are rejected",()=>assert.equal(assessCalibrationCohortAtCutoff(rows,"2025-01-15").status,"NOT_READY"));
test("invalid cutoff rejected",()=>assert.equal(assessCalibrationCohortAtCutoff(rows,"invalid").status,"NOT_READY"));
test("missing review blocks calibration",()=>assert.equal(assessCalibrationCohortAtCutoff(rows.map((r,i)=>i? r:{...r,reviewStatus:"PENDING"}),"2026-10-26").status,"NOT_READY"));
