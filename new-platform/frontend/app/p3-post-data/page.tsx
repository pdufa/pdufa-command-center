import type {Metadata} from "next";
import Link from "next/link";
import TickerChartButton from "../TickerChartButton";
import {bottomOnlyReport} from "../../lib/bottom-only-completion";
import {BottomClinicalRating} from "../BottomOnlyCompletionSheet";
import snapshot from "../../data/p3PostDataActive.json";
import {FOCUS_FINAL_TRIAL_AUDIT} from "../../lib/focus-final-gate-checks";
import {bottomTrialHistory} from "../../lib/bottom-only-exports";

export const metadata:Metadata={
 title:"FOCUS — Final-list Phase 3 / post-Phase 3 candidates | PDUFA",
 description:"Current final-list FOCUS trial NCTs with dated issuer capitalization and source-linked Phase 3 and FDA path pointers; acceptance under review."
};
const source="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=202611061";
/** Snapshot of the user's source-of-truth Google Sheet. Historical 762-trial cohorts are not active listings. */
const trials=snapshot.records;
const finalGateAudit=FOCUS_FINAL_TRIAL_AUDIT;
const finalGateByNct=new Map(finalGateAudit.rows.map(row=>[row.nct,row]));
const researchByNct=new Map(bottomOnlyReport().trials.map(t=>[t.nctId,t]));

export default function P3PostDataPage(){
 return <main style={{maxWidth:1220,margin:"28px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif",color:"#173d2b"}}>
  <nav style={{display:"flex",gap:18,marginBottom:18}}><Link href="/pool">POOL</Link><Link href="/tools">TOOLS</Link></nav>
  <h1>FOCUS</h1>
  <p><strong>{trials.length} distinct NCT trials</strong> · Final-list Phase 3 / post-Phase 3 candidates · Reported $300M–$10B market caps · Source-linked FDA pathways requiring independent verification.</p>
  <p>Snapshot of the final Google Sheets list as of {snapshot.asOf}. Recorded listing, readout and FDA-path links are evidence pointers, not independent certification of trial eligibility or a successful nightly sync. Completed trials remain if their program may continue toward approval. No retired or historical research-only cohort is included.</p>
  <p><a href={source} target="_blank" rel="noopener noreferrer" style={{fontWeight:700}}>Open and edit the source-of-truth FOCUS spreadsheet</a></p>
  <p style={{fontSize:13}}>Saved RAAS research and scoring history stays attached to the exact NCT, where available. Missing history is not a zero score.</p>
  <section aria-label="Final trial gate coverage" style={{border:"1px solid #b9cebe",padding:14,borderRadius:8,marginBottom:14}}>
    <h2 style={{margin:"0 0 8px",fontSize:18}}>Acceptance gates · final FOCUS trials only</h2>
    <p style={{margin:"0 0 7px"}}><strong>{finalGateAudit.trialCount} exact NCTs</strong> from the dated FOCUS list · <strong>{finalGateAudit.checksPerTrial} checks per trial</strong> · <strong>{finalGateAudit.totalChecks} trial checks</strong>.</p>
    <p style={{margin:"0 0 7px"}}>Independently certified: <strong>{finalGateAudit.independentlyVerified}</strong> · Source pointers recorded: {finalGateAudit.pointers} · Awaiting source review: {finalGateAudit.review} · Missing evidence: {finalGateAudit.missing}.</p>
    <p style={{fontSize:13,margin:0}}>Only these exact final-list NCTs are evaluated; the early-phase POOL, historical Phase 3 census and all-phase TOOLS counts are not included. Recorded links or scheduled jobs are not completed clinical, regulatory or live synchronization verification. Current list as of {finalGateAudit.asOf}.</p>
  </section>
  <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
   <table style={{width:"100%",borderCollapse:"collapse",minWidth:970,fontSize:14}}>
    <thead style={{background:"#e6f2ea"}}><tr><th style={{padding:10,textAlign:"left"}}>Ticker</th><th style={{padding:10,textAlign:"left"}}>NCT / Trial</th><th style={{padding:10,textAlign:"left"}}>Company</th><th style={{padding:10,textAlign:"right"}}>Market cap ($B)</th><th style={{padding:10,textAlign:"left"}}>FDA / PDUFA path</th><th style={{padding:10}}>Sources</th><th style={{padding:10}}>7 gate checks</th><th style={{padding:10}}>Clinical research rating</th><th style={{padding:10}}>RAAS history</th></tr></thead>
    <tbody>{trials.map((t,i)=>{const history=bottomTrialHistory(t.nct);const research=researchByNct.get(t.nct);const gateAudit=finalGateByNct.get(t.nct);return <tr key={t.nct} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
      <td style={{padding:10,fontWeight:700}}><TickerChartButton ticker={t.ticker}/></td>
      <td style={{padding:10}}><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">{t.nct}</a>{research&&<small style={{display:"block"}}>{research.drug}</small>}</td>
      <td style={{padding:10}}>{t.company}</td>
      <td style={{padding:10,textAlign:"right"}}>{(t.marketCap/1e9).toFixed(2)}</td>
      <td style={{padding:10}}>{t.fdaStatus}</td>
      <td style={{padding:10,whiteSpace:"nowrap"}}><a href={t.resultsUrl} target="_blank" rel="noopener noreferrer">Phase 3 source</a>{" · "}<a href={t.regulatoryUrl} target="_blank" rel="noopener noreferrer">FDA source</a></td>
      <td style={{padding:10,minWidth:240,verticalAlign:"top"}}>{gateAudit?<details><summary style={{cursor:"pointer",fontWeight:650}}>{gateAudit.independentlyVerified} / {gateAudit.gates.length} verified · expand</summary>
        <div style={{fontSize:12,margin:"9px 0 0"}}>{gateAudit.gates.map(g=><div key={g.id} style={{borderTop:"1px solid #dbe9de",padding:"7px 0"}}>
          <strong>{g.title}</strong><div>{g.state==="RECORDED_POINTER"?"Source pointer only":g.state==="SOURCE_REVIEW_REQUIRED"?"Needs source review":"Missing evidence"}</div>
          <div>{g.note}</div>{g.sourceUrl&&<a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Inspect source</a>}
        </div>)}</div>
      </details>:<span role="alert">Gate identity mismatch — not verified</span>}</td>
      <td style={{padding:10,minWidth:180}}>{research?<BottomClinicalRating nctId={t.nct} score={research.clinicalFullScore} graded={research.clinicalScoredFactors}/>:<span>No exact-trial clinical review yet</span>}</td>
      <td style={{padding:10,minWidth:180}}>{history.length?<details><summary style={{cursor:"pointer"}}>{history.length} saved record{history.length===1?"":"s"}</summary>{history.map(h=><div key={h.eventId} style={{borderTop:"1px solid #dbe9de",padding:"8px 0",fontSize:12}}><strong>{h.recordedAt} · {h.eventType}</strong>{("clinicalFullScore" in h)&&<p>Clinical rating: {typeof h.clinicalFullScore==="number"?h.clinicalFullScore.toFixed(1)+" / 100":"Not fully scored"}</p>}<p>{h.note}</p></div>)}</details>:<span style={{color:"#687b6a",fontSize:12}}>No saved rating yet</span>}</td>
    </tr>;})}</tbody>
   </table>
  </div>
  <p style={{fontSize:12,color:"#4f6556",marginTop:15}}>Some entries are planned NDA/BLA filings rather than FDA-accepted submissions. Source snapshots require continued review.</p>
 </main>;
}
