"use client";

import {
  assessmentForPhase3CensusRow, PIPELINE_REVIEW_GATES,
  PIPELINE_GATE_AUTOMATION, researchLinksForPhase3Gate,
  type PipelineEvidenceGap,
} from "../../../lib/phase3-census-evidence-gaps";
import type { Phase3CensusTrial } from "../../../lib/phase3-census-rows";
import Phase3LiveRegistry from "./Phase3LiveRegistry";
import { sourcesForPhase3Trial, type Phase3CensusSourceDirectory } from "../../../lib/phase3-census-sources";

/**
 * On-demand view of *unverified* research gaps for one exact NCT.
 * Browser only. No source edits, reviewer approvals, scans, or scoring.
 */
export default function Phase3EvidenceDetails({ trial, directory }: { trial: Phase3CensusTrial; directory: Phase3CensusSourceDirectory }) {
  const assessed: PipelineEvidenceGap = assessmentForPhase3CensusRow(trial);
  const company = sourcesForPhase3Trial(trial,directory);
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
    <p><strong>Saved company mapping:</strong> {company.company} · CIK {company.cik}.
      {" "}<strong>Saved market cap:</strong> {company.marketCapUsd.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0})}
      {" "}checked <time dateTime={company.marketCapCheckedAt}>{company.marketCapCheckedAt}</time>.
      These dates describe the saved census inputs. The separate live registry lookup below
      can fetch current trial metadata on demand; it does not refresh these saved company inputs.</p>
    <p><strong>Research links only.</strong> Company filings and configured issuer websites
      help locate documents. They are not a matched trial/program document or a verified FDA event.
      No trial-specific FDA/PDUFA document has been established by this checklist.</p>
    <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%",minWidth:680}}>
      <thead><tr><th scope="col" style={{textAlign:"left",padding:9}}>Requirement</th>
        <th scope="col" style={{textAlign:"left",padding:9}}>Available evidence / research sources</th>
        <th scope="col" style={{textAlign:"left",padding:9}}>How this can be checked</th></tr></thead>
      <tbody>{PIPELINE_REVIEW_GATES.map(gate=><tr key={gate.id}>
        <th scope="row" style={{textAlign:"left",padding:9,borderTop:"1px solid #e2e8f0"}}>{gate.label}</th>
        <td style={{padding:9,borderTop:"1px solid #e2e8f0"}}>
          {gate.state==="CENSUS_ONLY" ? "Dated research census only — not reverified for live eligibility"
            : "Missing independently verified source"}
          {researchLinksForPhase3Gate(gate.id,trial,company).length > 0 && <ul>
            {researchLinksForPhase3Gate(gate.id,trial,company).map(link=><li key={link.url}>
              <a href={link.url} target="_blank" rel="noopener noreferrer">{link.label}</a>
            </li>)}
          </ul>}
        </td>
        <td style={{padding:9,borderTop:"1px solid #e2e8f0"}}>
          <strong>{PIPELINE_GATE_AUTOMATION[gate.id].mode==="STRUCTURED_RECHECK" ? "Structured recheck possible"
            : PIPELINE_GATE_AUTOMATION[gate.id].mode==="DOCUMENT_RECONCILIATION" ? "Original-document reconciliation"
            : "Check each restriction"}</strong>
          <p>{PIPELINE_GATE_AUTOMATION[gate.id].note}</p>
        </td>
      </tr>)}</tbody>
    </table></div>
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
