/** Reproducible source-readiness audit across the FULL market-cap-screened TOOLS
 * trial inventory. This is research triage, not FDA eligibility or a stock rank.
 * Do not equate registry completion, a dated readout, or evidence coverage with
 * clinical superiority, an approved label, trade eligibility, or FDA action.
 */
import {COMPETITIVE_STRATEGY_TOPICS} from "./tools-competitive-strategy";
import {benefitForTrial,type BenefitFeed,type BenefitFact} from "./benefit-assessments";
import {pipelineDayCounts,type TimelineDates} from "./pipeline-timeline";

export type CompetitiveResearchTrial={
  nctId:string;ticker:string;drug:string;indication:string;stage:string;
  timeline?:TimelineDates|null;
};
export type ReadoutWindowStatus=
  "NO_VERIFIED_PUBLIC_READOUT"|"PDUFA_DATE_UNVERIFIED"|
  "RESEARCH_WINDOW_OPEN"|"PDUFA_CUTOFF_REACHED";
export type CompetitiveEvidenceStatus=
  "NOT_ASSESSED"|"PARTIAL_EVIDENCE"|"EVIDENCE_REVIEW_READY";
export type CompetitiveTopicCoverage={
  key:typeof COMPETITIVE_STRATEGY_TOPICS[number]["key"];
  verified:number;modeled:number;missing:number;
  sources:{field:string;status:BenefitFact["status"];sourceUrl:string;sourceDate:string}[];
};
export type CompetitiveReadiness={
  status:ReadoutWindowStatus;daysSinceReadout:number|null;daysToPdufa:number|null;
  evidence:CompetitiveEvidenceStatus;verifiedTopics:number;modeledTopics:number;
  topics:CompetitiveTopicCoverage[];
  readyToRank:false; // must not infer quantitative competitive rankings from coverage
  reasons:string[];
};
/** This function is source-driven, independent of user-selected filter categories. */
export function competitiveReadiness(
  row:CompetitiveResearchTrial,today:string,feed:BenefitFeed|null=null
):CompetitiveReadiness{
  const exact=/^NCT\d{8}$/.test(row.nctId)&&!!row.ticker.trim()&&
    !!row.drug.trim()&&!!row.indication.trim();
  const timing=pipelineDayCounts(row.timeline||{phase3DataRelease:null,pdufaTarget:null},today);
  const hasReadout=exact&&timing.daysSincePhase3Release!==null;
  const status:ReadoutWindowStatus=!hasReadout?"NO_VERIFIED_PUBLIC_READOUT":
    timing.daysToPdufa===null?"PDUFA_DATE_UNVERIFIED":
    timing.daysToPdufa<=3?"PDUFA_CUTOFF_REACHED":"RESEARCH_WINDOW_OPEN";
  const record=hasReadout?benefitForTrial(feed,row):null;
  const topics:CompetitiveTopicCoverage[]=COMPETITIVE_STRATEGY_TOPICS.map(topic=>{
    const sources=topic.fields.flatMap(field=>{
      const fact=record?.facts[field];
      return fact?[{field,status:fact.status,sourceUrl:fact.sourceUrl,sourceDate:fact.sourceDate}]:[];
    });
    return {key:topic.key,verified:sources.filter(x=>x.status==="VERIFIED").length,
      modeled:sources.filter(x=>x.status==="MODELED").length,
      missing:topic.fields.length-sources.length,sources};
  });
  const verifiedTopics=topics.filter(t=>t.verified>0).length;
  const modeledTopics=topics.filter(t=>t.verified===0&&t.modeled>0).length;
  const evidence:CompetitiveEvidenceStatus=verifiedTopics===0&&modeledTopics===0
    ?"NOT_ASSESSED":verifiedTopics===topics.length
    ?"EVIDENCE_REVIEW_READY":"PARTIAL_EVIDENCE";
  const reasons:string[]=[];
  if(!exact)reasons.push("Exact NCT, issuer, drug or indication identity missing");
  if(!hasReadout)reasons.push("No exact-program source-verified public Phase 3 release date; registry completion is insufficient");
  if(status==="PDUFA_DATE_UNVERIFIED")reasons.push("Exact-program PDUFA target not verified; still in research queue");
  if(status==="PDUFA_CUTOFF_REACHED")reasons.push("At or beyond three days before PDUFA; outside requested trading-research window");
  if(evidence==="NOT_ASSESSED")reasons.push("No source-verified or explicitly modeled CS topic inputs in the reconciled research feed");
  if(verifiedTopics<topics.length)reasons.push("Some competitive-strategy topics lack verified evidence");
  reasons.push("Product rights, comparator relevance and current trade qualification require separate review");
  return {status,daysSinceReadout:hasReadout?timing.daysSincePhase3Release:null,
    daysToPdufa:hasReadout?timing.daysToPdufa:null,evidence,verifiedTopics,modeledTopics,
    topics,readyToRank:false,reasons};
}

