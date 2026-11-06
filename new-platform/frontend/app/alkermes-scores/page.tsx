import Link from "next/link";
import source from "../../data/alks34ClinicalScorecard20261106.json";
import deepResults from "../../data/alks34RegistryDeepResults20261106.json";
import researchAudit from "../../data/alks34ProtocolSafetyApplicabilityAudit20261106.json";
import {clinicalFiveForTrial} from "../../lib/raas-clinical-five";

export const metadata={title:"Alkermes 34-Trial Clinical Scoring | PDUFA Command Center"};

const registryByNct=new Map(deepResults.records.map(r=>[r.nctId,r] as const));
const evidenceAuditByNct=new Map(researchAudit.records.map(r=>[r.nctId,r] as const));
const rows=source.records.map(r=>{
 const stage=r.clinicalStage==="post"?"post":"pre";
 const assessed=clinicalFiveForTrial({
  nctId:r.nctId,ticker:r.ticker,
  drug:r.clinicalProgramDrug||r.drug,
  indication:r.clinicalProgramIndication||r.indication
 },stage,r.clinicalStageVerified);
 const typeSpecificScore=r.studyPurpose==="SAFETY_PRIMARY"?
  (assessed.factors.find(f=>f.key==="safety")?.grade??null):assessed.researchScore;
 return {...r,assessed,typeSpecificScore,registry:registryByNct.get(r.nctId),evidenceAudit:evidenceAuditByNct.get(r.nctId)};
});
const clinicalGraded=rows.reduce((n,r)=>n+r.assessed.graded,0);
const completed=rows.filter(r=>r.studyPurpose!=="SAFETY_PRIMARY"&&r.assessed.researchScore!==null).length;
const safetyRated=rows.filter(r=>r.studyPurpose==="SAFETY_PRIMARY"&&r.typeSpecificScore!==null).length;
const typeSpecificRated=rows.filter(r=>r.typeSpecificScore!==null).length;
const knownResults=rows.filter(r=>r.historicalPrimaryOutcome!==null).length;
const allCategorized=rows.filter(r=>Boolean(r.researchDisposition)).length;
const safetyPrimary=rows.filter(r=>r.studyPurpose==="SAFETY_PRIMARY").length;
const efficacyPrimary=rows.length-safetyPrimary;
// The five-factor clinical rubric contains three efficacy-focused metrics that
// do not apply to safety-only extension studies without an efficacy hypothesis.
const notApplicableClinical=rows.reduce((n,r)=>n+r.notApplicableClinicalFactors.length,0);
const applicableClinical=rows.length*5-notApplicableClinical;
const applicableClinicalPending=applicableClinical-clinicalGraded;
const numeric=(v:number|null)=>v===null?"N/A":v.toFixed(1)+"/100";

