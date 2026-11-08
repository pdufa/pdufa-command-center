import Link from "next/link";
import AnalyzeNowTrial from "../focus/AnalyzeNowTrial";
import type {Metadata} from "next";

export const metadata:Metadata={
 title:"Analyze Now — exact-trial archived medical analysis | PDUFA",
 description:"Look up previously saved medical research by exact NCT, including after trial spreadsheet movement."
};
export const dynamic="force-dynamic";
export default async function AnalyzeNowHistoryPage({searchParams}:{searchParams:Promise<{nct?:string}>}){
 const query=await searchParams;
 const nct=typeof query.nct==="string"?query.nct.trim().toUpperCase():"";
 const valid=/^NCT\d{8}$/.test(nct);
 return <main style={{maxWidth:1000,margin:"28px auto",padding:"0 18px",fontFamily:"system-ui,sans-serif",color:"#183d2d"}}>
  <nav style={{display:"flex",gap:15}}><Link href="/main">MAIN</Link><Link href="/focus">FOCUS</Link></nav>
  <h1>Analyze Now · complete saved trial history</h1>
  <p>Search an exact ClinicalTrials.gov NCT to retrieve prior saved research, including trials moved between POOL, FOCUS, or historical spreadsheets. This lookup is read-only and never starts a new analysis or installs advanced components.</p>
  <form action="/analyze-now" method="get" style={{display:"flex",gap:9,flexWrap:"wrap",margin:"15px 0"}}>
   <label style={{display:"grid",gap:6,flex:"1 1 260px"}}>Exact NCT
    <input name="nct" defaultValue={nct} placeholder="NCT06081894" pattern="NCT[0-9]{8}" required
      style={{minHeight:39,padding:9,border:"1px solid #a8c8b4",borderRadius:7}}/>
   </label>
   <button type="submit" style={{alignSelf:"end",border:0,borderRadius:7,background:"#08614e",color:"white",padding:"11px 15px"}}>Find saved history</button>
  </form>
  {nct&&!valid&&<p role="alert" style={{color:"#99342a"}}>Enter a valid exact identifier, such as NCT06081894.</p>}
  {valid&&<section style={{padding:16,border:"1px solid #bfd6c6",borderRadius:10,background:"white"}}>
   <h2 style={{marginTop:0}}>{nct} · read-only history</h2>
   <AnalyzeNowTrial nct={nct} enabled={false} historyOnly={true}/>
   <p style={{fontSize:13,color:"#506a59"}}>Choose History to retrieve all saved research revisions. The archived scores are historical source-backed research, not newly calculated RAAS grades or FDA approval forecasts.</p>
  </section>}
 </main>;
}
