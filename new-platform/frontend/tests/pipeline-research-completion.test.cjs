const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {loadCompleteResearch}=require('../lib/pipeline-research-pagination.ts');
const {canonicalResearchPage}=require('../lib/pipeline-research-export.ts');
const {programEligibility}=require('../lib/pipeline-program-eligibility.ts');
const {RANKED_BENEFIT_ASSESSMENTS,auditAssessmentFieldMapping}=require('../lib/pipeline-benefit-assessments.ts');
const make=n=>({nctId:'NCT'+String(n).padStart(8,'0'),ticker:'TEST',company:'Isolated fixture',drug:'A',indication:'B',sourceUrl:'https://clinicaltrials.gov/study/NCT'+String(n).padStart(8,'0'),poolStatus:'EXACT_MATCH',postPhase3Evidence:'REGISTRY_COMPLETED',reasons:['Independent current evidence missing'],qualification:'NEEDS_REVIEW',timeline:{phase3DataRelease:null,pdufaTarget:null}});
const all=Array.from({length:1207},(_,i)=>make(i+1));
const page=(offset,limit)=>({view:'pipeline',offset,limit,total:all.length,rows:all.slice(offset,offset+limit),nextOffset:offset+limit<all.length?offset+limit:null,datasetVersion:'a'.repeat(64),caveat:'Research only',overview:{qualifiedPrograms:null}});
test('all20 have dedicated inputs while all38 remain uniquely mapped',()=>{const a=auditAssessmentFieldMapping();assert.equal(a.originalFields,38);assert.equal(a.extensionFields,9);assert.equal(a.originalAssignedFields,29);assert.deepEqual(a.unassigned,[]);assert.deepEqual(a.duplicates,[]);assert.ok(RANKED_BENEFIT_ASSESSMENTS.every(s=>s.fields.length>0));});
test('complete retrieval exceeds500 without truncation and preserves exact order',async()=>{const p=await loadCompleteResearch(async(o,l)=>page(o,l));assert.equal(p.rows.length,1207);assert.equal(p.rows[1206].nctId,'NCT00001207');});
test('duplicate, changed-version and incomplete pages fail closed',async()=>{await assert.rejects(loadCompleteResearch(async(o,l)=>({...page(o,l),datasetVersion:o?'b':'a'})),/changed/);await assert.rejects(loadCompleteResearch(async(o,l)=>({...page(o,l),rows:[make(1),make(1)]})),/Duplicate/);await assert.rejects(loadCompleteResearch(async(o,l)=>({...page(o,l),nextOffset:null})),/Incomplete/);});
test('canonical export preserves38 fields,20 assessments, unknowns and stable identity',()=>{const p={...page(0,200),rows:[make(1)]};const a=canonicalResearchPage(p,'2026-10-31'),b=canonicalResearchPage(p,'2026-10-31');assert.equal(a.records[0].fields.length,38);assert.equal(a.records[0].assessments.length,20);assert.equal(a.records[0].recordId,b.records[0].recordId);assert.equal(a.records[0].approvedCompetitors,null);assert.equal(a.records[0].comparativeRank,null);assert.equal(a.verifiedEligiblePrograms,null);assert.ok(a.records[0].assessments.every(s=>s.state==='NOT_ASSESSED'));});
const identity={nctId:'NCT00116805',ticker:'TEST',drug:'A',indication:'B',sponsor:'C'};
const fact=value=>({value,identity,status:'VERIFIED',sourceUrl:'https://example.org/isolated-fixture',publishedAt:'2026-10-28T00:00:00Z',verifiedAt:'2026-10-30T00:00:00Z',validUntil:'2026-11-01T00:00:00Z'});
const evidence=()=>({listing:fact({public:true,exchangeCountry:'US'}),marketCap:fact({usd:300000000}),identity:fact({reconciled:true}),pivotal:fact({phase:3,pivotal:true,completed:true,finalReadout:true,publicResultsRelease:'2026-10-01'}),fda:fact({relevant:true,pdufaDate:'2026-11-20'})});
test('approved capbounds inclusive withUSlisting, source identity and prospective window',()=>{for(const usd of [300000000,10000000000]){const e=evidence();e.marketCap=fact({usd});assert.equal(programEligibility(identity,e,'2026-10-31').status,'QUALIFIED');}for(const usd of [299999999,10000000001]){const e=evidence();e.marketCap=fact({usd});assert.equal(programEligibility(identity,e,'2026-10-31').status,'REJECTED');}});
test('missing, mismatched, stale, foreign listing and cutoff cannotqualify',()=>{assert.equal(programEligibility(identity,undefined,'2026-10-31').status,'NEEDS_REVIEW');let e=evidence();e.listing=fact({public:true,exchangeCountry:'GB'});assert.equal(programEligibility(identity,e,'2026-10-31').status,'REJECTED');e=evidence();e.identity.identity={...identity,drug:'wrong'};assert.equal(programEligibility(identity,e,'2026-10-31').status,'NEEDS_REVIEW');e=evidence();e.marketCap.validUntil='2026-10-29T00:00:00Z';assert.equal(programEligibility(identity,e,'2026-10-31').status,'NEEDS_REVIEW');e=evidence();e.fda=fact({relevant:true,pdufaDate:'2026-11-03'});assert.equal(programEligibility(identity,e,'2026-10-31').researchWindow,'CUTOFF_REACHED');});

 test('disease-only and unmatched treatment lines cannotenable clinicalcompare',()=>{
 const {comparableResearchGroup}=require('../lib/pipeline-research-view.ts');
 assert.equal(comparableResearchGroup(make(1)),null);
 const comparisonScope={status:'VERIFIED',lineOfTherapy:'second line',patientPopulation:'adult marker positive',endpoint:'OS',followUpMonths:24,sourceUrl:'https://example.org/isolated-source',verifiedAt:'2026-10-30'};
 const a={...make(1),comparisonScope};
 assert.ok(comparableResearchGroup(a));
 assert.notEqual(comparableResearchGroup(a),comparableResearchGroup({...a,comparisonScope:{...comparisonScope,lineOfTherapy:'first line'}}));
 });
