const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {auditScienceInvestigation,parseScienceInvestigation}=require('../lib/decision-science-investigation.ts');
const {investigation}=require('./fixtures/decision-investigation.cjs');
const identity={programId:'PDUFA-999999',trialId:'NCT12345678',ticker:'TEST',exactKey:'TRIAL|NCT12345678|TEST',stage:'GEM_JR'},asOf='2026-10-26T11:00:00Z';
const audit=(d=investigation(identity,asOf))=>auditScienceInvestigation(d,identity,asOf);
test('synthetic complete inventory yields cautious research review with 40 assessments, 20 levels and 8 layers',()=>{
 const r=audit();assert.equal(r.status,'READY_FOR_RESEARCH_REVIEW');assert.equal(r.completedAssessments,40);assert.equal(r.completedLevels,20);assert.equal(r.coveredLayers,8);
 assert.equal(r.evidenceCompletenessPct,100);assert.equal(r.reluctantAssessment,'CAUTIOUS_RESEARCH_ONLY');assert.equal(r.readiness.reviewedLevels,20);assert.match(r.warnings.join(' '),/independent verification/);
});
test('missing science has unknown completion instead of an invented zero-percent result',()=>{const r=audit(null);assert.equal(r.status,'NOT_READY');assert.equal(r.evidenceCompletenessPct,null);assert.equal(r.readiness,null);});
test('summary completeness cannot replace the source-cited investigation inventory',()=>{assert.equal(audit({reviewedLevels:20,sourceStatus:'VERIFIED'}).status,'NOT_READY');});
test('dossier identity is bound to the exact program,trial,ticker,key and stage',()=>{for(const change of [{stage:'GEM'},{programId:'PDUFA-111111'},{trialId:'NCT87654321'},{ticker:'OTHER'},{exactKey:'other'}]){const d=investigation(identity,asOf);Object.assign(d.identity,change);const r=audit(d);assert.equal(r.status,'NOT_READY');assert.equal(r.completedAssessments,0);}});
test('missing,duplicate or unrepresented subject layers never pass science readiness',()=>{
 for(const mutate of [d=>d.layers.pop(),d=>d.layers[1].id=d.layers[0].id,d=>d.levels.forEach(l=>l.layerId='subject-0'),d=>d.levels[0].layerId='unknown']){const d=investigation(identity,asOf);mutate(d);assert.equal(audit(d).status,'NOT_READY');}
});
test('missing or repeated levels and assessment identities cannot inflate completeness',()=>{
 for(const mutate of [d=>d.levels.pop(),d=>d.levels[1].id=d.levels[0].id,d=>d.levels[0].assessments.pop(),d=>d.levels[1].assessments[0].id=d.levels[0].assessments[0].id]){const d=investigation(identity,asOf);mutate(d);const r=audit(d);assert.equal(r.status,'NOT_READY');assert.equal(r.evidenceCompletenessPct,null);}
});
test('critical evaluation,uncertainty,independent sources and unresolved findings remain mandatory',()=>{
 for(const changes of [{criticalEvaluation:''},{uncertainty:''},{reviewer:''},{unresolvedCriticalFindings:1},{sources:[]},{status:'CONFLICT'}]){const d=investigation(identity,asOf);Object.assign(d.levels[0].assessments[0],changes);const r=audit(d);assert.equal(r.status,'NOT_READY');assert.equal(r.completedAssessments,39);assert.equal(r.completedLevels,19);assert.equal(r.evidenceCompletenessPct,97.5);assert.equal(r.reluctantAssessment,'WITHHELD');}
});
test('source observations at or after cutoff and observation before publication are unavailable',()=>{
 for(const changes of [{observedAt:asOf},{observedAt:'2026-10-27T00:00:00Z'},{publishedAt:'2026-10-25T00:00:00Z'},{independentlyReviewed:false},{independentlyReviewed:'true'}]){const d=investigation(identity,asOf);Object.assign(d.levels[0].assessments[0].sources[0],changes);assert.equal(audit(d).status,'NOT_READY');}
});
test('different cutoff and invalid company/application identities stay blocked',()=>{
 for(const changes of [{asOf:'2026-10-25T00:00:00Z'},{companyCik:'0000000000'},{fdaApplication:'invalid'},{drug:''},{indication:''}]){const d=Object.assign(investigation(identity,asOf),changes);assert.equal(audit(d).status,'NOT_READY');}
});
test('impossible calendar dates and ambiguous local timestamps cannot enter source chronology',()=>{
 for(const publishedAt of ['2026-02-31T00:00:00Z','2026-02-29T00:00:00Z','2026-10-24T25:00:00Z','2026-10-24T10:00:00']){const d=investigation(identity,asOf);d.levels[0].assessments[0].sources[0].publishedAt=publishedAt;assert.equal(audit(d).status,'NOT_READY');}
});
test('parser rejects excessive inventories,non-HTTPS or credential sources and unexpected trading fields',()=>{
 for(const mutate of [d=>d.layers.push({id:'9',label:'extra'}),d=>d.levels.push(d.levels[0]),d=>d.levels[0].assessments.push(d.levels[0].assessments[0]),d=>d.levels[0].assessments[0].sources[0].url='https://user:secret@example.org/source',d=>d.levels[0].assessments[0].sources[0].url='http://example.org/source',d=>d.tradeAuthorized=true]){const d=investigation(identity,asOf);mutate(d);assert.throws(()=>parseScienceInvestigation(d));}
});
