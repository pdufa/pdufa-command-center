import Link from "next/link";
import type {Metadata} from "next";
import focus from "../../../../data/p3PostDataActive.json";
import {applicationsForNct} from "../../../../lib/medical-intelligence-applications";
import {caseForCycle,MEDICAL_CASES} from "../../../../lib/medical-intelligence-md-casebook";
import {DEEP_ASSESSMENTS,SCIENTIFIC_LAYERS,SCIENTIFIC_LEVELS,DEPTH_SLOT_COUNT} from "../../../../lib/medical-intelligence-master-depth";

export const metadata:Metadata={title:"20-Level Scientific Investigation Coverage — FOCUS",description:"Evidence-gated progress audit of the Medical Master scientific analysis across all FOCUS trials."};
export const dynamic="force-dynamic";
const border="#c6dacd",subtle="#4f665a";
const rows=focus.records.map(r=>{
 const cases=applicationsForNct(r.nct).map(a=>caseForCycle(a.id)).filter(c=>c?.nct===r.nct);
 const positions=cases.flatMap(c=>c?.investigations||[]);
 const keys=new Set(positions.map(x=>x.assessmentId+":L"+x.level));
 return {...r,positions:keys.size,example:cases.length>0};
});
const examined=rows.reduce((n,r)=>n+r.positions,0);
export default function MedicalDepthCoverage(){
 return <main style={{fontFamily:"system-ui,sans-serif",maxWidth:1340,margin:"26px auto",padding:"0 16px 42px",color:"#15382d"}}>
  <div style={{fontSize:12,fontWeight:700,letterSpacing:1,color:"#006452"}}>INDEPENDENT MEDICAL SCIENCE → VERIFIABLE RESEARCH COVERAGE</div>
  <h1 style={{margin:"10px 0"}}>Medical Master Depth · 29-FOCUS evidence coverage</h1>
  <p style={{lineHeight:1.6}}>Every FOCUS trial has access to the same <strong>20-level × 40-assessment investigation system</strong>. A trial has up to 800 possible investigation positions, but only medically applicable positions should be performed, and none is counted as completed merely because a question exists.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:10}}>
   {[
    ["FOCUS trials",rows.length],
    ["Scientific methods",SCIENTIFIC_LEVELS.length],
    ["Assessment topics",DEEP_ASSESSMENTS.length],
    ["Potential positions per trial",DEPTH_SLOT_COUNT],
    ["Source-examined example positions",examined],
    ["Programs with source-examined examples",MEDICAL_CASES.length]
   ].map(([label,value])=><div key={String(label)} style={{border:"1px solid "+border,borderRadius:10,padding:13,background:"#fff"}}><div style={{color:subtle,fontSize:12}}>{label}</div><div style={{fontSize:27,fontWeight:750,marginTop:5}}>{value}</div></div>)}
  </div>
  <section style={{border:"1px solid "+border,padding:16,borderRadius:11,marginTop:15,background:"#fff"}}>
   <h2 style={{margin:"0 0 5px",fontSize:19}}>Phase-appropriate investigation ledger</h2>
   <p style={{fontSize:13,color:subtle}}>Source-examined positions are separately documented examples, <strong>not</strong> complete investigation of a 20-level method or the entire application. Other source findings exist in the 29-trial medical intelligence ledger; they have not been automatically converted into Master-depth completion claims.</p>
   <div style={{overflowX:"auto"}}>
    <table style={{width:"100%",minWidth:800,borderCollapse:"collapse",fontSize:13}}>
     <thead><tr>{["Trial","FOCUS source","Master-depth framework","Source-examined example positions","Current limitation"].map(h=><th key={h} style={{textAlign:"left",padding:9,background:"#f0f7f0",borderBottom:"1px solid "+border}}>{h}</th>)}</tr></thead>
     <tbody>{rows.map(r=><tr key={r.nct} style={{borderBottom:"1px solid "+border}}>
      <td style={{padding:9}}><strong>{r.ticker}</strong><div><Link href={"/medical-intelligence-preview/master-depth?nct="+r.nct+"&assessment=4.3"}>{r.nct} · open Master investigation</Link></div></td>
      <td style={{padding:9}}>{r.company}</td>
      <td style={{padding:9}}>8 layers · 40 assessments · 20 levels</td>
      <td style={{padding:9}}><strong>{r.positions}</strong> / 800 potential</td>
      <td style={{padding:9,color:subtle}}>{r.example?"Source-examined example; still requires full clinical and FDA review":"No Master-level source adjudication yet"}</td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  <section style={{border:"1px solid "+border,padding:16,borderRadius:11,marginTop:15,background:"#fff"}}>
   <h2 style={{fontSize:18,margin:"0 0 8px"}}>Eight scientific layers and evidence standard</h2>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(270px,1fr))",gap:9}}>
    {SCIENTIFIC_LAYERS.map((layer,i)=><div key={layer.id} style={{padding:12,background:"#f3f7f3",borderRadius:9}}>
      <strong>{i+1}. {layer.title}</strong>
      <p style={{margin:"6px 0 0",fontSize:12,color:subtle}}>Five focused assessments; each gets 20 scientific methods only where applicable and adequately sourced.</p>
    </div>)}
   </div>
  </section>
  <p style={{fontSize:13,color:subtle,marginTop:20}}>All research remains on an isolated preview branch. <Link href="/medical-intelligence-preview/master-depth">Return to interactive Master Depth</Link> · <Link href="/medical-intelligence-preview/failure-desk">Open FDA failure desk</Link>.</p>
 </main>;
}
