"use client";

import {useState} from "react";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";
type SourceManifest=NonNullable<
 typeof import("../../../lib/focus-r86-original-document-inventory").R86_ORIGINAL_DOCUMENT_MANIFEST
>;
type Row=SourceManifest["rows"][number];
type Document={
 type:string;label:string|null;documentDate:string|null;uploadDate:string|null;
 filename:string;sizeBytes:number;listsProtocol:boolean;listsSap:boolean;listsIcf:boolean;
};
type Current={
 nct:string;docsInCurrentRegistry:number;listedProtocolDocuments:number;
 listedSapDocuments:number;listedConsentDocuments:number;
 currentRegistryResultsPosted:boolean;
 postedResultModules:null|{
  participantFlowGroups:number|null;endpointMeasures:number|null;
  seriousAdverseEventTerms:number|null;otherAdverseEventTerms:number|null
 };
 documents:Document[];nextEvidenceAction:string;
 prospectivelyLockedSapAuthenticated:false;
 qualifiedIndependentScientificReview:false;
 independentFDAForecast:"ABSTAIN";
};
type Lookup={status:"loading"|"ok"|"error";result?:Current;error?:string};
type PdfReceipt={nct:string;filename:string;sha256:string;pdfByteLength:number;
 sourcePdfUrl:string;retrievedAtUtc:string;originalSignedSapChronologyVerified:false;
 independentHumanReviewSigned:false};