export type CompetitivePopulationScan={
  scope:"FULL_RESTRICTED_TOOLS_POOL";populationCount:number;sourceDate:string;
  verifiedPublicReadouts:number;openResearchWindow:number;unknownPdufa:number;
  pastResearchCutoff:number;withoutVerifiedReadout:number;
  /** A recorded public release does not establish a complete results dataset. */
  evidenceCoverage:"NOT_COMPUTED_FOR_FULL_POOL"|"SOURCE_INPUT_AUDIT_IN_WINDOW";
  /** Exact-NCT source facts in the verified public-readout to PDUFA-3 research
   * window; six topic slots per candidate. NOT treatment-effect or stock ranks. */
  topicSourceAudit:{
    eligibleTrials:number;topicSlots:number;verifiedSlots:number;
    modeledOnlySlots:number;missingSlots:number;verifiedPercent:number|null;
    trialsWithSixVerifiedTopics:number;sourceFeedAsOf:string|null;
  }|null;
  qualification:"NOT_VERIFIED";
};
/** Compute the census from ALL restricted rows, never merely 50 visible trials. */
export function scanCompetitivePopulation(
  rows:readonly CompetitiveResearchTrial[],today:string,sourceDate:string,
  feed:BenefitFeed|null=null
):CompetitivePopulationScan{
  const counts={verifiedPublicReadouts:0,openResearchWindow:0,unknownPdufa:0,
    pastResearchCutoff:0,withoutVerifiedReadout:0};
  const audited={verifiedSlots:0,modeledOnlySlots:0,missingSlots:0,
    trialsWithSixVerifiedTopics:0};
  const ids=new Set<string>();
  for(const row of rows){
    if(ids.has(row.nctId))throw Error("DUPLICATED_COMPETITIVE_TRIAL_ID");
    ids.add(row.nctId);
    const readiness=competitiveReadiness(row,today,feed);
    const status=readiness.status;
    if(status==="NO_VERIFIED_PUBLIC_READOUT")counts.withoutVerifiedReadout++;
    else {
      counts.verifiedPublicReadouts++;
      if(status==="PDUFA_DATE_UNVERIFIED")counts.unknownPdufa++;
      else if(status==="PDUFA_CUTOFF_REACHED")counts.pastResearchCutoff++;
      else {
        counts.openResearchWindow++;
        if(feed){
          const verified=readiness.topics.filter(topic=>topic.verified>0).length;
          audited.verifiedSlots+=verified;
          audited.modeledOnlySlots+=readiness.topics.filter(
            topic=>topic.verified===0&&topic.modeled>0).length;
          audited.missingSlots+=readiness.topics.filter(
            topic=>topic.verified===0&&topic.modeled===0).length;
          if(verified===COMPETITIVE_STRATEGY_TOPICS.length)
            audited.trialsWithSixVerifiedTopics++;
        }
      }
    }
  }
  const topicSlots=counts.openResearchWindow*COMPETITIVE_STRATEGY_TOPICS.length;
  if(feed&&audited.verifiedSlots+audited.modeledOnlySlots+
    audited.missingSlots!==topicSlots)throw Error("COMPETITIVE_SOURCE_AUDIT_PARITY_FAILED");
  const topicSourceAudit=feed?{
    eligibleTrials:counts.openResearchWindow,topicSlots,...audited,
    verifiedPercent:topicSlots?Math.round(audited.verifiedSlots/topicSlots*1000)/10:null,
    sourceFeedAsOf:feed.sourceAsOf
  }:null;
  return {scope:"FULL_RESTRICTED_TOOLS_POOL",populationCount:rows.length,
    sourceDate,...counts,
    evidenceCoverage:feed?"SOURCE_INPUT_AUDIT_IN_WINDOW":"NOT_COMPUTED_FOR_FULL_POOL",
    topicSourceAudit,qualification:"NOT_VERIFIED"};
}
