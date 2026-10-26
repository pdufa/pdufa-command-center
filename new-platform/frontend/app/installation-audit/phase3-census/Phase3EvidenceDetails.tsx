"use client";

import {
  assessmentForPhase3CensusRow, PIPELINE_REVIEW_GATES,
  type PipelineEvidenceGap,
} from "../../../lib/phase3-census-evidence-gaps";
import type { Phase3CensusTrial } from "../../../lib/phase3-census-rows";
import Phase3LiveRegistry from "./Phase3LiveRegistry";

/**
 * On-demand view of *unverified* research gaps for one exact NCT.
 * Browser only. No source edits, reviewer approvals, scans, or scoring.
 */
export default function Phase3EvidenceDetails({ trial }: { trial: Phase3CensusTrial }) {
  const assessed: PipelineEvidenceGap = assessmentForPhase3CensusRow(trial);
  const note = assessed.registryGroup === "REGISTRY_CLOSED_RECORD"
    ? "The registry record is completed, terminated or withdrawn; this alone does not establish whether the company continues developing its drug."
    : assessed.registryGroup === "REGISTRY_OPEN_RECORD"
    ? "The registry record is open/ongoing; this alone does not establish that the company's development program is funded or eligible for a U.S. PDUFA."
    : "The registry status is unknown. Current trial activity and continuing development require original-source research.";

  return <section aria-label={"Pipeline evidence gaps for " + assessed.nctId}
    style={{background:"#f8fafc",border:"1px solid #94a3b8",padding:15,marginTop:14,borderRadius:8}}>
    <h3>Evidence checklist · {assessed.nctId} · {assessed.ticker}</h3>
    <p><strong>PIPELINE: NOT QUALIFIED / NOT DETERMINED.</strong>
      {" "}This is a source-work checklist, not a disqualification,
      trade instruction or scientific score.</p>
    <p>{note}</p>
    <table style={{borderCollapse:"collapse",width:"100%"}}>
      <thead><tr><th scope="col" style={{textAlign:"left",padding:9}}>Requirement</th>
        <th scope="col" style={{textAlign:"left",padding:9}}>Available evidence</th></tr></thead>
      <tbody>{PIPELINE_REVIEW_GATES.map(gate=><tr key={gate.id}>
        <th scope="row" style={{textAlign:"left",padding:9,borderTop:"1px solid #e2e8f0"}}>{gate.label}</th>
        <td style={{padding:9,borderTop:"1px solid #e2e8f0"}}>
          {gate.state==="CENSUS_ONLY" ? "Dated research census only — not reverified for live eligibility"
            : "Missing independently verified source"}</td>
      </tr>)}</tbody>
    </table>
    <p><strong>Five independent evidence gates remain unverified.</strong> Current
      market-cap and Phase 3 records also require source freshness checks.
      A current drug-indication pair and verified FDA pathway/PDUFA cannot be
      inferred from this historical CSV.</p>
    <p><a href={assessed.registrySource} target="_blank" rel="noopener noreferrer">
      Inspect original ClinicalTrials.gov study record</a></p>
    <Phase3LiveRegistry nctId={assessed.nctId}
      datedStatus={assessed.registryStatus} censusLeadCompany={assessed.company}/>
    <small>0 validated FDA probability estimates; no Pipeline membership updates.
      A matching census record is NOT an FDA regulatory event.</small>
  </section>;
}
