"use client";
import {useEffect,useMemo,useState} from "react";
import type {DmiApplication,DmiSnapshot,DmiSource} from "../lib/deep-medical-intelligence";
import css from "./DeepMedicalIntelligencePreview.module.css";

const show=(value:unknown)=>typeof value==="string"&&value.trim()?value:"Not documented";
const status=(value:unknown)=>show(value).replaceAll("_"," ");
const sourceUrl=(source:DmiSource)=>{
 try{const url=new URL(source.url);return url.protocol==="https:"&&!url.username&&!url.password?source.url:null;}catch{return null;}
};
function SourceButtons({ids,sources,onSelect}:{ids:readonly string[];sources:readonly DmiSource[];onSelect:(id:string)=>void}){
 return <>{ids.map(id=>{
  const source=sources.find(item=>item.id===id);
  return source?<button type="button" className={css.sourceButton} key={id} onClick={()=>onSelect(id)} data-dmi-source-link={id}>{source.title}</button>:<span key={id} className={css.subtle}>Source reference unavailable: {id}</span>;
 })}</>;
}
function SourceViewer({source}:{source:DmiSource|null}){
 if(!source)return <div className={css.sourceViewer}><h4>Source drilldown</h4><p>Select a source to inspect the recorded observation, document locator and dates.</p></div>;
 const url=sourceUrl(source);
 return <div className={css.sourceViewer} data-dmi-source-viewer={source.id} aria-live="polite">
  <h4>{source.title}</h4><span className={css.badge}>{status(source.status)}</span><span className={css.badge}>{source.kind}</span>
  <dl><dt>Source date</dt><dd>{show(source.sourceDate)}</dd><dt>Retrieved</dt><dd>{show(source.retrievedAt)}</dd>
   <dt>Locator</dt><dd>{show(source.locator)}</dd><dt>Evidence type</dt><dd>{show(source.evidenceType)}</dd>
   <dt>Reliability</dt><dd>{show(source.reliability)}</dd><dt>Identifiers</dt><dd>{source.identifiers?.join(" · ")||"Not documented"}</dd></dl>
  <p><strong>Recorded finding</strong></p><blockquote>{show(source.observation)}</blockquote>
  {url?<a href={url} target="_blank" rel="noopener noreferrer">Open original document</a>:<p>Original document URL is unavailable.</p>}
 </div>;
}
function ApplicationDossier({application,sourceFilter}:{application:DmiApplication;sourceFilter:string}){
 const [selectedSource,setSelectedSource]=useState<string|null>(null);
 const sources=application.sources;
 const selected=sources.find(source=>source.id===selectedSource)??null;
 const sourceMatches=sources.filter(source=>[source.id,source.title,source.url,source.observation].some(text=>text.toLowerCase().includes(sourceFilter.trim().toLowerCase())));
 const selectSource=(id:string)=>{
  setSelectedSource(id);
  requestAnimationFrame(()=>document.getElementById("dmi-sources-"+application.id)?.scrollIntoView({behavior:"smooth",block:"nearest"}));
 };
 return <section className={css.dossier} aria-label={"Application dossier for "+application.drug} data-dmi-dossier={application.id}>
  <header className={css.dossierHeader}>
   <p className={css.eyebrow}>{application.ticker} · {application.company}</p><h2>{application.drug} · {application.indication}</h2>
   <p>{application.applicationNumber??"Application number not documented"} · {show(application.applicationType)} · Review cycle: {show(application.reviewCycle)}</p>
   <p>Linked trials: {application.nctIds.map((nct,index)=><span key={nct}>{index>0?" · ":""}<a href={"https://clinicaltrials.gov/study/"+nct} target="_blank" rel="noopener noreferrer">{nct}</a></span>)}</p>
  </header>
  <div className={css.decisionGrid}>
   {[{title:"Leading application outcome",decision:application.outcome},{title:"Decision timing",decision:application.timing}].map(item=><div key={item.title} className={css.decision}>
    <h3>{item.title}</h3><strong>{show(item.decision.leading)}</strong><span className={css.badge}>Confidence: {status(item.decision.confidence)}</span>
    <p>{show(item.decision.rationale)}</p><p><b>Contrary argument:</b> {show(item.decision.contraryArgument)}</p>
    <p><b>Evidence that would change the assessment:</b> {show(item.decision.evidenceWouldChange)}</p>
    <span className={css.subtle}>Assessment timestamp: {show(item.decision.predictionTimestamp)}</span>
    <SourceButtons ids={item.decision.sourceIds} sources={sources} onSelect={selectSource}/>
   </div>)}
  </div>
  {application.blockers.length>0&&<div className={css.blockers}><strong>Unresolved blockers</strong><ul>{application.blockers.map((blocker,index)=><li key={index}>{blocker}</li>)}</ul></div>}
  <h3 className={css.railHeading}>Medical and regulatory dossier · scroll horizontally</h3>
  <div className={css.rail} role="region" tabIndex={0} aria-label={"Ten dossier sections for "+application.id} data-dmi-rail={application.id}>
   {application.sections.map((section,index)=><article key={section.id} className={css.sectionCard} data-dmi-section={section.id}>
    <span className={css.sectionNumber}>{String(index+1).padStart(2,"0")}</span><h3>{section.title}</h3>
    {section.findings.length>0?section.findings.map((finding,position)=><div key={position} className={css.finding}>
     <span className={css.badge}>{status(finding.status)}</span><span className={css.badge}>{finding.kind}</span>
     <p>{finding.text}</p>{finding.limitations&&<p className={css.subtle}>Limit: {finding.limitations}</p>}
     <SourceButtons ids={finding.sourceIds} sources={sources} onSelect={selectSource}/>
    </div>):<p className={css.subtle}>Evidence has not been established for this section.</p>}
   </article>)}
  </div>
  <div className={css.bodySection}><h3>Failure risks and resolution requirements</h3><div className={css.riskGrid}>
   {application.failureRisks.map(risk=><article key={risk.id} className={css.risk} data-dmi-risk={risk.id}>
    <h4>{risk.title}</h4><span className={css.badge}>{status(risk.status)}</span><span className={css.badge}>Severity: {status(risk.severity)}</span>
    <p><b>Possible consequence:</b> {show(risk.consequence)}</p><p><b>Evidence:</b> {show(risk.evidence)}</p>
    <SourceButtons ids={risk.sourceIds} sources={sources} onSelect={selectSource}/>
    <p><b>Counterevidence:</b> {show(risk.counterevidence)}</p><SourceButtons ids={risk.counterSourceIds} sources={sources} onSelect={selectSource}/>
    <p><b>Resolution:</b> {show(risk.resolution)}</p>
    <p><b>Missing documents:</b> {risk.missingDocuments.length?risk.missingDocuments.join("; "):"No specific resolution document recorded"}</p>
   </article>)}
  </div></div>
  <div className={css.bodySection}><h3>Competing application arguments</h3><div className={css.argumentGrid}>
   {([{id:"approval",title:"Approval argument"},{id:"crl",title:"Complete Response Letter argument"},{id:"delay",title:"Delay argument"}] as const).map(argument=><article className={css.argument} key={argument.id}>
    <h4>{argument.title}</h4>{application.arguments[argument.id].length?application.arguments[argument.id].map((item,index)=><div key={index}><p>{item.text}</p><SourceButtons ids={item.sourceIds} sources={sources} onSelect={selectSource}/></div>):<p>No supported argument recorded.</p>}
   </article>)}
  </div></div>
  <div className={css.bodySection}><h3>Owner critical review</h3><p className={css.subtle}>No outside reviewer or independent signoff required. Owner checks competing arguments, source limits and unresolved evidence; no owner signoff is recorded by this preview.</p>
   {application.gaps.length>0&&<details><summary>Unresolved evidence gaps ({application.gaps.length})</summary><ul>{application.gaps.map((gap,index)=><li key={index}>{gap}</li>)}</ul></details>}
  </div>
  <div id={"dmi-sources-"+application.id} className={css.bodySection}><h3>Source documents and exact findings</h3><div className={css.sourceArea}>
   <div className={css.sourceList}>{sourceMatches.length?sourceMatches.map(source=><div key={source.id} className={css.sourceItem}>
    <button type="button" className={css.sourceButton} onClick={()=>setSelectedSource(source.id)} data-dmi-source={source.id}>{source.title}</button>
    <span className={css.subtle}>{show(source.sourceDate)} · {status(source.status)}</span>
   </div>):<p>No sources match this filter.</p>}</div><SourceViewer source={selected}/>
  </div></div>
 </section>;
}
export default function DeepMedicalIntelligencePreview(){
 const [data,setData]=useState<DmiSnapshot|null>(null),[error,setError]=useState("");
 const [query,setQuery]=useState(""),[trial,setTrial]=useState("ALL"),[sourceFilter,setSourceFilter]=useState("");
 const [selected,setSelected]=useState<string|null>(null);
 useEffect(()=>{
  const controller=new AbortController();
  fetch("/api/preview/deep-medical-intelligence",{signal:controller.signal}).then(async response=>{
   if(!response.ok)throw Error("The preview evidence packet is unavailable or requires identity/source validation.");
   return response.json();
  }).then(value=>setData(value)).catch(reason=>{if(reason.name!=="AbortError")setError(reason.message);});
  return()=>controller.abort();
 },[]);
 const trials=useMemo(()=>data?[...new Set(data.applications.flatMap(application=>application.nctIds))].sort():[],[data]);
 const applications=useMemo(()=>{
  const term=query.trim().toLowerCase(),source=sourceFilter.trim().toLowerCase();
  return data?.applications.filter(application=>[application.company,application.ticker,application.drug,application.indication,application.applicationNumber??""].some(value=>value.toLowerCase().includes(term)))
   .filter(application=>trial==="ALL"||application.nctIds.includes(trial))
   .filter(application=>!source||application.sources.some(item=>[item.id,item.title,item.url,item.observation].some(value=>value.toLowerCase().includes(source))))??[];
 },[data,query,trial,sourceFilter]);
 const opened=applications.find(application=>application.id===selected)??null;
 return <main className={css.root}>
  <p className={css.eyebrow}>Isolated functional preview · source-linked research</p><h1>Deep Medical Intelligence</h1>
  <p className={css.intro}>Application-level medical and regulatory dossiers connect each proposed drug and indication to its supporting trials. The leading application outcome and decision timing remain separate assessments, with uncertainty, contrary arguments and unresolved evidence shown alongside them.</p>
  <p className={css.notice}>Preview evidence is distinct from an FDA decision. An indeterminate assessment means the available evidence cannot support a categorical conclusion. This area does not change existing trial records or numerical ratings.</p>
  {error?<p role="alert" className={css.error}>{error}</p>:!data?<p role="status">Loading application dossiers and source records…</p>:<>
   <p className={css.counts}>{data.inventory.focusTrials} FOCUS trials · {data.inventory.applications} grouped applications · Snapshot {data.asOf}. Metadata screened: {data.inventory.metadataScreenedTrials}; source extracted: {data.inventory.sourceExtractedTrials}; fully reviewed: {data.inventory.fullyReviewedTrials}; incomplete: {data.inventory.incompleteTrials}.</p>
   <p className={css.counts}>Completed decisions: {data.inventory.completedDecisions} · Unresolved blockers: {data.inventory.unresolvedBlockers} · Source documents: {data.inventory.sourceDocuments}. <a href="/api/preview/deep-medical-intelligence?format=json">Open the preview evidence packet</a></p>
   <div className={css.toolbar}>
    <label>Application<input aria-label="Filter applications" placeholder="Company, drug, indication or application" value={query} onChange={event=>setQuery(event.target.value)}/></label>
    <label>Exact trial<select aria-label="Filter exact trial" value={trial} onChange={event=>setTrial(event.target.value)}><option value="ALL">All linked trials</option>{trials.map(nct=><option value={nct} key={nct}>{nct}</option>)}</select></label>
    <label>Source<input aria-label="Filter sources" placeholder="Document title, URL or finding" value={sourceFilter} onChange={event=>setSourceFilter(event.target.value)}/></label>
   </div>
   <p className={css.counts}>{applications.length} application{applications.length===1?"":"s"} match the filters.</p>
   <div className={css.tableScroll}><table className={css.table}><thead><tr><th>Company / drug</th><th>Indication / supporting trials</th><th>PDUFA / source status</th><th>Review progress</th><th>Leading application outcome</th><th>Decision timing</th><th>Blockers / dossier</th></tr></thead>
    <tbody>{applications.map(application=><tr key={application.id} data-dmi-application={application.id}>
     <td><b>{application.ticker} · {application.company}</b><span className={css.subtle}>{application.drug}</span></td>
     <td>{application.indication}<span className={css.subtle}>{application.nctIds.join(" · ")}</span></td>
     <td>{show(application.pdufa.date)}<span className={css.badge}>{status(application.pdufa.status)}</span></td>
     <td>{show(application.progress.stage)}<span className={css.badge}>{status(application.progress.status)}</span></td>
     <td><b>{show(application.outcome.leading)}</b><span className={css.subtle}>Confidence: {status(application.outcome.confidence)}</span></td>
     <td>{show(application.timing.leading)}<span className={css.subtle}>Confidence: {status(application.timing.confidence)}</span></td>
     <td><span className={css.subtle}>{application.blockers.length} unresolved</span><button type="button" className={css.expand} aria-expanded={selected===application.id} aria-controls={"dmi-dossier-"+application.id} onClick={()=>setSelected(selected===application.id?null:application.id)}>Dossier {selected===application.id?"▾":"▸"}</button></td>
    </tr>)}</tbody>
   </table></div>
   {opened&&<div id={"dmi-dossier-"+opened.id}><ApplicationDossier key={opened.id} application={opened} sourceFilter={sourceFilter}/></div>}
   {data.limitations.length>0&&<details style={{marginTop:20}}><summary>Preview scope and limitations</summary><ul>{data.limitations.map((limitation,index)=><li key={index}>{limitation}</li>)}</ul></details>}
  </>}
 </main>;
}
