import type {Metadata} from "next";
import Link from "next/link";
import focus from "../../data/p3PostDataActive.json";

export const metadata:Metadata={
 title:"FDA outcome assessments — Independent Medical Intelligence | PDUFA",
 description:"Evidence-gated independent FDA approval, complete response and review-delay decisions for current FOCUS trials."
};
export const dynamic="force-dynamic";

const outcomes=["APPROVAL","COMPLETE RESPONSE LETTER","REVIEW DELAY"] as const;
const panel={border:"1px solid #c4d9c9",borderRadius:10,padding:14,background:"white"} as const;
const subtle={color:"#4e6558",fontSize:13,lineHeight:1.6} as const;

/** The active prediction page never imports archived scores or historical
 * scoring forecasts. This table displays explicit abstention until the
 * separate scientific evidence and temporal calibration release gates pass.
 */
export default function PredictionsPage(){
 return <main style={{maxWidth:1220,margin:"28px auto",padding:"0 18px",fontFamily:"system-ui,sans-serif",color:"#193d2d"}}>
  <nav style={{display:"flex",gap:15,marginBottom:16}}>
   <Link href="/main">MAIN</Link><Link href="/focus">FOCUS</Link>
   <Link href="/medical-intelligence-preview/advanced">12 medical investigation levels</Link>
  </nav>
  <h1>FDA prediction engine · independent medical evidence</h1>
  <p style={subtle}>Approval, Complete Response Letter (CRL), and review-delay outcomes are independent research questions. No current trial has a verified historical-calibration release and independently adjudicated FDA dossier. An absent probability is not zero, a negative recommendation, or a completed review.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(175px,1fr))",gap:10,margin:"15px 0"}}>
   {outcomes.map(name=><section key={name} style={panel}>
     <h2 style={{fontSize:14,margin:"0 0 6px"}}>{name}</h2>
     <strong>ABSTAIN</strong>
     <p style={subtle}>No validated numerical forecast</p>
   </section>)}
   <section style={panel}>
    <h2 style={{fontSize:14,margin:"0 0 6px"}}>Independent certainty</h2>
    <strong>NOT VALIDATED</strong>
    <p style={subtle}>No reliability rating issued</p>
   </section>
  </div>
  <section style={panel}>
   <h2>FOCUS research candidates · dated roster</h2>
   <p style={subtle}>The {focus.records.length} exact-NCT entries are source pointers dated {focus.asOf}. Their filing eligibility and reviewer findings need ongoing verification. Click to inspect available medical evidence and saved research history, not a fabricated probability.</p>
   <div style={{overflowX:"auto"}}>
    <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
     <thead><tr style={{textAlign:"left",background:"#e9f2ec"}}>
      <th style={{padding:9}}>Trial</th><th style={{padding:9}}>Company / drug</th>
      <th style={{padding:9}}>Approval</th><th style={{padding:9}}>CRL</th>
      <th style={{padding:9}}>Review delay</th><th style={{padding:9}}>Certainty</th><th style={{padding:9}}>Evidence</th>
     </tr></thead>
     <tbody>{focus.records.map(r=><tr key={r.nct} style={{borderTop:"1px solid #d7e7db"}}>
      <td style={{padding:9}}>{r.nct}</td>
      <td style={{padding:9}}>{r.company}</td>
      <td style={{padding:9}}>ABSTAIN</td><td style={{padding:9}}>ABSTAIN</td>
      <td style={{padding:9}}>ABSTAIN</td><td style={{padding:9}}>Not validated</td>
      <td style={{padding:9}}><Link href={"/medical-intelligence-preview?nct="+encodeURIComponent(r.nct)}>Open source review</Link></td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  <p style={{...subtle,marginTop:15}}>This page is read-only. No trial is automatically approved, rejected, traded, or assigned numerical certainty from its appearance here.</p>
 </main>;
}
