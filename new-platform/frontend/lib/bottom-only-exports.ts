import {bottomOnlyReport,bottomOnlySummary} from './bottom-only-completion';
import scoreHistory from '../data/bottomOnlyScoreHistory20261107.json';
import researchHistory from '../data/bottomOnlyResearchHistory20261107.json';
import sharedHistory from '../data/raas-trial-score-history.json';
export function bottomTrialHistory(nctId:string){
 const shared=sharedHistory.records.filter(r=>r.nctId===nctId).map(r=>({
  ...r,eventType:r.kind,note:r.summary,historyOrigin:'PRESERVED_SHARED_CROSS_STAGE',
  legacyScore:r.score,legacyScoreKind:r.scoreKind,
  metricGrades:(('metricGrades' in r?r.metricGrades:[])??[]).map(g=>({
   ...g,id:g.metricId,grade:g.score,observedResult:g.inputs,
   sourceUrl:g.sourceUrl
  }))
 }));
 return [...researchHistory.records,...scoreHistory.records,...shared].filter(r=>r.nctId===nctId);
}
export function bottomSummary(allowedNcts?:ReadonlySet<string>){
 const {trials,headers,...summary}=bottomOnlyReport();
 const selected=trials.filter(t=>!allowedNcts||allowedNcts.has(t.nctId));
 return {...summary,
  scope:allowedNcts?'CANONICAL_ACTIVE_BOTTOM_ONLY':summary.scope,
  preservedResearchTrialCount:trials.length,trialCount:selected.length,
  activeMatchedResearchCount:selected.length,
  allFieldsAccounted:selected.filter(t=>t.fields.length===headers.length).length,
  allMetricsEvaluated:selected.filter(t=>t.metrics.length===30).length,
  activeFactorCount:selected.length*5,
  activeFactorsScored:selected.reduce((n,t)=>n+t.clinicalScoredFactors,0),
  completeClinicalOverallScores:selected.filter(t=>t.clinicalFullScore!==null).length,
  sourceBackedQuestionCount:selected.reduce((n,t)=>n+t.sourceBackedQuestions,0),
  totalQuestionCount:selected.length*30,
  unresolvedQuestionCount:selected.reduce((n,t)=>n+t.sourceGaps,0),
  rows:selected.map(bottomOnlySummary)};
}
export function csvCell(value:unknown){
 let text=value===null||value===undefined?'':typeof value==='object'?JSON.stringify(value):String(value);
 if(/^\s*[=+@-]/.test(text))text="'"+text;
 return '"'+text.replaceAll('"','""')+'"';
}
export function bottomExport(format:string,allowedNcts?:ReadonlySet<string>){
 const report=bottomOnlyReport();
 if(allowedNcts)report.trials=report.trials.filter(t=>allowedNcts.has(t.nctId));
 let headers:string[],rows:unknown[][];
 if(format==='csv'){
  headers=report.headers;rows=report.trials.map(t=>t.fields.map(f=>f.exportValue));
 }else if(format==='facts'){
  headers=['nctId','question','classification','evidence','criticalLimit','sourceUrl','sourceDate'];
  rows=report.trials.flatMap(t=>t.additionalReviewedFacts.map(f=>headers.map(k=>f[k as keyof typeof f])));
 }else if(format==='metrics'){
  headers=['nctId','metricId','name','activeClinicalWeightPercent','grade','finding','state','sourceUrl','sourceDate','observedResult','benchmarkContext','uncertaintyReview','criticalRiskReview'];
  rows=report.trials.flatMap(t=>t.metrics.map(m=>[t.nctId,m.id,m.name,m.activeClinicalWeightPercent,m.score,m.finding,m.state,m.sourceUrl,m.sourceDate,m.observedResult,m.benchmarkContext,m.uncertaintyReview,m.criticalRiskReview]));
 }else if(format==='rating-evidence'){
  headers=['nctId','metricId','name','grade','weightPercent','combinedFiveFactorScore','evidenceState','blocker','observedResult','benchmarkContext','uncertaintyReview','criticalRiskReview','sourceUrl','benchmarkSourceUrl','sourceDate','assessedAt','reviewEvidence'];
  rows=report.trials.flatMap(t=>t.clinicalFactors.map(f=>[t.nctId,f.id,f.name,f.grade,20,t.clinicalFullScore,f.evidenceState,f.blocker,f.observedResult,f.benchmarkContext,f.uncertaintyReview,f.criticalRiskReview,f.sourceUrl,f.benchmarkSourceUrl,f.sourceDate,f.assessedAt,f.reviewEvidence]));
 }else throw Error('UNKNOWN_BOTTOM_EXPORT');
 return '\uFEFF'+[headers,...rows].map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
}
