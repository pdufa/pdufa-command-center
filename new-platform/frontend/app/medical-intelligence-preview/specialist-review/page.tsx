import Link from "next/link";
import type {Metadata} from "next";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";
import {CLINICAL_SPECIALTY_AXES,CLINICAL_SPECIALTY_PROFILES,CLINICAL_SPECIALTY_ASSIGNMENTS,CLINICAL_SPECIALTY_STANDARDS,getSpecialtyProfile,getSpecialtyTasks} from "../../../lib/medical-intelligence-specialty";
import {caseForCycle} from "../../../lib/medical-intelligence-md-casebook";
import {ALL_SPECIALIST_CASES,getFullSpecialistCase} from "../../../lib/medical-intelligence-specialist-all";
import {buildSpecialtyEvidenceAudit} from "../../../lib/medical-intelligence-specialty-evidence";
import {deskIssuesForCycle} from "../../../lib/medical-intelligence-failure-desk";

export const metadata:Metadata={
  title:"Clinical Subspecialty Review — PDUFA Deep Medical Intelligence",
  description:"Disease-specialized clinical evidence review, patient-important outcomes and FDA risk interpretation by indication."
};
export const dynamic="force-dynamic";
const theme={ink:"#173a30",muted:"#56685e",line:"#c9dacf",light:"#f3f8f4",green:"#006453"};
const card={background:"#fff",padding:16,border:"1px solid "+theme.line,borderRadius:12} as const;
type SearchParams={cycle?:string};

