import Link from "next/link";
import type {Metadata} from "next";
import {allSpecialtyEvidenceAudits} from "../../../../lib/medical-intelligence-specialty-evidence";
import {SPECIALIST_CASES} from "../../../../lib/medical-intelligence-specialist-casebook";
import {EXPANDED_SPECIALIST_CASES} from "../../../../lib/medical-intelligence-specialist-expanded";
import {CLINICAL_SPECIALTY_AXES} from "../../../../lib/medical-intelligence-specialty";
import {APPLICATION_CYCLES} from "../../../../lib/medical-intelligence-applications";

export const metadata:Metadata={
  title:"Clinical Specialist Evidence Coverage — PDUFA Intelligence",
  description:"Current-source coverage and outstanding clinical review questions for all FOCUS FDA application cycles."
};
export const dynamic="force-dynamic";
const border="#cbdacd",muted="#52645b",accent="#006351";
const cases=[...SPECIALIST_CASES,...EXPANDED_SPECIALIST_CASES];
const audits=allSpecialtyEvidenceAudits();
const sourceAxes=audits.reduce((n,a)=>n+a.sourceBackedAxes,0);
const totalAxes=APPLICATION_CYCLES.length*CLINICAL_SPECIALTY_AXES.length;

export default function SpecialistCoveragePage(){
 return <main style={{fontFamily:"system-ui,sans-serif",maxWidth:1390,margin:"26px auto",padding:"0 16px 42px",color:"#15392d"}}>
  <div style={{fontSize:12,letterSpacing:1,fontWeight:750,color:accent}}>CLINICAL SPECIALTY → ORIGINAL EVIDENCE → FDA REVIEW</div>
  <h1 style={{margin:"9px 0 6px"}}>Clinical subspecialty evidence coverage</h1>
  <p style={{lineHeight:1.6,maxWidth:1080}}>A reproducible audit of the available sourced evidence for every FOCUS application. A colored research position would be misleading here: <strong>source coverage is not completed physician-level medical adjudication</strong>. All ten review areas per application remain eligible for deeper source, statistical, comparative and specialist verification.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:10}}>
   {[
    ["Distinct FDA application cycles",audits.length],
    ["Ten-axis clinical research positions",totalAxes],
    ["Areas with relevant curated source",sourceAxes],
    ["Areas still lacking curated source",totalAxes-sourceAxes],
    ["Partial specialty case dossiers",cases.length],
    ["Licensed specialist sign-offs",0]
   ].map(([label,value])=><div key={String(label)} style={{border:"1px solid "+border,borderRadius:11,padding:14,background:"#fff"}}>
    <div style={{fontSize:12,color:muted}}>{label}</div><div style={{fontSize:28,fontWeight:750,marginTop:6}}>{value}</div>
   </div>)}
  </div>
  <section style={{border:"1px solid "+border,borderRadius:11,padding:16,background:"#fff",marginTop:17}}>
   <h2 style={{margin:"0 0 8px",fontSize:19}}>All application-level clinical investigations</h2>
   <p style={{fontSize:13,color:muted}}>The axis values below are numbers of *relevant source findings*, not questions answered or clinical risk grades. Multiple axes may reference the same source; those are not independent observations. Every case remains incomplete.</p>
   <div style={{overflowX:"auto"}}>
    <table style={{minWidth:1500,width:"100%",borderCollapse:"collapse",fontSize:12}}>
     <thead><tr>
      <th style={{textAlign:"left",borderBottom:"1px solid "+border,padding:9,minWidth:230}}>Application / clinical specialty</th>
      {CLINICAL_SPECIALTY_AXES.map(a=><th key={a.id} title={a.name} style={{textAlign:"center",borderBottom:"1px solid "+border,padding:8,minWidth:73}}>{a.id}<div style={{fontWeight:400,color:muted}}>{a.name.split(" ").slice(0,2).join(" ")}</div></th>)}
      <th style={{textAlign:"center",borderBottom:"1px solid "+border,padding:8}}>Sourced axes</th>
      <th style={{textAlign:"left",borderBottom:"1px solid "+border,padding:9}}>Depth status</th>
     </tr></thead>
     <tbody>{audits.map(a=>{
       const detail=cases.find(c=>c.cycleId===a.cycleId);
       return <tr key={a.cycleId} style={{borderBottom:"1px solid "+border}}>
        <td style={{padding:9}}><strong><Link href={"/medical-intelligence-preview/specialist-review?cycle="+a.cycleId}>{a.drug}</Link></strong><div style={{fontSize:11,color:muted}}>{a.specialty}</div></td>
        {a.axes.map(ax=><td key={ax.axis} title={ax.sourceCount?ax.sourceCount+" evidence pointers — clinical interpretation incomplete":"No curated evidence mapped to this topic"} style={{textAlign:"center",padding:8,color:ax.sourceCount?accent:muted,fontWeight:ax.sourceCount?700:400}}>{ax.sourceCount||"—"}</td>)}
        <td style={{textAlign:"center",padding:9}}><strong>{a.sourceBackedAxes}/10</strong></td>
        <td style={{padding:9,color:muted}}>{detail?detail.dimensions.length+" sourced interpretations; incomplete":"Initial curated evidence only; specialist review incomplete"}</td>
       </tr>;
     })}</tbody>
    </table>
   </div>
  </section>
  <section style={{border:"1px solid "+border,borderRadius:11,padding:16,marginTop:17,background:"#fff"}}>
   <h2 style={{margin:"0 0 7px",fontSize:18}}>What a completed specialist investigation still requires</h2>
   <p style={{fontSize:14,lineHeight:1.65}}>Clinical examination is not being performed. Instead, this system must develop a medical case interpretation using the original disease phenotype, full pivotal protocols and statistical plans, patient-important outcomes, competing treatment choices, adverse events, subgroups, contradictory FDA/sponsor analyses, and evidence that could reverse a recommendation. An actual physician or subspecialist sign-off is separate and has not occurred for any application.</p>
   <p style={{fontSize:13,color:muted,marginBottom:0}}>All material remains in an isolated development preview. <Link href="/medical-intelligence-preview/specialist-review">Return to clinical specialist dossiers</Link> · <Link href="/medical-intelligence-preview/failure-desk">FDA failure desk</Link> · <Link href="/medical-intelligence-preview/coverage">FOCUS trials</Link>.</p>
  </section>
 </main>;
}
