import Link from "next/link";
import type {Metadata} from "next";
import {APPLICATION_CYCLES,CYCLE_COUNTS} from "../../../lib/medical-intelligence-applications";
import {findingsForNct,REVIEW_AS_OF} from "../../../lib/medical-intelligence-reviewed-findings";
import focus from "../../../data/p3PostDataActive.json";

export const metadata:Metadata={title:"FDA Application Cycles — Deep Medical Intelligence",description:"Read-only verification of exact applications, regulatory status and failure-first evidence for FOCUS trials."};
export const dynamic="force-dynamic";
const ink="#15382d",muted="#4e6256",line="#c6dacc";
const stageLabels:{[k:string]:string}={
 UNDER_REVIEW:"Accepted / under FDA review",
 SUPPLEMENT_UNDER_REVIEW:"Supplement under FDA review",
 SUBMITTED_PENDING_ACCEPTANCE:"Submitted; acceptance/goal not confirmed",
 PLANNED:"Application filing planned; no assigned review goal",
 PRIOR_CRL_RESUBMISSION_PLANNED:"Previous CRL; resubmission planned",
 APPROVED_ALREADY:"Already FDA-approved indication / reconcile old goal"
};
export default function ApplicationsPage(){
 const queue=[...APPLICATION_CYCLES].sort((a,b)=>(a.reportedGoal||"9999-12-31").localeCompare(b.reportedGoal||"9999-12-31")||a.ticker.localeCompare(b.ticker));
 const nctCount=new Set(APPLICATION_CYCLES.flatMap(x=>x.ncts)).size;
 return <main style={{maxWidth:1370,margin:"24px auto",padding:"0 16px 44px",fontFamily:"system-ui,sans-serif",color:ink}}>
  <div style={{fontSize:12,letterSpacing:1,color:"#006452",fontWeight:750}}>FOCUS → APPLICATION IDENTITY → FAILURE INVESTIGATION</div>
  <h1 style={{margin:"9px 0"}}>FDA application and review-cycle intelligence</h1>
  <p style={{lineHeight:1.55}}>Every FOCUS clinical trial must be matched to the <strong>specific drug, indication, NDA/BLA or supplement, and review cycle</strong> before predicting approval, CRL, withdrawal or extension. The 29 NCTs do not equal 29 FDA applications. This page is a dated, cited research inventory, not a validated FDA forecast.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:10,marginTop:18}}>
   {[
    ["Distinct application cycles",CYCLE_COUNTS.total],
    ["FOCUS NCTs linked",nctCount+" / "+focus.records.length],
    ["Accepted review or supplement",CYCLE_COUNTS.underReview],
    ["Filing planned",CYCLE_COUNTS.planned],
    ["Submitted, awaiting acceptance",CYCLE_COUNTS.pendingAcceptance],
    ["Prior CRL, resubmission planned",CYCLE_COUNTS.priorCrlPlannedResubmission],
    ["Approved indication, reconcile goal",CYCLE_COUNTS.alreadyApproved]
   ].map(([label,value])=><div key={String(label)} style={{border:"1px solid "+line,borderRadius:9,padding:14,background:"#fff"}}><span style={{fontSize:12,color:muted}}>{label}</span><div style={{fontSize:26,fontWeight:750,marginTop:6}}>{value}</div></div>)}
  </div>
  <section style={{border:"1px solid "+line,borderRadius:12,padding:16,marginTop:18,background:"#fff"}}>
   <h2 style={{fontSize:19,margin:"0 0 8px"}}>Application-level review queue</h2>
   <p style={{fontSize:13,color:muted}}>Sorted by source-reported goal date; undated or planned filings follow. <strong>Every item is indeterminate for future outcome and timing.</strong> Prior CRLs and confirmed extensions are historical facts, not forecasts of additional events. Research data as of {REVIEW_AS_OF}.</p>
   <div style={{overflowX:"auto"}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:970,fontSize:13}}>
     <thead style={{background:"#edf6f0"}}><tr>{["Drug / application","Indication / status","Goal date","Source findings","Decision-critical uncertainty","Source"].map(x=><th key={x} style={{textAlign:"left",padding:"10px",borderBottom:"1px solid "+line}}>{x}</th>)}</tr></thead>
     <tbody>{queue.map(a=>{
       const findings=Array.from(new Map(a.ncts.flatMap(findingsForNct).map(f=>[f.id,f])).values());
       const historicalCrl=findings.filter(f=>f.type==="PREVIOUS_CRL").length;
       const openStat=findings.filter(f=>f.type==="SCIENTIFIC_UNCERTAINTY").length;
       const extension=findings.filter(f=>f.type==="EXTENSION_CONFIRMED").length;
       return <tr key={a.id} style={{borderTop:"1px solid "+line}}>
        <td style={{padding:10,verticalAlign:"top",minWidth:200}}><strong>{a.ticker} · {a.drug}</strong><div style={{marginTop:5}}><Link href={"/medical-intelligence-preview/applications/"+a.id}>Open decision brief</Link></div><div style={{color:muted,marginTop:4}}>{a.applicationType}</div><div style={{marginTop:6}}>{a.ncts.map(n=><div key={n}><Link href={"/medical-intelligence-preview?nct="+n}>{n}</Link></div>)}</div></td>
        <td style={{padding:10,verticalAlign:"top",minWidth:190}}>{a.indication}<div style={{color:muted,marginTop:6}}>{stageLabels[a.stage]||a.stage}</div></td>
        <td style={{padding:10,verticalAlign:"top",whiteSpace:"nowrap"}}>{a.reportedGoal||"Not assigned"}<div style={{color:muted,fontSize:11,marginTop:6}}>Source-reported only</div></td>
        <td style={{padding:10,verticalAlign:"top",minWidth:158}}>{findings.length} cited finding(s)<div style={{color:muted,marginTop:6}}>{historicalCrl?historicalCrl+" prior CRL(s) · ":""}{openStat?openStat+" open scientific issue(s) · ":""}{extension?extension+" prior extension(s)":"Not fully adjudicated"}</div></td>
        <td style={{padding:10,verticalAlign:"top",minWidth:260}}>{a.criticalQuestion}<div style={{fontWeight:650,marginTop:8}}>Predicted outcome: Indeterminate</div></td>
        <td style={{padding:10,verticalAlign:"top"}}><a target="_blank" rel="noopener noreferrer" href={a.sourceUrl}>Source ({a.sourceDate})</a></td>
       </tr>;
      })}</tbody>
    </table>
   </div>
  </section>
  <p style={{fontSize:13,lineHeight:1.6,color:muted,marginTop:18}}>Caveat: the grouped application identity is reconstructed from dated sponsor/SEC records and trial associations, not verified against confidential FDA application files. Some entries, especially the Cytokinetics oHCM listing, require correction of the original FOCUS date-to-application relationship. No source spreadsheets were changed. <Link href="/medical-intelligence-preview">Return to individual trial dossier</Link> · <Link href="/medical-intelligence-preview/coverage">Registry coverage</Link>.</p>
 </main>;
}
