"use client";
import {phase3QuestionSlots,phase3CompletedQuestions,PHASE3_QUESTION_COUNT} from "../lib/phase3-top-questions";
const tableCell={padding:"8px",borderBottom:"1px solid #d6e6db",textAlign:"left" as const};
export function TopPhase3Analysis({nctId}:{nctId:string}){
 const questions=phase3QuestionSlots(nctId),completed=phase3CompletedQuestions(nctId);
 return <details data-phase3-analysis={nctId} style={{minWidth:235,maxWidth:500}}>
  <summary style={{cursor:"pointer",fontWeight:700}}>
   Analysis · {completed}/{PHASE3_QUESTION_COUNT} documented
  </summary>
  <div style={{fontSize:12,lineHeight:1.5,marginTop:7}}>
   <p><strong>Pre-readout predictions only.</strong> No Phase 3 efficacy result is inferred. Question scores are subjective 0–100 confidence indicators, not calibrated probabilities; RAAS surveys remain cancelled.</p>
   {questions.map(q=><details key={q.number} open={(q.number===2||q.number===3)&&!!q.answer} style={{padding:"7px 0",borderTop:"1px solid #d6e6db"}}>
    <summary style={{cursor:"pointer"}}>
     Q{q.number} · {q.heading}{q.answer?" — predicted "+q.answer.prediction:" — not assessed"}
    </summary>
    {q.answer?<div>
     <p><strong>{q.answer.question}</strong></p>
     <div data-phase3-prediction={q.answer.prediction} style={{margin:"10px 0",padding:"10px 12px",border:"2px solid #a4c9ad",borderRadius:8,background:"#f0f8f2"}}>
      <div style={{fontSize:12,fontWeight:750,letterSpacing:"0.07em",color:"#24583a"}}>PREDICTED · NOT REPORTED</div>
      <div style={{display:"flex",alignItems:"baseline",gap:14,flexWrap:"wrap"}}>
       <div style={{fontSize:34,lineHeight:1.12,fontWeight:900,letterSpacing:"0.05em",color:"#155e34"}}>{q.answer.prediction}</div>
       <div data-question-score={q.number} style={{fontSize:27,lineHeight:1.16,fontWeight:850,color:"#155e34"}}>{q.answer.score}<span style={{fontSize:15,fontWeight:650}}>/100</span></div>
      </div>
      <div style={{fontSize:11,color:"#38624a",marginTop:4}}>Subjective prediction-confidence score · not a reported result or statistically calibrated probability</div>
      <p style={{margin:"6px 0 0"}}>{q.answer.summary}</p>
     </div>
     <p><strong>Reason:</strong> {q.answer.reason}</p>
     <p>Prediction recorded: {q.answer.asOf}. Evidence baseline: {q.answer.evidenceCutoff}.</p>
     <p><strong>Actual IZAR-2 Phase 3 result:</strong> not reported as of 2026-11-05.</p>
     <ul>{q.answer.sources.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.label}</a></li>)}</ul>
    </div>:<p>Reserved for the original Question {q.number}. Its wording and analysis have not been established; no result has been invented.</p>}
   </details>)}
  </div>
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
   This is an <strong>analysis example, not an added cap-screen-qualified trial</strong>,
   and is not included in TOP source counts.
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
