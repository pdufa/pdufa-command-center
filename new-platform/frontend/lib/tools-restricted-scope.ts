/**
 * Shared TOOLS research gate. Both Phase and FDA facets, the opening grid,
 * the filtered grid and CSV MUST use precisely this SAME trial universe.
 *
 * A dated research census establishes only a provisional $300M–$10B sponsor
 * cap screen and registry-completed Phase 3 identity, NOT current/complete
 * PIPELINE qualification, FDA rights or a verified upcoming PDUFA date.
 */
import {isPoolTrial,normalizePoolStage,poolStageStatistics,type PostPhase3Review} from "./pool-pipeline-funnel";
import type {verifiedToolPool} from "./tools-pool-inventory";

type Snapshot=ReturnType<typeof verifiedToolPool>;
export const TOOL_MIN_CAP_USD=300_000_000;
export const TOOL_MAX_CAP_USD=10_000_000_000;
export type RestrictedToolsScope={
  scope:"DATED_300M_10B_COMPLETED_PHASE3_RESEARCH_SCREEN";
  qualification:"NOT_VERIFIED";
  censusAsOf:string;
  originalPoolTrials:number;
  screenedTrials:number;
  /** Still requiring current cap, listing, rights, filing and PDUFA verification. */
  outstanding:["CURRENT_CAP_AND_LISTING","PIVOTAL_AND_RIGHTS","PDUFA_TARGET_AND_STATUS"];
};
export function restrictedToolsSnapshot(
  snapshot:Snapshot,reviews:readonly PostPhase3Review[],censusAsOf:string
):{snapshot:Snapshot;scope:RestrictedToolsScope}{
  if(!reviews.length||!Number.isFinite(Date.parse(censusAsOf)))
    throw Error("RESTRICTED_PIPELINE_CENSUS_UNAVAILABLE");
  const eligibleIds=new Set<string>();
  for(const row of reviews){
    if(row.poolStatus!=="EXACT_MATCH"||
       row.postPhase3Evidence!=="REGISTRY_COMPLETED"||
       row.qualification!=="NEEDS_REVIEW"||
       !Number.isFinite(row.capUsd)||
       row.capUsd<TOOL_MIN_CAP_USD||row.capUsd>TOOL_MAX_CAP_USD||
       !row.capAsOf||!Number.isFinite(Date.parse(row.capAsOf)))continue;
    eligibleIds.add("TRIAL|"+row.nctId+"|"+row.ticker.toUpperCase());
  }
  const poolRows=snapshot.poolRows.filter(row=>
    isPoolTrial(row)&&["Phase 3","Phase 3 Results"].includes(normalizePoolStage(row.stage))&&
    eligibleIds.has(row.id+"|"+row.ticker.toUpperCase()));
  const stageStats=poolStageStatistics(poolRows);
  // If the historical census and current published POOL cannot produce even
  // one exact completed Phase 3 match, this is a source-reconciliation failure,
  // not proof the investable research universe has zero trials.
  if(stageStats.trials===0)throw Error("RESTRICTED_PIPELINE_EXACT_MATCH_UNAVAILABLE");
  const scope:RestrictedToolsScope={
    scope:"DATED_300M_10B_COMPLETED_PHASE3_RESEARCH_SCREEN",
    qualification:"NOT_VERIFIED",
    censusAsOf,
    originalPoolTrials:snapshot.stageStats.trials,
    screenedTrials:stageStats.trials,
    outstanding:["CURRENT_CAP_AND_LISTING","PIVOTAL_AND_RIGHTS","PDUFA_TARGET_AND_STATUS"]
  };
  return {
    snapshot:{...snapshot,poolRows,stageStats},
    scope
  };
}
