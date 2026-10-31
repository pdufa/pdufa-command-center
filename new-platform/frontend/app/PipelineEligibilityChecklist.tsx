"use client";
import styles from "./FunnelWorkspace.module.css";
import { pipelineEvidenceGates, pipelineGateCounts } from "../lib/pipeline-gate-evidence";
import type { PipelineResearchRow } from "../lib/pipeline-research-view";
const SHEET="https://docs.google.com/spreadsheets/d/1FSRXFXc4u2KTpdyP-vSbWil-Fgtrj3ucELSk2kpQAG0/edit";
const label={
 HISTORICAL_POINTER:"Historical source pointer",
 SOURCE_REVIEW_REQUIRED:"Independent review required",
 MISSING_EVIDENCE:"Evidence missing",
 IDENTITY_CONFLICT:"Unresolved identity",
} as const;
/** UI renders historical/source review states only; never an unsupported qualification badge. */
export default function PipelineEligibilityChecklist({row,today}:{row:PipelineResearchRow;today:string}){
 const checks=pipelineEvidenceGates(row,today),counts=pipelineGateCounts(row,today);
 return <details className={styles.dossierSection} aria-label={"Evidence gates for "+row.nctId}>
  <summary><strong>Eligibility proof checklist · 7 gates</strong><span>{counts.missing} missing · {counts.review} require review · {counts.conflicts} conflicts</span></summary>
  <div className={styles.dossierFields}>
   <p className={styles.muted}>Research readiness only. No historical snapshot, registry completion or source-recorded date establishes an eligible post–Phase 3 commercial program.</p>
   {checks.map(g=><details key={g.id} className={styles.dossierField}>
     <summary><span>{g.title}</span><strong>{label[g.status]}</strong></summary>
     <div className={styles.dossierEvidence}><p>{g.explanation}</p>
      {g.sourceUrl&&<a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Review underlying source</a>}
     </div>
    </details>)}
   <p><a href={SHEET+"#gid=1138168786"} target="_blank" rel="noopener noreferrer">Open 22 Eligibility Gate Matrix in Google Sheets</a></p>
   <p className={styles.muted}>The Google Sheet is a separate, manual reviewer workspace. Site-to-Sheet synchronization is not installed; updates in the Sheet do not automatically update these website gate labels.</p>
  </div>
 </details>;
}
