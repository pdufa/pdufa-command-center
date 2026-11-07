import type {Metadata} from "next";
import Link from "next/link";
import snapshot from "../../data/p3PostDataActive.json";

export const metadata:Metadata={
 title:"P3 POST-DATA — Results-released FDA/PDUFA candidates | PDUFA",
 description:"Only companies with $300M–$10B market cap, published Phase 3 results and an active FDA/PDUFA application path."
};
const source="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=202611061";
/** Snapshot of the user's source-of-truth Google Sheet. Historical 762-trial cohorts are not active listings. */
const trials=snapshot.records;

export default function P3PostDataPage(){
 return <main style={{maxWidth:1220,margin:"28px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif",color:"#173d2b"}}>
  <nav style={{display:"flex",gap:18,marginBottom:18}}><Link href="/pool">POOL</Link><Link href="/tools">TOOLS</Link></nav>
  <h1>P3 POST-DATA</h1>
  <p><strong>{trials.length} distinct NCT trials</strong> · Publicly reported Phase 3 results · $300M–$10B market cap · Current FDA/PDUFA path.</p>
  <p>Snapshot of the verified Google Sheets list as of {snapshot.asOf}. Refreshed from the source of truth after the scheduled sync. Completed trials remain if their drug continues toward approval. No TOP, GEM or historical research-only cohort is included.</p>
  <p><a href={source} target="_blank" rel="noopener noreferrer" style={{fontWeight:700}}>Open and edit the source-of-truth P3 Post-Data spreadsheet</a></p>
  <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
   <table style={{width:"100%",borderCollapse:"collapse",minWidth:780,fontSize:14}}>
    <thead style={{background:"#e6f2ea"}}><tr><th style={{padding:10,textAlign:"left"}}>Ticker</th><th style={{padding:10,textAlign:"left"}}>NCT / Trial</th><th style={{padding:10,textAlign:"left"}}>Company</th><th style={{padding:10,textAlign:"right"}}>Market cap ($B)</th><th style={{padding:10,textAlign:"left"}}>FDA / PDUFA path</th><th style={{padding:10}}>Sources</th></tr></thead>
    <tbody>{trials.map((t,i)=><tr key={t.nct} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
      <td style={{padding:10,fontWeight:700}}>{t.ticker}</td>
      <td style={{padding:10}}><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">{t.nct}</a></td>
      <td style={{padding:10}}>{t.company}</td>
      <td style={{padding:10,textAlign:"right"}}>{(t.marketCap/1e9).toFixed(2)}</td>
      <td style={{padding:10}}>{t.fdaStatus}</td>
      <td style={{padding:10,whiteSpace:"nowrap"}}><a href={t.resultsUrl} target="_blank" rel="noopener noreferrer">Phase 3</a>{" · "}<a href={t.regulatoryUrl} target="_blank" rel="noopener noreferrer">FDA path</a></td>
    </tr>)}</tbody>
   </table>
  </div>
  <p style={{fontSize:12,color:"#4f6556",marginTop:15}}>Some entries are planned NDA/BLA filings rather than FDA-accepted submissions. Source snapshots require continued review.</p>
 </main>;
}