type PdfLookup={status:"loading"|"ok"|"error";result?:PdfReceipt;error?:string};
export default function OriginalSourceDocumentsR86Client({rows}:{rows:Row[]}){
 const [checks,setChecks]=useState<Record<string,Lookup>>({});
 const [fileReceipts,setFileReceipts]=useState<Record<string,PdfLookup>>({});
 const [runningAll,setRunningAll]=useState(false);
 async function checkOne(nct:string){
  setChecks(x=>({...x,[nct]:{status:"loading"}}));
  try{
   const response=await fetch(
    "/predictions/original-documents/check?nct="+encodeURIComponent(nct),
    {cache:"no-store",headers:{"Accept":"application/json"}}
   );
   const body:unknown=await response.json();
   if(!response.ok || !body || typeof body!=="object" ||
      !("nct" in body) || body.nct!==nct){
    const message=body&&typeof body==="object"&&"error" in body&&
      typeof body.error==="string"?body.error:"OFFICIAL_REGISTRY_CHECK_FAILED";
    setChecks(x=>({...x,[nct]:{status:"error",error:message}}));
    return;
   }
   const result=body as Current;
   setChecks(x=>({...x,[nct]:{status:"ok",result}}));
  }catch{
   setChecks(x=>({...x,[nct]:{status:"error",
     error:"NETWORK_ERROR_NO_SOURCE_VERIFICATION_CLAIM"}}));
  }
 }
 async function hashPublicOriginal(nct:string,filename:string){
  const key=nct+":"+filename;
  setFileReceipts(x=>({...x,[key]:{status:"loading"}}));
  try{
   const r=await fetch(
    "/predictions/original-documents/checksum?nct="+encodeURIComponent(nct)+
    "&filename="+encodeURIComponent(filename),
    {cache:"no-store",headers:{"Accept":"application/json"}}
   );
   const data:unknown=await r.json();
   if(!r.ok||!data||typeof data!=="object"||
      !("nct" in data)||data.nct!==nct||
      !("filename" in data)||data.filename!==filename||
      !("sha256" in data)||typeof data.sha256!=="string"||
      !/^[0-9a-f]{64}$/u.test(data.sha256)){
     const reason=data&&typeof data==="object"&&"error" in data&&
      typeof data.error==="string"?data.error:"PUBLIC_PDF_BYTE_CHECK_FAILED";
     setFileReceipts(x=>({...x,[key]:{status:"error",error:reason}}));return;
   }
   setFileReceipts(x=>({...x,[key]:{status:"ok",result:data as PdfReceipt}}));
  }catch{
   setFileReceipts(x=>({...x,[key]:{status:"error",
     error:"PUBLIC_PDF_BYTE_RETRIEVAL_FAILED_NO_HASH_CLAIM"}}));
  }
 }
 async function checkAll(){
  if(runningAll)return;
  setRunningAll(true);
  try{
   // Fixed concurrency four, no background storage or periodic polling.
   for(let start=0;start<rows.length;start+=4){
    await Promise.all(rows.slice(start,start+4).map(r=>checkOne(r.nct)));
   }
  }finally{setRunningAll(false);}
 }
 const completed=rows.filter(r=>checks[r.nct]?.status==="ok").length;
 const failed=rows.filter(r=>checks[r.nct]?.status==="error").length;
 const withProtocol=rows.filter(r=>checks[r.nct]?.result?.listedProtocolDocuments).length;
 const withSAP=rows.filter(r=>checks[r.nct]?.result?.listedSapDocuments).length;
 const withResults=rows.filter(r=>checks[r.nct]?.result?.currentRegistryResultsPosted).length;
 return <section aria-label="Live original-document metadata inventory">
  <div className={styles.controls}>
   <button type="button" onClick={()=>{void checkAll();}} disabled={runningAll}
    style={{cursor:"pointer",padding:"11px 16px",borderRadius:8,
      background:"#155c47",color:"#fff",border:"none",fontWeight:750}}>
    {runningAll?"Checking original-source records…":"Check all 29 current registry source records"}
   </button>
  </div>
  <p className={styles.notice} aria-live="polite">
   <strong>{completed}/29</strong> current records inspected in this session;
   <strong> {failed}</strong> check errors;
   among checked records <strong>{withProtocol}</strong> list protocol files,
   <strong> {withSAP}</strong> list SAP files, and
   <strong> {withResults}</strong> report posted aggregate results.
   These count public source listings, <em>not</em> authenticated signed
   originals or verified medical analyses.
  </p>
  <div className={styles.coverageGrid}>
  {rows.map(row=>{
   const lookup=checks[row.nct];
   const current=lookup?.result;
   return <article className={styles.coverageGroup} key={row.nct}>
    <strong>{row.ticker} · {row.nct}</strong>
    <div>{row.registryReportedPhase} · last archived registry update {row.sourceUpdatedDate}</div>
    {row.focusCase&&<div><b>Original-source pilot:</b> {row.focusCase==="ACACIA_HCM"?
      "ACACIA-HCM — dual primary and safety chronology":
      "Launch-HTN — original SAP and unblinding chronology"}</div>}
    <div><b>Existing publication lead:</b> {row.publishedMainReportLead?
      <a href={row.publishedMainReportLead} target="_blank" rel="noopener noreferrer">
       Open indexed publication (not adjudicated)
      </a>:"No publication indexed in five-study subset; other sources may exist"}</div>
    <div><b>Provisional FDA cycle(s):</b> {row.cycleIds.join(", ")}</div>
    <p><button type="button" disabled={runningAll||lookup?.status==="loading"}
     onClick={()=>{void checkOne(row.nct);}} style={{cursor:"pointer",
      border:"1px solid #75a592",background:"#fff",borderRadius:7,
      padding:"8px 12px",fontWeight:700,color:"#145d45"}}>
      {lookup?.status==="loading"?"Checking current record…":
       "Check current protocol/SAP and result listings"}
    </button></p>
    {lookup?.status==="error"&&<p role="alert">
     No successful source read: {lookup.error}. Nothing is verified.</p>}
    {current&&<div aria-live="polite">
     <div><b>Current public document listings:</b> {current.docsInCurrentRegistry}
      {" · "} Protocol {current.listedProtocolDocuments}
      {" · "} SAP {current.listedSapDocuments}
      {" · "} Consent {current.listedConsentDocuments}</div>
     <div><b>Registry aggregate results:</b> {current.currentRegistryResultsPosted?
       "posted (unreviewed)":"not posted in this current registry record"}</div>
     {current.postedResultModules&&<div>
       Posted endpoint measures: {current.postedResultModules.endpointMeasures??"not shown"};
       serious AE terms: {current.postedResultModules.seriousAdverseEventTerms??"not shown"};
       participant-flow groups: {current.postedResultModules.participantFlowGroups??"not shown"}.
       These are metadata counts, not trial conclusions.
     </div>}
     <details className={styles.coverageDetails}>
      <summary>Review the {current.documents.length} original-file listing entries</summary>
      {current.documents.length===0?<p>No protocol/SAP large-file metadata
       in the current registry record. Historical or other documents may exist.</p>:
       <ul>{current.documents.map((d,i)=><li key={d.filename+"-"+i}>
        <b>{d.filename}</b> ({d.type}) · {d.sizeBytes.toLocaleString()} bytes;
        {d.listsProtocol?" protocol":""}{d.listsSap?" SAP":""}
        {d.listsIcf?" ICF":""}; document date {d.documentDate??"unlisted"},
        upload {d.uploadDate??"unlisted"}
        {d.label&&<div>{d.label}</div>}
        {(d.listsProtocol||d.listsSap)&&<div>
         <button type="button" disabled={fileReceipts[row.nct+":"+d.filename]?.status==="loading"}
          onClick={()=>{void hashPublicOriginal(row.nct,d.filename);}}
          style={{padding:"7px 10px",borderRadius:7,
           border:"1px solid #75a592",background:"white",color:"#165c47",
           cursor:"pointer",fontWeight:700}}>
          {fileReceipts[row.nct+":"+d.filename]?.status==="loading"?
           "Retrieving public PDF bytes…":"Read public PDF and compute SHA-256"}
         </button>
         {fileReceipts[row.nct+":"+d.filename]?.status==="error"&&
           <div role="alert">Public source checksum unavailable:
            {fileReceipts[row.nct+":"+d.filename]?.error}</div>}
         {fileReceipts[row.nct+":"+d.filename]?.result&&<div>
          <strong>Public source byte SHA-256 (not a signed-source attestation):</strong>
          <code>{fileReceipts[row.nct+":"+d.filename].result?.sha256}</code>
          <div>Read {fileReceipts[row.nct+":"+d.filename].result?.pdfByteLength.toLocaleString()} PDF bytes;
           source retrieval {fileReceipts[row.nct+":"+d.filename].result?.retrievedAtUtc}</div>
          <a href={fileReceipts[row.nct+":"+d.filename].result?.sourcePdfUrl}
           target="_blank" rel="noopener noreferrer">Open public source PDF</a>
          <small>Original prospective signature and database-lock chronology
           remain unverified; this checksum alone is not a clinical assessment.</small>
         </div>}
        </div>}
       </li>)}</ul>}
      <p>No document bytes, provenance hashes, effective signed dates,
       database-lock log, or unblinding history have been authenticated by this check.
       Open the original study for documents.</p>
     </details>
     <p><small><strong>Next evidence action:</strong> {current.nextEvidenceAction}</small></p>
    </div>}
    {row.knownBlockers.length>0&&<details className={styles.coverageDetails}>
     <summary>{row.knownBlockers.length} original-source issues requiring independent review</summary>
     <ul>{row.knownBlockers.map(b=><li key={b.id}>
      <b>{b.label}</b> — {b.status}<div>{b.evidence}</div>
     </li>)}</ul>
    </details>}
    <p><small>Original registry identity SHA-256:
      <code>{row.archivedOriginalRegistrySha256}</code></small></p>
    <a href={row.registryUrl} target="_blank" rel="noopener noreferrer">
      Open official ClinicalTrials.gov record
    </a>
   </article>;
  })}
  </div>
 </section>;
}
