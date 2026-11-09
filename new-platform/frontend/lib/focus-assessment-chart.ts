/**
 * Read-only presentation data for the ASSESMENTS tab.
 * Evidence-check proportions are NOT clinical assessment completion, FDA
 * outcome probabilities, or predictive accuracy.
 */
import {FOCUS_FINAL_TRIAL_AUDIT} from "./focus-final-gate-checks";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE} from "./focus-specialty-assessment";

export type EvidencePieSlice = {
  key:"verified"|"pointer"|"review"|"missing";
  label:string;
  value:number;
  color:string;
};
export type EvidencePieCounts = {
  verified:number;
  pointer:number;
  review:number;
  missing:number;
};
export type LatestReleasedTrial = {
  ticker:string;
  nct:string;
  releasedAt:string;
  decision:string;
  counts:EvidencePieCounts;
};
export type PublishedPredictionCandidate = {
  nct:string;
  ticker:string;
  prediction:string;
  certainty:string;
  releasedAt?:string|null;
  releaseStatus?:string|null;
};

export const evidencePieSlices = (counts:EvidencePieCounts):EvidencePieSlice[] => [
  {key:"verified",label:"Independently verified",value:counts.verified,color:"#168a6d"},
  {key:"pointer",label:"Recorded source pointers",value:counts.pointer,color:"#317bb1"},
  {key:"review",label:"Source review required",value:counts.review,color:"#db9c35"},
  {key:"missing",label:"Missing evidence",value:counts.missing,color:"#97a5b1"},
];

const isoTimestamp=(value:unknown):value is string=>
  typeof value==="string"&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)&&
  Number.isFinite(Date.parse(value));

/** Do not confuse a completed source scan with an explicitly published forecast. */
export function findLatestReleasedTrial(
  candidates:readonly PublishedPredictionCandidate[],
  audit=FOCUS_FINAL_TRIAL_AUDIT
):LatestReleasedTrial|null {
  const ordered=candidates.filter(row=>
    row.releaseStatus==="PUBLISHED"&&
    row.prediction!=="ABSTAIN"&&
    row.certainty!=="NOT_VALIDATED"&&
    isoTimestamp(row.releasedAt)
  ).sort((a,b)=>Date.parse(b.releasedAt!)-Date.parse(a.releasedAt!));
  for(const item of ordered){
    const gate=audit.rows.find(row=>row.nct===item.nct&&row.ticker===item.ticker);
    if(!gate)continue;
    return {
      nct:item.nct,ticker:item.ticker,releasedAt:item.releasedAt!,
      decision:item.prediction,
      counts:{verified:gate.independentlyVerified,pointer:gate.pointers,review:gate.review,missing:gate.missing}
    };
  }
  return null;
}

export function getAssessmentPieData(){
  const audit=FOCUS_FINAL_TRIAL_AUDIT;
  return {
    asOf:audit.asOf,
    totalTrials:audit.trialCount,
    totalChecks:audit.totalChecks,
    overall:evidencePieSlices({
      verified:audit.independentlyVerified,
      pointer:audit.pointers,
      review:audit.review,
      missing:audit.missing
    }),
    // The current intake is research-only, ABSTAIN, NOT_VALIDATED and has
    // no published-release timestamps. Never substitute a source revision.
    latest:findLatestReleasedTrial(FOCUS_SPECIALTY_ASSESSMENT_QUEUE),
  };
}
