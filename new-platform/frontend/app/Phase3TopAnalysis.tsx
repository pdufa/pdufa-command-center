"use client";
import {useState} from "react";
import {phase3QuestionSlots,phase3CompletedQuestions,phase3DocumentedQuestionFacts,PHASE3_QUESTION_COUNT} from "../lib/phase3-top-questions";
const tableCell={padding:"8px",borderBottom:"1px solid #d6e6db",textAlign:"left" as const};
export function TopPhase3Analysis({nctId}:{nctId:string}){
 const questions=phase3QuestionSlots(nctId),predictions=phase3CompletedQuestions(nctId);
 const facts=phase3DocumentedQuestionFacts(nctId);
 const [expanded,setExpanded]=useState(false);
 const [openQuestions,setOpenQuestions]=useState<number[]>(nctId==="NCT06641089"?[2,3]:[]);
 return <details data-phase3-analysis={nctId} onToggle={e=>{if(e.currentTarget===e.target)setExpanded(e.currentTarget.open);}}
  style={{minWidth:230,maxWidth:510}}>
  <summary style={{cursor:"pointer",fontWeight:750}}>
   {PHASE3_QUESTION_COUNT} questions · {predictions} predictions · {facts} source facts
  </summary>
  {expanded&&<div style={{fontSize:12,lineHeight:1.5,marginTop:7}}>
   <p><strong>Pre-readout research only.</strong> Predictions, source documentation and missing evidence
    are separate. Source-documentation scores are NOT approval probabilities. RAAS surveys remain cancelled.</p>
   {questions.map(q=><details key={q.number} open={openQuestions.includes(q.number)}
    onToggle={e=>{const nowOpen=e.currentTarget.open;
     setOpenQuestions(old=>nowOpen?
       old.includes(q.number)?old:[...old,q.number]:old.filter(x=>x!==q.number));}}
    style={{padding:"7px 0",borderTop:"1px solid #d6e6db"}}>
    <summary style={{cursor:"pointer"}}>
     Q{q.number} · {q.heading}{q.answer?" · "+q.answer.prediction+" "+q.answer.score+"/100":
      q.observation?" · source documented":" · not scored"}
    </summary>
    <div><p><strong>{q.question}</strong></p>
    {q.answer?<div>
     <div data-phase3-prediction={q.answer.prediction} style={{margin:"10px 0",padding:"10px 12px",
      border:"2px solid #a4c9ad",borderRadius:8,background:"#f0f8f2"}}>
      <div style={{fontSize:12,fontWeight:750,letterSpacing:"0.07em",color:"#24583a"}}>PREDICTED · NOT REPORTED</div>
      <div style={{display:"flex",alignItems:"baseline",gap:14,flexWrap:"wrap"}}>
       <div style={{fontSize:34,lineHeight:1.12,fontWeight:900,letterSpacing:"0.05em",color:q.answer.prediction==="FAIL"?"#9d2424":"#155e34"}}>{q.answer.prediction}</div>
       <div data-question-score={q.number} style={{fontSize:27,fontWeight:850,color:"#155e34"}}>
        {q.answer.score}<span style={{fontSize:15,fontWeight:650}}>/100</span>
       </div>
      </div>
      <div style={{fontSize:11,color:"#38624a",marginTop:4}}>
       Subjective favorable-outcome score · not a reported result or statistically calibrated probability
      </div>
      <p style={{margin:"6px 0 0"}}>{q.answer.summary}</p>
     </div>
     <p><strong>Reason:</strong> {q.answer.reason}</p>
     <p>Prediction recorded {q.answer.asOf}; evidence cutoff: {q.answer.evidenceCutoff}.</p>
     <p><strong>Actual Phase 3 results:</strong> not included in this prediction.</p>
     <ul>{q.answer.sources.map(s=><li key={s.url}>
      <a href={s.url} target="_blank" rel="noopener noreferrer">{s.label}</a></li>)}</ul>
    </div>:q.observation?<div>
     <p style={{fontSize:15,fontWeight:800,color:"#155e34"}}>DOCUMENTED SOURCE FACT · {q.observation.documentationScore}/100</p>
     <p><strong>Documentation-only score.</strong> It confirms the registry field appears in the saved
      source; it does not predict trial PASS, clinical benefit, FDA approval or a PDUFA decision.</p>
     <p>{q.observation.description}</p>
     <a href={q.observation.sourceUrl} target="_blank" rel="noopener noreferrer">Source registry</a>
    </div>:<div>
     <p><strong>NOT SCORED.</strong> Available evidence cannot support a trial-outcome prediction.</p>
     <p><strong>Evidence needed:</strong> {q.missingEvidence}</p>
    </div>}
    </div>
   </details>)}
  </div>}
 </details>;
}

/** A visible analysis example, kept explicitly outside the market-cap-screened
 * membership and source counts until the live CSV verifies inclusion. */
export function TopPhase3ResearchExample(){
 return <section data-top-phase3-research-example="NCT06641089"
  style={{border:"1px solid #94bba3",borderRadius:8,padding:12,margin:"12px 0",background:"#f8fcf9"}}>
  <h4 style={{margin:"0 0 6px"}}>Current analysis case · IZAR-2 (MLTX)</h4>
  <p style={{fontSize:12,margin:"5px 0"}}>
   Sonelokimab · psoriatic arthritis · Phase 3 NCT06641089. Public primary
   readout has not been released; MoonLake expects initial Week 16 results in Q1 2027.
   This example is also in the dated candidate batch. It is <strong>not issuer-confirmed
   unreleased</strong> and is not automatically counted as FDA/PDUFA-qualified.
  </p>
  <p style={{fontSize:12,margin:"5px 0"}}>
   <a href="https://clinicaltrials.gov/study/NCT06641089" target="_blank" rel="noopener noreferrer">ClinicalTrials.gov</a>{" · "}
   <a href="https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and" target="_blank" rel="noopener noreferrer">Company update · Nov 4, 2026</a>
  </p>
  <div style={{overflowX:"auto"}}><table style={{width:"100%",fontSize:13,borderCollapse:"collapse"}}>
   <thead><tr>{["Ticker","NCT","Drug","Indication","Public Phase 3 result","30-question analysis"].map(h=><th key={h} scope="col" style={tableCell}>{h}</th>)}</tr></thead>
   <tbody><tr>
    <td style={tableCell}>MLTX</td><td style={tableCell}>NCT06641089</td>
    <td style={tableCell}>Sonelokimab</td><td style={tableCell}>Psoriatic arthritis</td>
    <td style={tableCell}>Not reported</td>
    <td style={tableCell}><TopPhase3Analysis nctId="NCT06641089"/></td>
   </tr></tbody>
  </table></div>
 </section>;
}
