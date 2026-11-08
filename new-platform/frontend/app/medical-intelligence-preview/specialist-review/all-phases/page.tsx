import Link from "next/link";
import type {Metadata} from "next";
import {CLINICAL_SPECIALTY_PROFILES} from "../../../../lib/medical-intelligence-specialty";
import {getRegistryPhases} from "../../../../lib/medical-intelligence-registry-phase";
import {buildAllPhaseSubspecialtyReview} from "../../../../lib/medical-intelligence-specialty-all-phases";
import {DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS} from "../../../../lib/medical-intelligence-master-depth";

export const metadata:Metadata={
 title:"All-Phase Deep Clinical Subspecialty Intelligence",
 description:"Consistent disease-specific specialist research across phases, with phase-aware evidence requirements and risks."
};
export const dynamic="force-dynamic";
type Params={nct?:string;specialty?:string};
const theme={ink:"#173a30",muted:"#50695b",line:"#c9dacf",light:"#f3f8f4",green:"#006453"};
const card={background:"#fff",padding:16,border:"1px solid "+theme.line,borderRadius:12} as const;
export default async function AllPhaseSpecialistPage({searchParams}:{searchParams:Promise<Params>}){
 const query=await searchParams;
 const selectedNct=typeof query.nct==="string"&&/^NCT\d{8}$/.test(query.nct)?query.nct:"NCT06081894";
 const selectedProfileId=typeof query.specialty==="string"?query.specialty:"";
 const [registry]=await getRegistryPhases([selectedNct]);
 const review=selectedProfileId?buildAllPhaseSubspecialtyReview(selectedNct,registry.verifiedPhase,selectedProfileId):null;
 return <main style={{maxWidth:1220,margin:"24px auto",padding:"0 16px 56px",color:theme.ink,fontFamily:"system-ui,sans-serif"}}>
   <div style={{fontSize:12,color:theme.green,letterSpacing:0.8,fontWeight:780}}>POOL → VERIFIED PHASE → DEEP CLINICAL SUBSPECIALTY INTELLIGENCE</div>
   <h1 style={{fontSize:"clamp(1.7rem,4vw,2.5rem)",margin:"8px 0 6px"}}>Deep Clinical Subspecialty Intelligence · All Phases</h1>
   <p style={{fontSize:14,lineHeight:1.65,maxWidth:1050}}>
     <strong>The same disease-specialty research depth applies to every verified trial phase.</strong> The clinical questions, risks and evidence standard adapt to what the drug has actually demonstrated so far. Early-phase trials are not failed for missing later-phase results. These are scientific research prompts, not physician-certified reviews or calibrated FDA forecasts.
   </p>
   <section style={{...card,marginTop:16}}>
     <h2 style={{fontSize:18,margin:"0 0 10px"}}>Choose a trial and a clinical specialty</h2>
     <form action="/medical-intelligence-preview/specialist-review/all-phases" method="get" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:12,alignItems:"end"}}>
       <label style={{display:"grid",gap:5,fontSize:13,fontWeight:680}}>Exact ClinicalTrials.gov NCT
         <input name="nct" defaultValue={selectedNct} pattern="NCT[0-9]{8}" maxLength={11} required style={{padding:12,borderRadius:8,border:"1px solid #a3bdad",fontSize:14}}/>
       </label>
       <label style={{display:"grid",gap:5,fontSize:13,fontWeight:680}}>Proposed medical specialty (must match actual indication)
         <select name="specialty" defaultValue={selectedProfileId} required style={{padding:12,borderRadius:8,border:"1px solid #a3bdad",fontSize:14,background:"#fff"}}>
           <option value="">Select specialty</option>
           {CLINICAL_SPECIALTY_PROFILES.map(p=><option key={p.id} value={p.id}>{p.specialty}</option>)}
         </select>
       </label>
       <button type="submit" style={{padding:12,borderRadius:8,border:0,color:"#fff",background:theme.green,fontWeight:750,fontSize:14,cursor:"pointer"}}>Open phase-specific specialty assessment</button>
     </form>
     <p style={{fontSize:12,color:theme.muted,marginBottom:0}}>
       Current verified registry phase: <strong>{registry.verifiedPhase}</strong>.{" "}
       {registry.sourceUrl?<a href={registry.sourceUrl} target="_blank" rel="noopener noreferrer">View exact ClinicalTrials.gov study</a>:"Registry phase unavailable"}. Choosing a specialty does not verify the drug/indication match; that requires independent source review.
     </p>
   </section>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:10,marginTop:14}}>
     {[
       ["Consistent specialty axes",10],
       ["Science assessments",DEEP_ASSESSMENTS.length],
       ["Methods per assessment",SCIENTIFIC_LEVELS.length],
       ["Specialty profiles",CLINICAL_SPECIALTY_PROFILES.length]
     ].map(([label,value])=><div key={label} style={card}>
       <p style={{fontSize:12,color:theme.muted,margin:"0 0 7px"}}>{label}</p>
       <strong style={{fontSize:26}}>{value}</strong>
     </div>)}
   </div>
   {!review?<section style={{...card,marginTop:16}}>
     <h2 style={{fontSize:18,marginTop:0}}>Specialty confirmation required</h2>
     <p style={{fontSize:14,lineHeight:1.6}}>Select the medical specialty for the verified trial indication. The engine will not guess a subspecialty, or create a scientific score, when the specialty link has not been established.</p>
   </section>:<>
     <section style={{...card,marginTop:16}}>
       <h2 style={{fontSize:19,margin:"0 0 8px"}}>{review.profile.specialty} · {review.phase.replaceAll("_"," ")}</h2>
       <p style={{fontSize:14,lineHeight:1.6,margin:"0 0 10px"}}><strong>Disease-specific challenge:</strong> {review.profile.coreChallenge}</p>
       <p style={{fontSize:13,color:theme.muted}}>
         Specialty selection must be reconciled against the exact drug and indication before clinical findings can be attributed to this candidate.
         No historical phase completion or previous-phase efficacy is inferred from the current registry phase.
       </p>
       <div style={{display:"flex",flexWrap:"wrap",gap:14,fontSize:13}}>
         <span><strong>Phase specialist grade:</strong> {review.score.finalizedScore===null?"Not yet rated":review.score.finalizedScore+"/100"}</span>
         <span><strong>Reviewed current-phase domains:</strong> {review.score.reviewedRequiredAxes}/{review.score.requiredAxes}</span>
         <span><strong>Clinical status:</strong> {review.score.status.replaceAll("_"," ")}</span>
       </div>
     </section>
     <section style={{...card,marginTop:16}}>
       <h2 style={{fontSize:19,margin:"0 0 8px"}}>Current-phase clinical risks to investigate</h2>
       <p style={{fontSize:13,color:theme.muted}}>These are research priorities, not evidence that any listed risk actually occurred. Confirmed risk findings and their severity must be sourced to the exact study.</p>
       <div style={{display:"grid",gap:8}}>
         {review.riskQuestions.map(r=><div key={r.domain} style={{padding:11,border:"1px solid "+theme.line,borderRadius:9,background:theme.light}}>
           <strong style={{fontSize:13}}>{r.domain.replaceAll("_"," ")}</strong>
           <p style={{fontSize:13,margin:"5px 0 0"}}>{r.question}</p>
         </div>)}
       </div>
     </section>
     <section style={{...card,marginTop:16}}>
       <h2 style={{fontSize:19,margin:"0 0 8px"}}>Ten unchanged clinical subspecialty reasoning domains</h2>
       <p style={{fontSize:13,color:theme.muted}}>The domain identities are fixed throughout a drug's life cycle. Their phase-specific investigations and evidence thresholds change; unreported future data are not required prematurely.</p>
       {review.axes.map((a,i)=><details key={a.axis} open={i===0} style={{padding:"12px 14px",marginTop:8,border:"1px solid "+theme.line,borderRadius:9}}>
         <summary style={{cursor:"pointer",fontWeight:750,fontSize:14}}>
           {a.axis}. {a.name} <span style={{color:theme.muted,fontWeight:450,fontSize:12}}>· {a.expectation==="FORWARD_LOOKING"?"Future-phase consideration":"Current-phase assessment"} · Not reviewed</span>
         </summary>
         <div style={{fontSize:13,lineHeight:1.6}}>
           <p><strong>Consistent specialist question:</strong> {a.universalQuestion}</p>
           <p><strong>Current-phase examination:</strong> {a.phaseQuestion}</p>
           <p><strong>Disease-specific challenge:</strong> {a.conditionSpecificChallenge}</p>
           <p><strong>Original evidence to collect:</strong> {a.evidenceStandard}</p>
           <p><strong>Grade:</strong> Not rated. A source-backed test grade requires actual clinical evidence, an independent countercase and a dated review.</p>
         </div>
       </details>)}
       <p style={{fontSize:12,color:theme.muted,marginBottom:0}}>Scores from one phase are not treated as identical evidence quality to a different phase. Previous phase-end results, current-phase accumulated results and newest-event effects stay separate and dated.</p>
     </section>
   </>}
   <p style={{fontSize:13,marginTop:17}}>
     <Link href="/medical-intelligence-preview/specialist-review">Existing FDA application specialty dossiers</Link>
     {" · "}<Link href="/medical-intelligence-preview/master-depth">40 assessments × 20 investigations</Link>
   </p>
 </main>;
}
