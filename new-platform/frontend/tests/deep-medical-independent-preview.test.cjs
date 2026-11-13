const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText,f);
const {parseDeepMedicalSnapshot}=require('../lib/deep-medical-intelligence.ts');
const data=require('../data/deepMedicalIntelligencePreview.json');
test('independent source preview preserves all current trial identities and distinguishes medical completion',()=>{
 const d=parseDeepMedicalSnapshot(data),active=require('../data/p3PostDataActive.json').records;
 const current=new Set(active.map(r=>r.nct));
 const frozen=[...new Set(d.applications.flatMap(a=>a.nctIds))];
 assert.equal(frozen.length,29,"older research snapshot must retain its original 29 trial identities");
 assert.equal(current.size,32,"current source roster has 32 exact trials");
 assert.ok(frozen.every(nct=>current.has(nct)),"historic clinical research cannot introduce a foreign trial");
 assert.equal(d.installationLevels.length,12);assert.equal(d.inventory.completedDecisions,0);
 assert.ok(d.applications.every(a=>a.outcome.leading==='Indeterminate'&&a.timing.leading==='Indeterminate'));
 assert.ok(d.inventory.metadataScreenedTrials>d.inventory.fullyReviewedTrials);
});
test('unsupported decision and future source cannot bypass independent review',()=>{
 let d=structuredClone(data);d.applications[0].outcome.leading='Complete Response Letter';
 assert.throws(()=>parseDeepMedicalSnapshot(d),/INDEPENDENT_CHALLENGE/);
 d=structuredClone(data);d.sources[0].sourceDate='2099-01-01';assert.throws(()=>parseDeepMedicalSnapshot(d),/FUTURE_SOURCE/);
 d=structuredClone(data);d.legacyCompositeRating=75;assert.throws(()=>parseDeepMedicalSnapshot(d),/UNKNOWN_SCHEMA_FIELD/);
});
test('application outcome and timing remain separate and source references resolve',()=>{
 const d=structuredClone(data);d.applications[0].timing.leading='Complete Response Letter';assert.throws(()=>parseDeepMedicalSnapshot(d),/SEPARATE_DECISION/);
 const missing=structuredClone(data);missing.applications[0].outcome.sourceIds=['absent'];assert.throws(()=>parseDeepMedicalSnapshot(missing),/SOURCE_REFERENCE/);
});
