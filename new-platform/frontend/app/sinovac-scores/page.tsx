import Link from "next/link";
import data from "../../data/sva27TrialEvidenceScorecard20261106.json";
export const metadata={title:"Sinovac 27-trial evidence scoring | PDUFA Command Center"};
const outcomes=data.records.filter(r=>r.observedPrimaryOutcome!==null);
const finished=data.records.filter(r=>r.registryStatus==="COMPLETED").length;
const scoreLabel=(r:typeof data.records[number])=>r.observedPrimaryOutcome==="PRIMARY_ENDPOINT_MET"?"MET":
  r.observedPrimaryOutcome==="PRIMARY_ENDPOINT_NOT_MET"?"NOT MET":
  r.observedPrimaryOutcome==="NO_BINARY_PASS_FAIL"?"MIXED / NONBINARY":"No exact-NCT primary verdict";
export default function SinovacScores(){
 return <main className="shell" style={{maxWidth:1330}}>
  <div className="topline">PDUFA COMMAND CENTER · SVA · COMPANY RESEARCH #2 · 2026-11-06</div>
  <h1>Sinovac — 27 Phase 3 trial records</h1>
  <p><Link href="/phase-first">Open current phase-specific evidence, missing-data audit and rating history</Link>. The documentary scores below are the preserved earlier source snapshot.</p>
  <p><strong>All 27 exact-NCT trials have numeric documentary coverage scores.</strong> These measure the fraction of the existing 30 analytical data slots with recorded evidence or observations, <strong>not clinical efficacy, regulatory probability or trade suitability</strong>. A full five-factor clinical rating remains unavailable unless supported by five individually reviewed primary and benchmark sources.</p>
  <div className="panel" style={{border:"2px solid #d19a54"}}>
   <h2>Trading gate — excluded from actionable shortlist</h2>
   <p>Sinovac reported that Nasdaq trading has remained halted since February 22, 2019. The company's 2026 return to periodic-report compliance does not itself prove trading has resumed. Preserve historical clinical evidence while excluding SVA from a live tradable $300M–$10B PDUFA screening shortlist.</p>
   <p><a href={data.tradeGate.evidenceUrl} target="_blank" rel="noopener noreferrer">Original 2025 annual report (filed 2026)</a></p>
  </div>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(155px,1fr))",gap:12,margin:"18px 0"}}>
   {[
    ["Census trial records",data.records.length+" / "+data.censusCount],
    ["Documentary Q slots",data.documentedQuestionSlots+" / "+data.questionTotal],
    ["Primary endpoints identified",data.exactTrialPrimaryEndpointsCaptured+" / "+data.records.length],
    ["Historical outcomes",outcomes.length+" / "+data.records.length],
    ["Primary MET",String(data.historicalPrimaryMet)],
    ["Mixed outcome",String(data.historicalPrimaryMixed)],
    ["Completed registry trials",String(finished)],
   ].map(([label,value])=><section key={label} style={{border:"1px solid #bed8c7",borderRadius:9,padding:13,background:"#f4faf5"}}>
    <strong style={{fontSize:23,color:"#194b2e"}}>{value}</strong><div style={{fontSize:12,color:"#416451"}}>{label}</div>
   </section>)}
  </div>
  <section className="panel">
   <h2>All 27 source-linked studies</h2>
   <p>The score below is documentary completeness only. Registry status COMPLETED means follow-up has finished, <em>not</em> that a primary endpoint was achieved. A published journal result may exist even when no results are deposited on ClinicalTrials.gov.</p>
   <div style={{overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:1020,fontSize:13}}>
     <thead><tr style={{background:"#e7f1e9",textAlign:"left"}}>
      {["Exact trial","Drug and indication","Study status","Documentary score","Clinical score","Historical endpoint","Original evidence"].map(x=><th key={x} scope="col" style={{padding:9,borderBottom:"2px solid #aac8b3"}}>{x}</th>)}
     </tr></thead>
     <tbody>{data.records.map(r=><tr key={r.nctId} style={{borderBottom:"1px solid #d8e7dc",verticalAlign:"top"}}>
      <td style={{padding:9,whiteSpace:"nowrap"}}><a href={r.registryUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
      <td style={{padding:9,minWidth:170}}><strong>{r.drug}</strong><div style={{fontSize:11,color:"#486650"}}>{r.indication}</div></td>
      <td style={{padding:9}}>{r.registryStatus.replaceAll("_"," ")}</td>
      <td style={{padding:9}}><strong>{r.documentationScore.toFixed(1)}%</strong><div style={{fontSize:11}}>{r.documentedQuestionCount}/30 documented slots</div></td>
      <td style={{padding:9}}>N/A<div style={{fontSize:11}}>Five-factor clinical grade not established</div></td>
      <td style={{padding:9}}><strong>{scoreLabel(r)}</strong></td>
      <td style={{padding:9}}>
       {r.observedPrimarySource?<a href={r.observedPrimarySource} target="_blank" rel="noopener noreferrer">Published NCT-linked result</a>:r.otherPublishedResearchSource?<a href={r.otherPublishedResearchSource} target="_blank" rel="noopener noreferrer">Published study — not adjudicated</a>:<span>Registry only — no adjudicated outcome</span>}
       <details><summary style={{cursor:"pointer",fontWeight:600}}>Evidence notes ▸</summary>
        <p><strong>Registered primary outcome:</strong> {r.registeredPrimaryEndpoint}</p>
        <p>{r.observedPrimaryOutcomeRationale||"No exact-NCT public primary-endpoint conclusion accepted yet. Do not infer efficacy from the registry status."}</p>
        {r.otherPublishedResearchSource&&<p><a href={r.otherPublishedResearchSource} target="_blank" rel="noopener noreferrer">Other published study evidence (not primary adjudication)</a>: {r.otherPublishedResearchNote}</p>}
        <p>{r.clinicalScoreReason}</p>
       </details>
      </td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  <p><strong>Source as of:</strong> {data.asOf}. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/reports/sva-27-documentation-and-outcome-scores-2026-11-06.csv" target="_blank" rel="noopener noreferrer">Download all 27 evidence scores (CSV)</a>. <Link href="/pipeline">Back to Pipeline</Link>.</p>
 </main>
}
