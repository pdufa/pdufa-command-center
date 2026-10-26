import Link from "next/link";
import ScientificOutcomeLive from "./ScientificOutcomeLive";
import IndependentInstallationLane from "./IndependentInstallationLane";
import { isAccepted, summarizeInstallationAudit } from "../../lib/installation-audit-summary";
import { FDA_REVIEW_WORKLIST_SNAPSHOT, auditFDAReviewWorklist } from "../../lib/fda-review-worklist-snapshot";

type Gate = "Code present" | "Preview READY" | "Partial" | "Not verified" | "Not audited" | "Not applicable" | "Verified";
type Check = {
  component: string;
  requirement: string;
  code: Gate;
  deployment: Gate;
  runtime: Gate;
  evidence: Gate;
  blocker: string;
  lastVerified: string;
  source: string;
  sourceLabel: string;
};

const report = "https://github.com/pdufa/pdufa-command-center/blob/main/data/daily_scan_results.json";
const audit = "https://github.com/pdufa/pdufa-command-center/issues/331";
const sourceAudit = "https://github.com/pdufa/pdufa-command-center/blob/main/data/pdufa_source_report.json";
const ci = "https://github.com/pdufa/pdufa-command-center/actions/runs/40242456530";
const sourceRecovery = "https://github.com/pdufa/pdufa-command-center/actions/runs/40241024969";
const preview = "https://vercel.com/pdufa/pdufa-new-dashboard/2ZuphnZFivGJGsskHHXAv9QBMWDo";

