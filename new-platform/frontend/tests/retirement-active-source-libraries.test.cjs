'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,file);
const {phaseFirstReport}=require('../lib/phase-first-report.ts');
const {renderToolsSpreadsheetCsv}=require('../lib/tools-spreadsheet.ts');
const {phase3PeerReviewedFact}=require('../lib/phase3-source-fact-enrichment.ts');
test('active source reports cannot load retired scoring implementations',()=>{
 for(const scope of ['alkermes','axsome','sinovac','census']){
  const report=phaseFirstReport(scope);assert.equal(report.analysisMode,'PHASE_APPROPRIATE_SOURCE_EVIDENCE_ONLY');
  for(const row of report.trials)for(const key of ['raasScore','raasPredictionConfidence','overallRating','ratingCoverage','factors'])assert.equal(key in row,false,scope+':'+row.trialId+':'+key);
 }
 assert.deepEqual(Object.keys(require.cache).filter(file=>/[\\/]lib[\\/]raas-[^\\/]+\.(?:ts|js)$/.test(file)),[]);
});
test('TOOLS CSV keeps source identity and dates without retired rating columns',()=>{
 const row={id:'TRIAL|NCT00000001',nctId:'NCT00000001',ticker:'TEST',company:'Company',drug:'Drug',indication:'Condition',stage:'Phase 2'};
 const csv=renderToolsSpreadsheetCsv([row],['Phase 2'],[],null,'2026-11-08');
 assert.ok(csv.includes('NCT00000001'));assert.ok(csv.split('\r\n')[0].includes('NCT ID'));
 assert.doesNotMatch(csv.split('\r\n')[0],/RAAS|approved.*score|rating|source areas mapped/i);
});
test('saved clinical facts expose observations without historical score fields',()=>{
 const ledger=require('../data/phase3PeerReviewedClinicalEvidence20261106.json');
 for(const original of ledger.facts){const fact=phase3PeerReviewedFact(original.nctId,original.question);
  assert.equal(fact.evidence,original.evidence);assert.equal(fact.sourceUrl,original.sourceUrl);
  assert.equal('raasScore' in fact,false);assert.equal('clinicalRating' in fact,false);
 }
});
