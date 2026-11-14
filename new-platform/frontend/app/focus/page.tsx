import type {Metadata} from "next";
import Link from "next/link";
import TickerChartButton from "../TickerChartButton";
import IndicationIntelligence from "../IndicationIntelligence";
import ScientificStepsReadiness from "../ScientificStepsReadiness";
import {ExactTrialIntakeSelector} from "../ExactTrialScientificIntake";
import CompanyDateBadges from "../CompanyDateBadges";
import snapshot from "../../data/p3PostDataActive.json";
import designationData from "../../data/focusFdaDesignations.json";
import {FOCUS_FINAL_TRIAL_AUDIT} from "../../lib/focus-final-gate-checks";

export const metadata:Metadata={
 title:"FOCUS — Final-list Phase 3 / post-Phase 3 candidates | PDUFA",
 description:"Current final-list FOCUS trial NCTs with dated issuer capitalization and source-linked Phase 3 and FDA path pointers; acceptance under review."
};
const source="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=202611061";
/** Snapshot of the user's source-of-truth Google Sheet. Historical 762-trial cohorts are not active listings. */
const trials=snapshot.records;
const designationByNct=new Map(designationData.records.map(r=>[r.nct,r]));
const finalGateAudit=FOCUS_FINAL_TRIAL_AUDIT;
const finalGateByNct=new Map(finalGateAudit.rows.map(row=>[row.nct,row]));

