import Link from "next/link";
import type {Metadata} from "next";
import {notFound} from "next/navigation";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";
import {ADVANCED_LEVELS,buildAdvancedAssessment,type SourceRecord} from "../../../lib/medical-intelligence-advanced";
import {HISTORICAL_CALIBRATION} from "../../../lib/medical-intelligence-calibration";
export const metadata:Metadata={title:"12 Advanced Medical Intelligence Levels — PDUFA",description:"Independent failure-first research and uncalibrated outcome/CRL/delay decision gates."};
export const dynamic="force-dynamic";
const ink="#153a2d",muted="#496455",line="#c9ddcf",red="#8f352f",teal="#006451";
function SourceRow({s}:{s:SourceRecord}){
 return <div style={{padding:"10px 0",borderBottom:"1px solid #e4ece6"}}>
   <div style={{fontWeight:700,fontSize:13}}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a></div>
   <p style={{fontSize:12,color:muted,margin:"4px 0"}}>{s.date} · {s.sourceClass.replaceAll("_"," ")} · {s.scope.replaceAll("_"," ")}</p>
   <p style={{fontSize:13,margin:"5px 0"}}>{s.observation}</p>
   <p style={{fontSize:13,margin:"5px 0",color:red}}>Unresolved: {s.limitations}</p>
 </div>;
}
export default async function AdvancedReviewPage({searchParams}:{searchParams:Promise<{cycle?:string}>}){
 const q=await searchParams;
 const id=typeof q.cycle==="string"?q.cycle:APPLICATION_CYCLES[0]?.id;
 const a=id?buildAdvancedAssessment(id):null;
 if(!a)notFound();
 const isPending=a.cycle.stage!=="APPROVED_ALREADY";
 return <main style={{maxWidth:1250,margin:"22px auto",padding:"0 16px 44px",fontFamily:"system-ui,sans-serif",color:ink}}>
  <div style={{fontSize:12,color:teal,fontWeight:750}}>POOL → FOCUS → STANDALONE MEDICAL → FDA PREDICTIONS + SEPARATE CERTAINTY</div>
  <h1 style={{margin:"9px 0 4px"}}>12 advanced Deep Medical Intelligence levels</h1>
  <p style={{marginTop:6,lineHeight:1.5}}>Universal application-level research framework · Preview research, not an FDA or licensed clinician determination.
   No RAAS or survey scores. Source presence is never counted as completion of an independent analysis.</p>
  <form action="/medical-intelligence-preview/advanced" method="GET" style={{background:"#f5faf6",border:"1px solid "+line,borderRadius:10,padding:15}}>
   <label htmlFor="advanced-cycle" style={{fontWeight:700}}>FDA application / indication</label>
   <div style={{display:"flex",gap:8,flexWrap:"wrap",marginTop:8}}>
    <select id="advanced-cycle" name="cycle" defaultValue={a.cycle.id} style={{padding:"10px",maxWidth:"100%",flex:"1 1 280px"}}>
     {APPLICATION_CYCLES.map(c=><option value={c.id} key={c.id}>{c.ticker} · {c.drug} · {c.indication} ({c.stage.replaceAll("_"," ")})</option>)}
    </select>
    <button type="submit" style={{padding:"10px 16px",color:"white",background:teal,border:0,borderRadius:6}}>Show analysis</button>
   </div>
   <p style={{fontSize:12,color:muted,marginBottom:0}}>Current curated cohort: {APPLICATION_CYCLES.length} separately identified review cycles. Not a claim of comprehensive market coverage.</p>
  </form>
  <section style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:10,marginTop:16}}>
   {[
    ["Review cycle",a.cycle.ticker+" · "+a.cycle.applicationType],
    ["Source-lead levels",a.sourceLeadLevelCount+" / "+ADVANCED_LEVELS.length],
    ["Completed independent reviews","0 / 12"],
    ["Registry phase",a.phase.map(p=>p.verifiedPhase).join(", ")],
    ["Historical cohort",HISTORICAL_CALIBRATION.eligibleCount+" validated rows"],
    ["Automatic source watch","Not yet enabled"]
   ].map(([label,value])=><div key={label} style={{border:"1px solid "+line,borderRadius:9,padding:12,background:"white"}}>
    <div style={{fontSize:12,color:muted}}>{label}</div><strong style={{fontSize:15,overflowWrap:"anywhere"}}>{value}</strong>
   </div>)}
  </section>
  <p style={{fontSize:13,color:muted}}>Verified phase is required before phase-specific statistical or pivotal evidence can be judged. An unknown phase is a verification gap, not a failed clinical trial. <Link href={"/medical-intelligence-preview?nct="+a.cycle.ncts[0]}>See registry-linked trial dossier</Link>.</p>
  <section style={{border:"1px solid "+line,borderRadius:10,padding:15,marginTop:16,background:"#f7faf7"}}>
   <h2 style={{fontSize:19,marginTop:0}}>Separate FDA prediction outcomes</h2>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(225px,1fr))",gap:11}}>
    {a.predictions.map(p=><div key={p.outcome} style={{border:"1px solid "+line,background:"white",borderRadius:8,padding:12}}>
     <div style={{fontSize:13,color:muted,fontWeight:650}}>{p.outcome.replaceAll("_"," ")}</div>
     <div style={{fontSize:20,color:p.status==="ABSTAIN"?red:ink,fontWeight:800}}>{p.status==="ABSTAIN"?"ABSTAIN":"Not a pending decision"}</div>
     <p style={{fontSize:13,marginBottom:4}}>Probability: <strong>not issued</strong></p>
     <p style={{fontSize:13,color:muted}}>{p.reasoning}</p>
     <details><summary style={{cursor:"pointer",fontWeight:650}}>Supporting evidence ({p.supportingEvidence.length}) and gaps ({p.missingEvidence.length})</summary>
      <div style={{maxHeight:300,overflowY:"auto"}}>{p.supportingEvidence.map(s=><SourceRow key={p.outcome+s.id} s={s}/>)}</div>
      <ul style={{fontSize:13}}>{p.missingEvidence.map((g,i)=><li key={i}>{g}</li>)}</ul>
     </details>
    </div>)}
   </div>
   <h3 style={{fontSize:17,marginBottom:4}}>Independent prediction certainty</h3>
   <p style={{marginTop:2}}><strong>{a.certainty.status.replaceAll("_"," ")}</strong> · Certainty rating: <strong>not issued</strong> · Historical calibration: {HISTORICAL_CALIBRATION.eligibleCount} independently qualified examples.</p>
   <p style={{fontSize:13,color:muted}}>{a.certainty.explanation}</p>
   <p style={{fontSize:13,color:muted}}>These three outcomes are distinct: review delay can precede approval or a CRL. Historical approval or extension events are not forward forecasts.</p>
  </section>
  <section style={{marginTop:18}}>
   <h2 style={{fontSize:20,marginBottom:6}}>Failure-first investigation — all 12 levels</h2>
   <p style={{fontSize:13,color:muted}}>Expand any level to inspect the question, exact primary-source leads and what remains missing. There are no silently completed categories.</p>
   {a.levels.map(l=><details key={l.id} style={{background:"white",border:"1px solid "+line,borderRadius:9,padding:"13px 14px",marginBottom:9}}>
    <summary style={{cursor:"pointer",display:"flex",justifyContent:"space-between",gap:14,flexWrap:"wrap",fontWeight:700}}>
     <span>{l.number}. {l.title}</span>
     <span style={{fontSize:12,color:l.state==="EVIDENCE_GAP"?red:muted}}>{l.state.replaceAll("_"," ")} · {l.sources.length} source pointers</span>
    </summary>
    <p style={{fontSize:14,fontWeight:650}}>{l.failureQuestion}</p>
    <p style={{fontSize:13,color:muted}}>{l.explanation}</p>
    {l.sources.length?<div style={{borderTop:"1px solid "+line}}>{l.sources.map(s=><SourceRow key={l.id+s.id} s={s}/>)}</div>:<p style={{fontSize:13,color:red}}>No original-source item selected for this level; research remains outstanding.</p>}
    <h3 style={{fontSize:14,marginBottom:4}}>Evidence still required for adjudication</h3>
    <ul style={{fontSize:13,lineHeight:1.5,marginTop:3}}>{l.missing.map((m,i)=><li key={i}>{m}</li>)}</ul>
   </details>)}
  </section>
  <section style={{border:"1px solid "+line,padding:14,borderRadius:9,marginTop:16}}>
   <h2 style={{fontSize:18,marginTop:0}}>Historical calibration and automatic reanalysis</h2>
   <p style={{fontSize:13}}>No validated historical outcome/prediction cohort is installed. The calibration evaluator enforces temporal outcome separation and reports held-out Brier scores only when real locked historical records are provided. It cannot authorize release of percentages by itself.</p>
   <p style={{fontSize:13}}>Evidence-change monitoring and persistent historical prediction-change records require the preview backend PostgreSQL connection and validated source-diff processing; they are not currently live.</p>
   <p style={{fontSize:13,color:muted}}>Application source: <a href={a.cycle.sourceUrl} target="_blank" rel="noopener noreferrer">{a.cycle.sourceDate} record</a>. Source snapshot as of {a.snapshotDate}; check subsequent FDA updates before decisions.</p>
   <Link href={"/medical-intelligence-preview/applications/"+a.cycle.id}>Open original FDA decision brief</Link> · <Link href="/medical-intelligence-preview/applications">All application cycles</Link>
  </section>
  <p style={{fontSize:12,color:muted}}>Current status: {isPending?"Pending/reconstructed application research":"Previously approved indication — prospective approval prediction not applicable"}. All outputs are evidence-gated and default to ABSTAIN until retrospective and prospective validation supports otherwise.</p>
 </main>;
}
