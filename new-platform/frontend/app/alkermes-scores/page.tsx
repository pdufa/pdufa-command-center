import Link from "next/link";
import source from "../../data/alks34ClinicalScorecard20261106.json";
import {clinicalFiveForTrial} from "../../lib/raas-clinical-five";

export const metadata={title:"Alkermes 34-Trial Clinical Scoring | PDUFA Command Center"};

const rows=source.records.map(r=>{
 const stage=r.clinicalStageVerified?"post":"pre";
 const assessed=clinicalFiveForTrial({
  nctId:r.nctId,ticker:r.ticker,
  drug:r.clinicalProgramDrug||r.drug,
  indication:r.clinicalProgramIndication||r.indication
 },stage,r.clinicalStageVerified);
 return {...r,assessed};
});
const clinicalGraded=rows.reduce((n,r)=>n+r.assessed.graded,0);
const completed=rows.filter(r=>r.assessed.researchScore!==null).length;
const knownResults=rows.filter(r=>r.historicalPrimaryOutcome!==null).length;
const numeric=(v:number|null)=>v===null?"N/A":v.toFixed(1)+"/100";

export default function AlkermesTrialScorePage(){
 return <main className="shell" data-alks-source-scoring="2026-11-06" style={{maxWidth:1320}}>
  <div className="topline">PDUFA COMMAND CENTER · ALKS · 34 EXACT NCT TRIALS</div>
  <h1>Alkermes — Clinical scoring</h1>
  <p>All 34 historical Alkermes Phase 3 records are present. The five clinical metrics are rated individually only where there is exact-trial, dated original-source evidence. <strong>Unknown measurements remain N/A, never an invented zero, midpoint or FDA approval probability.</strong></p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:12,margin:"20px 0"}}>
   {[
    ["Trial records",String(rows.length)],
    ["Clinical factors graded",clinicalGraded+" / "+rows.length*5],
    ["Complete five-factor ratings",completed+" / "+rows.length],
    ["Observed primary results",knownResults+" / "+rows.length]
   ].map(([label,value])=><section key={label} style={{background:"#f4faf5",border:"1px solid #bdd7c5",borderRadius:9,padding:15}}>
    <div style={{fontSize:24,fontWeight:800,color:"#194b2e"}}>{value}</div>
    <div style={{fontSize:13,color:"#416451"}}>{label}</div>
   </section>)}
  </div>
  <section className="panel">
   <h2>Every trial and its five scientific factors</h2>
   <p><strong>Evidence coverage</strong> and <strong>design diagnostics</strong> are documentation measures, NOT efficacy scores. Clinical grades use the ordinal 0, 25, 50, 75, 100 rubric, with full composite shown only when all five are graded and the trial's readout stage is documented.</p>
   <div style={{overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:1030,fontSize:13}}>
     <thead><tr style={{textAlign:"left",background:"#e7f1e9"}}>
      {["Exact trial","Drug / indication","Registry status","Evidence coverage","Design diagnostic","Clinical grades","Five-factor score","Primary outcome","Details"].map(h=><th key={h} scope="col" style={{padding:"11px 8px",borderBottom:"2px solid #aac8b3"}}>{h}</th>)}
     </tr></thead>
     <tbody>{rows.map(r=><tr key={r.nctId} data-alks-scored-trial={r.nctId} style={{borderBottom:"1px solid #d8e7dc",verticalAlign:"top"}}>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><a href={r.registryUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
      <td style={{padding:"10px 8px",minWidth:190}}><strong>{r.clinicalProgramDrug||r.drug}</strong><div style={{fontSize:11,color:"#486650",marginTop:4}}>{r.clinicalProgramIndication||r.indication}</div></td>
      <td style={{padding:"10px 8px"}}>{r.registryStatus.replaceAll("_"," ")}</td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><strong>{r.evidenceCoverage.toFixed(1)}%</strong><div style={{fontSize:11}}>{r.unscoredQuestions}/30 analytical questions unscored</div></td>
      <td style={{padding:"10px 8px"}}>{r.designDiagnostic}/100<div style={{fontSize:11}}>Not clinical</div></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><strong>{r.assessed.graded}/5</strong></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><strong>{numeric(r.assessed.researchScore)}</strong></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}>
       {r.historicalPrimaryOutcome==="MET"?"MET":
        r.historicalPrimaryOutcome==="NOT_MET"?"NOT MET":"Not adjudicated"}
      </td>
      <td style={{padding:"10px 8px"}}>
       <details data-alks-five-factor-expand={r.nctId}>
        <summary style={{cursor:"pointer",fontWeight:700,whiteSpace:"nowrap"}}>Five factors ▸</summary>
        <div style={{display:"flex",gap:8,overflowX:"auto",maxWidth:"min(700px,65vw)",padding:"12px 4px"}}>
         {r.assessed.factors.map(f=><div key={f.id} style={{flex:"0 0 190px",background:"#fff",border:"1px solid #bed8c7",borderRadius:8,padding:10}}>
          <strong style={{display:"block",fontSize:12}}>{f.name}</strong>
          <strong style={{display:"block",fontSize:20,margin:"7px 0"}}>{f.grade===null?"N/A":f.grade+"/100"}</strong>
          <div style={{fontSize:12}}>{f.finding?.replaceAll("_"," ")||"No supported grade yet"}</div>
          <p style={{fontSize:11,margin:"8px 0"}}>{f.grade===null?f.requiredEvidence:"Source-accepted research grade; not a validated FDA forecast."}</p>
          {f.sourceUrl&&<a href={f.sourceUrl} target="_blank" rel="noopener noreferrer" style={{fontSize:11}}>Original source</a>}
          {f.benchmarkSourceUrl&&<p style={{fontSize:11}}><a href={f.benchmarkSourceUrl} target="_blank" rel="noopener noreferrer">Comparator / benchmark</a></p>}
          {f.assessedAt&&<small>Reviewed {f.assessedAt}</small>}
         </div>)}
        </div>
        {r.historicalOutcomeExplanation&&<p style={{fontSize:12}}><strong>Observed primary result:</strong> {r.historicalOutcomeExplanation} {r.historicalOutcomeSource&&<a href={r.historicalOutcomeSource} target="_blank" rel="noopener noreferrer">Outcome evidence</a>}</p>}
        {!r.clinicalStageVerified&&<p style={{fontSize:12}}>Pre/post readout has not been adjudicated for this exact NCT. A complete post-readout score is unavailable.</p>}
       </details>
      </td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  <section className="panel" style={{marginTop:18}}>
   <h2>Research exclusions and remaining work</h2>
   <p>Historical safety extensions and terminated studies cannot automatically be treated as pivotal efficacy successes or failures. Published results should be linked to the original endpoints, regulatory correspondence and the exact trial drug/indication. A null grade is an explicit research gap, not a negative result.</p>
   <p>Data snapshot: {source.asOf}. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/reports/alks-34-trial-evidence-scoring-2026-11-06.csv" target="_blank" rel="noopener noreferrer">Download the 34-trial audit CSV</a>. <Link href="/pipeline">Back to Pipeline</Link>.</p>
  </section>
 </main>;
}