export default async function SpecialistReviewPage({searchParams}:{searchParams:Promise<SearchParams>}){
 const q=await searchParams;
 const selected=APPLICATION_CYCLES.find(x=>x.id===q.cycle)||APPLICATION_CYCLES.find(x=>x.id==="capr-deramiocel")||APPLICATION_CYCLES[0];
 const p=getSpecialtyProfile(selected.id);
 const tasks=getSpecialtyTasks(selected.id);
 const research=caseForCycle(selected.id);
 const actualSpecialtyReview=getFullSpecialistCase(selected.id);
 const clinicalAudit=buildSpecialtyEvidenceAudit(selected.id);
 const sourceIssues=deskIssuesForCycle(selected.id);
 const sourceCounts=ALL_SPECIALIST_CASES.length;
 return <main style={{maxWidth:1320,margin:"26px auto",padding:"0 16px 45px",fontFamily:"system-ui,sans-serif",color:theme.ink}}>
   <div style={{fontWeight:750,color:theme.green,letterSpacing:1,fontSize:12}}>CLINICAL SPECIALTY SCIENCE → INDEPENDENT FDA EVIDENCE REVIEW</div>
   <h1 style={{fontSize:"clamp(1.7rem,4vw,2.4rem)",margin:"9px 0 5px"}}>Clinical Subspecialty Intelligence</h1>
   <p style={{fontSize:14,fontWeight:700}}><Link href="/medical-intelligence-preview/specialist-review/coverage">Clinical evidence coverage: 23 applications</Link></p>
   <p style={{maxWidth:1040,lineHeight:1.65}}>
     This is the <strong>medical-doctor specialist depth</strong> you requested: investigation of disease phenotype, diagnosis, prognosis, meaningful patient benefit, treatment decisions, serious adverse effects and how these change a drug&apos;s clinical benefit-risk case. The questions are tailored to the indication and reviewed against original sources. <strong>It is not a clinical specialist&apos;s signed opinion</strong> and does not pretend a licensed physician has examined or endorsed an application.
   </p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:10,marginTop:15}}>
     {[
       ["Specialty-specific profiles",CLINICAL_SPECIALTY_PROFILES.length],
       ["Application cycles mapped",Object.keys(CLINICAL_SPECIALTY_ASSIGNMENTS).length],
       ["Clinical reasoning domains",CLINICAL_SPECIALTY_AXES.length],
       ["Applications with partial specialty case analyses",sourceCounts]
     ].map(([label,value])=><div style={card} key={String(label)}><div style={{fontSize:12,color:theme.muted}}>{label}</div><div style={{fontSize:26,fontWeight:750,marginTop:7}}>{value}</div></div>)}
   </div>
   <section style={{...card,marginTop:17}}>
     <h2 style={{fontSize:19,margin:"0 0 8px"}}>Select an application and its relevant medical specialty</h2>
     <form action="/medical-intelligence-preview/specialist-review" method="get" style={{display:"flex",gap:10,flexWrap:"wrap",alignItems:"end"}}>
       <label style={{display:"grid",gap:6,flex:"1 1 420px",fontSize:13,fontWeight:700}}>FOCUS drug / medical indication
         <select defaultValue={selected.id} name="cycle" style={{padding:12,border:"1px solid #a3bdad",borderRadius:8,background:"#fff",fontSize:14}}>
           {APPLICATION_CYCLES.map(a=><option key={a.id} value={a.id}>{a.ticker} · {a.drug} — {a.indication}</option>)}
         </select>
       </label>
       <button type="submit" style={{padding:12,border:0,borderRadius:8,color:"white",background:theme.green,cursor:"pointer",fontWeight:700}}>Review medical evidence</button>
     </form>
   </section>
   {p&&<section style={{...card,marginTop:15}}>
     <div style={{fontSize:12,color:theme.green,fontWeight:750}}>SPECIALTY CLINICAL REVIEW · APPLICATION-CYCLE SPECIFIC</div>
     <h2 style={{margin:"6px 0",fontSize:22}}>{p.specialty}</h2>
     <p style={{fontSize:15}}><strong>{selected.drug}</strong> · {selected.indication} · {selected.applicationType} · {selected.stage.replace(/_/g," ")}</p>
     <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(270px,1fr))",gap:10}}>
       {[
        ["Biological and disease focus",p.mechanism],
        ["Medical phenotype, staging and differential",p.clinicalContext],
        ["Patient-important outcomes",p.meaningfulOutcomes],
        ["Subgroups that change clinical decisions",p.subgroups],
        ["Potential serious harms to adjudicate",p.seriousRisks],
        ["Core skeptical specialist challenge",p.coreChallenge]
       ].map(([label,text])=><div key={label} style={{padding:13,background:theme.light,borderRadius:9}}>
         <strong style={{fontSize:13}}>{label}</strong>
         <p style={{fontSize:13,lineHeight:1.55,margin:"7px 0 0"}}>{text}</p>
       </div>)}
     </div>
     <p style={{fontSize:13,color:theme.muted,marginBottom:0}}>These are clinical research targets, not findings that the candidate actually has each listed medical problem. Every claim requires disease-specific evidence and a current-cycle FDA relevance check.</p>
   </section>}
   <section style={{...card,marginTop:15}}>
     <h2 style={{fontSize:19,margin:"0 0 8px"}}>Ten disease-specialist reasoning investigations</h2>
     <p style={{fontSize:13,color:theme.muted,lineHeight:1.6}}>All ten are required lines of inquiry when applicable; they are <strong>not marked medically adjudicated</strong> merely because we can generate precise questions. The purpose is to replicate the scrutiny of specialty-level case interpretation.</p>
     <div style={{display:"grid",gap:8}}>
       {tasks.map((task,i)=><details key={task.id} style={{padding:"12px 14px",border:"1px solid "+theme.line,borderRadius:9}} open={i===3}>
         <summary style={{fontWeight:700,cursor:"pointer"}}>
           {task.axis}. {CLINICAL_SPECIALTY_AXES[i].name}
           <span style={{fontSize:12,fontWeight:450,color:theme.muted}}> · Not yet independently clinically adjudicated</span>
         </summary>
         <div style={{fontSize:14,lineHeight:1.6,paddingTop:9}}>
           <p><strong>Clinical challenge:</strong> {task.prompt}</p>
           <p><strong>Evidence required:</strong> {task.requiredEvidence}</p>
           <p><strong>How this could affect FDA:</strong> {task.potentialFdaConsequence}</p>
           {clinicalAudit&&<div style={{background:theme.light,padding:12,borderRadius:8,marginTop:10}}>
             <strong>Relevant published-source triage:</strong> {clinicalAudit.axes[i]?.sourceCount??0} curated findings.
             <span style={{fontSize:12,color:theme.muted}}> Not a completed specialist adjudication.</span>
             {clinicalAudit.axes[i]?.supportingSourceFindings.map(f=><details key={f.id} style={{borderTop:"1px solid "+theme.line,padding:"8px 0"}}>
               <summary style={{fontWeight:700,cursor:"pointer",fontSize:13}}>{f.headline} · {f.evidence.replace(/_/g," ")}</summary>
               <p style={{margin:"7px 0"}}><strong>Published evidence:</strong> {f.detail}</p>
               <p style={{margin:"7px 0"}}><strong>Clinical/FDA implication:</strong> {f.fdaRelevance}</p>
               <p style={{margin:"7px 0"}}><strong>Counterevidence:</strong> {f.counterpoint}</p>
               <p style={{margin:"7px 0"}}><strong>Still to resolve:</strong> {f.remainingQuestion}</p>
               <a target="_blank" rel="noopener noreferrer" href={f.sourceUrl}>{f.sourceTitle} ({f.published})</a>
             </details>)}
             {clinicalAudit.axes[i]?.notes.map((note,j)=><p key={j} style={{fontSize:12,color:theme.muted,marginBottom:3}}>{note}</p>)}
           </div>}
         </div>
       </details>)}
     </div>
   </section>
   {actualSpecialtyReview&&<section style={{...card,marginTop:15}} aria-label="Source-examined clinical subspecialty case analysis">
     <div style={{fontSize:12,fontWeight:750,color:theme.green}}>SOURCE-EXAMINED SPECIALTY-STYLE REASONING · NOT A LICENSED PHYSICIAN'S SIGN-OFF</div>
     <h2 style={{fontSize:21,margin:"7px 0"}}>{actualSpecialtyReview.specialty} · clinical case interpretation</h2>
     <p style={{fontSize:15,lineHeight:1.6}}><strong>Central medical question:</strong> {actualSpecialtyReview.medicalQuestion}</p>
     <p style={{fontSize:13,color:theme.muted}}>{actualSpecialtyReview.dimensions.length} domain-specific clinical interpretations grounded in existing public records. The data do not substitute for the complete clinical study report or patient-level records.</p>
     <div style={{display:"grid",gap:9,marginTop:13}}>
       {actualSpecialtyReview.dimensions.map((dimension,i)=><details key={dimension.topic} open={i===0} style={{border:"1px solid "+theme.line,borderRadius:9,padding:"12px 14px"}}>
         <summary style={{cursor:"pointer",fontWeight:700}}>{i+1}. {dimension.topic}</summary>
         <div style={{fontSize:14,lineHeight:1.6,paddingTop:9}}>
           <p><strong>Current published clinical evidence:</strong> {dimension.observedClinicalEvidence}</p>
           <p><strong>Specialty-style interpretation:</strong> {dimension.specialistInterpretation}</p>
           <p><strong>What the evidence must still resolve:</strong> {dimension.neededToResolve}</p>
           {dimension.sourceUrl&&<p style={{fontSize:12}}><a target="_blank" rel="noopener noreferrer" href={dimension.sourceUrl}>Original dated source ({dimension.sourceDate||"date unavailable"})</a></p>}
         </div>
       </details>)}
     </div>
     <p style={{fontSize:13,marginBottom:0}}>Lead reference: <a href={actualSpecialtyReview.source} target="_blank" rel="noopener noreferrer">{actualSpecialtyReview.sourceTitle}</a>. This is a partial public-evidence interpretation, not a completed medical adjudication, licensed specialist opinion or FDA outcome prediction. Individual source links are shown where curated; earlier examples may provide only a lead source.</p>
   </section>}
   <section style={{...card,marginTop:15}}>
     <h2 style={{margin:"0 0 8px",fontSize:19}}>Actual source-examined medical evidence</h2>
     {research?<>
       <p style={{fontSize:13,color:theme.muted}}>Partial source-examined case: <strong>{research.investigations.length}</strong> evidence-linked medical-scientific positions. This is still not a full subspecialist assessment or FDA decision. Original source: <a href={research.source} target="_blank" rel="noopener noreferrer">{research.sourceTitle}</a>.</p>
       <p style={{lineHeight:1.6}}><strong>Central clinical issue:</strong> {research.finding}</p>
       <p style={{lineHeight:1.6}}><strong>Best counterargument:</strong> {research.strongestCounter}</p>
       <div style={{overflowX:"auto"}}>
         <table style={{borderCollapse:"collapse",minWidth:650,width:"100%",fontSize:13}}>
           <thead><tr>{["Sourced medical measure","Result","Evidence provenance"].map(x=><th key={x} style={{padding:9,textAlign:"left",borderBottom:"1px solid "+theme.line}}>{x}</th>)}</tr></thead>
           <tbody>{research.facts.map((f,i)=><tr key={i}>
             <td style={{padding:9,borderBottom:"1px solid "+theme.line}}>{f.label}</td>
             <td style={{padding:9,borderBottom:"1px solid "+theme.line}}>{f.value}</td>
             <td style={{padding:9,borderBottom:"1px solid "+theme.line}}>{f.source}</td>
           </tr>)}</tbody>
         </table>
       </div>
       <details style={{marginTop:12}}>
         <summary style={{fontWeight:700,cursor:"pointer"}}>What evidence must the specialist-level review still resolve?</summary>
         <ul style={{fontSize:13,lineHeight:1.65}}>{research.uncertainties.map((u,i)=><li key={i}>{u}</li>)}</ul>
       </details>
     </>:<p style={{fontSize:14,lineHeight:1.55}}>No expanded source-examined specialty case is available for this application yet. Its clinical research questions above are tailored to the disease, but they must be answered using original studies, independent medical literature, current treatment standards and pertinent FDA source documents.</p>}
     <div style={{borderTop:"1px solid "+theme.line,marginTop:14,paddingTop:10}}>
       <strong>Existing targeted FDA evidence ({sourceIssues.length} issues)</strong>
       <p style={{fontSize:13,color:theme.muted}}>Investigate all clinical findings and their counterevidence independently before a regulatory outcome assessment.</p>
       {sourceIssues.map(issue=><details key={issue.id} style={{padding:"9px 0",borderTop:"1px solid "+theme.line}}>
         <summary style={{fontSize:13,fontWeight:700,cursor:"pointer"}}>{issue.title} · {issue.evidenceClass.replace(/_/g," ")}</summary>
         <div style={{fontSize:13,lineHeight:1.6,paddingTop:7}}>
           <p>{issue.observation}</p>
           <p><strong>Clinical/FDA relevance:</strong> {issue.whyItMatters}</p>
           <p><strong>Counterevidence:</strong> {issue.responseOrCounterevidence}</p>
           <p><strong>What needs resolving:</strong> {issue.decisiveFollowUp}</p>
           <a href={issue.sourceUrl} target="_blank" rel="noopener noreferrer">{issue.sourceTitle}</a>
         </div>
       </details>)}
     </div>
   </section>
   <section style={{...card,marginTop:15}}>
     <h2 style={{fontSize:18,margin:"0 0 8px"}}>Specialty-review evidence standard</h2>
     <p style={{fontSize:13,lineHeight:1.6}}>Relevant original clinical studies, full statistical plans, a disease-specific standard-of-care comparison, patient-important outcome validation, serious safety assessment, contradictory data and independently sourced regulatory concerns must be reviewed before a conclusion is described as medically comprehensive. A clinical specialist's actual review/sign-off is a separate process.</p>
     <div style={{fontSize:13,lineHeight:1.9}}>{CLINICAL_SPECIALTY_STANDARDS.map(s=><div key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a></div>)}</div>
     <p style={{fontSize:13,color:theme.muted}}>Status: research framework + partial sourced examples. Clinical sign-off: none. FDA application disposition and timing forecast: indeterminate unless independently established. No invented approval odds.</p>
   </section>
   <p style={{fontSize:13,color:theme.muted,marginTop:18}}><Link href="/medical-intelligence-preview">FOCUS trial evidence</Link> · <Link href="/medical-intelligence-preview/master-depth">20-level scientific analysis</Link> · <Link href="/medical-intelligence-preview/applications">FDA application dossiers</Link>. This preview cannot alter production POOL or FOCUS.</p>
 </main>;
}
