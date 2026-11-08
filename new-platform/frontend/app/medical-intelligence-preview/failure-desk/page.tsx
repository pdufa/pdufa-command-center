import Link from "next/link";
import type {Metadata} from "next";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";
import {FAILURE_DESK,FAILURE_DESK_AS_OF,deskIssuesForCycle, type ReviewIssue} from "../../../lib/medical-intelligence-failure-desk";

export const metadata:Metadata={
 title:"FDA Failure-First Decision Desk — Medical Intelligence",
 description:"Source-linked evidence and unresolved failure mechanisms for near-term FDA application cycles."
};
export const dynamic="force-dynamic";
const colors={text:"#16372d",muted:"#53675e",line:"#cbdacf",bg:"#f4f8f4",danger:"#8d352e",accent:"#006356"};
const outer={border:"1px solid "+colors.line,borderRadius:12,padding:16,background:"#fff"} as const;
const labels:Record<ReviewIssue["evidenceClass"],string>={
 FDA_REVIEWER_OBJECTION:"FDA reviewer objection",
 TRIAL_SIGNAL:"Observed clinical or statistical signal",
 PREVIOUS_CRL:"Previous CRL",
 PRIOR_EXTENSION:"Past PDUFA extension",
 SPONSOR_MITIGATION:"Sponsor's supporting response",
 REVIEW_GAP:"Evidence still needed"
};
const consequences:Record<ReviewIssue["consequence"],string>={
 POTENTIAL_CRL:"Potential CRL relevance — not predicted",
 LABEL_OR_BENEFIT_RISK:"Potential safety / labeling relevance",
 REVIEW_TIMING:"Documented prior timing event",
 NEEDS_VERIFICATION:"More evidence required"
};
const sourceTypes:Record<ReviewIssue["sourceType"],string>={
 FDA:"FDA reviewer document",
 SEC_SPONSOR:"SEC-filed sponsor disclosure",
 SPONSOR:"Company clinical or regulatory release"
};
const today="2026-11-07";
function daysUntil(date:string|null):number|null{
 if(!date||!/^20\d\d-\d\d-\d\d$/.test(date))return null;
 return Math.round((Date.parse(date+"T00:00:00Z")-Date.parse(today+"T00:00:00Z"))/86400000);
}
function Issue({item}:{item:ReviewIssue}){
 return <details style={{border:"1px solid "+colors.line,borderRadius:9,padding:"12px 14px",margin:"9px 0",background:"#fff"}}>
   <summary style={{cursor:"pointer",fontWeight:700,lineHeight:1.5}}>
     <span style={{display:"block",color:item.evidenceClass==="FDA_REVIEWER_OBJECTION"||item.evidenceClass==="PREVIOUS_CRL"?colors.danger:colors.muted,fontSize:12,fontWeight:650,marginBottom:3}}>
       {labels[item.evidenceClass]} · {sourceTypes[item.sourceType]} · {item.sourceDate}
     </span>
     {item.title}
   </summary>
   <div style={{fontSize:14,lineHeight:1.6,marginTop:11}}>
     <p><strong>Observed:</strong> {item.observation}</p>
     <p><strong>Why it could matter:</strong> {item.whyItMatters}</p>
     <p><strong>Counterevidence or mitigation:</strong> {item.responseOrCounterevidence}</p>
     <p><strong>Current evidence status:</strong> {item.resolutionState.replace(/_/g," ").toLowerCase()}.</p>
     <p><strong>Potential consequence:</strong> {consequences[item.consequence]}.</p>
     <p><strong>Most important next verification:</strong> {item.decisiveFollowUp}</p>
     <p><a href={item.sourceUrl} target="_blank" rel="noopener noreferrer" style={{color:colors.accent}}>{item.sourceTitle}</a></p>
   </div>
 </details>;
}
export default function FailureDesk(){
 const all=[...APPLICATION_CYCLES].sort((a,b)=>(a.reportedGoal||"9999-12-31").localeCompare(b.reportedGoal||"9999-12-31"));
 const researched=all.filter(a=>deskIssuesForCycle(a.id).length>0);
 const remaining=all.filter(a=>deskIssuesForCycle(a.id).length===0);
 const documented=FAILURE_DESK.filter(i=>i.evidenceClass==="FDA_REVIEWER_OBJECTION"||i.evidenceClass==="PREVIOUS_CRL").length;
 return <main style={{maxWidth:1330,margin:"24px auto",padding:"0 16px 44px",fontFamily:"system-ui,sans-serif",color:colors.text}}>
   <div style={{color:colors.accent,letterSpacing:1,fontSize:12,fontWeight:750}}>FOCUS → APPLICATION → FAILURE-FIRST RESEARCH</div>
   <h1 style={{fontSize:"clamp(1.6rem,4vw,2.4rem)",margin:"10px 0 6px"}}>FDA failure-first decision desk</h1>
   <p style={{maxWidth:1040,lineHeight:1.6}}>
     Targeted investigation of what could cause a <strong>Complete Response Letter, restricted label, or delayed FDA decision</strong>. This desk distinguishes a confirmed reviewer objection, an observed trial signal, historical regulatory events, sponsor explanations, and missing information. It is <strong>not a score or a forecast</strong>.
   </p>
   <p style={{fontSize:13,color:colors.muted}}>Research cut-off: {FAILURE_DESK_AS_OF}. Calendar reference: {today}. Goal dates are tied to dated public filings and can change; no confidential FDA correspondence is accessible.</p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:10,margin:"18px 0"}}>
     {[
       ["FOCUS application cycles",APPLICATION_CYCLES.length],
       ["Targeted failure reviews",researched.length],
       ["Sourced review issues",FAILURE_DESK.length],
       ["FDA-reviewer objections or past CRLs",documented]
     ].map(([name,value])=><div key={String(name)} style={outer}><div style={{fontSize:12,color:colors.muted}}>{name}</div><div style={{fontSize:28,fontWeight:750,marginTop:6}}>{value}</div></div>)}
   </div>
   <section style={{...outer,marginTop:16}}>
     <h2 style={{margin:"0 0 8px",fontSize:19}}>Near-term and high-impact investigation cases</h2>
     <p style={{fontSize:13,color:colors.muted}}>Ordered by public PDUFA goals where available; a company with a previous CRL but no accepted current application remains in the queue without an invented goal. Every case below has an incomplete final FDA decision review.</p>
     {researched.map(a=>{
       const issues=deskIssuesForCycle(a.id);
       const days=daysUntil(a.reportedGoal);
       const fda=issues.filter(x=>x.evidenceClass==="FDA_REVIEWER_OBJECTION").length;
       const pastCrl=issues.filter(x=>x.evidenceClass==="PREVIOUS_CRL").length;
       const trial=issues.filter(x=>x.evidenceClass==="TRIAL_SIGNAL").length;
       return <article key={a.id} style={{...outer,marginTop:12,background:colors.bg}}>
         <div style={{display:"flex",flexWrap:"wrap",justifyContent:"space-between",gap:12}}>
           <div style={{flex:"2 1 330px"}}>
             <div style={{fontSize:12,color:colors.muted,fontWeight:650}}>{a.ticker} · {a.applicationType} · {a.indication}</div>
             <h3 style={{margin:"4px 0 6px",fontSize:20}}>{a.drug}</h3>
             <p style={{fontSize:14,margin:"4px 0",maxWidth:700}}><strong>Decision-critical question:</strong> {a.criticalQuestion}</p>
             <div style={{marginTop:8,fontSize:13}}><Link href={"/medical-intelligence-preview/applications/"+a.id}>Open full application evidence brief</Link></div>
           </div>
           <div style={{flex:"1 1 180px",textAlign:"left",background:"#fff",border:"1px solid "+colors.line,borderRadius:9,padding:12}}>
             <div style={{fontSize:12,color:colors.muted}}>Source-reported FDA goal</div>
             <strong style={{fontSize:17}}>{a.reportedGoal||"Not assigned"}</strong>
             <div style={{fontSize:12,color:colors.muted,marginTop:4}}>{days===null?"No verified review clock":days>=0?days+" calendar days from Nov 7":"Historical recorded goal"}</div>
             <div style={{fontSize:13,marginTop:7,fontWeight:700}}>FDA outcome: INDETERMINATE</div>
             <div style={{fontSize:12,color:colors.muted}}>Timing outlook: not assessed</div>
           </div>
         </div>
         <p style={{fontSize:12,color:colors.muted,margin:"12px 0 2px"}}>{issues.length} sourced investigation issues · {fda} direct FDA reviewer objection(s) · {pastCrl} historical CRL reference(s) · {trial} observed trial signal(s). This is not a ranking of approval odds.</p>
         <details style={{marginTop:6}}>
           <summary style={{fontWeight:750,cursor:"pointer",padding:"9px 0",color:colors.accent}}>Expand documented issues, counterarguments and clearance questions</summary>
           {issues.map(issue=><Issue item={issue} key={issue.id}/>)}
         </details>
       </article>;
     })}
   </section>
   <section style={{...outer,marginTop:16}}>
     <h2 style={{margin:"0 0 7px",fontSize:19}}>Other applications awaiting targeted adjudication ({remaining.length})</h2>
     <p style={{fontSize:13,color:colors.muted}}>These cycles already have an initial source-backed dossier in the main application center, but not the deeper issue-by-issue investigation used above. Absence from the targeted desk never means no FDA risk.</p>
     <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
       {remaining.map(a=><div key={a.id} style={{padding:11,border:"1px solid "+colors.line,borderRadius:9,minWidth:220,maxWidth:350,flex:"1 1 230px"}}>
         <div style={{fontWeight:750,fontSize:13}}>{a.ticker} · {a.drug}</div>
         <div style={{fontSize:12,color:colors.muted}}>{a.reportedGoal||"No assigned goal"} · Review not fully adjudicated</div>
         <div style={{fontSize:13,marginTop:6}}><Link href={"/medical-intelligence-preview/applications/"+a.id}>Existing evidence brief</Link></div>
       </div>)}
     </div>
   </section>
   <p style={{marginTop:18,fontSize:13,color:colors.muted}}><Link href="/medical-intelligence-preview/applications">All FDA application cycles</Link> · <Link href="/medical-intelligence-preview/coverage">All 29 FOCUS trials</Link> · <Link href="/medical-intelligence-preview">Individual clinical dossiers</Link>. All additions are read-only and isolated from production POOL/FOCUS.</p>
 </main>;
}
