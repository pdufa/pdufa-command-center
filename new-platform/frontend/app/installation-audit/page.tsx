import Link from "next/link";

type Gate = "Code present" | "Preview READY" | "Partial" | "Not verified" | "Not audited" | "Not applicable";
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
  { component: "Core Platform", requirement: "Dashboard navigation, frontend/backend checks and release controls", code: "Code present", deployment: "Preview READY", runtime: "Not verified", evidence: "Not applicable", blocker: "Production runtime audit remains a separate requirement", lastVerified: "2026-10-25 · code/CI", source: ci, sourceLabel: "CI checks" },
  { component: "Pipeline", requirement: "Public companies; $300M–$10B market cap; mandatory filters", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Full qualified Pipeline total unknown; 11,598 clinical records are not qualified candidates", lastVerified: "2026-10-24 · partial inventory", source: report, sourceLabel: "Saved RESULTS" },
  { component: "GEM JR / GEM / WT", requirement: "Independent lists, WT operation and original GEM FS/FA presets", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "11 GEM JR and 6 GEM are saved membership counts, not certified trial scores; WT runtime not confirmed", lastVerified: "2026-10-24 · memberships", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Scientific Assessment", requirement: "All 40 assessments per exact trial, source citations and uncertainty", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Trial-level 40-assessment and source-by-source completion unverified", lastVerified: "2026-10-25 · development review", source: audit, sourceLabel: "Requirements" },
  { component: "Historical Trial Database", requirement: "Complete, deduplicated and source-verified historical trial records", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "11,598 tracked inventory records are not certified as a qualified or complete historical population", lastVerified: "2026-10-24 · partial inventory", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Prediction Engine", requirement: "Reproducible candidate-level predictions and uncertainty bounds", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "No certified per-trial prediction outputs or acceptance metrics", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Evidence Verification", requirement: "Authoritative provenance and all source-family checks", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "2026-10-25 source audit: 995/1121 verified, 21 unresolved, 2 conflicted, 93 unavailable, 10 N/A; SEC and FINANCIAL source families remain missing", lastVerified: "2026-10-25 16:40 UTC · PARTIAL", source: sourceAudit, sourceLabel: "Source audit" },
  { component: "Regulatory Intelligence", requirement: "FDA designations, decision dates and original sources", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "FDA designation grant evidence and dates not fully verified", lastVerified: "2026-10-24 · gap recorded", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Investment Analysis", requirement: "Research outputs kept separate from trading permissions", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "No audited runtime or complete evidence coverage; no trading change authorized", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Nightly Scanning", requirement: "8 PM Pacific schedule, duplicate guard and full chained source collection", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "Scheduled workflow exists; full-chain 8 PM run/source coverage not independently verified", lastVerified: "2026-10-24 · PARTIAL run", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Results & Reporting", requirement: "Date-indexed nightly result totals, gaps and unknowns", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Partial", blocker: "Saved RESULTS is PARTIAL; unavailable/unknown Pipeline and designation totals must remain unknown", lastVerified: "2026-10-24 · PARTIAL report", source: report, sourceLabel: "Saved RESULTS" },
  { component: "Automation", requirement: "Automated scans, notifications, status feedback and independent audit trail", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "End-to-end scheduling and notification delivery not verified", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Backup & Recovery", requirement: "Restorable versioned data and reproducible recovery rehearsal", code: "Code present", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Isolated source recovery CI passed; production backup restore not demonstrated", lastVerified: "2026-10-25 · rehearsal CI", source: sourceRecovery, sourceLabel: "Recovery CI" },
  { component: "Prediction Validation", requirement: "FDA-labelled historical holdouts, calibration, leakage checks and backtests", code: "Not audited", deployment: "Not verified", runtime: "Not verified", evidence: "Not verified", blocker: "Authoritative outcomes and out-of-sample calibration are not certified", lastVerified: "Not yet verified", source: audit, sourceLabel: "Requirements" },
  { component: "Final Acceptance", requirement: "Every gate independently verified with reproducible proof", code: "Code present", deployment: "Preview READY", runtime: "Not verified", evidence: "Not verified", blocker: "Requires production verification, complete science evidence and validated outcomes", lastVerified: "2026-10-25 · preview build", source: preview, sourceLabel: "Preview build" },
];

const tone: Record<Gate, string> = {
  "Code present": "#166534",
  "Preview READY": "#166534",
  "Partial": "#92400e",
  "Not verified": "#9f1239",
  "Not audited": "#64748b",
  "Not applicable": "#64748b",
};

