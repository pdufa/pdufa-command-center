import {evaluatePilotRun,type PilotIdentity} from "../../lib/pilot-assessment-run";

/** Display a saved research run. Rendering never starts collection, a job or a trade. */
export default function PersistedPilotResult({run,expectedIdentity}:{run:unknown;expectedIdentity?:PilotIdentity}){
 const assessment=evaluatePilotRun(run,expectedIdentity);
 const saved=assessment.run;
 if(!saved)return <section className="panel" aria-label="Persisted trial assessment"><h2>Saved trial assessment unavailable</h2><p role="status">INDETERMINATE. {assessment.issues.join(" ")}</p></section>;
 const findingIds=new Set(assessment.usableFindingIds),historyIds=new Set(assessment.usableHistoricalIds);
 const findings=saved.findings.filter(f=>findingIds.has(f.id)),history=saved.history.filter(h=>historyIds.has(h.id));
 const sourceById=new Map(saved.sources.map(source=>[source.id,source]));
 const citations=(ids:string[])=><ul>{ids.map(id=>{const source=sourceById.get(id);return source?<li key={id}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.id}</a> · {source.sourceClass} · Published {source.publishedOn||"date unverified"} · Observed {source.observedAt}</li>:null;})}</ul>;
 const duration=(seconds:number|null)=>seconds===null?"Not measured":`${seconds.toFixed(1)} seconds`;
 const completed=assessment.science?.completedAssessments??0;
 return <section className="panel" aria-label="Persisted trial assessment">
  <h2>Saved first-trial assessment · {saved.drug}</h2>
  <p>{saved.indication} · {saved.nctId} · Cutoff {saved.asOf} · Run {saved.runId}</p>
  <p>FDA target: {saved.decisionTarget.date} · Sponsor reported; independently verified application/cycle reconciliation remains required.</p>
  <p role="status"><strong>Preliminary outcome: {assessment.preliminaryOutcome}</strong> · {assessment.status.replaceAll("_"," ")}. This is an abstention, not an FDA regulatory outcome.</p>
  <p>Approval probability: unavailable. Nonapproval probability: unavailable. Prediction confidence: unavailable. Model validation: incomplete. Trading authorization: disabled.</p>
  <p>{assessment.sources.textObserved} source text observations; {assessment.sources.unavailable} unavailable; {assessment.sources.unknownPublicationDate} without verified publication dates. These counts do not certify independent evidence review.</p>
  <h3>Source-cited findings</h3>
  {findings.length?findings.map(finding=><article key={finding.id}><h4>{finding.domain} · {finding.approvalDirection.replaceAll("_"," ")}</h4><p>{finding.text}</p>{citations(finding.sourceIds)}</article>):<p>No source-available findings can be displayed at this cutoff.</p>}
  {saved.findings.length>findings.length&&<p>{saved.findings.length-findings.length} findings withheld because citations are unavailable or outside the cutoff.</p>}
  <h3>Supporting and opposing arguments</h3>
  {(["supportingFindingIds","opposingFindingIds"] as const).map(side=><article key={side}><h4>{side==="supportingFindingIds"?"Supporting approval":"Opposing approval"}</h4>
   {saved.adversarial[side].filter(id=>findingIds.has(id)).map(id=><p key={id}>{findings.find(f=>f.id===id)?.text}</p>)}
  </article>)}
  {saved.adversarial.notes.map((note,i)=><p key={i}>{note}</p>)}
  <details aria-label="Saved historical trial comparison"><summary>Historical context · {history.length} source-cited examples · {assessment.independentlyVerifiedHistoricalCycles} independently verified eligible cycles</summary>
   <p>Selected development examples are excluded from independent validation. Observed source claims do not establish a complete or calibrated outcome cohort.</p>
   {history.map(item=><article key={item.id}><h4>{item.drug} · {item.nctId||"Trial identity unresolved"}</h4>
    <p>Observed action claim: {item.actionObserved.replaceAll("_"," ")} · {item.actionDate||"Date unresolved"} · Application {item.applicationId||"not reconciled"}. Model eligible: no.</p>
    <p>Similarities: {item.similarities.join("; ")||"Not established"}</p><p>Differences: {item.differences.join("; ")||"Not established"}</p>{citations(item.sourceIds)}
   </article>)}
  </details>
  <h3>Scientific framework</h3>
  <p>{completed}/40 completed assessment records; {assessment.science?.completedLevels??0}/20 reviewed levels; {assessment.science?.coveredLayers??0}/8 represented layers. {assessment.science?.status.replaceAll("_"," ")||"Reviewed scientific protocol and independent dossier remain missing."}</p>
  {saved.science.notes.map((note,i)=><p key={i}>{note}</p>)}
  <h3>Processing time</h3>
  <ul><li>Total: {duration(saved.timing.totalSeconds)}</li><li>Evidence collection: {duration(saved.timing.collectionSeconds)}</li><li>Historical comparison: {duration(saved.timing.comparisonSeconds)}</li><li>Scientific assessments: {duration(saved.timing.scienceSeconds)}</li><li>Prediction generation: {duration(saved.timing.predictionSeconds)}</li></ul>
  <p>{saved.timing.measurementBasis} The 45-minute processing target remains an engineering objective.</p>
  <h3>Outstanding evidence and method requirements</h3>
  <ul>{assessment.issues.map((issue,i)=><li key={i}>{issue}</li>)}</ul>
  <p>Research method: {assessment.methodVersion}. No justified PASS/FAIL classifier or independently validated prediction accuracy is established by this run.</p>
 </section>;
}
