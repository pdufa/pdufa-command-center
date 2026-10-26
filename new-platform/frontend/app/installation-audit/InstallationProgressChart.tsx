import type { AuditGroup, AuditTotals } from "../../lib/installation-audit-summary";
import { AUDIT_BASELINE, compareAuditToBaseline } from "../../lib/installation-audit-history";

/**
 * This page reports evidence STATES, not estimated implementation effort.
 * Positive-looking code or deployment signals NEVER become accepted tasks.
 */
const segments = [
  { key: "independentlyVerified", label: "Independently verified gate", color: "#166534" },
  { key: "implementationSignals", label: "Code/deployment evidence only", color: "#2563eb" },
  { key: "partial", label: "Partially verified", color: "#d97706" },
  { key: "unverified", label: "Not verified or not audited", color: "#64748b" },
] as const;

type Counts = Pick<AuditTotals, "gates" | "independentlyVerified" | "implementationSignals" | "partial" | "unverified">;

function EvidenceBar({counts, name, height = 18}: {counts: Counts; name: string; height?: number}) {
  const denominator = counts.gates;
  const accessible = segments.map(item => item.label + ": " + counts[item.key] + " of " + denominator).join("; ");
  return <div role="img" aria-label={name + " — " + accessible} style={{
    width:"100%", height, background:"#e2e8f0", borderRadius:6, display:"flex", overflow:"hidden",
    border:"1px solid #cbd5e1",
  }}>
    {segments.map(item => counts[item.key] > 0 && <div key={item.key} style={{
      width: (100 * counts[item.key] / denominator) + "%",
      background: item.color,
      borderRight:"1px solid rgba(255,255,255,.8)",
    }}/>)}
  </div>;
}

const delta = (n: number) => n > 0 ? "+" + n : String(n);
const countLine = (count: number, total: number) => count + "/" + total;

