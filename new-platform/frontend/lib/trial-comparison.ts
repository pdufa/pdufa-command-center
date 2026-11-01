/** Evidence-first, read-only comparison of exact Pipeline study identities.
 * No composite score or FDA approval probability may be inferred from coverage.
 */
import {BENEFIT_GROUPS,benefitForTrial,type BenefitFeed,type BenefitFact} from "./benefit-assessments";
import type {PipelineResearchRow} from "./pipeline-research-view";

export type TrialComparisonField={id:string;label:string;fact:BenefitFact|null};
export type TrialComparisonGroup={rank:number;title:string;verified:number;modeled:number;fields:TrialComparisonField[]};
export type TrialComparisonSnapshot={
  groups:TrialComparisonGroup[];
  verified:number;
  modeled:number;
  required:number;
  evidenceDate:string|null;
  readiness:"PARTIAL_EVIDENCE"|"NOT_ASSESSED";
};

const clean=(v:string|null|undefined)=>(v||"").trim().toLowerCase();
export function trialComparisonKey(row:Pick<PipelineResearchRow,"nctId"|"ticker"|"drug"|"indication">):string{
  return [row.nctId,row.ticker,row.drug,row.indication].map(clean).join("|");
}

/** Historical post-Phase 3 screening, NOT a claim of current qualified FDA programs.
 * Require exact POOL match, a dated $300M-$10B cap, and identified issuer/drug/indication.
 */
export function screenComparisonCandidates(rows:readonly PipelineResearchRow[]):PipelineResearchRow[]{
  const seen=new Set<string>();
  return rows.filter(row=>{
    if(!row||!/^NCT\d{8}$/.test(row.nctId)||!clean(row.ticker)||!clean(row.drug)||!clean(row.indication)
      ||row.poolStatus!=="EXACT_MATCH"||row.postPhase3Evidence!=="REGISTRY_COMPLETED"
      ||!Number.isFinite(row.capUsd)||row.capUsd<300_000_000||row.capUsd>10_000_000_000
      ||!/^\d{4}-\d{2}-\d{2}$/.test(row.capAsOf||"")
      ||row.qualification==="REJECTED"||row.qualification==="EXCLUDED")return false;
    const key=trialComparisonKey(row);
    if(seen.has(key))return false;
    seen.add(key);
    return true;
  }).sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
}

/** Readiness counts independently sourced facts only. Missing is never a score of zero. */
export function comparisonSnapshot(row:PipelineResearchRow,feed:BenefitFeed|null):TrialComparisonSnapshot{
  const record=benefitForTrial(feed,{
    nctId:row.nctId,ticker:row.ticker,drug:row.drug||"",indication:row.indication||""
  });
  const groups=BENEFIT_GROUPS.map(group=>{
    const fields=group.fields.map(f=>({id:f.id,label:f.label,fact:record?.facts[f.id]||null}));
    return {rank:group.number,title:group.name,
      verified:fields.filter(f=>f.fact?.status==="VERIFIED").length,
      modeled:fields.filter(f=>f.fact?.status==="MODELED").length,fields};
  });
  const verified=groups.reduce((sum,g)=>sum+g.verified,0);
  const modeled=groups.reduce((sum,g)=>sum+g.modeled,0);
  const required=groups.reduce((sum,g)=>sum+g.fields.length,0);
  return {groups,verified,modeled,required,evidenceDate:feed?.sourceAsOf||null,
    readiness:verified>0?"PARTIAL_EVIDENCE":"NOT_ASSESSED"};
}

/** Same indication alone does not establish comparable endpoint, trial design or treatment line. */
export function comparisonCaveat(rows:readonly PipelineResearchRow[]):string{
  if(rows.length<2)return "Choose at least two distinct study records.";
  if(new Set(rows.map(r=>clean(r.indication))).size>1)
    return "Different indications: do not compare raw endpoint results or infer clinical superiority across diseases.";
  return "Matching indication does not prove matching treatment line, endpoints, populations or head-to-head evidence.";
}
