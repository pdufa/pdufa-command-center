import Link from "next/link";
import type {Metadata} from "next";
import {notFound} from "next/navigation";
import {buildDecisionBrief} from "../../../../lib/medical-intelligence-decision-brief";
import type {ReviewedFinding} from "../../../../lib/medical-intelligence-reviewed-findings";

export const metadata:Metadata={title:"FDA Decision Brief — Deep Medical Intelligence",description:"Source-linked approval, CRL and timing evidence for a specific FDA application review cycle."};
export const dynamic="force-dynamic";
const ink="#15382d",muted="#52655d",line="#c6dacc",red="#8b342d";
function EvidenceGroup({title,items,description}:{title:string;items:ReviewedFinding[];description:string}){
 return <section style={{border:"1px solid "+line,padding:16,borderRadius:10,marginTop:14,background:"#fff"}}>
   <h2 style={{margin:"0 0 5px",fontSize:18}}>{title} ({items.length})</h2>
   <p style={{fontSize:13,color:muted,marginTop:2}}>{description}</p>
   {items.length===0?<p style={{fontSize:13,color:muted}}>No curated source-backed finding in this category. This does not prove that the candidate has no such risk.</p>:
    items.map(f=><details key={f.id} style={{borderTop:"1px solid "+line,padding:"11px 0"}}>
      <summary style={{fontWeight:700,cursor:"pointer"}}>{f.headline} <small style={{color:muted,fontWeight:400}}>({f.published})</small></summary>
      <div style={{fontSize:14,lineHeight:1.55}}>
        <p><strong>Evidence:</strong> {f.detail}</p>
        <p><strong>Regulatory relevance:</strong> {f.fdaRelevance}</p>
        <p><strong>Counterargument:</strong> {f.counterpoint}</p>
        <p><strong>Still unresolved:</strong> {f.remainingQuestion}</p>
        <p><a href={f.sourceUrl} target="_blank" rel="noopener noreferrer">Primary source: {f.sourceTitle}</a> · {f.evidence.replace(/_/g," ")}</p>
      </div>
    </details>)}
  </section>;
}
export default async function DecisionBriefPage({params}:{params:Promise<{id:string}>}){
 const {id}=await params;
 const brief=buildDecisionBrief(id);
 if(!brief)notFound();
 const a=brief.cycle;
 return <main style={{maxWidth:1140,margin:"26px auto",padding:"0 16px 44px",fontFamily:"system-ui,sans-serif",color:ink}}>
   <div style={{fontSize:12,fontWeight:750,color:"#006451",letterSpacing:1}}>FOCUS → APPLICATION → INDEPENDENT FAILURE-FIRST BRIEF</div>
   <h1 style={{margin:"10px 0 4px"}}>{a.ticker} · {a.drug}</h1>
   <p style={{marginTop:0,color:muted}}>{a.applicationType} · {a.indication}</p>
   <p style={{lineHeight:1.55}}>This is an <strong>application-specific decision research brief</strong>, not a score or the historical result of a survey. Every source-backed claim has a contrary argument and an unresolved verification question.</p>
   <section style={{background:"#f0f7f1",border:"1px solid "+line,borderRadius:12,padding:17}}>
     <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(190px,1fr))",gap:16}}>
       <div><small style={{color:muted}}>FDA application disposition</small><div style={{fontSize:20,fontWeight:750}}>{brief.outcome==="ALREADY_APPROVED"?"Approved in prior cycle":"Indeterminate"}</div></div>
       <div><small style={{color:muted}}>Next review timing outcome</small><div style={{fontSize:20,fontWeight:750}}>{brief.timing==="NOT_APPLICABLE"?"Not applicable to prior approval":"Indeterminate"}</div></div>
       <div><small style={{color:muted}}>Current source-reported stage</small><div style={{fontSize:16,fontWeight:750}}>{a.stage.replace(/_/g," ")}</div></div>
       <div><small style={{color:muted}}>Source-reported PDUFA goal</small><div style={{fontSize:16,fontWeight:750}}>{a.reportedGoal||"No current date established"}</div></div>
     </div>
     <p style={{marginBottom:0,color:muted,fontSize:13}}>Confidence: not calibrated · Research maturity: initial source mapping only · No numerical approval odds. An FDA prior CRL or an already announced PDUFA extension is not an automatic prediction that the next cycle fails.</p>
   </section>
   <section style={{border:"1px solid "+line,padding:16,borderRadius:10,marginTop:14,background:"#fff"}}>
     <h2 style={{margin:"0 0 8px",fontSize:18}}>Decision-critical unresolved question</h2>
     <p style={{fontWeight:650,lineHeight:1.6}}>{brief.primaryReviewQuestion}</p>
     <p style={{fontSize:13,color:muted}}>Linked NCT studies: {a.ncts.join(", ")}</p>
     <p style={{fontSize:13,marginBottom:0}}><a href={a.sourceUrl} target="_blank" rel="noopener noreferrer">Source establishing this application cycle ({a.sourceDate})</a></p>
   </section>
   <EvidenceGroup title="Documented FDA objections" items={brief.documentedFdaObjections} description="FDA-origin objections in the reviewed source record; not a final future decision."/>
   <EvidenceGroup title="Previous Complete Response Letters" items={brief.pastCrls} description="Historical application-level CRLs and their stated causes. Whether a new cycle resolves them must be established separately."/>
   <EvidenceGroup title="Scientific and statistical concerns" items={brief.scientificUncertainties} description="Observed endpoint failures, dose inconsistencies or safety signals. Sponsor/FDA evidence type is explicit; a concern is not automatically a CRL."/>
   <EvidenceGroup title="Evidence supporting approval" items={brief.approvalEvidence} description="Published clinical efficacy/benefit evidence; full trial and submission adjudication is still outstanding."/>
   <EvidenceGroup title="Previously confirmed PDUFA extensions" items={brief.priorExtensions} description="Recorded review timing events, not fresh extension forecasts."/>
   <EvidenceGroup title="Other regulatory and scientific context" items={brief.otherEvidence} description="Filing status, published interim reviews and other relevant source evidence."/>
   <section style={{border:"1px solid "+line,padding:16,borderRadius:10,marginTop:14}}>
     <h2 style={{margin:"0 0 8px",fontSize:18}}>What still blocks a defensible prediction?</h2>
     <ul style={{paddingLeft:22,lineHeight:1.6,fontSize:14}}>{brief.evidenceLimitations.map((g,i)=><li key={i}>{g}</li>)}</ul>
     <p style={{fontSize:13,color:red,marginBottom:0}}>Until independent source review resolves these material gaps, the system must not label this application as likely approved, likely CRL, or likely extended.</p>
   </section>
   <p style={{fontSize:13,color:muted,marginTop:20}}><Link href="/medical-intelligence-preview/applications">All application review cycles</Link> · <Link href={"/medical-intelligence-preview?nct="+a.ncts[0]}>Open trial evidence</Link> · <Link href="/medical-intelligence-preview/coverage">FOCUS registry audit</Link></p>
 </main>;
}
