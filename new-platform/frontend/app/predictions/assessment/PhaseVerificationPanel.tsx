"use client";
import {useEffect,useState} from "react";

type Row={
  nct:string;rank:number;category:string;reviewPriority:number;phase:string[];
  phaseAgreement:string;registryLastUpdate:string;registeredPrimaryOutcomes:number;
  postedPrimaryResults:number;officialUrl:string;nextAction:string;
  snapshotId:string;sourceRunId:string;reviewerStatus:string;
};
type Handoff={
  schema:string;nct:string;canonicalTrials:number;
  buckets:{phaseReconciliationRequired:number;postedPrimaryResultsNeedReview:number;noPostedPrimaryResults:number};
  selected:Row&{
    title:string;sponsor:string;overallStatus:string;savedRegistryPhases:string[];
    latestRecordUpdatePosted:string;snapshotSavedAt:string;rationale:string;
    registrySha256:string;savedStageSha256:string;
    priorCompletedPhaseVerified:boolean;currentPhaseReviewerVerified:boolean;
  };
  queue:Row[];
  reviewerSignoff:false;scientificGradesWritten:number;
};
const panel={border:"1px solid #a8c9bc",borderRadius:9,padding:14,margin:"12px 0"} as const;
const category=(status:string)=>({
  PHASE_RECONCILIATION_REQUIRED:"Registry phase conflict or ambiguity",
  POSTED_PRIMARY_RESULTS_NEED_ADJUDICATION:"Posted primary results need assessment",
  NO_POSTED_PRIMARY_RESULTS_FIND_ORIGINAL_READOUT:"Look for original clinical readout",
} as Record<string,string>)[status]??"Review needed";

export default function PhaseVerificationPanel({nct}:{nct:string}){
  const [handoff,setHandoff]=useState<Handoff|null>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  useEffect(()=>{
    const abort=new AbortController();
    setHandoff(null);setError("");setLoading(true);
    fetch("/api/predictions/medical-phase-handoff?nct="+encodeURIComponent(nct),
      {cache:"no-store",signal:abort.signal})
      .then(async response=>{
        const value=await response.json();
        if(!response.ok)throw Error(value.error||"Phase review handoff unavailable");
        if(!abort.signal.aborted)setHandoff(value as Handoff);
      }).catch(e=>{if(!abort.signal.aborted)setError(e instanceof Error?e.message:"Review handoff unavailable");})
      .finally(()=>{if(!abort.signal.aborted)setLoading(false);});
    return ()=>abort.abort();
  },[nct]);
  const selected=handoff?.selected;
  return <section aria-label="Phase verification evidence handoff" style={{...panel,background:"#fff"}}>
    <h3 style={{margin:"4px 0 8px"}}>Current MAIN task: independent phase verification</h3>
    <p style={{fontSize:13,lineHeight:1.6}}>
      Source capture is complete, but the phase reviewer gate is not.
      This handoff displays saved sponsor-submitted registry facts and an exact-NCT review queue.
      It does not authorize a phase, sign a clinical review, or create scientific grades.
    </p>
    {loading?<p role="status">Reading the isolated 29-trial review queue…</p>:null}
    {error?<p role="alert">{error} No review completion is inferred.</p>:null}
    {selected&&handoff?<div>
      <p><strong>29 review items:</strong> {handoff.buckets.phaseReconciliationRequired} registry phase reconciliations,
        {" "}{handoff.buckets.postedPrimaryResultsNeedReview} posted-result reviews,
        {" "}{handoff.buckets.noPostedPrimaryResults} original-readout searches.</p>
      <p><strong>Selected: {selected.nct}</strong> · {selected.sponsor} · Registry-reported:
        {" "}{selected.phase.join(" / ")||"No phase"} · {selected.overallStatus}</p>
      <p><strong>Source status:</strong> {selected.phaseAgreement} — {selected.rationale}</p>
      <p><strong>Review queue:</strong> position {selected.rank}/29 · {category(selected.category)}.
        {" "}Primary outcome definitions: {selected.registeredPrimaryOutcomes};
        {" "}registry-posted primary results: {selected.postedPrimaryResults}.</p>
      <p><strong>Registry last updated:</strong> {selected.latestRecordUpdatePosted||"Not recorded"}.
        {" "}Captured snapshot: {selected.snapshotSavedAt}.</p>
      <p><strong>Current phase:</strong> awaiting independent reviewer.
        {" "}<strong>Previously completed phases:</strong> not independently verified.
        {" "}No scientific grade or FDA probability is assigned.</p>
      <p style={{fontSize:13}}><strong>Next evidence action:</strong> {selected.nextAction}</p>
      {selected.nct==="NCT06081894"?<aside style={{padding:12,border:"1px solid #d5c298",borderRadius:8,background:"#fff9ec",margin:"12px 0"}}>
        <strong>ACACIA-HCM — updated Phase 3 source review docket (Nov 8)</strong>
        <p style={{fontSize:13}}>November 4 SEC safety reporting and planned nHCM filing are source-linked. The NEJM publisher lists a protocol and supplementary appendix, but their contents have not been independently retrieved and verified. No scientific phase approval, grade or PDUFA date is inferred.</p>
        <a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/phase3-reviewer-handoff-revision2-20261108.md" target="_blank" rel="noopener noreferrer">Open source-linked Phase 3 reviewer handoff</a>
        <p style={{fontSize:13,marginBottom:0}}><strong>New source reconciliation:</strong> open publisher protocol/appendix access checks, the secondary responder-analysis missingness rules, and two unresolved adverse-event reporting discrepancies. No reviewer grades or approvals inferred.</p>
        <a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/source-reconciliation-revision3-20261108.md" target="_blank" rel="noopener noreferrer">Open revision 3 · safety and statistical source review</a>
      </aside>:null}
      <p>
        <a href={selected.officialUrl} target="_blank" rel="noopener noreferrer">Original ClinicalTrials.gov study</a>
        {" · "}
        <a href={selected.officialUrl+"?tab=history"} target="_blank" rel="noopener noreferrer">Registry record history</a>
      </p>
      <details style={panel}><summary>Evidence provenance and integrity</summary>
        <p>Registry snapshot ID: <code>{selected.snapshotId}</code></p>
        <p>Saved source-run ID: <code>{selected.sourceRunId}</code></p>
        <p>Registry SHA-256: <code style={{overflowWrap:"anywhere"}}>{selected.registrySha256}</code></p>
        <p>Source-stage SHA-256: <code style={{overflowWrap:"anywhere"}}>{selected.savedStageSha256}</code></p>
        <p>Only a separate authorized reviewer may record a verified phase. No previously completed phase is inferred from this trial's registry label.</p>
      </details>
      <details style={panel}><summary>All 29 original-source review tasks · priority order</summary>
        <p>Priority is evidence-review order, not evidence strength or FDA approval likelihood.</p>
        <div style={{display:"grid",gap:8}}>
          {handoff.queue.map(item=><div key={item.nct} style={{padding:10,border:"1px solid #d7e5df",borderRadius:8,background:item.nct===nct?"#e5f6ee":"#fff"}}>
            <a style={{fontWeight:750}} href={"/predictions/assessment?nct="+encodeURIComponent(item.nct)}>
              {item.rank}. {item.nct}
            </a>
            {" · "}{item.phase.join(" / ")||"Phase review"}
            <div style={{fontSize:12}}>{category(item.category)} · {item.phaseAgreement}</div>
            <div style={{fontSize:12}}>Posted primary results: {item.postedPrimaryResults} · Original record updated: {item.registryLastUpdate}</div>
          </div>)}
        </div>
      </details>
    </div>:null}
  </section>;
}
