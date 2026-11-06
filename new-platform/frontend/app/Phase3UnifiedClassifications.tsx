"use client";
import {useEffect,useMemo,useState} from "react";
import endpointAdjudications from "../data/phase3EndpointAdjudications20261105.json";
import liveCoverageSummary from "../public/phase3-six-source-harvest-summary-20261105.json";

type TrialRow={
 nctId:string;ticker:string;company:string;registryStatus:string;rosterStatus:string;
 registryAsOf:string;classificationCode:string;classification:string;classificationEvidence:string;
 classificationVerified:boolean;readoutEvidenceType:string;readoutSourceDate:string|null;
 readoutEvidenceUrl:string|null;readoutOutcome:string;drug:string|null;indication:string|null;
 registeredInterventions:string|null;registrySourceUrl:string;fdaApplicationStatus:string;
 fdaReviewType:string;pdufaGoalDate:string|null;marketCapSourceStatus:string;
 inDatedMarketCapScreen:boolean;
};
type Snapshot={schemaVersion:number;asOf:string;total:number;note:string;
 classifications:{code:string;label:string}[];counts:Record<string,number>;rows:TrialRow[]};
type MissingAudit={
 trials:number;scope:string;assessment:{
 totalSlots:number;predicted:number;observed:number;sourceFacts:number;unscored:number;
 trialsWithNumericalPredictions:number;trialsWithOutcomeAdjudication:number;
 };fields:{
 missingDrugField:number;unknownRegistryStatus:number;detailedOfficialResearch:number;
 missingDetailedOfficialResearch:number;storedProtocol:number;missingStoredProtocol:number;
 unverifiedFDAApplication:number;unverifiedPDUFADate:number;
 missingAdjudicatedEndpoint:number;outsideDatedMarketCapScreen:number;
 onlineRegistryRecords:number;onlinePrimaryEndpointCount:number;registryResultsPosted:number;
 registryStatisticalAnalyses:number;pubmedNctArticleLeads:number;secNctFilingLeads:number;
 };perQuestion:{number:number;heading:string;predictions:number;observed:number;sourceFacts:number;unscored:number}[];
 exceptions:{unknownRegistryNcts:string[];outsideMarketCapScreenNcts:string[]};
};
const cell={padding:"8px 10px",borderBottom:"1px solid #d9e5de",textAlign:"left" as const,verticalAlign:"top" as const};
const endpointByNct=new Map(endpointAdjudications.records.map(r=>[r.nctId,r] as const));
const endpointClass=(r:TrialRow):string=>{
 const result=endpointByNct.get(r.nctId)?.endpointOutcome||r.readoutOutcome;
 return result==="PRIMARY_ENDPOINT_MET"?"PASS_DOCUMENTED_PRIMARY_ENDPOINT":
  result==="PRIMARY_ENDPOINT_NOT_MET"?"FAIL_DOCUMENTED_PRIMARY_ENDPOINT":
  result==="NO_BINARY_PASS_FAIL"?"NON_BINARY_ENDPOINT":"UNDETERMINED";
};
const labels:Record<string,string>={
 NOT_INDEPENDENTLY_REVIEWED:"Unreviewed",
 PRIMARY_ENDPOINT_MET:"Primary endpoint met",
 PRIMARY_ENDPOINT_NOT_MET:"Primary endpoint not met",
 NO_BINARY_PASS_FAIL:"No binary PASS/FAIL determination",
 NOT_VERIFIED:"Not verified"
};
export default function Phase3UnifiedClassifications(){
 const [data,setData]=useState<Snapshot|null>(null);
 const [audit,setAudit]=useState<MissingAudit|null>(null);
 const [auditError,setAuditError]=useState("");
 const [error,setError]=useState("");
 const [query,setQuery]=useState("");
 const [classification,setClassification]=useState("ALL");
 const [passingFilter,setPassingFilter]=useState("ALL");
 const [page,setPage]=useState(0);
 const perPage=50;
 useEffect(()=>{
  const controller=new AbortController();
  fetch("/phase3-unified-classifications-2026-11-05.json",{cache:"no-store",signal:controller.signal})
   .then(async r=>{if(!r.ok)throw new Error("Classification source unavailable");return await r.json() as Snapshot;})
   .then(d=>{
    if(d.total!==762||d.rows.length!==762||
      new Set(d.rows.map(x=>x.nctId)).size!==762||
      Object.values(d.counts).reduce((a,b)=>a+b,0)!==762)
     throw new Error("The 762-trial classification ledger failed validation");
    if(!controller.signal.aborted)setData(d);
   })
   .catch(()=>{if(!controller.signal.aborted)setError("The source classification ledger could not be loaded or verified.");});
  return ()=>controller.abort();
 },[]);
 useEffect(()=>{
  const controller=new AbortController();
  fetch("/api/phase3-missing-data-audit",{cache:"no-store",signal:controller.signal})
   .then(async r=>{if(!r.ok)throw Error("Missing-data source unavailable");return await r.json() as MissingAudit;})
   .then(d=>{
    if(d.trials!==762||d.assessment.totalSlots!==22860||
       d.assessment.predicted+d.assessment.observed+d.assessment.sourceFacts+d.assessment.unscored!==22860||
       d.perQuestion.length!==30)throw Error("Missing-data audit failed integrity checks");
    if(!controller.signal.aborted)setAudit(d);
   })
   .catch(()=>{if(!controller.signal.aborted)setAuditError("Missing-data audit could not be loaded.");});
  return ()=>controller.abort();
 },[]);
 const filtered=useMemo(()=>{
  const term=query.trim().toLowerCase();
  return (data?.rows||[]).filter(r=>
   (classification==="ALL"||r.classificationCode===classification)&&
   (passingFilter==="ALL"||endpointClass(r)===passingFilter)&&
   (!term||[r.nctId,r.ticker,r.company,r.registryStatus,r.classification,
    r.drug||"",r.indication||"",r.registeredInterventions||""]
    .some(v=>v.toLowerCase().includes(term))));
 },[data,query,classification,passingFilter]);
 const maxPage=Math.max(1,Math.ceil(filtered.length/perPage));
 const currentPage=Math.min(page,maxPage-1);
 const shown=filtered.slice(currentPage*perPage,(currentPage+1)*perPage);
 return <section data-phase3-unified-census="762" style={{margin:"14px 0 22px",padding:14,border:"2px solid #7ea18b",borderRadius:12}}>
  <h2 style={{margin:"0 0 7px"}}>Unified Phase 3 master spreadsheet · 762 trials</h2>
  <p style={{fontSize:13,margin:"0 0 10px"}}>One unique NCT per row. <strong>Classification is based on observed evidence, not assumed 425/337 counts.</strong> The original registry state, registered outcome and released readout evidence are retained separately. Source-qualified primary-endpoint PASS and FAIL refer to clinical results, not FDA approval. Unreviewed and descriptive studies remain explicitly distinguished. All 762 records have a 190-column export, but not all 190 fields have scored scientific results.</p>
  {!data?<p role="status">{error||"Loading classifications for 762 trials…"}</p>:<>
   <div style={{display:"flex",flexWrap:"wrap",gap:8,margin:"10px 0 14px"}}>
    {data.classifications.map(c=><button type="button" key={c.code} onClick={()=>{setClassification(classification===c.code?"ALL":c.code);setPage(0)}}
      aria-pressed={classification===c.code}
      style={{padding:"7px 10px",borderRadius:8,cursor:"pointer",fontSize:12,border:classification===c.code?"2px solid #287c53":"1px solid #a2b9aa",background:"transparent",color:"inherit",textAlign:"left"}}>
      {c.label} <strong>({data.counts[c.code]})</strong>
     </button>)}
    <button type="button" onClick={()=>{setClassification("ALL");setPage(0)}} aria-pressed={classification==="ALL"}
      style={{padding:"7px 10px",border:"1px solid #a2b9aa",borderRadius:8,background:"transparent",color:"inherit",cursor:"pointer",fontSize:12}}>All 762</button>
   </div>
   <p style={{fontSize:13,margin:"10px 0"}}><strong>Outcome scrutiny:</strong>{" "}
    {endpointAdjudications.totalReviewed} of {data.total} exact-NCT public result records reviewed.{" "}
    <strong>{endpointAdjudications.counts.PRIMARY_ENDPOINT_MET} primary endpoints met</strong>,{" "}
    <strong>{endpointAdjudications.counts.PRIMARY_ENDPOINT_NOT_MET} not met</strong>,{" "}
    {endpointAdjudications.counts.NO_BINARY_PASS_FAIL} descriptive/non-binary,{" "}
    {data.total-endpointAdjudications.totalReviewed} without source-adjudicated primary endpoint status.
    Source review is not equivalent to completing every predictive assessment.</p>
   <div style={{display:"flex",gap:7,flexWrap:"wrap",margin:"10px 0"}}>
    {[
      ["ALL","All passing classifications",data.total],
      ["PASS_DOCUMENTED_PRIMARY_ENDPOINT","PASS",endpointAdjudications.counts.PRIMARY_ENDPOINT_MET],
      ["FAIL_DOCUMENTED_PRIMARY_ENDPOINT","FAIL",endpointAdjudications.counts.PRIMARY_ENDPOINT_NOT_MET],
      ["NON_BINARY_ENDPOINT","Non-binary",endpointAdjudications.counts.NO_BINARY_PASS_FAIL],
      ["UNDETERMINED","Undetermined",data.total-endpointAdjudications.totalReviewed]
     ].map(([code,label,count])=><button type="button" key={String(code)}
      aria-pressed={passingFilter===code}
      onClick={()=>{setPassingFilter(String(code));setPage(0)}}
      style={{padding:"6px 9px",border:"1px solid #9bb3a3",borderRadius:8,background:"transparent",color:"inherit",cursor:"pointer"}}>
      {label} ({count})</button>)}
   </div>
   <label style={{display:"block",fontSize:13}}>Search the entire unified trial spreadsheet
    <input type="search" value={query} onChange={e=>{setQuery(e.target.value);setPage(0)}}
     placeholder="Ticker, NCT, company, indication, classification" style={{display:"block",padding:9,width:"100%",maxWidth:510,marginTop:5}}/>
   </label>
   <p style={{fontSize:12,margin:"12px 0"}}><strong><a href="/api/phase3-unified-190-columns?live=1">Download live-registry evidence · all 762 trials × 190 columns (CSV)</a></strong>{" · "}<a href="/api/phase3-unified-190-columns">Saved evidence version</a>{" · "}<a href="/phase3-unified-classifications-2026-11-05.csv" download>Original classification CSV</a></p>
   <section aria-label="Six-source online research sweep" data-phase3-six-source-sweep="762"
    style={{border:"1px solid #a1b5a7",borderRadius:10,padding:12,margin:"12px 0"}}>
    <h3 style={{margin:"0 0 8px"}}>Online source recovery · all 762 trials</h3>
    <p style={{fontSize:13,margin:"6px 0"}}>
     <strong>{liveCoverageSummary.sources.clinicalTrialsGov.nctRecordsRetrieved} / 762</strong> registry records queried;{" "}
     <strong>{liveCoverageSummary.sources.clinicalTrialsGov.postedResults}</strong> have posted registry results,
     including <strong>{liveCoverageSummary.sources.clinicalTrialsGov.postedStatisticalAnalyses}</strong> with statistical analyses.
     <strong> {liveCoverageSummary.sources.clinicalTrialsGov.publicDocuments}</strong> have public documents.
    </p>
    <p style={{fontSize:12,margin:"6px 0"}}>
     <strong>{liveCoverageSummary.sources.pubMed.trialsWithExactNctArticleMentions}</strong> NCTs have PubMed article mentions;{" "}
     <strong>{liveCoverageSummary.sources.secEdgar.trialsWithExactNctFilingMentions}</strong> have SEC filing mentions.
     Publications and filings are evidence leads, not verified primary-endpoint outcomes.
    </p>
    <p style={{fontSize:12,margin:"6px 0"}}>
     <strong><a href="/api/phase3-live-registry-backfill">Download current registry evidence for all 762 trials (CSV)</a></strong>{" · "}
     <a href="/api/phase3-source-coverage?format=csv">Recovered source facts for 762 trials (CSV)</a>{" · "}
     <a href="/phase3-six-source-harvest-summary-20261105.json">Six-source coverage report (JSON)</a>
    </p>
    <p style={{fontSize:11,margin:"6px 0 0"}}>AACT, FDA and international sources were also probed; access and NCT-to-application matching limitations are documented in the report.
     A posted registry result is not automatically PASS, and an SEC or PubMed hit is not proof of success.</p>
   </section>
   <section aria-label="Phase 3 missing data audit" data-phase3-missing-audit="762"
    style={{border:"1px solid #a1b5a7",borderRadius:10,padding:12,margin:"12px 0"}}>
    <h3 style={{margin:"0 0 8px"}}>Missing-data recheck · all 762 NCTs</h3>
    {!audit?<p style={{fontSize:12}}>{auditError||"Checking saved research coverage…"}</p>:<>
     <p style={{fontSize:13,margin:"8px 0"}}>
      <strong>{audit.assessment.unscored.toLocaleString()} of {audit.assessment.totalSlots.toLocaleString()}</strong> assessment question slots remain UNSCORED;{" "}
      {audit.assessment.sourceFacts.toLocaleString()} hold documented source facts,{" "}
      {audit.assessment.observed} observed outcome/readout facts, and{" "}
      {audit.assessment.predicted} have numerical predictions across{" "}
      {audit.assessment.trialsWithNumericalPredictions} trials.
     </p>
     <p style={{fontSize:12,margin:"8px 0"}}>
      <strong>Current online recovery:</strong> {audit.fields.onlineRegistryRecords} registry records;{" "}
      {audit.fields.onlinePrimaryEndpointCount} primary outcome fields;{" "}
      {audit.fields.registryResultsPosted} posted registry results;{" "}
      {audit.fields.registryStatisticalAnalyses} posted statistical analyses.
      <strong> Earlier local cache:</strong> {audit.fields.detailedOfficialResearch} detailed records
      and {audit.fields.storedProtocol} protocol summaries. The earlier cache counts
      do not reflect today's online source availability.
     </p>
     <p style={{fontSize:12,margin:"8px 0"}}>
      <strong>Important missingness:</strong> {audit.fields.missingDrugField} separately named drug fields empty
      (but registered interventions are preserved); {audit.fields.unknownRegistryStatus} unknown registry statuses;{" "}
      {audit.fields.missingAdjudicatedEndpoint} primary-endpoint outcomes not adjudicated;{" "}
      {audit.fields.unverifiedFDAApplication} FDA applications unverified;{" "}
      {audit.fields.unverifiedPDUFADate} PDUFA dates unverified.
     </p>
     <p style={{fontSize:12,margin:"8px 0"}}>
      <strong>Universe exception:</strong> {audit.fields.outsideDatedMarketCapScreen} trial(s) outside the stored
      dated market-cap screen ({audit.exceptions.outsideMarketCapScreenNcts.join(", ")||"none"}).
      Registry-status exceptions: {audit.exceptions.unknownRegistryNcts.join(", ")||"none"}.
     </p>
     <p style={{fontSize:12,margin:"8px 0"}}><strong>
      <a href="/api/phase3-missing-data-audit?format=csv">Download missing-data audit · 762 trial rows × 46 columns (CSV)</a>
     </strong></p>
     <details>
      <summary style={{cursor:"pointer",fontWeight:650,fontSize:13}}>Expand missing data by all 30 analytical questions</summary>
      <div style={{overflowX:"auto",maxHeight:420,overflowY:"auto"}}>
       <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:670}}>
        <thead><tr>{["Question","Unscored","Documented source facts","Observed evidence","Predictions"].map(h=>
         <th key={h} scope="col" style={cell}>{h}</th>)}</tr></thead>
        <tbody>{audit.perQuestion.map(q=><tr key={q.number}>
         <td style={cell}>Q{String(q.number).padStart(2,"0")} · {q.heading}</td>
         <td style={cell}>{q.unscored}</td><td style={cell}>{q.sourceFacts}</td>
         <td style={cell}>{q.observed}</td><td style={cell}>{q.predictions}</td>
        </tr>)}</tbody>
       </table>
      </div>
     </details>
     <p style={{fontSize:11,margin:"8px 0 0"}}>Scope: {audit.scope}.
      An UNSCORED question is not proof that no public evidence exists.
      A registry fact, PubMed mention, or SEC hit is not a favorable scientific prediction.
      FDA application and PDUFA dates can be inapplicable for earlier-stage trials.</p>
    </>}
   </section>
   <p role="status" style={{fontSize:12}}>Showing {shown.length} of {filtered.length} matching trials · source classification as of {data.asOf}. Dated registry status is not proof of trial results.</p>
   <div role="region" aria-label="Unified Phase 3 trial classifications" style={{overflowX:"auto",maxHeight:630,overflowY:"auto"}}>
    <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:1000}}>
     <thead><tr>{["Ticker","Trial / NCT","Company","Registry status","Trial classification","Passing classification","Result","FDA / PDUFA","Evidence / details"].map(x=><th key={x} scope="col" style={{...cell,position:"sticky",top:0,background:"var(--surface,#f7f9f8)",zIndex:1}}>{x}</th>)}</tr></thead>
     <tbody>{shown.map(r=><tr key={r.nctId} data-nct-id={r.nctId} data-trial-classification={r.classificationCode} data-passing-classification={endpointClass(r)}>
      <td style={cell}>{r.ticker}</td>
      <td style={cell}><a href={r.registrySourceUrl} rel="noopener noreferrer" target="_blank">{r.nctId}</a></td>
      <td style={cell}>{r.company}</td>
      <td style={cell}>{r.registryStatus.replaceAll("_"," ")}</td>
      <td style={cell}><strong>{r.classification}</strong></td>
      <td style={cell}>{endpointClass(r)==="PASS_DOCUMENTED_PRIMARY_ENDPOINT"?<strong>PASS · primary endpoint met</strong>:
       endpointClass(r)==="FAIL_DOCUMENTED_PRIMARY_ENDPOINT"?<strong>FAIL · primary endpoint not met</strong>:
       endpointClass(r)==="NON_BINARY_ENDPOINT"?"Descriptive / not binary":"Undetermined"}</td>
      <td style={cell}>{labels[endpointByNct.get(r.nctId)?.endpointOutcome||r.readoutOutcome]||(endpointByNct.get(r.nctId)?.endpointOutcome||r.readoutOutcome).replaceAll("_"," ")}</td>
      <td style={cell}>{r.fdaApplicationStatus==="NOT_VERIFIED"?"FDA application not verified":r.fdaApplicationStatus}{r.pdufaGoalDate?" · "+r.pdufaGoalDate:""}</td>
      <td style={cell}>
       <details><summary style={{cursor:"pointer",fontWeight:650}}>Sources & status</summary>
        <div style={{padding:"8px 0",minWidth:240}}>
         <p style={{margin:"4px 0"}}>{r.classificationEvidence}</p>
         {endpointByNct.get(r.nctId)&&<p style={{margin:"4px 0"}}>
          <strong>Primary-endpoint adjudication:</strong> {endpointByNct.get(r.nctId)?.rationale}
         </p>}
         {endpointByNct.get(r.nctId)&&<p><a href={endpointByNct.get(r.nctId)?.evidenceUrl}
          rel="noopener noreferrer" target="_blank">Primary endpoint source</a></p>}
         <p style={{margin:"4px 0"}}>Registry as of: {r.registryAsOf}</p>
         {r.drug&&<p style={{margin:"4px 0"}}>Drug: {r.drug}</p>}
         {r.indication&&<p style={{margin:"4px 0"}}>Indication: {r.indication}</p>}
         {r.readoutSourceDate&&<p style={{margin:"4px 0"}}>Public data date: {r.readoutSourceDate}</p>}
         <a href={r.registrySourceUrl} rel="noopener noreferrer" target="_blank">ClinicalTrials.gov</a>
         {r.readoutEvidenceUrl&&r.readoutEvidenceUrl!==r.registrySourceUrl&&
           <p><a href={r.readoutEvidenceUrl} rel="noopener noreferrer" target="_blank">Readout evidence</a></p>}
        </div>
       </details>
      </td>
     </tr>)}</tbody>
    </table>
   </div>
   <div style={{display:"flex",alignItems:"center",gap:14,marginTop:12}}>
    <button type="button" disabled={currentPage===0} onClick={()=>setPage(Math.max(0,currentPage-1))}>Previous</button>
    <span style={{fontSize:12}}>Page {currentPage+1} of {maxPage}</span>
    <button type="button" disabled={currentPage>=maxPage-1} onClick={()=>setPage(Math.min(maxPage-1,currentPage+1))}>Next</button>
   </div>
   <p style={{fontSize:12,marginBottom:0}}>Provisional pre-data means registry active without confirmed readout status. Official registry results and issuer publications are distinguished. Completed does not imply released results; review priority, PDUFA action date and FDA approval remain unverified without exact application evidence.</p>
  </>}
 </section>;
}
