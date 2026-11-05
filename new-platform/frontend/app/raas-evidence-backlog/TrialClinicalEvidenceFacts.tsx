"use client";
import type {RaasRegistryClinicalFact} from "../../lib/raas-registry-clinical-fact-ledger";
/** Reproducible clinical source facts, not trial outcomes or RAAS grades. */
export default function TrialClinicalEvidenceFacts({
 facts,nctId
}:{facts:readonly RaasRegistryClinicalFact[];nctId:string}){
 const numeric=facts.filter(x=>x.measurementValue!==null);
 const contrast=numeric.filter(x=>x.kind==="POSTED_PRIMARY_CONTRAST_RAW_MEASUREMENT");
 const safety=numeric.filter(x=>x.kind==="POSTED_SAE_AFFECTED_RATE_RAW_MEASUREMENT");
 return <details data-raas-clinical-source-facts={nctId}
  style={{padding:10,border:"1px solid #c8dacb",borderRadius:8,background:"#f9fbfa"}}>
  <summary style={{cursor:"pointer",fontWeight:750,color:"#20523c",fontSize:12}}>
   Clinical source facts ▸ {facts.length} source leads ·
   {" "}{numeric.length} numeric observations ·
   {" "}{contrast.length} primary contrasts ·
   {" "}{safety.length} safety affected rates
  </summary>
  <div style={{fontSize:12,lineHeight:1.6,display:"grid",gap:9,paddingTop:10}}>
   <p style={{margin:0}}><strong>Evidence provenance:</strong> All facts come from
    the saved exact NCT ClinicalTrials.gov registry, not independent
    clinical validation. Candidate RAAS metric IDs are routing tags only.
    Registry-posted results may appear after a trial's first public
    disclosure; do not backdate them to an earlier forecast date.
    Neither source facts nor their count verifies TOP/BOTTOM or FDA approval.</p>
   {facts.length===0?<p>No primary or safety source lead was recorded in
    the compact registry snapshot. Missing values remain N/A.</p>:
    facts.slice(0,60).map(f=><div key={f.id} data-raas-source-fact={f.kind}
     style={{borderTop:"1px solid #d8e3dc",paddingTop:7,display:"grid",gap:4}}>
     <strong>{f.kind.replaceAll("_"," ").toLowerCase()}</strong>
     <span>Research metric routing: {f.metricIds.join(", ")} ({f.candidateStage.toUpperCase()}
      {" "}requirements only — not independently confirmed readout stage)</span>
     <span>Source date {f.sourceDate}; {f.resultsFirstPosted?
      "registry results first posted "+f.resultsFirstPosted:
      "no results-first-posted date in this saved registry record"}</span>
     <span>{f.description}</span>
     {f.measurementValue!==null&&<span>
      <strong>Source-reported numeric observation:</strong>{" "}
      {f.measurementLabel}: {String(f.measurementValue)} {f.measurementUnit||""}
     </span>}
     <a href={f.sourceUrl} target="_blank" rel="noopener noreferrer"
      style={{color:"#1b6142"}}>Open original trial registry source</a>
    </div>)}
   {facts.length>60&&<p style={{margin:0}}>Showing 60 of {facts.length}
    source facts for this NCT. The complete source set is included in
    the downloadable clinical evidence CSV.</p>}
   <p style={{margin:0,fontWeight:700}}>No source fact is an approved
    RAAS metric grade, normalized treatment effect, comparative safety
    judgment or calibrated FDA PASS/CRL/EXTENSION probability.</p>
  </div>
 </details>;
}
