"use client";
import casebook from "../../data/raas-primary-estimand-five-case-triage.json";
import type {PrimaryContrastReconciliationLedger} from "../../lib/raas-primary-arm-reconciliation";
/** Source-checked interpretation notes are not an authenticated statistician
 * sign-off. A new source hash invalidates the saved snapshot note. */
export default function PrimaryFiveCaseTriage({
 ledger
}:{ledger:PrimaryContrastReconciliationLedger}){
 const byId=new Map(ledger.records.map(r=>[
  r.nctId+"|"+r.outcomeIndex+"|"+r.comparisonIndex,r
 ]));
 const historical=casebook.cases.map(x=>{
  const current=byId.get(x.nctId+"|"+x.outcomeIndex+"|"+x.comparisonIndex);
  const same=!!current&&current.ticker===x.ticker&&
   current.sourceHash===x.sourceHash&&
   ledger.sourceAsOf===casebook.sourceAsOf;
  return {item:x,current,same};
 });
 const newDiscrepancies=ledger.records.filter(x=>
  x.signal==="ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW");
 return <section data-raas-five-case-estimand-triage="source-interpretation-only"
  style={{margin:"18px 0",border:"1px solid #bad2c5",borderRadius:10,
   background:"#f6faf7",padding:15}}>
  <h2 style={{margin:"0 0 8px",fontSize:17,color:"#184f34"}}>
   Five original discrepancy flags · investigated sources
  </h2>
  <p style={{fontSize:12,lineHeight:1.65}}>
   The original five raw-arm mismatch signals were traced through exact
   ClinicalTrials.gov records and, when available, primary publications or
   FDA scientific review. The corrected algorithm no longer overwrites earlier
   observations when the same treatment-group ID appears across time points
   or endpoint categories. It distinguishes participant counts from proportions
   and allows ordinary displayed-value rounding.
   <strong> No independent statistician has authenticated these conclusions,
   and no RAAS score is approved.</strong>
  </p>
  <div style={{display:"flex",flexWrap:"wrap",gap:10,marginBottom:12,fontSize:12}}>
   <span><strong>{ledger.comparisons}</strong> saved primary contrasts</span>
   <span><strong>{ledger.rawArmDiscrepancies}</strong> currently flagged raw mean-difference gaps</span>
   <span><strong>{ledger.repeatedGroupOutcomes}</strong> repeated-group source ambiguities</span>
   <span><strong>{ledger.countProportionIncompatibilities}</strong> count/proportion scale mismatches</span>
   <span><strong>{ledger.roundingCompatible}</strong> rounding-compatible gaps</span>
  </div>
  <div style={{display:"grid",gap:8}}>
   {historical.map(({item,current,same})=><details key={item.nctId}
    data-raas-estimand-case={item.nctId}
    style={{border:"1px solid #d6e2da",background:"#fff",padding:12,borderRadius:8}}>
    <summary style={{cursor:"pointer",color:"#20543b",fontWeight:750,fontSize:12}}>
     {item.ticker} · {item.nctId} · {item.title}
     {" "}▸ {same?current?.signal.replaceAll("_"," ").toLowerCase():
      "source changed or comparison unavailable — revalidate"}
    </summary>
    <div style={{fontSize:12,lineHeight:1.6,paddingTop:10,display:"grid",gap:8}}>
     <p style={{margin:0}}><strong>Observed source facts:</strong> {item.rawObservation}</p>
     <p style={{margin:0}}><strong>Scientific interpretation:</strong> {item.interpretation}</p>
     <p style={{margin:0}}><strong>Next verification:</strong> {item.neededBeforeClosure}</p>
     <p style={{margin:0}}>
      <strong>Current source hash match:</strong> {same?"yes":"NO — requires new case review"}
      {" "}· original results first posted {current?.resultsFirstPosted||"not verified"}.
      {" "}No human-approved metric grade or calibrated FDA decision.</p>
     <div style={{display:"flex",flexWrap:"wrap",gap:12}}>
      <a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">
       Original trial registry</a>
      {item.corroborationUrl!==item.sourceUrl&&<a href={item.corroborationUrl}
       target="_blank" rel="noopener noreferrer">
       Additional clinical/FDA source</a>}
     </div>
    </div>
   </details>)}
  </div>
  {newDiscrepancies.some(x=>!historical.some(y=>y.item.nctId===x.nctId&&
   y.item.outcomeIndex===x.outcomeIndex&&
   y.item.comparisonIndex===x.comparisonIndex))&&<p style={{fontSize:12}}>
   Additional raw-arm discrepancies exist outside this five-case source
   review. They remain in the primary comparison export for investigation.</p>}
  <p style={{fontSize:11,margin:"12px 0 0",color:"#496d57"}}>
   Source snapshot {casebook.sourceAsOf} · review hypotheses recorded {casebook.triagedOn}.
   Historical source dates are not prediction dates. Missing class-level
   annotations and incomplete statistical methods remain unresolved until
   independent review; neither a matching arithmetic result nor a published
   result is evidence of favorable FDA action.
  </p>
 </section>;
}
