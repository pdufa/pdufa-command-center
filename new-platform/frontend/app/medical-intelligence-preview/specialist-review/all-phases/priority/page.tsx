import Link from "next/link";
import type {Metadata} from "next";
import {DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,getDepthSlot} from "../../../../../lib/medical-intelligence-master-depth";
import {getRegistryPhases} from "../../../../../lib/medical-intelligence-registry-phase";
import {rankScientificInvestigations,PRIORITY_ORDER,PRIORITY_PHASE_GUIDANCE,type PriorityTier} from "../../../../../lib/medical-intelligence-phase-priority";

export const metadata:Metadata={
 title:"All 800 Tests · Phase-Relative Investigation Priority",
 description:"Evidence-safe clinical phase priority for all 800 investigations, independent from scientific grades and FDA probabilities."
};
export const dynamic="force-dynamic";
const theme={ink:"#173a30",muted:"#536b5e",line:"#c6dacd",accent:"#006453",bg:"#f4f8f5"};
const card={background:"#fff",border:"1px solid "+theme.line,borderRadius:12,padding:15} as const;
type Params={nct?:string;tier?:string;page?:string;specialty?:string};
const PAGE_SIZE=40;
const queryString=(nct:string,tier:string,page:number,specialty:string)=>{
 const p=new URLSearchParams({nct,tier,page:String(page)});
 if(specialty)p.set("specialty",specialty);
 return "/medical-intelligence-preview/specialist-review/all-phases/priority?"+p.toString();
};
export default async function ScientificTestPriority({searchParams}:{searchParams:Promise<Params>}){
 const q=await searchParams;
 const nct=typeof q.nct==="string"&&/^NCT\d{8}$/.test(q.nct)?q.nct:"NCT06081894";
 const specialty=typeof q.specialty==="string"?q.specialty:"";
 const [registry]=await getRegistryPhases([nct]);
 // This is a static phase priority policy. No trial-specific sourced risk findings
 // are yet attached to a persistent verified scientific risk-escalation ledger.
 const report=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,nct,registry.verifiedPhase,[]);
 const tierFilter=q.tier==="ALL"||PRIORITY_ORDER.includes(q.tier as PriorityTier)?q.tier||"ALL":"ALL";
 const eligible=tierFilter==="ALL"?report.tests:report.tests.filter(t=>t.priority===tierFilter);
 const pages=Math.max(1,Math.ceil(eligible.length/PAGE_SIZE));
 const requested=typeof q.page==="string"&&/^\d+$/.test(q.page)?Number(q.page):1;
 const page=Math.max(1,Math.min(pages,Number.isSafeInteger(requested)?requested:1));
 const shown=eligible.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE);
 const back="/medical-intelligence-preview/specialist-review/all-phases?nct="+encodeURIComponent(nct)+
    (specialty?"&specialty="+encodeURIComponent(specialty):"");
 return <main style={{maxWidth:1270,margin:"24px auto",padding:"0 16px 60px",fontFamily:"system-ui,sans-serif",color:theme.ink}}>
  <div style={{fontWeight:750,letterSpacing:0.8,color:theme.accent,fontSize:12}}>DEEP CLINICAL SUBSPECIALTY INTELLIGENCE → ALL-PHASE SCIENTIFIC PRIORITY</div>
  <h1 style={{fontSize:"clamp(1.65rem,4vw,2.5rem)",margin:"7px 0"}}>800 Scientific Tests · Phase-Relative Priority Ranking</h1>
  <p style={{lineHeight:1.6,maxWidth:1040,fontSize:14}}>The 8 scientific layers, 40 assessments and 20 methods per assessment stay unchanged. Only their <strong>order of investigation</strong> changes by phase. A Critical priority indicates what deserves earliest review—it is <strong>not</strong> a confirmed clinical defect, a scientific grade or an FDA prediction.</p>
  <p style={{fontSize:13,margin:"4px 0 16px"}}><Link href={back}>Back to all-phase specialty review</Link> · <Link href="/medical-intelligence-preview/master-depth">Master scientific investigation</Link></p>
  <section style={card}>
   <h2 style={{fontSize:18,margin:"0 0 9px"}}>Study and priority filter</h2>
   <form action="/medical-intelligence-preview/specialist-review/all-phases/priority" method="get" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(215px,1fr))",gap:10,alignItems:"end"}}>
    <input type="hidden" name="specialty" value={specialty}/>
    <label style={{display:"grid",gap:6,fontWeight:700,fontSize:13}}>Exact trial NCT
     <input name="nct" defaultValue={nct} required pattern="NCT[0-9]{8}" maxLength={11} style={{border:"1px solid "+theme.line,borderRadius:7,padding:11,fontSize:14}}/>
    </label>
    <label style={{display:"grid",gap:6,fontWeight:700,fontSize:13}}>Priority category
     <select name="tier" defaultValue={tierFilter} style={{border:"1px solid "+theme.line,borderRadius:7,padding:11,fontSize:14,background:"#fff"}}>
      <option value="ALL">All 800 positions</option>
      {PRIORITY_ORDER.map(x=><option key={x} value={x}>{x.replaceAll("_"," ")}</option>)}
     </select>
    </label>
    <button type="submit" style={{padding:12,color:"white",background:theme.accent,border:0,borderRadius:7,fontWeight:700,cursor:"pointer"}}>Apply filter</button>
   </form>
   <p style={{fontSize:13,color:theme.muted,marginBottom:0}}>Exact-NCT registry phase: <strong>{registry.verifiedPhase}</strong>.{" "}
    {registry.sourceUrl&&<a href={registry.sourceUrl} rel="noopener noreferrer" target="_blank">Check ClinicalTrials.gov</a>}
    {" "}Phase policy: {PRIORITY_PHASE_GUIDANCE[registry.verifiedPhase]} No clinical priority rank is issued when phase verification fails.</p>
  </section>
  <section style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))",gap:9,marginTop:12}}>
   <div style={card}><div style={{fontSize:12,color:theme.muted}}>Defined scientific tests</div><strong style={{fontSize:25}}>{report.total}</strong></div>
   <div style={card}><div style={{fontSize:12,color:theme.muted}}>Ranked in phase</div><strong style={{fontSize:25}}>{report.ranked}</strong></div>
   {PRIORITY_ORDER.map(tier=><div key={tier} style={card}><div style={{fontSize:12,color:theme.muted}}>{tier.replaceAll("_"," ")} priority</div><strong style={{fontSize:25}}>{report.counts[tier]}</strong></div>)}
  </section>
  <section style={{...card,marginTop:15}}>
   <h2 style={{fontSize:19,margin:"0 0 9px"}}>Individual scientific test priorities</h2>
   <p style={{fontSize:13,color:theme.muted,lineHeight:1.6}}>
    Phase-driven investigation rankings are calculated for all 800 methods. No test has been automatically assigned a scientific result, 0–5 grade, observed risk, or approval probability. Each verified future risk finding can escalate only its exact test with dated original evidence.
   </p>
   <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:10,flexWrap:"wrap",fontSize:13,marginBottom:10}}>
    <strong>Showing {eligible.length?(page-1)*PAGE_SIZE+1:0}–{Math.min(page*PAGE_SIZE,eligible.length)} of {eligible.length}</strong>
    <span>Page {page} / {pages}</span>
   </div>
   <div style={{display:"grid",gap:8}}>
    {shown.map((test,i)=>{
     const slot=getDepthSlot(test.assessmentId,test.level);
     return <details key={test.id} open={i===0} style={{border:"1px solid "+theme.line,borderRadius:9,padding:"11px 13px",background:i===0?theme.bg:"#fff"}}>
      <summary style={{cursor:"pointer",fontSize:13,fontWeight:720,lineHeight:1.5}}>
       <span style={{fontVariantNumeric:"tabular-nums"}}>{test.rank===null?"Unranked":"#"+test.rank}</span>
       {" · "}<strong>{test.priority.replaceAll("_"," ")}</strong>
       {" · "}{test.assessmentId} — {test.assessmentLabel}
       {" · "}Method {test.level}: {test.methodName}
       <span style={{fontSize:12,fontWeight:450,color:theme.muted}}>
        {" · "}{test.phaseApplicability==="FORWARD_LOOKING"?"Future-phase, not yet required":"Scientific grade pending"}
       </span>
      </summary>
      <div style={{paddingTop:9,fontSize:13,lineHeight:1.65}}>
       <p style={{margin:"5px 0"}}><strong>Reason for this priority:</strong> {test.reason}</p>
       <p style={{margin:"5px 0"}}><strong>Question:</strong> {slot?.question}</p>
       <p style={{margin:"5px 0"}}><strong>Investigation method:</strong> {slot?.method}</p>
       <p style={{margin:"5px 0"}}><strong>Original evidence required:</strong> {slot?.requiredSources}</p>
       <p style={{margin:"5px 0"}}><strong>Evidence grade:</strong> Pending independent assessment. <strong>Observed risk:</strong> Not independently established in this view.</p>
      </div>
     </details>;
    })}
   </div>
   <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:12,marginTop:15,fontSize:13}}>
    {page>1?<Link href={queryString(nct,tierFilter,page-1,specialty)}>Previous 40 tests</Link>:<span style={{color:theme.muted}}>Start of ranking</span>}
    <span>Page {page} of {pages}</span>
    {page<pages?<Link href={queryString(nct,tierFilter,page+1,specialty)}>Next 40 tests</Link>:<span style={{color:theme.muted}}>End of ranking</span>}
   </div>
  </section>
 </main>;
}
