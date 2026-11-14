const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,f);
const {predictLevel3,abstinenceDirection}=require('../lib/level3-clinical-predictor.ts');
const {runAssessment,parseRunRequest}=require('../lib/level16-assessment-runner.ts');
const evidence=require('../data/level16AssessmentEvidence.json');
const cutoff=evidence.evidenceCutoffDate,trial=(nct='NCT04576949')=>structuredClone(evidence.trials.find(t=>t.nct===nct));
const call=t=>predictLevel3(t,cutoff).call;
test('ORCA-2 and ORCA-3 generate conditional source-linked approval leans, never probabilities or signoff',()=>{
 for(const nct of ['NCT04576949','NCT05206370']){
  const p=predictLevel3(trial(nct),cutoff);assert.equal(p.call,'APPROVAL_LEAN');assert.equal(p.fdaApplicationForecast,false);assert.equal(p.score,null);assert.equal(p.approvalProbability,null);assert.equal(p.ownerReviewStatus,'OWNER_NOT_REVIEWED');assert.equal(p.sources[0].kind,'PUBLICATION_FULL_TEXT');assert.match(p.reasons.join(' '),/reported OR/);assert.match(p.limitations.join(' '),/deaths/);
 }
});
test('all 32 trials have explicit predictions; 30 abstain where domain-specific original analysis is missing',()=>{
 const a=runAssessment({scope:'ALL',level:3});assert.equal(a.summary.levelsProcessed,32);assert.equal(a.summary.trialsProcessed,32);assert.ok(a.trials.every(t=>t.levels.length===1&&t.levels[0].level===3));assert.equal(a.trials.filter(t=>t.level3Prediction.call==='APPROVAL_LEAN').length,2);assert.equal(a.trials.filter(t=>t.level3Prediction.call==='INSUFFICIENT_EVIDENCE').length,30);
 assert.equal(a.trials.filter(t=>!t.provisionalApplicationCycleIds.length).length,3);
});
test('trial 14 CLDX remains insufficient rather than converting sponsor pointers or planned endpoints to efficacy',()=>{
 const p=predictLevel3(trial('NCT06455202'),cutoff);assert.equal(p.label,'Insufficient evidence');assert.match(p.missingEvidence.join(' '),/quantitative clinical results/);
});
test('a separately requested Level 3 run returns one level; existing six-level runs remain six',()=>{
 assert.equal(runAssessment({scope:'ONE',nct:'NCT04576949',level:3}).summary.levelsProcessed,1);
 assert.equal(runAssessment({scope:'ONE',nct:'NCT04576949'}).summary.levelsProcessed,6);
 for(const value of [{scope:'ALL',level:2},{scope:'ALL',level:'3'},{scope:'ALL',level:3,call:'APPROVAL_LEAN'},{scope:'ALL',level:3,ownerReviewStatus:'OWNER_ACCEPTED_WITH_LIMITATIONS'}])assert.throws(()=>parseRunRequest(value));
});
test('synthetic adverse primary comparisons exercise CRL branch; no genuine trial is rewritten',()=>{
 const t=trial();for(const c of t.reportedComparisons){[c.activeAbstinent,c.placeboAbstinent]=[c.placeboAbstinent,c.activeAbstinent];[c.activeRandomized,c.placeboRandomized]=[c.placeboRandomized,c.activeRandomized];[c.activePct,c.placeboPct]=[c.placeboPct,c.activePct];c.oddsRatioReported=1/c.oddsRatioReported;c.ci95Reported=[1/c.ci95Reported[1],1/c.ci95Reported[0]];}
 assert.equal(call(t),'CRL_LEAN');assert.equal(call(trial()),'APPROVAL_LEAN');
});
test('missing, null and inconclusive results never become CRL leans',()=>{
 for(const change of [t=>t.reportedComparisons=[],t=>t.publishedSafety=null,t=>t.reportedClinicalResultsPresent=false,t=>t.reportedComparisons[0].ci95Reported=[0.5,20]]){const t=trial();change(t);assert.equal(call(t),'INSUFFICIENT_EVIDENCE');}
});
test('mixed, duplicated, incomplete, secondary-only and internally inconsistent primary results abstain',()=>{
 for(const change of [t=>t.reportedComparisons.pop()&&t.reportedComparisons.shift(),t=>t.reportedComparisons.push(t.reportedComparisons[0]),t=>t.reportedComparisons.forEach(c=>c.classification='SECONDARY'),t=>t.reportedComparisons[0].activePct=99,t=>t.reportedComparisons[0].ci95Reported=[99,100]]){const t=trial();change(t);assert.equal(call(t),'INSUFFICIENT_EVIDENCE');}
});
test('opposing secondary evidence cannot be hidden behind a primary approval lean',()=>{
 const t=trial(),c=t.reportedComparisons[2];c.activeAbstinent=1;c.activePct=0.4;c.oddsRatioReported=0.1;c.ci95Reported=[0.02,0.5];assert.equal(abstinenceDirection(c),'ADVERSE');const p=predictLevel3(t,cutoff);assert.equal(p.call,'INSUFFICIENT_EVIDENCE');assert.match(p.contradictions.join(' '),/secondary outcome/);
});
test('source identity, digest, date, NCT, PMID and endpoint direction must remain bound',()=>{
 for(const change of [t=>t.publishedComparisonSource=null,t=>t.publishedComparisonSource.nct='NCT05206370',t=>t.publishedComparisonSource.pmid='invented',t=>t.publishedComparisonSource.documentSha256='0'.repeat(64),t=>t.publishedComparisonSource.endpointDomain='UNSUPPORTED',t=>t.publishedComparisonSource.publicationDate='2099-01-01',t=>t.publishedComparisonSource.retrievedAt='2026-11-14T23:00:00-05:00',t=>t.publishedComparisonSource.retrievedAt='2026-11-14T01:00:00']){const t=trial();change(t);assert.equal(call(t),'INSUFFICIENT_EVIDENCE');}
});
test('early phase, unresolved phase, unmapped and ambiguous applications abstain without inventing a mapping',()=>{
 for(const change of [t=>t.phases=['PHASE1'],t=>t.phases=['PHASE2'],t=>t.phases=[],t=>t.phases=['NA'],t=>t.provisionalApplicationCycleIds=[],t=>t.provisionalApplicationCycleIds.push('second'),t=>t.applicationMappingStatus='NOT_MAPPED_APPLICATION_CYCLE']){const t=trial();change(t);assert.equal(call(t),'INSUFFICIENT_EVIDENCE');}
});
test('chronology uncertainty is disclosed without inventing a post-hoc conclusion; outputs cannot enter blind history',()=>{
 const p=predictLevel3(trial(),cutoff);assert.match(p.limitations.join(' '),/unresolved/);assert.equal(p.historicalPredictionInputPermitted,false);assert.equal(p.prospectivelyBlind,false);
});
