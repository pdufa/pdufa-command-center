import Link from "next/link";
import data from "../../data/sva27TrialEvidenceScorecard20261106.json";

export const metadata={title:"Sinovac 27-Trial Evidence Scores | PDUFA Command Center"};

const records=[...data.records].sort((a,b)=>a.unscoredQuestionCount-b.unscoredQuestionCount);
const known=records.filter(r=>r.observedPrimaryOutcome!==null).length;
const numeric=(n:number)=>n.toFixed(1)+"/100";

export default function SinovacScoresPage(){
 return <main className="shell" style={{maxWidth:1280}}>
  <div className="topline">PDUFA COMMAND CENTER · SVA · 27 EXACT-NCT TRIALS</div>
  <h1>Sinovac — trial evidence scores</h1>
  <p>All 27 registered Phase 3 trials have an <strong>evidence-documentation coverage score</strong> and an exact ClinicalTrials.gov primary endpoint. These numeric documentation scores are <strong>not clinical effectiveness ratings, five-factor RAAS scores, investment recommendations, or FDA approval probabilities.</strong></p>
  <div style={{border:"1px solid #d8b77c",borderRadius:9,padding:12,background:"#fffaf0",margin:"16px 0"}}>
   <strong>US trading gate: research only.</strong> The company's 2025 Form 20-F reports Nasdaq trading of SVA common shares has been halted since 2019. Restoration of listing compliance is not evidence of trading resumption. No US PDUFA milestone is established for these trials. <a href="https://www.sec.gov/Archives/edgar/data/1084201/000119312526258534/sva-20251231.htm" target="_blank" rel="noopener noreferrer">Original filing</a>
  </div>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(156px,1fr))",gap:12,margin:"20px 0"}}>
   {[
    ["Trial rows",records.length+"/27"],
    ["Documentary scores",records.filter(r=>r.documentationScore!==null).length+"/27"],
    ["Registered primary definitions",records.filter(r=>Boolean(r.registeredPrimaryEndpoint)).length+"/27"],
    ["Published outcome classifications",known+"/27"],
    ["Original-source primary MET",String(records.filter(r=>r.observedPrimaryOutcome==="PRIMARY_ENDPOINT_MET").length)],
    ["Nonbinary / mixed readouts",String(records.filter(r=>r.observedPrimaryOutcome==="NO_BINARY_PASS_FAIL").length)],
    ["Full clinical-five scores",String(data.unvalidatedClinicalFiveScores)+"/27"]
   ].map(([label,value])=><section key={label} style={{background:"#f4faf5",border:"1px solid #bdd7c5",borderRadius:8,padding:12}}>
    <strong style={{display:"block",fontSize:23,color:"#194b2e"}}>{value}</strong><small>{label}</small>
   </section>)}
  </div>
  <section className="panel">
   <h2>All 27 trials — exact NCT and source evidence</h2>
   <p>Scores are <strong>100 × documented Q01–Q30 question slots / 30</strong>, rounded to one decimal. A 36.7 documentation score means 11 questions have documentary facts; it does <strong>not</strong> mean 36.7% clinical efficacy or chance of approval. Missing numerical clinical-five grades remain N/A.</p>
   <div style={{overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:960,fontSize:13}}>
     <thead><tr style={{textAlign:"left",background:"#e7f1e9"}}>
      {["Exact NCT","Vaccine / indication","Stage","Documentation score","Source coverage","Original readout","Research detail"].map(x=><th key={x} scope="col" style={{padding:"10px 8px",borderBottom:"2px solid #aac8b3"}}>{x}</th>)}
     </tr></thead>
     <tbody>{records.map(r=><tr key={r.nctId} style={{verticalAlign:"top",borderBottom:"1px solid #d8e7dc"}}>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><a href={r.registryUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
      <td style={{padding:"10px 8px",minWidth:180}}><strong>{r.drug}</strong><div style={{marginTop:4,fontSize:11}}>{r.indication}</div></td>
      <td style={{padding:"10px 8px"}}>{r.trialStage.startsWith("PRE")?"Ongoing / pre-readout":"Historical / completed"}<div style={{fontSize:11}}>{r.registryStatus.replaceAll("_"," ")}</div></td>
      <td style={{padding:"10px 8px"}}><strong>{numeric(r.documentationScore)}</strong><div style={{fontSize:11}}>Documentation only</div></td>
      <td style={{padding:"10px 8px"}}>{r.documentedQuestionCount}/30 documented<div style={{fontSize:11}}>{r.unscoredQuestionCount} questions pending</div></td>
      <td style={{padding:"10px 8px",minWidth:120}}>{r.observedPrimaryOutcome==="PRIMARY_ENDPOINT_MET"?"MET (historical)":r.observedPrimaryOutcome==="NO_BINARY_PASS_FAIL"?"MIXED / NONBINARY":"Not adjudicated"}</td>
      <td style={{padding:"10px 8px"}}>
       <details><summary style={{cursor:"pointer",fontWeight:700}}>View evidence ▸</summary>
        <div style={{padding:10,minWidth:235,maxWidth:420}}>
         <p><strong>Registered primary endpoint:</strong> {r.registeredPrimaryEndpoint}</p>
         <p><strong>Historical result:</strong> {r.observedPrimaryOutcomeRationale||"No exact-NCT source-accepted primary outcome yet; do not infer success from registry completion."}</p>
         {r.observedPrimarySource&&<p><a href={r.observedPrimarySource} target="_blank" rel="noopener noreferrer">Read original published result</a></p>}
         <p><strong>Five-factor clinical score:</strong> N/A — needs five source-supported reviews, not registry fields.</p>
         <p><a href={r.registryUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov original record</a></p>
        </div>
       </details>
      </td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  <section className="panel" style={{marginTop:18}}>
   <h2>What is and is not complete</h2>
   <p>27/27 registry identities, registered primary endpoints and numeric documentary scores are complete. {known}/27 exact-NCT historical readouts have been source adjudicated; the rest remain unresolved or ongoing. No full five-factor clinical composite is awarded without the required evidence. Some positive vaccine immune-response results are surrogate endpoints and cannot establish US FDA approval.</p>
   <p>Snapshot {data.asOf}. <Link href="/pipeline">Return to Pipeline</Link>.</p>
  </section>
 </main>;
}
