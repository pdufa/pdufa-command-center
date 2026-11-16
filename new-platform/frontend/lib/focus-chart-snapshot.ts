import archived from '../data/focus123EvidenceReadiness20261115.json';
import roster from '../data/p3PostDataActive.json';
import type {SurveyChartTrial} from '../app/FocusSurveyTrendChart';

/**
 * Source-verified FOCUS snapshot rendered in the FIRST server response.
 * The sign-in-gated current assessment API may replace it once reconciled.
 * Neither network/auth failure nor pending hydration should hide the graph.
 * Strictly documentary coverage only. Not FDA approval probabilities.
 */
export const FOCUS_CHART_SNAPSHOT_DATE=archived.generatedAt;
export const FOCUS_CHART_SNAPSHOT_ROSTER=archived.rosterId;
export const FOCUS_CHART_SNAPSHOT_METHOD=archived.formula;

export const FOCUS_CHART_SNAPSHOT_TRIALS:SurveyChartTrial[]=(()=>{
 if(archived.schemaVersion!==1||archived.trials!==32||archived.reports!==96||
   archived.rows.length!==96||roster.records.length!==32||
   archived.noApprovalProbabilities!==true||archived.noValidatedScientificScore!==true)
  return [];
 const grouped=new Map<string,typeof archived.rows>();
 for(const row of archived.rows){
  if(!/^NCT[0-9]{8}$/.test(row.nct)||![1,2,3].includes(row.level)||
    !row.runId||!row.executedAt||!row.reportHash||row.applicable<=0||
    row.sourceVerified<0||row.sourceVerified>row.applicable||
    row.checkCount-row.notYetExpected!==row.applicable||
    Math.round(100*row.sourceVerified/row.applicable)!==row.evidenceReadinessScore)return [];
  if(!grouped.has(row.nct))grouped.set(row.nct,[]);
  grouped.get(row.nct)!.push(row);
 }
 const rosterNcts=new Set(roster.records.map(t=>t.nct));
 if(rosterNcts.size!==32||grouped.size!==32||
   [...grouped].some(([nct,rows])=>!rosterNcts.has(nct)||rows.length!==3||
    new Set(rows.map(row=>row.level)).size!==3))return [];
 return roster.records.map(t=>{
  const rows=grouped.get(t.nct)!;
  const levels=Object.fromEntries(rows.map(row=>[String(row.level),{
   state:'COMPLETED',
   report:{
    nct:t.nct,level:row.level,runId:row.runId,executedAt:row.executedAt,
    engineVersion:archived.researchVersion+'/level-'+row.level,
    mode:'CURRENT_EVIDENCE',score:{kind:'NOT_VALIDATED',value:null},
    fdaPrediction:{outcome:'ABSTAIN'}
   },
   evidenceChecks:{total:row.checkCount,sourceVerified:row.sourceVerified,unresolved:row.unresolved}
  }]));
  return {nct:t.nct,ticker:t.ticker,company:t.company,levels};
 });
})();