/** Read-only, reproducible chart. Accepts computed tracker totals, never hard-coded current counts. */
export default function InstallationProgressChart({groups, total}: {
  groups: AuditGroup[];
  total: AuditTotals;
}) {
  const change = compareAuditToBaseline(groups, total);
  return <section aria-labelledby="acceptance-chart-heading" style={{
    border:"1px solid #cbd5e1", borderRadius:12, background:"#f8fafc",
    padding:"18px", margin:"18px 0",
  }}>
    <h3 id="acceptance-chart-heading" style={{margin:"0 0 10px"}}>Completed and remaining — evidence-based progress chart</h3>
    <p style={{margin:"0 0 14px"}}>
      <strong>{countLine(total.accepted,total.sections)} fully accepted requirements</strong> and{" "}
      <strong>{countLine(total.sections-total.accepted,total.sections)} requirements still open</strong>.
      A requirement is accepted only after its runtime and applicable evidence gates are verified.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,230px),1fr))",gap:10,marginBottom:16}}>
      <div style={{padding:12,borderRadius:8,border:"1px solid #cbd5e1",background:"#fff"}}>
        <strong style={{fontSize:24,display:"block"}}>{countLine(total.accepted,total.sections)}</strong>
        <span>Fully accepted sections</span>
      </div>
      <div style={{padding:12,borderRadius:8,border:"1px solid #cbd5e1",background:"#fff"}}>
        <strong style={{fontSize:24,display:"block"}}>{countLine(total.sections-total.accepted,total.sections)}</strong>
        <span>Sections still open</span>
      </div>
      <div style={{padding:12,borderRadius:8,border:"1px solid #cbd5e1",background:"#fff"}}>
        <strong style={{fontSize:24,display:"block"}}>{countLine(total.independentlyVerified,total.gates)}</strong>
        <span>Independently verified individual gates</span>
      </div>
    </div>
    <p style={{margin:"4px 0 8px",fontWeight:650}}>Individual gate evidence — {total.gates} applicable gates</p>
    <EvidenceBar counts={total} name="All three systems" height={22}/>
    <div aria-label="Gate status legend" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,215px),1fr))",gap:"8px 14px",margin:"12px 0 22px"}}>
      {segments.map(item => <span key={item.key} style={{fontSize:13,display:"flex",alignItems:"center",gap:7}}>
        <span aria-hidden="true" style={{width:11,height:11,background:item.color,display:"inline-block",flexShrink:0,borderRadius:2}}/>
        <span>{item.label}: <strong>{countLine(total[item.key],total.gates)}</strong></span>
      </span>)}
    </div>
    <h4 style={{margin:"0 0 12px"}}>Progress by system — denominators kept separate</h4>
    <div style={{display:"grid",gap:14}}>
      {groups.map(group => <div key={group.name} style={{padding:12,background:"#fff",borderRadius:8,border:"1px solid #d5dce4"}}>
        <div style={{display:"flex",flexWrap:"wrap",justifyContent:"space-between",gap:"4px 12px",marginBottom:7}}>
          <strong>{group.name}</strong>
          <span style={{fontSize:13}}>{countLine(group.totals.accepted,group.totals.sections)} sections accepted · {countLine(group.totals.sections-group.totals.accepted,group.totals.sections)} open</span>
        </div>
        <EvidenceBar counts={group.totals} name={group.name} height={16}/>
        <p style={{fontSize:12,margin:"7px 0 0",lineHeight:1.6}}>
          Verified {countLine(group.totals.independentlyVerified,group.totals.gates)} ·
          {" "}Code/deployment {countLine(group.totals.implementationSignals,group.totals.gates)} ·
          {" "}Partial {countLine(group.totals.partial,group.totals.gates)} ·
          {" "}Unverified {countLine(group.totals.unverified,group.totals.gates)}
        </p>
      </div>)}
    </div>
    <h4 style={{margin:"20px 0 8px"}}>Change since the recorded baseline</h4>
    {change ? <>
      <p style={{fontSize:13,margin:"0 0 12px"}}>
        Baseline: <a href={AUDIT_BASELINE.url} target="_blank" rel="noopener noreferrer">October 25, 2026, 5:05 PM Pacific, commit {AUDIT_BASELINE.commit.slice(0,7)}</a>.
        The baseline is an actual saved checklist, not an assumed starting point.
      </p>
      <div style={{display:"grid",gap:7,fontSize:13}}>
        <div><strong>Baseline:</strong> {countLine(AUDIT_BASELINE.total.accepted,AUDIT_BASELINE.total.sections)} accepted sections
          <EvidenceBar counts={AUDIT_BASELINE.total} name="Recorded October 25 baseline" height={14}/></div>
        <div><strong>Current checklist:</strong> {countLine(total.accepted,total.sections)} accepted sections
          <EvidenceBar counts={total} name="Current saved checklist" height={14}/></div>
      </div>
      <p style={{fontSize:13,margin:"10px 0 0"}}>
        <strong>Acceptance change: {delta(change.fullyAccepted)} of {total.sections} sections.</strong>{" "}
        Partial gates {countLine(AUDIT_BASELINE.total.partial,total.gates)} → {countLine(total.partial,total.gates)} ({delta(change.partial)});
        {" "}unverified gates {countLine(AUDIT_BASELINE.total.unverified,total.gates)} → {countLine(total.unverified,total.gates)} ({delta(change.unverified)}).
        Moving to partial is progress in verification, not full acceptance.
      </p>
    </> : <p role="status">
      The requirement scope or denominators changed, so a comparison with the prior checklist is withheld.
      Review the underlying requirements before interpreting any apparent percentage difference.
    </p>}
    <p style={{margin:"17px 0 0",fontSize:13,color:"#475569"}}>
      <strong>Accuracy note:</strong> All current bars recalculate from the 15 dated checklist rows directly below.
      A blue segment means supporting code or a deployed build, <em>not</em> a completed scientific or runtime requirement.
      Grey means not yet verified/audited, <em>not</em> proven absent. One evidence gate is not applicable and excluded.
      This is a saved, read-only acceptance snapshot—not a live measure of engineering hours remaining.
      Check the source links and last-verified dates in each expanded workstream for the evidence behind every item.
    </p>
  </section>;
}