export default function FocusPage(){
 return <main style={{maxWidth:1220,margin:"28px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif",color:"#173d2b"}}>
  <nav style={{display:"flex",gap:18,marginBottom:18}}><Link href="/pool">POOL</Link><Link href="/indications">INDICATIONS</Link><Link href="/tools">TOOLS</Link></nav>
  <h1>FOCUS</h1>
  <p data-testid="focus-owner-only" style={{padding:"10px 12px",background:"#eefaf5",border:"1px solid #b9cebe",borderRadius:8}}>
    <strong>OWNER-ONLY LEVELS 1–20:</strong> You check and accept FOCUS assessments.
    No external scientific reviewer, source attestor, independent challenger, or third-party signoff is required.
    Original source links, missing-evidence flags, and safety and phase checks remain.
  </p>
  <ScientificStepsReadiness cohort="FOCUS"/>
  <IndicationIntelligence mode="focus"/>
  <p><strong>{trials.length} distinct NCT trials</strong> · Final-list Phase 3 / post-Phase 3 candidates · Reported $300M–$10B market caps · Source-linked FDA pathways for owner checks; no external verification gate.</p>
  <p>Snapshot of the final Google Sheets list as of {snapshot.asOf}. Recorded listing, readout and FDA-path links are evidence pointers, not an owner-reviewed finding of trial eligibility or a successful nightly sync. Completed trials remain if their program may continue toward approval. No retired or historical research-only cohort is included.</p>
  <p><a href={source} target="_blank" rel="noopener noreferrer" style={{fontWeight:700}}>Open and edit the source-of-truth FOCUS spreadsheet</a></p>
  <p><Link href="/analyze-now?nct=NCT06081894">Open Analyze Now · PostgreSQL-backed saved research canary</Link> · Requires secure backend readiness; no FDA probabilities are released.</p>
  <p style={{fontSize:13}}>Active research uses clinical and regulatory source observations. Historical ratings are retained separately in the read-only archive and do not contribute to this view.</p>
  <section aria-label="Final trial gate coverage" style={{border:"1px solid #b9cebe",padding:14,borderRadius:8,marginBottom:14}}>
    <h2 style={{margin:"0 0 8px",fontSize:18}}>Acceptance gates · final FOCUS trials only</h2>
    <p style={{margin:"0 0 7px"}}><strong>{finalGateAudit.trialCount} exact NCTs</strong> from the dated FOCUS list · <strong>{finalGateAudit.checksPerTrial} checks per trial</strong> · <strong>{finalGateAudit.totalChecks} trial checks</strong>.</p>
    <p style={{margin:"0 0 7px"}}>Owner-reviewed assessments: <strong>0</strong> · Source pointers recorded: {finalGateAudit.pointers} · Awaiting source review: {finalGateAudit.review} · Missing evidence: {finalGateAudit.missing}.</p>
    <p style={{fontSize:13,margin:0}}>Only these exact final-list NCTs are evaluated; the early-phase POOL, historical Phase 3 census and all-phase TOOLS counts are not included. Recorded links or scheduled jobs are not completed clinical, regulatory or live synchronization verification. Current list as of {finalGateAudit.asOf}.</p>
  </section>
  <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
   <table style={{width:"100%",borderCollapse:"collapse",minWidth:970,fontSize:14}}>
    <thead style={{background:"#e6f2ea"}}><tr><th style={{padding:10,textAlign:"left"}}>Ticker</th><th style={{padding:10,textAlign:"left"}}>NCT / Trial</th><th style={{padding:10,textAlign:"left"}}>Company</th><th style={{padding:10,textAlign:"left"}}>FDA Special Designations</th><th style={{padding:10,textAlign:"right"}}>Market cap ($B)</th><th style={{padding:10,textAlign:"left"}}>FDA / PDUFA path</th><th style={{padding:10}}>Sources</th><th style={{padding:10}}>7 gate checks</th></tr></thead>
    <tbody>{trials.map((t,i)=>{const gateAudit=finalGateByNct.get(t.nct);const d=designationByNct.get(t.nct);return <tr key={t.nct} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
      <td style={{padding:10,fontWeight:700}}><TickerChartButton ticker={t.ticker}/></td>
      <td style={{padding:10}}><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">{t.nct}</a><div style={{marginTop:5,fontSize:12}}><Link href={"/analyze-now?nct="+encodeURIComponent(t.nct)}>View exact-trial research history</Link></div><details style={{marginTop:6}}><summary style={{cursor:"pointer",fontSize:12}}>Steps 1–3 · exact-program intake</summary><ExactTrialIntakeSelector cohort="FOCUS" nctId={t.nct}/></details></td>
      <td style={{padding:10}}>{t.company}<CompanyDateBadges nctId={t.nct} timeline={null} recordedReleaseDate={"recordedReleaseDate" in t && typeof t.recordedReleaseDate==="string" ? t.recordedReleaseDate : null} recordedPdufaDate={"recordedPdufaDate" in t && typeof t.recordedPdufaDate==="string" ? t.recordedPdufaDate : null} releaseSource={t.resultsUrl} pdufaSource={t.regulatoryUrl}/></td>
      <td style={{padding:10,minWidth:220,verticalAlign:"top",fontSize:12}}>
       {d?.designations.length?<><strong>{d.designations.map(x=>x.label).join(" · ")}</strong>
        <details style={{marginTop:5}}><summary style={{cursor:"pointer"}}>Branch 6 · Regulatory evidence ({d.designations.length})</summary>
          {d.designations.map((x,i)=><div key={i} style={{padding:"7px 0",borderTop:"1px solid #dce7e0"}}>
           <strong>{x.label}</strong> · {x.kind.replaceAll("_"," ")} · {x.verification==="FDA_DOCUMENT"?"FDA document":"Sponsor/SEC report"}
           <div>{x.scope}</div>{x.grantDate&&<div>Recorded date: {x.grantDate}</div>}
           <a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">Original designation evidence</a>
          </div>)}
        </details>
        <details style={{marginTop:5}}><summary style={{cursor:"pointer"}}>Branch 7 · FDA precedents and failure checks</summary>
          <div>Check whether historical FDA decisions for the same indication and regulatory pathway required additional studies, revised labeling, CMC changes or resulted in a CRL.</div>
          <div>Unknown: confidential FDA feedback, inspection outcomes, and whether the designation changes this application's approval risk.</div>
          <div>Designation alone is not proof of approval or a favorable forecast. No historical comparator adjudication completed here.</div>
        </details>
       </>:<span title={d?.notes||"No confirmed special designation for exact drug and indication; not a claim that no designation exists."}>Not verified</span>}
       </td>
      <td style={{padding:10,textAlign:"right"}}>{(t.marketCap/1e9).toFixed(2)}</td>
      <td style={{padding:10}}>{t.fdaStatus}</td>
      <td style={{padding:10,whiteSpace:"nowrap"}}><a href={t.resultsUrl} target="_blank" rel="noopener noreferrer">Phase 3 source</a>{" · "}<a href={t.regulatoryUrl} target="_blank" rel="noopener noreferrer">FDA source</a></td>
      <td style={{padding:10,minWidth:240,verticalAlign:"top"}}>{gateAudit?<details><summary style={{cursor:"pointer",fontWeight:650}}>{gateAudit.independentlyVerified} / {gateAudit.gates.length} verified · expand</summary>
        <div style={{fontSize:12,margin:"9px 0 0"}}>{gateAudit.gates.map(g=><div key={g.id} style={{borderTop:"1px solid #dbe9de",padding:"7px 0"}}>
          <strong>{g.title}</strong><div>{g.state==="RECORDED_POINTER"?"Source pointer only":g.state==="SOURCE_REVIEW_REQUIRED"?"Needs source review":"Missing evidence"}</div>
          <div>{g.note}</div>{g.sourceUrl&&<a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Inspect source</a>}
        </div>)}</div>
      </details>:<span role="alert">Gate identity mismatch — not verified</span>}</td>
    </tr>;})}</tbody>
   </table>
  </div>
  <p style={{fontSize:12,color:"#4f6556",marginTop:15}}>Some entries are planned NDA/BLA filings rather than FDA-accepted submissions. Source snapshots require continued review.</p>
 </main>;
}
