/** Current, explicitly exploratory RAAS *component* rating engine.
 * Does not generate overall RAAS, clinical probabilities, investment signals
 * or retroactive forecasts. Missing metrics are NEVER assigned a number.
 * The only defensible numeric pilot rule is sponsor readout-window specificity.
 */
import {parseRaasPilotFeed,type RaasObservation} from "./raas-score-engine";
import {parseProspectiveSourceBaselines} from "./raas-prospective-source-baselines";
import {provisionalTimingSpecificity,type ProvisionalMetricGrade} from "./raas-threshold-profiles";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import pilotData from "../data/raas-pilot-observations.json";
import prospectiveData from "../data/raas-prospective-source-baselines.json";

const pilot=parseRaasPilotFeed(pilotData);
const prospective=parseProspectiveSourceBaselines(prospectiveData);
const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
const norm=(s:string)=>s.trim().toLowerCase().replace(/\s+/g," ");
const related=(a:string,b:string)=>{
 const x=norm(a),y=norm(b);
 return !x||!y||x===y||(x.length>=5&&y.includes(x))||(y.length>=5&&x.includes(y));
};
export type RaasProvisionalTrialResult={
 readonly stage:RaasStage;
 readonly overallScore:null;
 readonly scoredMetrics:readonly ProvisionalMetricGrade[];
 readonly scoredOf30:number;
 readonly unscoredOf30:number;
 readonly model:"EXPLORATORY_COMPONENTS_ONLY_NOT_VALIDATED";
 readonly asOf:string;
};
export const RAAS_PROVISIONAL_METRIC_RULE_VERSION="timing-specificity-exploratory-2026-11-02-v1";
/** Accept only a clear first-sentence sponsor window for THIS trial.
 * A later mention of another trial's readout must never be scored.
 */
export function firstSentenceReadoutWindow(valueText:string):string|null{
 const head=valueText.trim().split(/\.\s+/)[0]?.trim()||"";
 if(!head)return null;
 const spans=head.match(/\b(?:first|second) half of 20\d{2}\b|\bH[12]\s+20\d{2}\b|\bQ[1-4]\s+20\d{2}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20\d{2}\b/gi);
 if(!spans||spans.length!==1)return null;
 const w=spans[0].toLowerCase().replace(/\s+/g," ");
 const half=w.match(/^h([12]) (20\d{2})$/);
 if(half)return (half[1]==="1"?"First":"Second")+" half of "+half[2];
 const month=w.match(/^(jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec) (20\d{2})$/);
 if(month){
  const labels:Record<string,string>={jan:"January",feb:"February",mar:"March",apr:"April",jun:"June",jul:"July",aug:"August",sep:"September",sept:"September",oct:"October",nov:"November",dec:"December"};
  return labels[month[1]]+" "+month[2];
 }
 return w;
}
/** Unique NCT+listed issuer+stage is required; optional drug/indication may
 * disambiguate, but a mismatched full trial identity is rejected.
 */
function chooseUnique<T extends {nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage}>(
 rows:readonly T[],trial:{nctId:string;ticker:string;drug?:string;indication?:string},stage:RaasStage
):T|null{
 const matches=rows.filter(r=>r.nctId===trial.nctId&&same(r.ticker,trial.ticker)&&r.stage===stage&&
   related(trial.drug||"",r.drug)&&related(trial.indication||"",r.indication));
 return matches.length===1?matches[0]:null;
}
export function provisionalScoresForTrial(
 trial:{nctId:string;ticker:string;drug?:string;indication?:string},stage:RaasStage
):RaasProvisionalTrialResult{
 const grades:ProvisionalMetricGrade[]=[];
 const p=chooseUnique(pilot.records,trial,stage);
 const prospect=chooseUnique(prospective.records,trial,stage);
 if(stage==="pre"){
  // Prefer exact-identity observed pilot fact over duplicated source baseline.
  if(p){
   for(const obs of p.observations){
    if(obs.assessmentDate>pilot.sourceAsOf)continue;
    const grade=provisionalTimingSpecificity(obs,stage,"CURRENT");
    if(grade)grades.push(grade);
   }
  }
  if(grades.length===0&&prospect){
   for(const fact of prospect.observations){
    if(fact.kind!=="PHASE3_READOUT_GUIDANCE"||
      !fact.metricIds.includes("pre-4-1")||
      fact.sourcePublishedAt>prospective.sourceAsOf||
      fact.sourcePublishedAt>prospect.capturedOn)continue;
    const window=firstSentenceReadoutWindow(fact.valueText);
    if(!window)continue;
    const obs:RaasObservation={
     id:fact.id,metricIds:["pre-4-1"],kind:"readout_window",
     title:"Documented sponsor readout-window guidance",valueText:window,
     unit:"sponsor timeframe",assessmentDate:fact.sourcePublishedAt,
     measurementDate:fact.observedAsOf,sourceUrl:fact.sourceUrl,
     method:"As-of captured issuer/SEC readout guidance; first sentence only",
     note:"Timing specificity, not likelihood of meeting the date or investment appreciation"
    };
    const grade=provisionalTimingSpecificity(obs,stage,"CURRENT");
    if(grade)grades.push(grade);
   }
  }
 }
 // All other 59 metrics lack predeclared source-validated numeric rules.
 const dedup=[...new Map(grades.map(g=>[g.metricId,g])).values()];
 const valid=new Set(RAAS_METRIC_CATALOG[stage].flatMap(g=>g.metrics.map(m=>m.id)));
 const scoredMetrics=dedup.filter(g=>valid.has(g.metricId));
 return {stage,overallScore:null,scoredMetrics,
  scoredOf30:scoredMetrics.length,unscoredOf30:30-scoredMetrics.length,
  model:"EXPLORATORY_COMPONENTS_ONLY_NOT_VALIDATED",
  asOf:pilot.sourceAsOf};
}
