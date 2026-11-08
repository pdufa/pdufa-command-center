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
        <p style={{fontSize:13}}>November 4 SEC safety reporting and planned nHCM filing are source-linked. The original EU CTIS Amendment 04 protocol has now been downloaded and source-hashed; the NEJM supplements and final locked SAP remain unverified. No scientific phase approval, grade or PDUFA date is inferred.</p>
        <a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/phase3-reviewer-handoff-revision2-20261108.md" target="_blank" rel="noopener noreferrer">Open source-linked Phase 3 reviewer handoff</a>
        <p style={{fontSize:13,marginBottom:0}}><strong>New source reconciliation:</strong> open publisher protocol/appendix access checks, the secondary responder-analysis missingness rules, and two unresolved adverse-event reporting discrepancies. No reviewer grades or approvals inferred.</p>
        <a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/source-reconciliation-revision3-20261108.md" target="_blank" rel="noopener noreferrer">Open revision 3 · safety and statistical source review</a>
        <details style={{...panel,background:"#f6fbf9",marginBottom:0}}>
          <summary><strong>Original Phase III protocol captured · final SAP still missing</strong></summary>
          <p style={{fontSize:13}}>Official EU clinical trial <strong>2023-505797-15-00</strong> matches this NCT and protocol CY 6033. Public Amendment 04 dated October 28, 2025 was captured from CTIS (90 PDF pages; SHA-256 recorded). It describes co-primary endpoints, analysis sets and graphical multiplicity, but refers detailed missing-data analyses to a separate final SAP that has not been obtained. No independent clinical phase certification or method grade has been recorded.</p>
          <p style={{fontSize:13}}>The EU countries report their regional study as ended; that does not override the global registry's Active, Not Recruiting status.</p>
          <p><a href="https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en" target="_blank" rel="noopener noreferrer">EMA official protocol listing</a></p>
          <p><a href="https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398" target="_blank" rel="noopener noreferrer">Original AM04 PDF and source receipt</a></p>
          <p><a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/authenticated-am4-original-protocol-revision5-20261108.md" target="_blank" rel="noopener noreferrer">Read revision 5 · original protocol research findings</a></p>
          <p style={{fontSize:12,marginBottom:0}}>Status: ORIGINAL PROTOCOL CAPTURED · SAP NOT OBTAINED · CLINICAL GRADES WITHHELD</p>
        </details>
        <details style={{...panel,background:"#f5f8ff",marginBottom:0}}>
          <summary><strong>Final SAP audit · public registry checked · analysis still unverified</strong></summary>
          <p style={{fontSize:13}}>The official ClinicalTrials.gov current study API shows no posted results section or separate study-document records for NCT06081894. This does not prove no SAP exists privately. The original Phase 3 protocol remains captured, but the final locked SAP and its complete alpha graph, missing-data rules, and version chronology have not been independently authenticated.</p>
          <p style={{fontSize:13}}><strong>Published trial results, not calibrated FDA predictions:</strong> KCCQ-CSS +3.0 points (p=0.021) and peak VO₂ +0.67 mL/kg/min (p=0.003) both meet the sponsor-reported 0.025 primary threshold. LAVI (p=0.058) and time to cardiovascular event (nominal p=0.678) do not establish secondary confirmatory benefit. Benefit–risk remains an open review question.</p>
          <p><a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/locked-sap-public-audit-revision6-20261108.md" target="_blank" rel="noopener noreferrer">Read revision 6 · original-SAP public search and endpoint audit</a></p>
          <p style={{fontSize:12,marginBottom:0}}>Source audit only · FINAL SAP NOT OBTAINED · INDEPENDENT PHASE REVIEW 0 · METHOD GRADES 0 · FDA ABSTAIN</p>
        </details>
        <details style={{...panel,background:"#f7f6fd",marginBottom:0}}>
          <summary><strong>Trial amendment history and unresolved safety counts · review revision 7</strong></summary>
          <p style={{fontSize:13}}>The official ClinicalTrials.gov history lists 31 versions. Version 27 (May 15, 2025) changed registered outcome measures and study design; versions 29 and 30 also changed outcome measures. An independent history index suggests the primary-outcome count changed from one to two, but the original before-and-after version text has not been independently authenticated.</p>
          <p style={{fontSize:13}}>The sponsor reported 516 treated/randomized participants in a May topline announcement and 517 in the later full-results announcement. Heart-failure SAE counts also differ between reports (11/1 versus 12/3). Both are unresolved source-accounting questions, not established mistakes or adverse FDA decisions.</p>
          <p><a href="https://clinicaltrials.gov/study/NCT06081894?tab=history" target="_blank" rel="noopener noreferrer">Official registry — compare versions 26 and 27</a></p>
          <p><a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/version-and-safety-crosscheck-revision7-20261108.md" target="_blank" rel="noopener noreferrer">Read revision 7 · timeline and safety audit</a></p>
          <p style={{fontSize:12,marginBottom:0}}>Research discrepancies only · NO VERIFIED SAP · NO REVIEWER SIGNOFF · NO SCORES OR FDA PREDICTIONS</p>
        </details>
        <details style={{...panel,background:"#edf8f4",marginBottom:0}}>
          <summary><strong>Endpoint redesign chronology · original 2023 → 2025 sponsor documents</strong></summary>
          <p style={{fontSize:13}}>The original October 2023 sponsor-hosted trial poster describes one primary KCCQ-CSS endpoint, pVO₂ as part of a secondary composite, and a 420-participant plan. The sponsor's May 6, 2025 earnings-call remarks explain elevating peak VO₂ to a second primary endpoint and expanding enrollment after feedback from non-U.S. regulators. ClinicalTrials.gov lists Outcome Measures and Study Design changes on May 15, 2025. The captured October 28, 2025 Amendment 04 specifies dual-primary analysis.</p>
          <p style={{fontSize:13}}>This confirms the documented sponsor-reported endpoint redesign—not independent verification of regulator advice, approval dates, a locked SAP, database-unblinding chronology or statistical adequacy. Automated access to full original registry versions was unsuccessful; the official overview request returned HTTP 403.</p>
          <p><a href="https://cytokinetics.com/wp-content/uploads/2023/10/Masri_HFSA23-ACACIA-HCM-Trial_poster_dk10-UPLOAD.pdf" target="_blank" rel="noopener noreferrer">Original 2023 Phase 3 design poster</a></p>
          <p><a href="https://clinicaltrials.gov/study/NCT06081894?tab=history" target="_blank" rel="noopener noreferrer">Official May 2025 registry history</a></p>
          <p><a href="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/issuer-design-chronology-revision8-20261108.md" target="_blank" rel="noopener noreferrer">Open revision 8 · original source redesign timeline</a></p>
          <p style={{fontSize:12,marginBottom:0}}>Source chronology corroborated · ORIGINAL VERSION DIFF PENDING · FINAL SAP MISSING · 0 SCIENTIFIC GRADES</p>
        </details>
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
