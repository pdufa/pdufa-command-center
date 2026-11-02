/** Provisional RAAS threshold calibration and first pilot grading rule.
 * Unlike a validated RAAS investment score, this measures the specificity
 * of dated readout guidance. It MUST NOT enter overall RAAS aggregation.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {observationsForTrial,type RaasObservation,type RaasPilotFeed,type Snapshot} from "./raas-score-engine";

export type ThresholdState="BENCHMARK_REQUIRED"|"PROVISIONAL_NOT_CALIBRATED";
export type RaasThresholdProfile={
 metricId:string;stage:RaasStage;category:string;
 status:ThresholdState;benchmarkRequired:string;minimumInputs:string;
 direction:"higher_is_better"|"lower_is_better"|"case_specific";
 approvedForComposite:false;
};
export type ProvisionalMetricGrade={
 metricId:string;stage:RaasStage;snapshot:Snapshot;score:0|25|50|75|100;
 ruleId:string;kind:"RESEARCH_ONLY_NOT_VALIDATED";observationId:string;
 sourceUrl:string;sourceDate:string;
 label:string;inputs:string;explanation:string;limitations:string;
};
const evidenceByCategory:Record<string,{minimumInputs:string;benchmarkRequired:string;direction:RaasThresholdProfile["direction"]}>={
 scientific:{minimumInputs:"Human efficacy estimates, uncertainty, prespecified design, independent safety and confounder review",benchmarkRequired:"Disease-specific clinically important outcomes and reference therapy benchmarks",direction:"case_specific"},
 valuation:{minimumInputs:"Timestamped adjusted stock price, fully diluted shares, net cash/debt, realistic three-case exit scenarios",benchmarkRequired:"Precommitted catalyst-window valuation and probabilistic return calibration",direction:"case_specific"},
 downside:{minimumInputs:"SEC financing and cash data, severe-event scenarios, liquidity and loss distributions",benchmarkRequired:"Historically calibrated tail-loss and financing reference distributions",direction:"lower_is_better"},
 timing:{minimumInputs:"Current source-backed readout/PDUFA target, time-to-exit and trading calendar",benchmarkRequired:"Historical sponsor timing accuracy, early-announcement risk and viable exit windows",direction:"case_specific"},
 medical:{minimumInputs:"Matched indication and treatment line, patient-important effects, safety and relevant comparator",benchmarkRequired:"Disease/endpoint-specific minimal important change and comparator-normalized assessment",direction:"case_specific"},
 execution:{minimumInputs:"Position-size-aware spread, volume, volatility, slippage and correlation data",benchmarkRequired:"Execution-cost and gap-risk distribution at specified portfolio size",direction:"lower_is_better"},
 clinical:{minimumInputs:"Full pivotal outcome effect, interval, protocol/analysis plan, safety and replication",benchmarkRequired:"Endpoint-specific medically meaningful effects and regulatorily relevant evidence standards",direction:"case_specific"},
 fda:{minimumInputs:"Exact application identity, official acceptance/PDUFA source, clinical/CMC/safety review status",benchmarkRequired:"FDA pathway-specific review risk and source-vetted remaining uncertainties",direction:"case_specific"},
 market:{minimumInputs:"Label-eligible population, payer coverage, comparators, net price and adoption forecasts",benchmarkRequired:"Comparable indications, payer data and conservative commercial sensitivity models",direction:"case_specific"}
};
const sectionKey=(stage:RaasStage,index:number)=>{
 const top=["scientific","valuation","downside","timing","medical","execution"];
 const bottom=["clinical","valuation","fda","downside","market","timing"];
 return (stage==="pre"?top:bottom)[index];
};
export const RAAS_THRESHOLD_PROFILES:readonly RaasThresholdProfile[]=
 (["pre","post"] as const).flatMap(stage=>RAAS_METRIC_CATALOG[stage].flatMap((cat,index)=>{
  const def=evidenceByCategory[sectionKey(stage,index)];
  return cat.metrics.map(metric=>({
   metricId:metric.id,stage,category:cat.name,
   status:metric.id==="pre-4-1"?"PROVISIONAL_NOT_CALIBRATED" as const:"BENCHMARK_REQUIRED" as const,
   minimumInputs:metric.requiredEvidence+"; "+def.minimumInputs,
   benchmarkRequired:metric.scoreRule+"; "+def.benchmarkRequired,
   direction:def.direction,
   approvedForComposite:false as const
  }));
 }));
export function thresholdProfile(stage:RaasStage,metricId:string):RaasThresholdProfile|null{
 return RAAS_THRESHOLD_PROFILES.find(x=>x.stage===stage&&x.metricId===metricId)||null;
}
/** A narrow proof-of-calculation: more specific sponsor guidance means
 * a more precise RESEARCH window. It is NOT a predicted stock return, a
 * readout success probability, or approved RAAS category grade.
 */
export function provisionalTimingSpecificity(
 obs:RaasObservation,stage:RaasStage,snapshot:Snapshot
):ProvisionalMetricGrade|null{
 if(stage!=="pre"||snapshot!=="CURRENT"||obs.kind!=="readout_window"||
    !obs.metricIds.includes("pre-4-1")||!obs.valueText||
    !/^https:\/\/[^\s/]+\/\S+/.test(obs.sourceUrl)||!/^\d{4}-\d{2}-\d{2}$/.test(obs.assessmentDate))
    return null;
 const t=obs.valueText.trim().toLowerCase();
 let score:ProvisionalMetricGrade["score"]|null=null;
 let precision="";
 if(/^(first|second) half of 20\d{2}$/.test(t)){score=50;precision="Six-month sponsor guidance window";}
 else if(/^q[1-4] 20\d{2}$/.test(t)){score=75;precision="Quarter-year sponsor guidance window";}
 else if(/^[a-z]+ 20\d{2}$/.test(t)){score=100;precision="Single-month sponsor guidance window";}
 else if(/^20\d{2}$/.test(t)){score=25;precision="Calendar-year sponsor guidance window";}
 // Unknown wordings are not forced into any band.
 if(score===null)return null;
 return {metricId:"pre-4-1",stage,snapshot,score,
  ruleId:"timing-specificity-exploratory-2026-11-02-v1",
  kind:"RESEARCH_ONLY_NOT_VALIDATED",observationId:obs.id,sourceUrl:obs.sourceUrl,
  sourceDate:obs.assessmentDate,label:"Readout window specificity (research only)",
  inputs:obs.valueText,explanation:precision+
   ". Predeclared exploratory bands: calendar year 25, half-year 50, quarter 75, single month 100. A precise window is NOT evidence that it will be met.",
  limitations:"Not calibrated against real sponsor timing errors or stock returns; excludes early announcement and exit buffer risk. Never contributes to category or overall RAAS."};
}
export function provisionalGradesForTrial(
 feed:RaasPilotFeed,trial:{nctId:string;ticker:string;drug:string;indication:string},
 stage:RaasStage,snapshot:Snapshot,asOf:string
):ProvisionalMetricGrade[]{
 if(snapshot!=="CURRENT")return [];
 return observationsForTrial(feed,trial,stage,asOf)
  .map(o=>provisionalTimingSpecificity(o,stage,snapshot))
  .filter((g):g is ProvisionalMetricGrade=>g!==null);
}
