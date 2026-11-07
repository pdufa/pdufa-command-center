/* Recompute from the canonical BOTTOM ledger, export coverage, append changed
 * exact-NCT score snapshots. No network, grades, roster changes or sheet writes.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),ts=require('typescript');
const root=path.resolve(__dirname,'..'),repo=path.resolve(root,'../..');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,f);
const {bottomOnlyReport}=require('../lib/bottom-only-completion.ts');
const {bottomExport}=require('../lib/bottom-only-exports.ts');
const report=bottomOnlyReport();
const dir=path.join(repo,'reports/bottom-only-20261107'),data=path.join(root,'data');
const historyPath=path.join(data,'bottomOnlyScoreHistory20261107.json');
const history=JSON.parse(fs.readFileSync(historyPath));
const hash=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');
for(const trial of report.trials){
 const metricGrades=trial.clinicalFactors.map(f=>({id:f.id,grade:f.grade,sourceUrl:f.sourceUrl,sourceDate:f.sourceDate,finding:f.finding,benchmarkSourceUrl:f.benchmarkSourceUrl,criticalRiskReview:f.criticalRiskReview,assessedAt:f.assessedAt,observedResult:f.observedResult,benchmarkContext:f.benchmarkContext,uncertaintyReview:f.uncertaintyReview,blocker:f.blocker}));
 const evidenceHash=hash(metricGrades),eventId=`BOTTOM_${trial.nctId}_${report.version}_${evidenceHash.slice(0,16)}`;
 if(!history.records.some(r=>r.eventId===eventId))history.records.push({eventId,nctId:trial.nctId,recordedAt:report.asOf,eventType:'EVIDENCE_REVIEW_RECALCULATION',clinicalFullScore:trial.clinicalFullScore,clinicalScoredFactors:trial.clinicalScoredFactors,metricGrades,scoreType:'SOURCE_ACCEPTED_POSTDATA_FIVE_FACTOR_RESEARCH_NOT_FDA_PROBABILITY',scoreVersion:report.version,evidenceHash,reason:'Full exact-NCT source review; new documented clinical reviews applied with existing 0/25/50/75/100 anchors and equal 20% weights. Prior snapshots retained.',note:'Every ungraded factor has an explicit disclosure, pending follow-up, or rule blocker. Missing is null, never an inferred score.'});
}
fs.writeFileSync(historyPath,JSON.stringify(history,null,2)+'\n');
fs.writeFileSync(path.join(dir,'bottom-score-sync.json'),JSON.stringify({asOf:report.asOf,records:report.trials.map(t=>({nctId:t.nctId,ticker:t.ticker,asOf:report.asOf,clinicalFullScore:t.clinicalFullScore,factors:t.clinicalFactors.map(f=>({id:f.id,grade:f.grade,state:f.evidenceState})),evidenceNote:t.clinicalFactors.map(f=>f.name+': '+(f.grade??f.evidenceState)+'; '+(f.observedResult??f.blocker)+'; Source: '+(f.sourceUrl??'Not reported')+'; Benchmark: '+(f.benchmarkSourceUrl??'Not applicable')+'; Uncertainty: '+(f.uncertaintyReview??f.blocker)).join('\n')+'\nEqual 20% weights. Research only, not FDA probability. Exact-NCT snapshots retained in repository.'}))},null,2)+'\n');
const coverage={scope:report.scope,asOf:report.asOf,version:report.version,trialCount:report.trialCount,processedTrials:report.trialCount,totalCells:report.trialCount*report.fieldsPerTrial,activeFactors:report.activeFactorCount,activeFactorsGraded:report.activeFactorsScored,missingActiveFactorGrades:report.activeFactorCount-report.activeFactorsScored,completeClinicalScores:report.completeClinicalOverallScores,completeThirtyMetricScores:report.completeThirtyMetricOverallScores,sourceBackedQuestionItems:report.sourceBackedQuestionCount,totalQuestionItems:report.totalQuestionCount,unresolvedQuestionItems:report.unresolvedQuestionCount,sourceCoveragePercent:Math.round(report.sourceBackedQuestionCount/report.totalQuestionCount*1000)/10,nonMissingFieldCount:report.trials.reduce((n,t)=>n+t.nonMissingFieldCount,0),gradedCoveragePercent:Math.round(report.activeFactorsScored/report.activeFactorCount*1000)/10,notValidatedFdaProbability:true};
coverage.fieldPopulationPercent=Math.round(coverage.nonMissingFieldCount/coverage.totalCells*1000)/10;
const researchFields=report.trials.flatMap(t=>t.fields).filter(f=>f.evidenceStatus!=='NOT_APPLICABLE');
coverage.applicableResearchFieldCount=researchFields.length;
coverage.sourceVerifiedResearchFieldCount=researchFields.filter(f=>f.evidenceVerified).length;
coverage.fieldEvidenceCompletionPercent=Math.round(coverage.sourceVerifiedResearchFieldCount/researchFields.length*1000)/10;
coverage.fullyPopulatedResearchTrials=report.trials.filter(t=>t.fields.every(f=>f.evidenceVerified||f.evidenceStatus==='NOT_APPLICABLE')).length;
coverage.partialResearchTrials=report.trials.filter(t=>t.fields.some(f=>f.evidenceVerified)&&t.fields.some(f=>!f.evidenceVerified&&f.evidenceStatus!=='NOT_APPLICABLE')).length;
coverage.unavailableResearchTrials=report.trials.filter(t=>!t.fields.some(f=>f.evidenceVerified)).length;
coverage.factorCoverage=report.trials[0].clinicalFactors.map(f=>({id:f.id,name:f.name,numericallyScored:report.trials.filter(t=>t.clinicalFactors.find(x=>x.id===f.id).grade!==null).length,pending:report.trials.filter(t=>{const x=t.clinicalFactors.find(x=>x.id===f.id);return x.grade===null&&x.evidenceState!=='BLOCKED_RULE'}).length,blocked:report.trials.filter(t=>t.clinicalFactors.find(x=>x.id===f.id).evidenceState==='BLOCKED_RULE').length}));
coverage.blockers=report.trials.flatMap(t=>t.clinicalFactors.filter(f=>f.grade===null).map(f=>({nctId:t.nctId,metricId:f.id,state:f.evidenceState,blocker:f.blocker})));
fs.writeFileSync(path.join(dir,'coverage.json'),JSON.stringify(coverage,null,2)+'\n');
for(const [format,file] of [['csv','bottom-research-190.csv'],['metrics','bottom-metric-dispositions.csv'],['facts','bottom-reviewed-facts.csv'],['rating-evidence','bottom-clinical-ratings.csv']])fs.writeFileSync(path.join(dir,file),bottomExport(format).replaceAll("\r\n","\n"));
const {csvCell}=require('../lib/bottom-only-exports.ts');
const csv=(headers,rows)=>[headers,...rows].map(r=>r.map(csvCell).join(',')).join('\n')+'\n';
fs.writeFileSync(path.join(dir,'bottom-missing-clinical-factors.csv'),csv(['nctId','metricId','state','blocker'],coverage.blockers.map(x=>[x.nctId,x.metricId,x.state,x.blocker])));
fs.writeFileSync(path.join(dir,'bottom-unreviewed-questions.csv'),csv(['nctId','question','state','observation','sourceUrl'],report.trials.flatMap(t=>t.questions.filter(q=>q.requiresFurtherReview).map(q=>[t.nctId,q.number,q.state,q.explanation,q.sourceUrl]))));
console.log(JSON.stringify(coverage,null,2));
