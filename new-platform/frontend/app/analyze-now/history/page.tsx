import type {Metadata} from "next";
import Link from "next/link";
import AnalyzeNowTrial from "../../focus/AnalyzeNowTrial";
export const metadata:Metadata={title:"Analyze Now — exact-NCT research history | PDUFA",
 description:"Read-only durable medical research history by exact registry trial identity, independent of spreadsheet location."};
export const dynamic="force-dynamic";
export default async function AnalyzeHistory({searchParams}:{
 searchParams:Promise<{nct?:string}>
}){
 const q=await searchParams;
 const nct=typeof q.nct==="string"&&/^NCT\d{8}$/.test(q.nct)?q.nct:null;
 return <main style={{maxWidth:960,margin:"28px auto",padding:"0 17px",fontFamily:"system-ui,sans-serif",color:"#163a2a"}}>
  <p><Link href="/focus">FOCUS</Link> · <Link href="/main">MAIN</Link></p>
  <h1>Analyze Now — historical trial record</h1>
  <p>Search by exact ClinicalTrials.gov NCT number. Completed research remains attached to its NCT when a trial moves from POOL to FOCUS, between worksheets, or leaves the active FOCUS roster. This does not authorize new work on an ineligible trial.</p>
  <form action="/analyze-now/history" method="GET" style={{display:"flex",gap:10,flexWrap:"wrap",margin:"16px 0",padding:14,border:"1px solid #c8d9ce",borderRadius:10}}>
   <label htmlFor="history-nct" style={{fontWeight:700,alignSelf:"center"}}>Exact NCT</label>
   <input name="nct" id="history-nct" type="text" inputMode="text" pattern="NCT[0-9]{8}" placeholder="NCT06081894" defaultValue={nct??""} required
    style={{padding:9,border:"1px solid #c8d9ce",borderRadius:7,minWidth:190}}/>
   <button type="submit" style={{padding:"9px 16px",background:"#00695a",color:"white",border:0,borderRadius:7,fontWeight:700}}>Find saved history</button>
  </form>
  {nct?<section style={{border:"1px solid #c8d9ce",borderRadius:10,padding:15}}>
    <h2 style={{fontSize:18,marginTop:0}}>Historical saved analyses · {nct}</h2>
    <p style={{fontSize:13,color:"#526a5b"}}>Sign in to access private research history. Select History to retrieve immutable reports. This page never starts an analysis.</p>
    <AnalyzeNowTrial nct={nct} enabled={false} historyOnly/>
   </section>:<p style={{color:"#526a5b"}}>Enter a valid NCT to retrieve its complete saved analysis history. An invalid or unavailable NCT is not treated as a completed analysis.</p>}
 </main>;
}
