import type {Metadata} from "next";
import Link from "next/link";
import ledger from "../../public/phase3-unified-classifications-2026-11-05.json";
import {auditCensus,ENABLED_POLICY,DISABLED_POLICY} from "../../lib/pdufa-selected-restrictions";
export const dynamic="force-dynamic";
export const metadata:Metadata={title:"PIPELINE · Selected Restrictions | PDUFA",description:"23 selected source-aware controls, 7 disabled optional restrictions and live status of the dated 762-NCT research census."};
const panel={padding:16,border:"1px solid #91a7a0",borderRadius:12,marginBottom:12} as const;
export default function RestrictionsPage(){
 const asOf=new Date().toISOString().slice(0,10);
 const valid=ledger.total===762&&ledger.rows.length===762&&new Set(ledger.rows.map(t=>t.nctId)).size===762;
 if(!valid)return <main className="shell"><h1>Restrictions</h1><p role="alert">The source census failed verification. No counts or exclusions have been applied.</p></main>;
 const audit=auditCensus(ledger.rows,asOf);
 const ruleById=new Map(audit.rules.map(r=>[r.id,r]));
 return <main className="shell" style={{maxWidth:1100}}>
  <div className="topline">POOL → ACTIVE PHASE VIEW / HISTORICAL BENCHMARKS / PDUFA</div>
  <h1>Selected Pipeline restrictions</h1>
  <p><strong>{ENABLED_POLICY.length} selected</strong> and <strong>{DISABLED_POLICY.length} optional restrictions OFF</strong>. This page audits the saved November 2026 research census; it does not treat unverified issuer rights, market caps, applications or statuses as passed restrictions.</p>
  <section style={panel} aria-label="Current study status split">
   <h2>762 trial records · study lifecycle</h2>
   <div style={{display:"flex",flexWrap:"wrap",gap:20}}>
    <p><strong>{audit.lifecycle.ACTIVE}</strong> active-study rows</p>
    <p><strong>{audit.lifecycle.HISTORICAL}</strong> completed / terminated / withdrawn</p>
    <p><strong>{audit.lifecycle.VERIFY}</strong> status verification required</p>
   </div>
   <p>Closed trials are hidden from the Active Phase View, <strong>not deleted</strong>. Keep any completed study still supporting an active NDA/BLA or PDUFA program in separate regulatory monitoring after exact-application verification.</p>
   <p><Link href="/phase-first">Open Phase View</Link> · <Link href="/pipeline">Open PDUFA Pipeline</Link> · <a href="/api/pdufa-restriction-audit?format=csv">Download all 762 rule assessments (CSV)</a></p>
  </section>
  <h2>23 selected controls <span title="Tap the circled i for a rule explanation" aria-label="More information">ⓘ</span></h2>
  <p>Counts are independent research checks, not a cumulatively verified Pipeline funnel. Only the Active Phase View lifecycle filter is an automatic view exclusion in this change. For other rules, UNKNOWN means no exact source-backed verdict can yet be established.</p>
  <div style={{display:"grid",gap:9}}>
   {ENABLED_POLICY.map((rule,i)=>{
    const result=ruleById.get(rule.id)!;
    return <details key={rule.id} style={{...panel,marginBottom:0}}>
     <summary style={{cursor:"pointer",display:"flex",alignItems:"center",flexWrap:"wrap",justifyContent:"space-between",gap:8}}>
      <span><strong>☑ {i+1}. {rule.label}</strong> <span title="Open for an explanation" aria-label="Information about this restriction" style={{fontWeight:700,color:"#2176a7"}}>ⓘ</span></span>
      <small>{result.counts.PASS} pass · {result.counts.FAIL} fail · {result.counts.UNKNOWN} unknown</small>
     </summary>
     <div style={{paddingTop:12}}>
      <p>{rule.detail}</p><p><strong>Audit role:</strong> {rule.kind.replaceAll("_"," ")}. {result.note}</p>
      {rule.id==="activeview"&&<p>FAIL means excluded <em>only</em> from the Active Phase View, not a failed drug program or FDA decision.</p>}
     </div>
    </details>;
   })}
  </div>
  <section style={{...panel,marginTop:16}}>
   <h2>Optional restrictions — disabled</h2>
   <p>These seven optional restrictions are disabled and do not affect current trial selection or independent medical evidence.</p>
   {DISABLED_POLICY.map(rule=><p key={rule.id}>☐ {rule.label} <span title={rule.detail} aria-label={rule.detail} style={{color:"#2176a7",cursor:"help"}}>ⓘ</span></p>)}
  </section>
  <section style={panel}>
   <h2>Pending enforcement and verification</h2>
   <p>Current listing, entry/current cap quotes, sponsor rights, exact FDA application crosswalks, phase-specific scientific evidence and recurring source refreshes need independently verified inputs. Until then their audit status is UNKNOWN, not PASS or FAIL. The dated census does not establish regulatory eligibility or production prediction readiness.</p>
   <p>Research source: <a href="/api/pdufa-restriction-audit">Audit JSON</a> · snapshot {ledger.asOf} · checked {asOf}. Historical trials, scores, predictions and benchmarks are preserved.</p>
  </section>
 </main>;
}
