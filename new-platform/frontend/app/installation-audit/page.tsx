import Link from "next/link";

type Check = { name: string; code: string; runtime: string; evidence: string; next: string };
const checks: Check[] = [
  { name: "Nightly 8 PM Pacific scanning", code: "Configured on main", runtime: "Not verified here", evidence: "Partial on 2026-10-24", next: "Inspect GitHub Actions full-chain execution and source reports" },
  { name: "Scientific assessment / 40 assessments", code: "Development present; full coverage unverified", runtime: "Not verified", evidence: "Not complete", next: "Verify each exact trial's source inputs, 40 assessments, uncertainty and citations" },
  { name: "Outcome prediction validation", code: "Audit development present; validated model unverified", runtime: "Not verified", evidence: "Not complete", next: "Reconcile authoritative FDA outcomes, evaluate calibration and leakage-free holdouts" },
  { name: "Daily RESULTS", code: "Date-indexed archive exists", runtime: "Not verified", evidence: "Partial", next: "Resolve source gaps; keep unknown counts null" },
  { name: "Pipeline qualification", code: "Not fully audited", runtime: "Not verified", evidence: "Qualified total unknown", next: "Verify public status, $300M–$10B market cap and mandatory filters" },
  { name: "GEM JR / GEM membership", code: "Saved ledgers reported", runtime: "Not verified", evidence: "11 GEM JR / 6 GEM members in 2026-10-24 report", next: "Preserve independent FS/FA preset associations" },
  { name: "WT", code: "Not fully audited", runtime: "Not verified", evidence: "Not verified", next: "Check current tracking and assessment operation" },
];
export default function InstallationAudit() {
  return <main style={{maxWidth:1100,margin:"0 auto",padding:"28px 18px",fontFamily:"system-ui,sans-serif",color:"#17212b"}}>
    <p><Link href="/">← Dashboard</Link></p>
    <h1>Installation & evidence readiness</h1>
    <p><strong>Read-only audit.</strong> Code presence, deployment, runtime operation and scientific evidence are separate gates. No grade or prediction is certified by this page.</p>
    <p>Baseline: 2026-10-25. Last saved nightly report: 2026-10-24, PARTIAL; 993/1121 source checks verified, 23 unresolved, 93 unavailable, 10 not applicable. This is a snapshot, not live status.</p>
    <div style={{overflowX:"auto"}}>
      <table style={{width:"100%",borderCollapse:"collapse",fontSize:14}}>
        <thead><tr>{["Component","Code","Runtime","Evidence","Next verification"].map(x=><th key={x} scope="col" style={{textAlign:"left",padding:10,borderBottom:"2px solid #a8b7c5"}}>{x}</th>)}</tr></thead>
        <tbody>{checks.map(x=><tr key={x.name}><th scope="row" style={{textAlign:"left",padding:10,borderBottom:"1px solid #d8e0e6"}}>{x.name}</th>{[x.code,x.runtime,x.evidence,x.next].map((v,i)=><td key={i} style={{padding:10,borderBottom:"1px solid #d8e0e6",verticalAlign:"top"}}>{v}</td>)}</tr>)}</tbody>
      </table>
    </div>
    <p>Source: <a href="https://github.com/pdufa/pdufa-command-center/blob/main/data/daily_scan_results.json">saved nightly results</a>. <a href="https://github.com/pdufa/pdufa-command-center/issues/331">Audit requirements</a>.</p>
    <p><strong>Safety:</strong> No scans, scoring, trading, restrictions or FS/FA memberships are changed by this page.</p>
  </main>;
}
