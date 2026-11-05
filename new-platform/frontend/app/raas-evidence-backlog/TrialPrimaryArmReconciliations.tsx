"use client";
import type {PrimaryContrastReconciliation,
 PrimaryContrastReconciliationLedger} from "../../lib/raas-primary-arm-reconciliation";

const pretty=(v:number|null)=>v===null?"N/A":String(v);
export default function TrialPrimaryArmReconciliations({
 nctId,records,summary
}:{nctId:string;records:readonly PrimaryContrastReconciliation[];
 summary:Pick<PrimaryContrastReconciliationLedger,"eligibleRawArmChecks"|"rawArmDiscrepancies">}){
 const discrepant=records.filter(x=>x.signal==="ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW");
 const evaluable=records.filter(x=>x.rawDifferenceEligible);
 return <details data-raas-arm-reconciliation={nctId}
  style={{border:"1px solid #b8d3c8",borderRadius:8,padding:10,background:"#f8fbf9"}}>
  <summary style={{cursor:"pointer",fontWeight:750,color:"#1b5b3e",fontSize:12}}>
   Reconcile original outcome arms ▸ {records.length} primary comparisons
   {" "}· {evaluable.length} raw mean-difference checks
   {" "}· {discrepant.length} require estimand review
  </summary>
  <div style={{display:"grid",gap:10,fontSize:12,lineHeight:1.6,paddingTop:10}}>
   <p style={{margin:0}}>Each comparison is tied to this exact NCT and to
    the original ClinicalTrials.gov <strong>OG</strong> outcome group names
    and numbers. Where applicable, we show the numerical first-arm-minus-second-arm
    difference alongside the reported estimate, allowing either effect direction.
    Source rows with repeated OG IDs are <strong>not reduced to the final row</strong>.
    Mismatch is only a <strong>review signal</strong>: adjusted models, time points,
    differing estimands, and rounding can explain differences. No automatic
    efficacy judgment, treatment ranking, statistical conclusion or RAAS score.</p>
   <p style={{margin:0,color:"#496b57"}}>
    This trial card displays {records.length} of the global comparison set.
    Global raw-difference eligibility: {summary.eligibleRawArmChecks};
    global numerical discrepancies to examine: {summary.rawArmDiscrepancies}.
    For source tables, open each exact NCT link.</p>
   {records.length===0&&<p>There are no saved primary statistical contrasts
    for this NCT. Protocol and result gaps remain unscored.</p>}
   {records.slice(0,35).map(x=><div key={x.id}
    data-raas-primary-arm-comparison={x.id}
    style={{padding:"10px",border:"1px solid #d5e5dc",borderRadius:6,background:"white"}}>
    <strong>{x.outcomeTitle||"Untitled primary outcome"}</strong>
    <div>Time frame: {x.outcomeTimeFrame||"not recorded"};
     unit: {x.outcomeUnit||"unspecified"}</div>
    {x.groupIds.map((g,i)=><div key={g}>
     <strong>{g}</strong> · {x.groupNames[i]} ·
     {x.groupMeasurementSeries[i]?.length>1?
      "multiple source rows ("+x.groupMeasurementSeries[i].join(", ")+
       ") — time point/category not retained in compact index":
      "source arm measurement "+pretty(x.groupValues[i])+" "+x.outcomeUnit}
    </div>)}
    <div>Reported statistic: {x.reportedStatisticType||"not identified"}
     {" "}· {x.reportedStatisticRaw||"not numeric"}
     {x.reportedCILower!==null&&x.reportedCIUpper!==null?
      " · CI ["+x.reportedCILower+", "+x.reportedCIUpper+"]":""}
     {x.pValueRaw?" · p = "+x.pValueRaw:""}</div>
    {x.observedFirstMinusSecond!==null&&<div>
     Raw first-minus-second arm measurement: {pretty(x.observedFirstMinusSecond)}
     {" "}· units as recorded. This is not necessarily the reported adjusted
     treatment effect.</div>}
    <div><strong>Reconciliation:</strong>{" "}

     {x.signal==="AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS"?
      "Multiple outcome rows share the same OG identifiers; the compact source loses their time-point/category labels. No arbitrary last or first value can be used as the primary analysis statistic.":
      x.signal==="COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS"?
      "Endpoint reports participant responder counts, while its contrast is a difference in proportions. Use exact per-arm efficacy denominators, not count subtraction.":
      x.signal==="ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED"?
      "The displayed arm values are rounded; their last-decimal rounding uncertainty can account for the numerical difference. Confirm the model before final review.":
      x.signal==="ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW"?
      "Raw arm difference differs from the reported mean-difference statistic; check model, estimand, arm order and source precision.":
      x.signal==="ARM_DELTA_NEAR_REPORTED_VALUE_STILL_UNREVIEWED"?
      "Reported estimate numerically resembles an arm difference in either direction; clinical review still required.":
      x.signal==="STATISTIC_NOT_RAW_MEAN_DIFFERENCE"?
      "Reported statistic is not an additive mean difference; do not compare by raw subtraction.":
      x.signal==="NO_NUMERIC_REPORTED_STATISTIC"?
      "Reported numeric contrast is unavailable; do not infer it from group measurements.":
      "Exact two-arm numeric reconstruction is unavailable; validate the full original registry tables."}
     {x.absoluteGapToEitherDirection!==null?
      " Absolute gap to either direction: "+pretty(x.absoluteGapToEitherDirection)+"; screening tolerance: "+pretty(x.gapThreshold)+
      (x.roundingUncertainty!==null?"; rounding uncertainty: "+pretty(x.roundingUncertainty):"")+".":""}
    </div>
    <div>Source results first posted: {x.resultsFirstPosted||"unverified"}
     {" "}· source snapshot: {x.sourceAsOf}</div>
    <a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">
     Recheck original registered outcome and statistical analysis</a>
   </div>)}
   {records.length>35&&<p>{records.length-35} additional comparisons
    available in the CSV export; the display is capped to avoid long mobile lists.</p>}
   <p style={{margin:0,fontWeight:750}}>No independently authenticated human
    review, FDA PASS/CRL/EXTENSION calibration, or score certification
    is performed by this comparison view. Outcome-arm OG IDs must never
    be equated to adverse-event EG IDs.</p>
  </div>
 </details>;
}