const checks: Check[] = [
  { component: "Core Platform", requirement: "Dashboard navigation, frontend/backend checks and release controls", code: "Code present", deployment: "Preview READY", runtime: "Partial", evidence: "Not applicable", blocker: "Production page and authenticated health/database checks passed; complete application runtime acceptance remains unverified", lastVerified: "2026-10-25 23:37 UTC · authenticated checks", source: audit, sourceLabel: "Acceptance record" },
  { component: "Pipeline", requirement: "Public companies; $300M–$10B market cap; mandatory filters", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Full qualified Pipeline total unknown; 11,598 clinical records are not qualified candidates", lastVerified: "2026-10-24 · partial inventory", source: report, sourceLabel: "Saved RESULTS" },
  { component: "GEM JR / GEM / WT", requirement: "Independent lists, WT operation and original GEM FS/FA presets", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "11 GEM JR and 6 GEM are saved membership counts, not certified trial scores; WT runtime not confirmed", lastVerified: "2026-10-24 · memberships", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Scientific Assessment", requirement: "All 40 assessments per exact trial, source citations and uncertainty", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Three existing seven-category scoring models are not the 40 scientific investigations. No completed analyst-review entries are committed; per-trial certification remains missing.", lastVerified: "2026-10-25 · committed source review", source: "https://github.com/pdufa/pdufa-command-center/blob/main/data/candidate_assessment_reviews.json", sourceLabel: "Analyst reviews" },
  { component: "Historical Trial Database", requirement: "Complete, deduplicated and source-verified historical trial records", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "11,598 tracked inventory records are not certified as a qualified or complete historical population", lastVerified: "2026-10-24 · partial inventory", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Prediction Engine", requirement: "Reproducible candidate-level predictions and uncertainty bounds", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "No certified per-trial prediction outputs or acceptance metrics", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Evidence Verification", requirement: "Authoritative provenance and all source-family checks", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "2026-10-25 source audit: 995/1121 verified, 21 unresolved, 2 conflicted, 93 unavailable, 10 N/A; SEC and FINANCIAL source families remain missing", lastVerified: "2026-10-25 16:40 UTC · PARTIAL", source: sourceAudit, sourceLabel: "Source audit" },
  { component: "Regulatory Intelligence", requirement: "FDA designations, decision dates and original sources", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "FDA designation grant evidence and dates not fully verified", lastVerified: "2026-10-24 · gap recorded", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Investment Analysis", requirement: "Research outputs kept separate from trading permissions", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "No audited runtime or complete evidence coverage; no trading change authorized", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Nightly Scanning", requirement: "8 PM Pacific schedule, duplicate guard and full chained source collection", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "Scheduled workflow exists; full-chain 8 PM run/source coverage not independently verified", lastVerified: "2026-10-24 · PARTIAL run", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Results & Reporting", requirement: "Date-indexed nightly result totals, gaps and unknowns", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "Saved RESULTS is PARTIAL; unavailable/unknown Pipeline and designation totals must remain unknown", lastVerified: "2026-10-24 · PARTIAL report", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Automation", requirement: "Automated scans, notifications, status feedback and independent audit trail", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "End-to-end scheduling and notification delivery not verified", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Backup & Recovery", requirement: "Restorable versioned data and reproducible recovery rehearsal", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Isolated source recovery CI passed; production backup restore not demonstrated", lastVerified: "2026-10-25 · rehearsal CI", source: sourceRecovery, sourceLabel: "Recovery CI" },
  { component: "Prediction Validation", requirement: "FDA-labelled historical holdouts, calibration, leakage checks and backtests", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "Source auditing and leak-resistant backtest safeguards exist, but the published FDA audit certifies zero eligible review cycles, no complete denominator and no calibrated probabilities.", lastVerified: "2026-10-25 · saved FDA source audit", source: "https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/backend/app/research_sources/hop_fda_full_action_pdf_audit_index.json", sourceLabel: "FDA source audit" },
  { component: "Final Acceptance", requirement: "Every gate independently verified with reproducible proof", code: "Code present", deployment: "Preview READY", runtime: "Not verified", evidence: "Not verified", blocker: "Requires production verification, complete science evidence and validated outcomes", lastVerified: "2026-10-25 · preview build", source: preview, sourceLabel: "Preview build" },
];

const tone: Record<Gate, string> = {
  "Code present": "#166534",
  "Preview READY": "#166534",
  "Partial": "#92400e",
  "Not verified": "#9f1239",
  "Not audited": "#64748b",
  "Not applicable": "#64748b",
  "Verified": "#166534",
};

function GateCell({ value }: { value: Gate }) {
  return <span style={{fontWeight:650,color:tone[value],whiteSpace:"nowrap"}}>{value}</span>;
}

export default function InstallationAudit() {
  const {groups, total} = summarizeInstallationAudit(checks);
  const fdaWorklist = auditFDAReviewWorklist(FDA_REVIEW_WORKLIST_SNAPSHOT);
  return <main style={{maxWidth:1420,margin:"0 auto",padding:"28px 18px",fontFamily:"system-ui,sans-serif",color:"#17212b"}}>
    <p><Link href="/">← Dashboard</Link></p>
    <h1>System installation & evidence tracker</h1>
    <p><strong>15-section audit · snapshot as of October 25, 2026.</strong> This is a dated read-only checklist with separate, on-demand protected SCIENCE/OUTCOME evidence checks below. A green build establishes neither scientific accuracy nor complete runtime operation.</p>
    <p><strong>Release:</strong> GitHub change #332 merged; Vercel production READY and user access reported on October 25, 2026. Deployment of the dashboard does not mean its scientific or prediction checks are complete. Implementation-stage counts are reported separately from verified acceptance; they are not an estimate of development-hours completion.</p>
    <IndependentInstallationLane />
    <p><strong>Latest saved RESULTS:</strong> October 24, 2026 · PARTIAL · 11,598 tracked clinical records (not Pipeline qualified) · GEM JR 11 · GEM 6. Source audit: 993/1121 verified; 23 unresolved, 93 unavailable, 10 N/A. Those listed categories add to 1,119; <strong>two checks have no separately stated classification in the saved report</strong>.</p>
    <p><strong>Newer source audit (October 25, 2026 · 16:40 UTC):</strong> 995/1121 verified, 21 unresolved, 2 conflicted, 93 unavailable and 10 not applicable: <strong>995 + 21 + 2 + 93 + 10 = 1,121</strong>. <a href={sourceAudit}>Source report</a> · <strong>PARTIAL</strong> because required SEC and FINANCIAL verification is still missing. This audit is separate from the October 24 nightly clinical RESULTS; later counts do not retrospectively validate that earlier run or its two unclassified checks.</p>
    <section aria-label="Installation acceptance balance" style={{margin:"20px 0"}}>
      <h2>Acceptance balance — measured from the dated checklist</h2>
      <p><strong>{total.accepted} / {total.sections} sections fully accepted · {total.sections - total.accepted} remain open.</strong> Full acceptance requires runtime verification and applicable evidence verification, not only installed code or a READY build.</p>
      <p><strong>Individual status gates:</strong> {total.independentlyVerified} independently verified · {total.implementationSignals} code/deployment signals · {total.partial} partial · {total.unverified} not verified/audited · {total.excluded} not applicable. Denominator: {total.gates} applicable gates. These gate counts do not measure percentage of engineering hours remaining.</p>
      <p><strong>Important:</strong> OUTCOME source connection verified on October 25, 2026 at 6:37 PM Pacific: the authenticated production evidence request returned HTTP 200 from the dedicated HOP service. This verifies read-only source access, not FDA decision validity. OUTCOME prediction validation remains blocked: 0 independently verified review-cycle outcomes, an incomplete approval/nonapproval decision denominator, and no established time-forward calibration. FDA approval probabilities remain unavailable; missing SCIENCE-40 evidence cannot be counted as complete. <a href={audit} target="_blank" rel="noopener noreferrer">See current acceptance record</a>.</p>
      {groups.map(group => <details key={group.name} open={group.name === "Core Platform"} style={{border:"1px solid #cbd5e1",borderRadius:8,margin:"12px 0",background:"#fff"}}>
        <summary style={{padding:"14px 16px",cursor:"pointer",fontWeight:700}}>
          {group.name} — {group.totals.accepted}/{group.totals.sections} accepted; {group.totals.sections - group.totals.accepted} open
          <span style={{fontSize:12,fontWeight:400,display:"block",marginTop:4}}>
            {group.totals.implementationSignals} code/deployment signals · {group.totals.partial} partial · {group.totals.unverified} unverified · {group.totals.gates} applicable gates
          </span>
        </summary>
        <div style={{overflowX:"auto",padding:"0 12px 12px"}}>
          <table style={{width:"100%",minWidth:1170,borderCollapse:"collapse",fontSize:13}}>
            <thead><tr>{["Component","Acceptance","Requirement","Code","Deployment","Runtime","Evidence","Blocker / remaining work","Last checked","Source"].map(x=><th key={x} scope="col" style={{textAlign:"left",padding:9,borderBottom:"2px solid #94a3b8",background:"#f1f5f9",whiteSpace:"nowrap"}}>{x}</th>)}</tr></thead>
            <tbody>{checks.filter(item => group.items.some(member => member.component === item.component)).map((item,i)=><tr key={item.component} style={{background:i%2?"#f8fafc":"white"}}>
              <th scope="row" style={{textAlign:"left",padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:135}}>{item.component}</th>
              <td style={{padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",fontWeight:700,color:isAccepted(item)?"#166534":"#92400e"}}>{isAccepted(item)?"ACCEPTED":"OPEN"}</td>
              <td style={{padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:205}}>{item.requirement}</td>
              {[item.code,item.deployment,item.runtime,item.evidence].map((gate,k)=><td key={k} style={{padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top"}}><GateCell value={gate}/></td>)}
              <td style={{padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:270}}>{item.blocker}</td>
              <td style={{padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:135}}>{item.lastVerified}</td>
              <td style={{padding:9,borderBottom:"1px solid #e2e8f0",verticalAlign:"top"}}><a href={item.source} target="_blank" rel="noopener noreferrer">{item.sourceLabel}</a></td>
            </tr>)}</tbody>
          </table>
        </div>
      </details>)}
    </section>
    <ScientificOutcomeLive />
    <section aria-labelledby="fda-research-worklist" style={{margin:"26px 0",padding:"18px",border:"1px solid #cbd5e1",borderRadius:9,background:"#f8fafc"}}>
      <h2 id="fda-research-worklist">OUTCOME source-review preparation — historical research only</h2>
      <p><strong>Research snapshot: October 25, 2026.</strong> The following values are from a separate quarantined FDA research workflow, not the live OUTCOME API, verified FDA decisions or current production model data.</p>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:12,margin:"14px 0"}}>
        <div style={{padding:12,background:"white",border:"1px solid #e2e8f0",borderRadius:7}}>
          <strong style={{display:"block",fontSize:24}}>{fdaWorklist.pendingLetterReferences}</strong>
          <span>Published-letter references needing identity review</span>
        </div>
        <div style={{padding:12,background:"white",border:"1px solid #e2e8f0",borderRadius:7}}>
          <strong style={{display:"block",fontSize:24}}>{fdaWorklist.searchPackets}</strong>
          <span>Prepared research packets (not FDA decisions)</span>
        </div>
        <div style={{padding:12,background:"white",border:"1px solid #e2e8f0",borderRadius:7}}>
          <strong style={{display:"block",fontSize:24}}>{fdaWorklist.independentlyVerifiedReviewCycles}</strong>
          <span>Independently verified review-cycle decisions</span>
        </div>
      </div>
      <p><strong>Reconciled source identities:</strong> {FDA_REVIEW_WORKLIST_SNAPSHOT.publishedLetterReferences} published letter references =
        {" "}{FDA_REVIEW_WORKLIST_SNAPSHOT.matchedOriginalApplicationReferences} linked references +
        {" "}{FDA_REVIEW_WORKLIST_SNAPSHOT.missingFromApprovalCentricRosterReferences} references missing from the approval-centric roster +
        {" "}{FDA_REVIEW_WORKLIST_SNAPSHOT.ambiguousApplicationReferences} ambiguous identities.
        The missing references represent {FDA_REVIEW_WORKLIST_SNAPSHOT.distinctMissingApplicationCandidates} provisional application groups. An application absent from this roster is <strong>not</strong> proven rejected or never approved.</p>
      <p><strong>Next acceptance gates:</strong> inspect original FDA action evidence with independently authenticated reviewers, reconcile exact application/review-cycle identities, reconstruct the complete approval and nonapproval population, then validate predecision time cutoffs and out-of-time calibration. No independent review is claimed complete; model-eligible decision cycles remain {fdaWorklist.modelEligibleReviewCycles}, and FDA approval probabilities remain unavailable.</p>
      <p><a href={FDA_REVIEW_WORKLIST_SNAPSHOT.researchWorkflowUrl} target="_blank" rel="noopener noreferrer">Pinned original-source research run</a> · <a href={FDA_REVIEW_WORKLIST_SNAPSHOT.reviewIssueUrl} target="_blank" rel="noopener noreferrer">Independent evidence review work queue</a>. This is a dated, read-only worklist summary; opening it does not authorize FDA outcome labels, grades, scans, or trades.</p>
    </section>
    <section aria-labelledby="scientific-gates">
      <h2 id="scientific-gates">Independent scientific acceptance gates</h2>
      <p><strong>SCIENCE:</strong> exact trial identity, 40 assessments, authoritative sources, uncertainty, conflicting evidence and independent reviewer signoffs must be verified before a readiness grade can be certified.</p>
      <p><strong>OUTCOME:</strong> FDA-labelled historical outcomes, prespecified holdouts, leakage checks, calibration and transparent error analysis must be verified before outcome probabilities can be certified.</p>
    </section>
    <p><strong>Sources:</strong> <a href={audit}>acceptance issue #331</a> · <a href={report}>saved nightly report</a> · <a href={sourceAudit}>newer source verification</a> · <a href={ci}>frontend/backend CI</a> · <a href={preview}>tracker preview deployment</a>.</p>
    <p><strong>Safety:</strong> this page does not trigger scans, rescoring, notifications, orders or trades, and does not alter restrictions or GEM JR/GEM FS/FA memberships.</p>
  </main>;
}
