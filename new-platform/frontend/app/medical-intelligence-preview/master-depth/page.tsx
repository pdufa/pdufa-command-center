import Link from "next/link";
import type {Metadata} from "next";
import type {CSSProperties} from "react";
import focus from "../../../data/p3PostDataActive.json";
import {SCIENTIFIC_LEVELS,SCIENTIFIC_LAYERS,DEEP_ASSESSMENTS,DEPTH_SLOT_COUNT,THERAPEUTIC_STRATEGY_QUESTIONS,getDepthSlot,FDA_GUIDANCE_SOURCES} from "../../../lib/medical-intelligence-master-depth";
import {applicationsForNct} from "../../../lib/medical-intelligence-applications";
import {getRegistryPhases} from "../../../lib/medical-intelligence-registry-phase";
import {rankTrialAssessments,PHASE_REVIEW_STANDARD,TEST_GRADE_RUBRIC} from "../../../lib/medical-intelligence-assessment-rankings";
import {MEDICAL_CASES,caseForCycle,researchForSlot,caprSapComparisonSummary,CAPR_FDA_PUL_SAP_COMPARISONS,cogtLiverSafetyDifference} from "../../../lib/medical-intelligence-md-casebook";

export const metadata:Metadata={
 title:"Medical Master Depth — 20-Level PDUFA Scientific Analysis",
 description:"Evidence-gated 20 scientific levels across 40 medical assessments, with independent FDA and trial adjudication examples."
};
export const dynamic="force-dynamic";
const c={ink:"#15382d",muted:"#4b6457",line:"#c6dacd",off:"#f4f8f5",accent:"#006654",alert:"#8e4138"};
const panel:CSSProperties={padding:17,background:"#fff",border:"1px solid "+c.line,borderRadius:12,marginTop:15};
const subtle:CSSProperties={fontSize:13,lineHeight:1.6,color:c.muted};
const href=(nct:string,assessment:string)=>"/medical-intelligence-preview/master-depth?nct="+encodeURIComponent(nct)+"&assessment="+encodeURIComponent(assessment);
type Params={nct?:string;assessment?:string};
function EvidenceSource({url,children}:{url:string;children:React.ReactNode}){
 return <a href={url} target="_blank" rel="noopener noreferrer" style={{color:c.accent}}>{children}</a>;
}
export default async function MedicalMasterDepth({searchParams}:{searchParams:Promise<Params>}){
 const query=await searchParams;
 const nct=focus.records.find(r=>r.nct===query.nct)?.nct||"NCT05126758";
 const base=focus.records.find(r=>r.nct===nct)||focus.records[0];
 const [phaseContext]=await getRegistryPhases([nct]);
 // Scores cannot be invented from source collection alone. Reviewed per-test marks
 // will be supplied by the independent assessment-review ledger once available.
 const assessmentRatings=rankTrialAssessments(DEEP_ASSESSMENTS,nct,phaseContext.verifiedPhase,[]);
 const evidenceCoverage=assessmentRatings.map(r=>({
   ...r,
   sourceSlots:SCIENTIFIC_LEVELS.filter(l=>applicationsForNct(nct).some(c=>Boolean(researchForSlot(c.id,r.id,l.id)))).length
 })).sort((a,b)=>b.sourceSlots-a.sourceSlots||a.id.localeCompare(b.id));
 const assessment=DEEP_ASSESSMENTS.find(a=>a.id===query.assessment)||DEEP_ASSESSMENTS.find(a=>a.id==="4.3")||DEEP_ASSESSMENTS[0];
 const layer=SCIENTIFIC_LAYERS.find(l=>l.id===assessment.layerId)||SCIENTIFIC_LAYERS[0];
 const matches=applicationsForNct(nct);
 const firstCase=matches.map(m=>caseForCycle(m.id)).find(caseStudy=>caseStudy?.nct===nct)||null;
 const caseStudies=matches.filter(m=>caseForCycle(m.id)?.nct===nct);
 const slots=SCIENTIFIC_LEVELS.map(l=>({lvl:l,slot:getDepthSlot(assessment.id,l.id),
  evidence:matches.filter(m=>caseForCycle(m.id)?.nct===nct).map(m=>researchForSlot(m.id,assessment.id,l.id)).find(Boolean)||null}));
 const sourceChecked=slots.filter(s=>s.evidence).length;
 const capr=firstCase?.cycleId==="capr-deramiocel";
 const cogt=firstCase?.cycleId==="cogt-gist";
 const summary=capr?caprSapComparisonSummary():null;
 const liver=cogt?cogtLiverSafetyDifference():null;
 return <main style={{maxWidth:1360,margin:"25px auto",padding:"0 16px 45px",fontFamily:"system-ui,sans-serif",color:c.ink}}>
   <div style={{fontWeight:750,letterSpacing:1,fontSize:12,color:c.accent}}>POOL → FOCUS → STANDALONE DEEP MEDICAL INTELLIGENCE</div>
   <h1 style={{fontSize:"clamp(1.7rem,4vw,2.5rem)",margin:"8px 0 4px"}}>Medical Master Depth · 20-Level Scientific Investigation</h1>
   <p style={{fontWeight:700,fontSize:14}}><Link href="/medical-intelligence-preview/master-depth/coverage">Open exact 29-trial Master Depth coverage audit</Link></p>
   <p style={{lineHeight:1.6,maxWidth:1130}}>The research architecture follows the original clinical scientific investigation standard: 8 disease/medical/regulatory layers, 5 assessments per layer, and 20 distinct scientific methods applied to each assessment. The result is 800 possible investigation positions <strong>per trial</strong>, supplemented by 75 therapeutic-strategy questions. A position is not an actual medical finding until source evidence has been investigated and documented.</p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(155px,1fr))",gap:10}}>
     {[
       ["Subject layers",SCIENTIFIC_LAYERS.length],
       ["Scientific assessments",DEEP_ASSESSMENTS.length],
       ["Depth levels",SCIENTIFIC_LEVELS.length],
       ["Evidence-gated positions",DEPTH_SLOT_COUNT],
       ["Therapeutic-strategy probes",THERAPEUTIC_STRATEGY_QUESTIONS.length]
     ].map(([name,value])=><div style={panel} key={String(name)}><div style={subtle}>{name}</div><div style={{fontSize:29,fontWeight:780}}>{value}</div></div>)}
   </div>

   <section style={panel}>
     <h2 style={{marginTop:0,fontSize:19}}>Choose a real FOCUS trial and a scientific assessment</h2>
     <form action="/medical-intelligence-preview/master-depth" method="get" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:12,alignItems:"end"}}>
       <label style={{display:"grid",gap:6,fontWeight:650,fontSize:13}}>FOCUS trial / company
         <select name="nct" defaultValue={nct} style={{padding:11,borderRadius:8,border:"1px solid #a6c1ae",fontSize:14}}>
           {focus.records.map(r=><option key={r.nct} value={r.nct}>{r.ticker} · {r.nct} · {r.company}</option>)}
         </select>
       </label>
       <label style={{display:"grid",gap:6,fontWeight:650,fontSize:13}}>One of 40 assessments
         <select name="assessment" defaultValue={assessment.id} style={{padding:11,borderRadius:8,border:"1px solid #a6c1ae",fontSize:14}}>
           {SCIENTIFIC_LAYERS.map(l=><optgroup key={l.id} label={l.title}>
             {l.assessments.map(a=><option key={a.id} value={a.id}>{a.id} · {a.label}</option>)}
           </optgroup>)}
         </select>
       </label>
       <button type="submit" style={{background:c.accent,color:"#fff",border:0,padding:12,borderRadius:8,fontSize:14,fontWeight:750,cursor:"pointer"}}>Open 20-Level Investigation</button>
     </form>
     <p style={{...subtle,marginBottom:0}}>Viewing {base.ticker} / {base.nct}. Matched to {matches.length} source-reconstructed FDA application cycle(s). The matrix always remains available; substantive research is shown only where completed.</p>
   </section>

   <section style={panel}>
     <h2 style={{margin:"0 0 8px",fontSize:19}}>Scientific test rankings · every assessment</h2>
     <p style={subtle}>Each of the 40 assessments contains 20 separately rated investigative tests. The evidence-backed scientific grade is 0–5 per test, with a transparent 0–100 assessment average. A final comparative rank is shown only after every phase-applicable method is independently reviewed or explicitly excluded with a rationale. Missing evidence never counts as a zero, a failure, or a clinical benefit.</p>
     <p style={{...subtle,marginTop:0}}><strong>Exact-NCT phase:</strong> {phaseContext.verifiedPhase} {phaseContext.sourceUrl&&<>· <EvidenceSource url={phaseContext.sourceUrl}>ClinicalTrials.gov</EvidenceSource></>}. <strong>Phase-specific standard:</strong> {PHASE_REVIEW_STANDARD[phaseContext.verifiedPhase]}. Scientific grades are not FDA approval probabilities or certainty ratings.</p>
     <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
       {TEST_GRADE_RUBRIC.map(r=><span key={r.grade} title={r.meaning} style={{fontSize:12,border:"1px solid "+c.line,borderRadius:6,padding:"5px 8px",background:c.off}}>{r.grade}/5: {r.meaning}</span>)}
     </div>
     <div style={{overflowX:"auto"}}>
       <table style={{borderCollapse:"collapse",width:"100%",minWidth:790,fontSize:13}}>
         <thead><tr>{["Assessment","Scientific grade / 100","Final grade rank","Scored / applicable tests","Source-examined methods / 20","Review status"].map(k=><th key={k} style={{padding:"9px 7px",textAlign:"left",borderBottom:"1px solid "+c.line}}>{k}</th>)}</tr></thead>
         <tbody>{evidenceCoverage.map(row=><tr key={row.id}>
           <td style={{padding:8,borderBottom:"1px solid "+c.line}}><Link href={href(nct,row.id)}>{row.id} · {row.label}</Link></td>
           <td style={{padding:8,borderBottom:"1px solid "+c.line,fontWeight:700}}>{row.score===null?"Not rated":row.score+"/100"+(row.status==="PROVISIONAL"?" (provisional)":"")}</td>
           <td style={{padding:8,borderBottom:"1px solid "+c.line}}>{row.rank===null?"—":"#"+row.rank}</td>
           <td style={{padding:8,borderBottom:"1px solid "+c.line}}>{row.scoredTests} / {row.applicableTests}</td>
           <td style={{padding:8,borderBottom:"1px solid "+c.line}}>{row.sourceSlots} / 20</td>
           <td style={{padding:8,borderBottom:"1px solid "+c.line}}>{row.status==="NOT_REVIEWED"?"Pending adjudication":row.status==="NOT_APPLICABLE"?"Excluded with rationale":row.status==="PROVISIONAL"?"Partial scientific review":"Complete"}</td>
         </tr>)}</tbody>
       </table>
     </div>
     <p style={{...subtle,marginBottom:0}}>Rows are sorted by documented source-investigation coverage, not by evidence strength. A source-examined observation does not automatically pass its scientific test. This preview has not yet connected a persistent, independently verified grade ledger; therefore scores and ranks remain pending rather than fabricated.</p>
   </section>

   <section style={panel}>
     <h2 style={{margin:"0 0 8px",fontSize:19}}>Eight subject layers · 40 scientific assessments</h2>
     <p style={subtle}>Each assessment opens the full 20-level scientific method sequence. Select a different assessment to explore its methods and any source-examined findings for this trial.</p>
     {SCIENTIFIC_LAYERS.map(l=><details key={l.id} open={l.id===layer.id} style={{border:"1px solid "+c.line,borderRadius:9,padding:"11px 14px",marginTop:9}}>
       <summary style={{fontWeight:750,cursor:"pointer"}}>{SCIENTIFIC_LAYERS.indexOf(l)+1}. {l.title} <small style={{fontWeight:400,color:c.muted}}>· 5 assessments · 100 investigation positions</small></summary>
       <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))",gap:8,marginTop:12}}>
         {l.assessments.map(a=><div key={a.id} style={{background:a.id===assessment.id?"#e9f3e9":c.off,padding:11,borderRadius:8,fontSize:13}}>
           <div style={{fontWeight:750}}><Link href={href(nct,a.id)}>{a.id} · {a.label}</Link></div>
           <div style={{...subtle,fontSize:12,marginTop:4}}>{a.objective}</div>
         </div>)}
       </div>
     </details>)}
   </section>

   <section style={panel}>
     <div style={{display:"flex",justifyContent:"space-between",alignItems:"start",gap:16,flexWrap:"wrap"}}>
       <div><p style={{...subtle,margin:0}}>CURRENT SCIENTIFIC ASSESSMENT</p>
         <h2 style={{fontSize:23,margin:"5px 0"}}>{assessment.id} · {assessment.label}</h2>
         <p style={{maxWidth:940,lineHeight:1.5}}>{assessment.objective}</p>
       </div>
       <div style={{border:"1px solid "+c.line,borderRadius:9,padding:12,background:c.off,minWidth:180}}>
         <strong>{sourceChecked} / 20</strong>
         <div style={{...subtle,fontSize:12}}>Methods with specific source-examined example evidence</div>
       </div>
     </div>
     <p style={{...subtle,margin:"4px 0 11px"}}><strong>Potential FDA deficiency:</strong> {assessment.failureMechanism}. <strong>Source requirements:</strong> {assessment.requiredSources}. An unreviewed slot is neither a clinical failure nor a passing scientific assessment.</p>
     <div style={{display:"grid",gap:8}}>
       {slots.map(({lvl,slot,evidence})=><details key={lvl.id} style={{border:"1px solid "+c.line,borderRadius:9,padding:"11px 13px",background:evidence?"#f2f8f0":"#fff"}} open={Boolean(evidence&&lvl.id===12)}>
         <summary style={{cursor:"pointer",fontWeight:720,fontSize:14}}>
           Level {lvl.id}. {lvl.name} <span style={{fontSize:12,fontWeight:450,color:evidence?c.accent:c.muted}}>· {evidence?"SOURCE-EXAMINED EXAMPLE":"NOT YET SOURCE-REVIEWED"}</span>
         </summary>
         <div style={{paddingTop:9,fontSize:13,lineHeight:1.6}}>
           <p style={{margin:"4px 0"}}><strong>Method:</strong> {slot?.method}</p>
           <p style={{margin:"4px 0"}}><strong>Investigation:</strong> {slot?.question}</p>
           <p style={{margin:"4px 0"}}><strong>Required sources:</strong> {slot?.requiredSources}</p>
           {evidence&&<div style={{padding:12,marginTop:10,background:"#fff",borderLeft:"3px solid "+c.accent,borderRadius:5}}>
             <strong>Source-examined observation</strong>
             <p style={{margin:"6px 0"}}>{evidence.sourceObservation}</p>
             <strong>Medical / FDA interpretation</strong>
             <p style={{margin:"6px 0"}}>{evidence.medicalInterpretation}</p>
             <p style={{...subtle,margin:0}}>Reference section: {evidence.sourceSection} · {firstCase&&<EvidenceSource url={evidence.sourceUrl||firstCase.source}>Open source for this observation</EvidenceSource>}. Full independent reproduction and final FDA adjudication are not implied.</p>
           </div>}
           <p style={{...subtle,margin:"8px 0 0"}}><strong>Expected output:</strong> {slot?.output}</p>
         </div>
       </details>)}
     </div>
   </section>

   <section style={panel}>
     <h2 style={{margin:"0 0 9px",fontSize:19}}>Source-examined Medical Master casebook</h2>
     {caseStudies.length===0&&<p style={subtle}>This trial has no in-depth source-examined Master example yet. The 20×40 protocol is available but should not be counted as completed research.</p>}
     {caseStudies.map(m=>{
       const current=caseForCycle(m.id);
       if(!current)return null;
       return <div key={m.id} style={{border:"1px solid "+c.line,borderRadius:10,padding:14,marginTop:12}}>
         <div style={{fontWeight:750,color:c.accent,fontSize:12}}>PARTIAL REFERENCE CASE · NOT COMPLETE MASTER ADJUDICATION</div>
         <h3 style={{margin:"4px 0 6px",fontSize:20}}>{current.name}</h3>
         <p style={{...subtle,marginTop:0}}>{current.reviewCycle} · {current.investigations.length} source-examined level/assessment combinations out of 800 possible slots</p>
         <p style={{fontSize:14,lineHeight:1.6}}><strong>Central medical finding:</strong> {current.finding}</p>
         <p style={{fontSize:14,lineHeight:1.6}}><strong>Most consequential open risk:</strong> {current.mainRisk}</p>
         <p style={{fontSize:14,lineHeight:1.6}}><strong>Independent countercase:</strong> {current.strongestCounter}</p>
         <div style={{overflowX:"auto"}}><table style={{borderCollapse:"collapse",width:"100%",minWidth:620,fontSize:13}}>
           <thead><tr>{["Scientific finding","Source-reported or calculated result","Provenance"].map(k=><th key={k} style={{textAlign:"left",padding:9,borderBottom:"1px solid "+c.line}}>{k}</th>)}</tr></thead>
           <tbody>{current.facts.map((f,i)=><tr key={i}><td style={{padding:9,borderBottom:"1px solid "+c.line}}>{f.label}</td><td style={{padding:9,borderBottom:"1px solid "+c.line}}>{f.value}</td><td style={{padding:9,borderBottom:"1px solid "+c.line,color:c.muted}}>{f.source}</td></tr>)}</tbody>
         </table></div>
         <details style={{marginTop:11}}>
           <summary style={{cursor:"pointer",fontWeight:750}}>What must be resolved before an FDA prediction?</summary>
           <ul style={{paddingLeft:22,lineHeight:1.7,fontSize:13}}>{current.uncertainties.map((x,i)=><li key={i}>{x}</li>)}</ul>
         </details>
         <div style={{fontSize:13,marginTop:12}}><EvidenceSource url={current.source}>{current.sourceTitle} ({current.sourceDate})</EvidenceSource></div>
       </div>;
     })}
     {capr&&summary&&<div style={{marginTop:17,border:"2px solid "+c.line,borderRadius:10,padding:15}}>
       <h3 style={{marginTop:0,fontSize:19}}>CAPR HOPE-3 · FDA-versus-sponsor prespecified SAP sensitivity table</h3>
       <p style={subtle}>This is the type of analysis needed for every pivotal trial. Original FDA July 2026 advisory briefing Table 7; same trial and endpoint family, but not the same estimand, effect scale or missing-data assumptions.</p>
       <div style={{overflowX:"auto"}}>
         <table style={{borderCollapse:"collapse",width:"100%",minWidth:730,fontSize:13}}>
           <thead><tr>{["Analysis and timing","Effect scale","Treatment difference","95% confidence interval","Reported p-value"].map(x=><th key={x} style={{textAlign:"left",padding:9,borderBottom:"1px solid "+c.line}}>{x}</th>)}</tr></thead>
           <tbody>{CAPR_FDA_PUL_SAP_COMPARISONS.map((x,i)=><tr key={i} style={{background:i===0?"#f2f6f2":i===6?"#fff6ed":"#fff"}}>
             <td style={{padding:9,borderBottom:"1px solid "+c.line}}>{x.version}</td>
             <td style={{padding:9,borderBottom:"1px solid "+c.line}}>{x.units}</td>
             <td style={{padding:9,borderBottom:"1px solid "+c.line}}>{x.effect}</td>
             <td style={{padding:9,borderBottom:"1px solid "+c.line}}>{x.lower} to {x.upper}</td>
             <td style={{padding:9,borderBottom:"1px solid "+c.line,fontWeight:700}}>{x.pValue.toFixed(x.pValue<0.1?3:2)}</td>
           </tr>)}</tbody>
         </table>
       </div>
       <p style={{fontSize:14}}><strong>Analysis sensitivity:</strong> {summary.nominalBelow005} of {summary.reportedAnalyses} reported variants have nominal p-values below 0.05, whereas the original SAP 1.1 yielded p=0.24. This is a descriptive sign of method sensitivity, <strong>not</strong> a statistical test of independent replication or an FDA approval probability.</p>
       <p style={subtle}>{summary.caution} <EvidenceSource url="https://www.fda.gov/media/193839/download">FDA Table 7 source</EvidenceSource>.</p>
     </div>}
     {cogt&&liver&&<div style={{marginTop:15,border:"1px solid "+c.line,borderRadius:9,padding:14,background:c.off}}>
       <strong>COGT benefit-risk calculation — descriptive only</strong>
       <p style={{fontSize:14,lineHeight:1.6}}>Grade ≥3 liver-enzyme abnormalities: {liver.combinationPercent}% on combination versus {liver.controlPercent}% on sunitinib alone, a difference of <strong>{liver.absoluteDifferencePercentagePoints} percentage points</strong>. The PFS HR was 0.50 (95% CI 0.39–0.65) in the sponsor report.</p>
       <p style={subtle}>{liver.caution}</p>
     </div>}
   </section>

   <section style={panel}>
     <h2 style={{marginTop:0,fontSize:19}}>75 additional therapeutic-strategy investigations</h2>
     <p style={subtle}>These are five groups of 15 targeted research questions. They supplement the original 800 positions; they do not introduce questionnaires, user surveys, arbitrary scores or automatically populated clinical findings.</p>
     {Array.from(new Set(THERAPEUTIC_STRATEGY_QUESTIONS.map(x=>x.group))).map(g=><details key={g} style={{border:"1px solid "+c.line,borderRadius:8,padding:"11px 13px",marginTop:8}}>
       <summary style={{fontWeight:750,cursor:"pointer"}}>{g} · 15 targeted questions</summary>
       <ol style={{fontSize:13,lineHeight:1.6,paddingLeft:21}}>{THERAPEUTIC_STRATEGY_QUESTIONS.filter(x=>x.group===g).map(x=><li key={x.id}><strong>{x.id}</strong> {x.question}</li>)}</ol>
     </details>)}
   </section>
   <section style={panel}>
     <h2 style={{marginTop:0,fontSize:18}}>FDA methodological standards</h2>
     <div style={{fontSize:13,lineHeight:1.8}}>{FDA_GUIDANCE_SOURCES.map(x=><div key={x.url}><EvidenceSource url={x.url}>{x.title}</EvidenceSource></div>)}</div>
     <p style={{...subtle,marginBottom:0}}>Independent source review and calibrated historical outcome testing are required before converting investigation findings into approval/CRL/extension forecasts. This prototype is independent of retired scoring systems and never writes to source spreadsheets.</p>
   </section>
   <p style={{...subtle,marginTop:16}}><Link href="/medical-intelligence-preview/specialist-review">Clinical Subspecialty Review</Link> · <Link href="/medical-intelligence-preview">Clinical trial dossier</Link> · <Link href="/medical-intelligence-preview/failure-desk">FDA failure desk</Link> · <Link href="/medical-intelligence-preview/applications">FDA application cases</Link></p>
 </main>;
}