export default function AlkermesTrialScorePage(){
 return <main className="shell" data-alks-source-scoring="2026-11-06" style={{maxWidth:1320}}>
  <div className="topline">PDUFA COMMAND CENTER · ALKS · 34 EXACT NCT TRIALS</div>
  <h1>Alkermes — Clinical scoring</h1>
  <p><strong>All 34 NCTs have a type-specific source-reviewed research grade.</strong> Efficacy/comparative trials receive a five-factor research score; safety-primary trials receive their actual graded safety factor, clearly labeled as <strong>safety only</strong>. These different scores must not be ranked as if they measure the same outcome. Neither is an FDA approval probability.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:12,margin:"20px 0"}}>
   {[
    ["Trial records classified",allCategorized+" / "+rows.length],
    ["Type-specific scores",typeSpecificRated+" / "+rows.length],
    ["Applicable clinical factors graded",clinicalGraded+" / "+applicableClinical],
    ["Complete efficacy five-factor scores",completed+" / "+efficacyPrimary],
    ["Safety-only grades",safetyRated+" / "+safetyPrimary],
    ["Non-applicable clinical factors",String(notApplicableClinical)],
    ["Applicable factors needing evidence",String(applicableClinicalPending)],
    ["Primary outcomes adjudicated",knownResults+" / "+rows.length]
   ].map(([label,value])=><section key={label} style={{background:"#f4faf5",border:"1px solid #bdd7c5",borderRadius:9,padding:15}}>
    <div style={{fontSize:24,fontWeight:800,color:"#194b2e"}}>{value}</div>
    <div style={{fontSize:13,color:"#416451"}}>{label}</div>
   </section>)}
  </div>
  <section className="panel">
   <h2>All 34 trials and five clinical factors</h2>
   <p><strong>{typeSpecificRated}/{rows.length} trials have a type-specific numeric score:</strong> {efficacyPrimary} five-factor efficacy/comparative assessments and {safetyPrimary} safety-only grades. The {notApplicableClinical} efficacy-oriented components that do not apply to safety-primary studies remain N/A, not failures. <strong>{applicableClinicalPending} applicable component grades are still missing.</strong> Ongoing Phase 3 efficacy results are not inferred from earlier Phase 2 findings.</p>
   <p><strong>Evidence coverage</strong> and <strong>design diagnostics</strong> are documentation measures, NOT efficacy scores. Clinical grades use the ordinal 0, 25, 50, 75, 100 rubric, with full composite shown only when all five are graded and the trial's readout stage is documented.</p>
   <div style={{overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:1230,fontSize:13}}>
     <thead><tr style={{textAlign:"left",background:"#e7f1e9"}}>
      {["Exact trial","Drug / indication","Registry status","Study purpose","Evidence coverage","Design diagnostic","Clinical grades","Type-specific research score","Primary outcome","Details"].map(h=><th key={h} scope="col" style={{padding:"11px 8px",borderBottom:"2px solid #aac8b3"}}>{h}</th>)}
     </tr></thead>
     <tbody>{rows.map(r=><tr key={r.nctId} data-alks-scored-trial={r.nctId} style={{borderBottom:"1px solid #d8e7dc",verticalAlign:"top"}}>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><a href={r.registryUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
      <td style={{padding:"10px 8px",minWidth:190}}><strong>{r.clinicalProgramDrug||r.drug}</strong><div style={{fontSize:11,color:"#486650",marginTop:4}}>{r.clinicalProgramIndication||r.indication}</div></td>
      <td style={{padding:"10px 8px"}}>{r.registryStatus.replaceAll("_"," ")}</td>
      <td style={{padding:"10px 8px",minWidth:155}}>{r.studyPurpose==="SAFETY_PRIMARY"?"Safety-primary":"Efficacy / comparative"}<div style={{fontSize:11}}>{r.clinicalStage==="pre"?"Prior-evidence scoring":r.clinicalStage==="post"?"Observed-result scoring":"Unclassified stage"}</div></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><strong>{r.evidenceCoverage.toFixed(1)}%</strong><div style={{fontSize:11}}>{r.unscoredQuestions}/30 analytical questions unscored</div></td>
      <td style={{padding:"10px 8px"}}>{r.designDiagnostic}/100<div style={{fontSize:11}}>Not clinical</div></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><strong>{r.assessed.graded}/{5-r.notApplicableClinicalFactors.length}</strong><div style={{fontSize:11}}>{r.notApplicableClinicalFactors.length?String(r.notApplicableClinicalFactors.length)+" factors N/A by study purpose":"All 5 factors applicable"}</div></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}} data-alks-type-score={r.nctId}><strong>{numeric(r.typeSpecificScore)}</strong><div style={{fontSize:11}}>{r.studyPurpose==="SAFETY_PRIMARY"?"Safety only — 1 factor":r.clinicalStage==="pre"?"Five-factor prior evidence":"Five-factor observed evidence"}</div></td>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}>
       {r.historicalPrimaryOutcome==="MET"?"MET":
        r.historicalPrimaryOutcome==="NOT_MET"?"NOT MET":
        r.historicalPrimaryOutcome==="NO_BINARY_PASS_FAIL"?"NON-BINARY":
        r.studyPurpose==="SAFETY_PRIMARY"?"SAFETY ENDPOINT":"Not adjudicated"}
      </td>
      <td style={{padding:"10px 8px"}}>
       <details data-alks-five-factor-expand={r.nctId}>
        <summary style={{cursor:"pointer",fontWeight:700,whiteSpace:"nowrap"}}>Five factors ▸</summary>
        <p style={{fontSize:12}}><strong>Primary outcome:</strong> {r.sourcePrimaryEndpoint}</p>
        <p style={{fontSize:12}}><strong>Evidence disposition:</strong> {r.researchDisposition.replaceAll("_"," ")}. {r.applicabilityNote}</p>
        <div style={{display:"flex",gap:8,overflowX:"auto",maxWidth:"min(700px,65vw)",padding:"12px 4px"}}>
         {r.assessed.factors.map(f=><div key={f.id} style={{flex:"0 0 190px",background:"#fff",border:"1px solid #bed8c7",borderRadius:8,padding:10}}>
          <strong style={{display:"block",fontSize:12}}>{f.name}</strong>
          <strong style={{display:"block",fontSize:20,margin:"7px 0"}}>{f.grade===null?"N/A":f.grade+"/100"}</strong>
          <div style={{fontSize:12}}>{f.finding?.replaceAll("_"," ")||((r.notApplicableClinicalFactors as readonly string[]).includes(f.key)?"Not applicable — no efficacy outcome measured":"Still requires supporting trial evidence")}</div>
          <p style={{fontSize:11,margin:"8px 0"}}>{f.grade===null&&(r.notApplicableClinicalFactors as readonly string[]).includes(f.key)?"This study did not test the clinical effect represented by this factor. No grade is applicable; this is not a zero score or efficacy failure.":f.grade===null?f.requiredEvidence:"Source-accepted research grade; not a validated FDA forecast."}</p>
          {f.sourceUrl&&<a href={f.sourceUrl} target="_blank" rel="noopener noreferrer" style={{fontSize:11}}>Original source</a>}
          {f.benchmarkSourceUrl&&<p style={{fontSize:11}}><a href={f.benchmarkSourceUrl} target="_blank" rel="noopener noreferrer">Comparator / benchmark</a></p>}
          {f.assessedAt&&<small>Reviewed {f.assessedAt}</small>}
         </div>)}
        </div>
        {r.historicalOutcomeExplanation&&<p style={{fontSize:12}}><strong>Observed primary result:</strong> {r.historicalOutcomeExplanation} {r.historicalOutcomeSource&&<a href={r.historicalOutcomeSource} target="_blank" rel="noopener noreferrer">Outcome evidence</a>}</p>}
        {r.registry&&<details style={{margin:"10px 0",border:"1px solid #c9decf",borderRadius:7,padding:9}}>
         <summary style={{cursor:"pointer",fontWeight:700}}>ClinicalTrials.gov primary results, safety events &amp; withdrawals ▸</summary>
         <p style={{fontSize:12}}><strong>Registry:</strong> {r.registry.postedResults?"Results posted":"Results not posted"} · <a href={r.registry.sourceUrl} target="_blank" rel="noopener noreferrer">Original trial record</a></p>
         {r.registry.results.map((result,i)=><div key={i} style={{margin:"8px 0",padding:8,background:"#f4faf5",borderRadius:5}}>
           <strong style={{display:"block",fontSize:12}}>{result.title}</strong>
           {result.measurements.length>0&&<p style={{fontSize:12}}>{result.measurements.map(z=>z.arm+": "+z.value+(z.lowerLimit&&z.upperLimit?" (registered interval "+z.lowerLimit+"–"+z.upperLimit+")":"")).join(" · ")}</p>}
           {result.analyses.map((a,j)=><p key={j} style={{fontSize:12}}><strong>Reported statistical analysis:</strong> {a.groupComparison} · p{a.pValueModifier||"="}{a.pValue||"unreported"}</p>)}
          </div>)}
         {r.registry.seriousAdverseEventsByArm&&<p style={{fontSize:12}}><strong>Serious adverse events by arm:</strong> {r.registry.seriousAdverseEventsByArm}</p>}
         {r.registry.otherAdverseEventsByArm&&<p style={{fontSize:12}}><strong>Other adverse events by arm:</strong> {r.registry.otherAdverseEventsByArm}</p>}
         {r.registry.participantFlowDiscontinuations&&<p style={{fontSize:12}}><strong>Withdrawal reasons:</strong> {r.registry.participantFlowDiscontinuations}</p>}
         <p style={{fontSize:11}}>Registered observations are not direct evidence of causation, and single-arm safety extension data are not efficacy results. No unreported endpoint value is inferred.</p>
        </details>}
        {!r.clinicalStageVerified&&<p style={{fontSize:12}}>The stage or current result is not sufficiently established for a complete clinical score.</p>}
       </details>
      </td>
     </tr>)}</tbody>
    </table>
   </div>
  </section>
  <section className="panel" style={{marginTop:18}} data-alks-protocol-safety-audit="2026-11-06">
   <h2>Protocol, statistics and safety evidence audit</h2>
   <p>The independent audit links all 34 exact NCT identities to recorded primary endpoints, protocol/SAP attachment status, published registry primary statistics, arm-level adverse-event summaries, and participant retention. <strong>{researchAudit.summary.publicProtocolAndSAPInSnapshot}/34</strong> have a full protocol and statistical-analysis-plan attachment in the stored registry extract; the other <strong>{researchAudit.summary.protocolAndSapNotAttachedInSnapshot}</strong> are still document-search gaps, not proof the documents do not exist. <strong>{researchAudit.summary.primaryOutcomeStatisticalAnalysesPosted}</strong> trials have posted primary statistical analyses. <strong>{researchAudit.summary.armLevelSeriousAERecords}</strong> have arm-level serious adverse-event summaries and <strong>{researchAudit.summary.participantFlowRecords}</strong> participant-flow records.</p>
   <p>Safety-only trials receive explicit primary-objective N/A labels for questions about confirmatory efficacy; these are <strong>research triage only</strong> and do not overwrite the separate 30-question production assessment or turn missing results into successes. An open-label extension cannot establish a randomized efficacy comparison. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/data/alks34ProtocolSafetyApplicabilityAudit20261106.json" target="_blank" rel="noopener noreferrer">View full source-linked research audit (JSON)</a>.</p>
   <div style={{overflowX:"auto",WebkitOverflowScrolling:"touch"}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:920,fontSize:12}}>
     <thead><tr style={{textAlign:"left",background:"#e7f1e9"}}>
      {["Exact trial","Protocol / SAP attachments","Primary analyses","Safety and retention","Review details"].map(h=><th key={h} scope="col" style={{padding:"10px 8px",borderBottom:"2px solid #aac8b3"}}>{h}</th>)}
     </tr></thead>
     <tbody>{rows.map(r=>{const a=r.evidenceAudit;return <tr key={r.nctId} data-alks-evidence-trial={r.nctId} style={{borderBottom:"1px solid #d8e7dc",verticalAlign:"top"}}>
      <td style={{padding:"10px 8px",whiteSpace:"nowrap"}}><a href={r.registryUrl} target="_blank" rel="noopener noreferrer">{r.nctId}</a></td>
      <td style={{padding:"10px 8px"}}>{a?.sourceDocuments.registryProtocolAttached?"Attached":"Not attached in registry"} / {a?.sourceDocuments.registrySapAttached?"Attached":"Not attached in registry"}</td>
      <td style={{padding:"10px 8px"}}>{a?.evidence.postedPrimaryAnalysesCount||0} registered analysis records</td>
      <td style={{padding:"10px 8px"}}>{a?.safety.seriousAdverseEventsByArm?"Arm-level SAE available":"No arm-level SAE posted"} · {a?.retention.participantFlowByArm?"Flow available":"No posted flow"}</td>
      <td style={{padding:"10px 8px"}}>
       <details data-alks-evidence-expand={r.nctId}><summary style={{cursor:"pointer",fontWeight:700}}>Sources and evidence ▸</summary>
        {a&&<div style={{maxWidth:660,marginTop:10}}>
         <p><strong>Registered primary objective:</strong> {a.primaryEndpoint.definition} ({a.primaryEndpoint.timeframe}).</p>
         <p><strong>Comparator in registry snapshot:</strong> {a.registeredComparator||"No comparator listed; do not infer a randomized comparator."}</p>
         <p><strong>Document status:</strong> {a.sourceDocuments.disposition.replaceAll("_"," ")}. This is a snapshot attachment check, not an exhaustive public-document search.</p>
         {a.evidence.reportedPrimaryStatistics.map((v,i)=><p key={i}><strong>Primary statistic:</strong> {v.primaryEndpoint} · {v.comparison||"Comparison not specified"} · p{v.pValueModifier||"="}{v.pValue||"not reported"}. <a href={v.sourceUrl} target="_blank" rel="noopener noreferrer">Registry</a></p>)}
         {a.safety.seriousAdverseEventsByArm&&<p><strong>Serious adverse-event summaries:</strong> {a.safety.seriousAdverseEventsByArm}</p>}
         {a.safety.otherNonSeriousAdverseEventsByArm&&<p><strong>Other adverse-event summaries:</strong> {a.safety.otherNonSeriousAdverseEventsByArm}</p>}
         {a.retention.participantFlowByArm&&<p><strong>Participant flow:</strong> {a.retention.participantFlowByArm}</p>}
         {a.retention.discontinuationReasonsByArm&&<p><strong>Discontinuation reasons:</strong> {a.retention.discontinuationReasonsByArm}</p>}
         {a.reviewApplicability.universalThirtyQuestionPrimaryObjectiveOnlyNotApplicable.length>0&&<p><strong>Safety-primary question triage (not applied to universal ratings):</strong> {a.reviewApplicability.universalThirtyQuestionPrimaryObjectiveOnlyNotApplicable.map(x=>x.question+" "+x.heading).join("; ")}. These questions do not test this study's registered primary safety objective.</p>}
         {a.additionalSourceEvidence&&<p><strong>Additional source crosscheck ({a.additionalSourceEvidence.evidenceType}):</strong> {a.additionalSourceEvidence.observations} <a href={a.additionalSourceEvidence.sourceUrl} target="_blank" rel="noopener noreferrer">Original report</a>. <strong>Limitations:</strong> {a.additionalSourceEvidence.limitations}</p>}
         <p><small>Observed evidence is not a prospective forecast. AE events are not proof of causation; extension cohorts cannot be compared as if randomized.</small></p>
        </div>}
       </details>
      </td>
     </tr>})}</tbody>
    </table>
   </div>
  </section>
  <section className="panel" style={{marginTop:18}}>
   <h2>Research exclusions and remaining work</h2>
   <p>Historical safety extensions and terminated studies cannot automatically be treated as pivotal efficacy successes or failures. Published results should be linked to the original endpoints, regulatory correspondence and the exact trial drug/indication. A null grade is an explicit research gap, not a negative result.</p>
   <p>Data snapshot: {source.asOf}. The type-specific score is an unvalidated research rating, not a clinical-success probability. Five-factor and safety-only values are not directly comparable. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/reports/alks-34-type-specific-research-scores-2026-11-06.csv" target="_blank" rel="noopener noreferrer">Download all 34 type-specific scores (CSV)</a>. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/reports/alks-34-trial-five-clinical-scores-2026-11-06.csv" target="_blank" rel="noopener noreferrer">Download all 34 clinical scorecards (CSV)</a>. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/reports/alks-34-clinical-factor-dispositions-2026-11-06.json" target="_blank" rel="noopener noreferrer">All 170 factor classifications and original sources</a>. <a href="https://github.com/pdufa/pdufa-command-center/blob/main/reports/alks-34-trial-evidence-scoring-2026-11-06.csv" target="_blank" rel="noopener noreferrer">Original data-gaps audit</a>. <Link href="/pipeline">Back to Pipeline</Link>.</p>
  </section>
 </main>;
}