function GateCell({ value }: { value: Gate }) {
  return <span style={{fontWeight:650,color:tone[value],whiteSpace:"nowrap"}}>{value}</span>;
}

export default function InstallationAudit() {
  return <main style={{maxWidth:1420,margin:"0 auto",padding:"28px 18px",fontFamily:"system-ui,sans-serif",color:"#17212b"}}>
    <p><Link href="/">← Dashboard</Link></p>
    <h1>System installation & evidence tracker</h1>
    <p><strong>15-section audit · snapshot as of October 25, 2026.</strong> This is a read-only checklist, not a live progress monitor. A green build establishes neither operational runtime success nor scientific accuracy.</p>
    <p><strong>Release:</strong> Vercel preview READY and page access confirmed on October 25, 2026. This historical snapshot does not certify the current production deployment or scientific acceptance. Verify current deployment status separately. No numerical installation percentage is asserted.</p>
    <p><strong>Latest saved RESULTS:</strong> October 24, 2026 · PARTIAL · 11,598 tracked clinical records (not Pipeline qualified) · GEM JR 11 · GEM 6. Source audit: 993/1121 verified; 23 unresolved, 93 unavailable, 10 N/A. Those listed categories add to 1,119; <strong>two checks have no separately stated classification in the saved report</strong>.</p>
    <p><strong>Newer source audit (October 25, 2026 · 16:40 UTC):</strong> 995/1121 verified, 21 unresolved, 2 conflicted, 93 unavailable and 10 not applicable: <strong>995 + 21 + 2 + 93 + 10 = 1,121</strong>. <a href={sourceAudit}>Source report</a> · <strong>PARTIAL</strong> because required SEC and FINANCIAL verification is still missing. This audit is separate from the October 24 nightly clinical RESULTS; later counts do not retrospectively validate that earlier run or its two unclassified checks.</p>
    <div style={{overflowX:"auto",border:"1px solid #d8e0e6",borderRadius:8}}>
      <table style={{width:"100%",minWidth:1300,borderCollapse:"collapse",fontSize:13}}>
        <thead><tr>{["Component","Acceptance requirement","Code","Deployment","Runtime","Evidence","Blocker / remaining work","Last checked","Source"].map(x=><th key={x} scope="col" style={{textAlign:"left",padding:10,borderBottom:"2px solid #94a3b8",background:"#f1f5f9",whiteSpace:"nowrap"}}>{x}</th>)}</tr></thead>
        <tbody>{checks.map((item,i)=><tr key={item.component} style={{background:i%2?"#f8fafc":"white"}}>
          <th scope="row" style={{textAlign:"left",padding:10,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:145}}>{item.component}</th>
          <td style={{padding:10,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:205}}>{item.requirement}</td>
          {[item.code,item.deployment,item.runtime,item.evidence].map((gate,k)=><td key={k} style={{padding:10,borderBottom:"1px solid #e2e8f0",verticalAlign:"top"}}><GateCell value={gate}/></td>)}
          <td style={{padding:10,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:260}}>{item.blocker}</td>
          <td style={{padding:10,borderBottom:"1px solid #e2e8f0",verticalAlign:"top",minWidth:135}}>{item.lastVerified}</td>
          <td style={{padding:10,borderBottom:"1px solid #e2e8f0",verticalAlign:"top"}}><a href={item.source} target="_blank" rel="noopener noreferrer">{item.sourceLabel}</a></td>
        </tr>)}</tbody>
      </table>
    </div>
    <section aria-labelledby="scientific-gates">
      <h2 id="scientific-gates">Independent scientific acceptance gates</h2>
      <p><strong>SCIENCE:</strong> exact trial identity, 40 assessments, authoritative sources, uncertainty, conflicting evidence and independent reviewer signoffs must be verified before a readiness grade can be certified.</p>
      <p><strong>OUTCOME:</strong> FDA-labelled historical outcomes, prespecified holdouts, leakage checks, calibration and transparent error analysis must be verified before outcome probabilities can be certified.</p>
    </section>
    <p><strong>Sources:</strong> <a href={audit}>acceptance issue #331</a> · <a href={report}>saved nightly report</a> · <a href={sourceAudit}>newer source verification</a> · <a href={ci}>frontend/backend CI</a> · <a href={preview}>tracker preview deployment</a>.</p>
    <p><strong>Safety:</strong> this page does not trigger scans, rescoring, notifications, orders or trades, and does not alter restrictions or GEM JR/GEM FS/FA memberships.</p>
  </main>;
}
