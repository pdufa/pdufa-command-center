import Link from "next/link";
import AnalyzeNowTrial from "../focus/AnalyzeNowTrial";
import type {Metadata} from "next";
import focus from "../../data/p3PostDataActive.json";

export const metadata:Metadata={
 title:"Analyze Now — exact-trial archived medical analysis | PDUFA",
 description:"Look up previously saved medical research by exact NCT, including after trial spreadsheet movement."
};
export const dynamic="force-dynamic";
export default async function AnalyzeNowHistoryPage({searchParams}:{searchParams:Promise<{nct?:string}>}){
 const query=await searchParams;
 const nct=typeof query.nct==="string"?query.nct.trim().toUpperCase():"";
 const valid=/^NCT\d{8}$/.test(nct);
 const member=valid&&focus.records.some(record=>record.nct===nct);
 const canary=nct==="NCT06081894";
 const rollout=process.env.PDUFA_ANALYZE_NOW_ALL_ENABLED==="true";
 const canStart=Boolean(member&&(canary||rollout));
 return <main style={{maxWidth:1000,margin:"28px auto",padding:"0 18px",fontFamily:"system-ui,sans-serif",color:"#183d2d"}}>
  <nav style={{display:"flex",gap:15}}><Link href="/main">MAIN</Link><Link href="/focus">FOCUS</Link></nav>
  <h1>Analyze Now · 12-stage medical research canary</h1>
  <p>Enter an exact ClinicalTrials.gov NCT to view immutable source-research history. Only the FOCUS canary NCT06081894 may start a new 12-stage research run before a verified database-backed rollout; older trials remain read-only. Running research requires an enabled preview backend and persistent PostgreSQL.</p>
  <p><strong>Medical evidence is not an FDA prediction.</strong> Approval, CRL, and review-delay outcomes stay ABSTAIN; certainty is not validated until independent calibration and review.</p>
  <form action="/analyze-now" method="get" style={{display:"flex",gap:9,flexWrap:"wrap",margin:"15px 0"}}>
   <label style={{display:"grid",gap:6,flex:"1 1 260px"}}>Exact NCT
    <input name="nct" defaultValue={nct} placeholder="NCT06081894" pattern="NCT[0-9]{8}" required
      style={{minHeight:39,padding:9,border:"1px solid #a8c8b4",borderRadius:7}}/>
   </label>
   <button type="submit" style={{alignSelf:"end",border:0,borderRadius:7,background:"#08614e",color:"white",padding:"11px 15px"}}>Find saved history</button>
  </form>
  {nct&&!valid&&<p role="alert" style={{color:"#99342a"}}>Enter a valid exact identifier, such as NCT06081894.</p>}
  {valid&&<section style={{padding:16,border:"1px solid #bfd6c6",borderRadius:10,background:"white"}}>
   <h2 style={{marginTop:0}}>{nct} · {canStart?"canary research and history":"read-only history"}</h2>
   <AnalyzeNowTrial nct={nct} enabled={canStart} historyOnly={!canStart}/>
   <p style={{fontSize:13,color:"#506a59"}}>{canStart?"The button requests a persistent source-only canary run, never an FDA forecast. If the preview PostgreSQL or backend has not been configured, the request fails closed.":"Choose History to retrieve prior revisions. Historical NCTs cannot start a new run without active FOCUS eligibility."}</p>
  </section>}
 </main>;
}
