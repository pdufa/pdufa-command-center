import Link from "next/link";
import type {Metadata} from "next";
import {
 ADJUDICATION_CASES,ADJUDICATION_AS_OF,INVESTIGATION_PRIORITIES,
 adverseEventAbsoluteDifference,type AdjudicationClaim,type AdjudicationCase
} from "../../../lib/medical-intelligence-clinical-adjudication";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";

export const metadata:Metadata={
 title:"Independent Clinical Adjudication — Deep Medical Intelligence",
 description:"Trace original FDA, trial publication and sponsor evidence in disputed efficacy and benefit-risk cases."
};
export const dynamic="force-dynamic";
const ink="#15382d",muted="#52665b",line="#c6d9cb",green="#006453",red="#893e32";
const card={padding:16,border:"1px solid "+line,borderRadius:12,background:"#fff"} as const;
const small={fontSize:13,lineHeight:1.6,color:muted} as const;
const dateRange=(d:string|null)=>d||"No confirmed current goal";
function Claim({claim}:{claim:AdjudicationClaim}){
 const label=claim.type==="FDA_REVIEWER"?"FDA reviewer analysis":
  claim.type==="FDA_DOCUMENTED_APPLICANT_ANALYSIS"?"Applicant model recorded in FDA document":
  claim.type==="PEER_REVIEWED_TRIAL"?"Peer-reviewed clinical trial":
  claim.type==="SPONSOR_REPORT_OF_FDA_COMMUNICATION"?"Sponsor's report of FDA meeting":
  claim.type==="SPONSOR_STATUS"?"Sponsor-reported application status":"Sponsor-reported clinical data";
 return <div style={{border:"1px solid "+line,borderRadius:9,padding:13,background:"#fff"}}>
   <div style={{fontSize:12,fontWeight:750,color:claim.role==="CHALLENGING"?red:green}}>
     {claim.role==="CHALLENGING"?"Evidence challenging the favorable interpretation":claim.role==="FAVORABLE"?"Evidence favoring the treatment claim":"Context requiring independent verification"}
   </div>
   <div style={{fontSize:12,color:muted,marginTop:4}}>{label} · {claim.date} · {claim.trial}</div>
   <h4 style={{margin:"7px 0 5px",fontSize:15}}>{claim.measure}</h4>
   <p style={{fontSize:14,fontWeight:650,lineHeight:1.5,margin:"5px 0"}}>{claim.result}</p>
   <p style={{...small,margin:"7px 0"}}><strong>Interpretive restriction:</strong> {claim.limits}</p>
   <p style={{...small,margin:"8px 0 0"}}><a href={claim.url} target="_blank" rel="noopener noreferrer" style={{color:green}}>{claim.title}</a> · {claim.section}</p>
 </div>;
}
function Case({item}:{item:AdjudicationCase}){
 const cycle=APPLICATION_CYCLES.find(a=>a.id===item.cycleId);
 return <article id={item.id} style={{...card,marginTop:14}}>
   <div style={{color:green,fontSize:12,letterSpacing:0.6,fontWeight:750}}>DETAILED SOURCE ADJUDICATION · {item.mode.replace(/_/g," ")}</div>
   <h2 style={{fontSize:21,margin:"6px 0"}}>{cycle?.ticker} · {item.title}</h2>
   <p style={{...small,margin:"3px 0 12px"}}>{item.specialty} · {item.nct} · Review as of {item.researchDate} · Current FDA disposition: <strong>indeterminate</strong></p>
   <div style={{padding:13,background:"#f1f7f2",borderRadius:9,lineHeight:1.6,fontSize:14}}>
     <p style={{margin:"0 0 9px"}}><strong>Clinical specialist question:</strong> {item.clinicalQuestion}</p>
     <p style={{margin:0}}><strong>FDA reviewer question:</strong> {item.regulatoryQuestion}</p>
   </div>
   <h3 style={{fontSize:17,margin:"16px 0 9px"}}>Original evidence, compared—not blended</h3>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(265px,1fr))",gap:9}}>
    {item.sources.map(claim=><Claim key={claim.id} claim={claim}/>)}
   </div>
   <section style={{marginTop:15,fontSize:14,lineHeight:1.65}}>
     <p><strong>Independent clinical synthesis:</strong> {item.clinicalSynthesis}</p>
     <p><strong>Mechanism that could prevent approval:</strong> {item.whyItCouldFail}</p>
     <p><strong>Strongest favorable explanation:</strong> {item.bestCase}</p>
     <p style={{color:muted}}><strong>Evidence classification:</strong> {item.sourceInterpretation}</p>
   </section>
   <details style={{marginTop:12,border:"1px solid "+line,borderRadius:9,padding:"11px 13px"}}>
     <summary style={{fontWeight:750,cursor:"pointer"}}>What evidence would resolve this adjudication? ({item.whatWouldResolve.length} checks)</summary>
     <ol style={{paddingLeft:21,lineHeight:1.75,fontSize:13}}>
       {item.whatWouldResolve.map((x,i)=><li key={i}>{x}</li>)}
     </ol>
   </details>
   <p style={{fontSize:12,color:muted,marginBottom:0,marginTop:12}}>
      No final CRL or approval judgment is produced by this case. No new PDUFA timing event has been established here. <Link href={"/medical-intelligence-preview/specialist-review?cycle="+item.cycleId}>Full disease-specialist dossier</Link> · <Link href={"/medical-intelligence-preview/applications/"+item.cycleId}>FDA application brief</Link>.
   </p>
 </article>;
}
export default function AdjudicationDesk(){
 const published=ADJUDICATION_CASES.reduce((n,c)=>n+c.sources.length,0);
 const worked=new Set(ADJUDICATION_CASES.map(x=>x.cycleId)).size;
 const discontinuation=adverseEventAbsoluteDifference(69,325,10,319);
 return <main style={{maxWidth:1370,margin:"24px auto",padding:"0 16px 50px",fontFamily:"system-ui,sans-serif",color:ink}}>
   <div style={{color:green,fontSize:12,fontWeight:750,letterSpacing:1}}>FOCUS → CLINICAL SPECIALIST → INDEPENDENT FDA EVIDENCE</div>
   <h1 style={{fontSize:"clamp(1.7rem,4vw,2.5rem)",margin:"8px 0 5px"}}>Independent clinical evidence adjudication</h1>
   <p style={{maxWidth:1070,lineHeight:1.6}}>Original statistical, clinical and regulatory evidence is examined side by side. Each case challenges an apparent success or failure with the strongest opposing evidence, separates FDA reviewer records from sponsor claims, and specifies what source information could change the conclusion. This is <strong>in-progress research, not a licensed specialist opinion or a predictive rating</strong>.</p>
   <p style={{...small,marginTop:4}}>Dated research snapshot: {ADJUDICATION_AS_OF}. A sponsor filing, an advisory package, a peer-reviewed clinical report and a final FDA regulatory decision are different kinds of evidence.</p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(175px,1fr))",gap:10,marginTop:16}}>
     {[
       ["FDA application cycles tracked",APPLICATION_CYCLES.length],
       ["Open deep adjudication cases",ADJUDICATION_CASES.length],
       ["Cycles with new detailed comparisons",worked],
       ["Individually documented evidence claims",published],
       ["Completed regulatory forecasts",0]
     ].map(([name,value])=><div key={String(name)} style={card}>
       <div style={{fontSize:12,color:muted}}>{name}</div><div style={{fontSize:28,fontWeight:750,marginTop:5}}>{value}</div>
     </div>)}
   </div>
   <section style={{...card,marginTop:15}}>
      <h2 style={{fontSize:18,margin:"0 0 7px"}}>APMD safety example — reproducible descriptive calculation</h2>
      <p style={{margin:"0 0 8px",fontSize:14}}>
        AD109 adverse-event discontinuations: 69 of 325 participants (<strong>{discontinuation.treatedPercent}%</strong>)
        versus placebo 10 of 319 (<strong>{discontinuation.controlPercent}%</strong>).
        Observed absolute excess: <strong>{discontinuation.excessPercentagePoints} percentage points</strong>.
      </p>
      <p style={{...small,margin:0}}>{discontinuation.interpretation} These are not classified as treatment-related serious events. See the peer-reviewed SynAIRgy safety Table 6 below.</p>
   </section>
   <section style={{marginTop:15}}>
    <h2 style={{fontSize:19}}>Current high-information adjudications</h2>
    {ADJUDICATION_CASES.map(item=><Case key={item.id} item={item}/>)}
   </section>
   <section style={{...card,marginTop:16}}>
    <h2 style={{fontSize:19,marginTop:0}}>Remaining FDA application review queue</h2>
    <p style={small}>The queue retains all current or proposed application cycles and sorts known review goals first. Opening a research case does not signal approval/CRL odds, and a pending BLA with no accepted goal is not assigned an invented deadline. The already-approved CYTK obstructive indication is excluded from the pending-review queue.</p>
    <div style={{overflowX:"auto"}}>
     <table style={{borderCollapse:"collapse",width:"100%",minWidth:850,fontSize:13}}>
      <thead><tr>{["Company / medicine","Review goal from public source","Deep comparison status","Unresolved evidence requirement"].map(h=><th key={h} style={{borderBottom:"1px solid "+line,padding:10,textAlign:"left",background:"#f1f7f2"}}>{h}</th>)}</tr></thead>
      <tbody>{INVESTIGATION_PRIORITIES.map(c=><tr key={c.cycleId} style={{borderBottom:"1px solid "+line}}>
        <td style={{padding:10}}><strong>{c.ticker}</strong> · <Link href={"/medical-intelligence-preview/applications/"+c.cycleId}>{c.drug}</Link></td>
        <td style={{padding:10}}>{dateRange(c.goal)}</td>
        <td style={{padding:10}}>{c.detailedCaseCount?c.detailedCaseCount+" detailed unresolved evidence case(s)":"Not independently reconciled"}</td>
        <td style={{padding:10,color:muted}}>{c.missingCoreEvidence[1]}</td>
      </tr>)}</tbody>
     </table>
    </div>
   </section>
   <p style={{...small,marginTop:19}}><Link href="/medical-intelligence-preview/specialist-review">All clinical specialist dossiers</Link> · <Link href="/medical-intelligence-preview/specialist-review/coverage">23-application evidence audit</Link> · <Link href="/medical-intelligence-preview/failure-desk">FDA failure desk</Link>. This draft analysis is read-only and does not update production or the POOL/FOCUS spreadsheets.</p>
 </main>;
}
