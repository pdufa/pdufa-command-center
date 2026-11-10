"use client";
import {useState} from "react";
import {R89_ARCHIVED_ACACIA_SOURCE_HISTORY} from "../../../lib/focus-r89-acacia-prior-original-history";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";
type Manifest=NonNullable<typeof import(
 "../../../lib/focus-r89-historical-source-recovery").R89_HISTORICAL_SOURCE_RECOVERY>;
type Row=Manifest["rows"][number];
type HistoryIndex={
 nct:string;historyVersionCount:number;
 versions:Array<{apiIndex:number;uiVersion:number;submittedDate:string}>;
};
type HistoricalVersion={
 nct:string;apiIndex:number;uiVersion:number;submittedDate:string;
 originalPrimaryOutcomeCount:number|null;originalPublicDocumentListingCount:number;
 listedProtocolOrSapDocuments:Array<{
  filename:string;typeAbbrev:string|null;documentDate:string|null;
  registryUploadDate:string|null;hasProtocol:boolean;hasSAP:boolean;
  reportedSize:number|null;
 }>;
 prospectivelyAuthenticatedSignedSAP:false;independentScientificReview:false;
 FDAForecast:"ABSTAIN";
};
type Readback={status:"loading"|"ok"|"error";data?:HistoryIndex;error?:string};
type VersionReadback={status:"loading"|"ok"|"error";data?:HistoricalVersion;error?:string};
function errMessage(value:unknown){
 return value&&typeof value==="object"&&"error" in value&&
  typeof value.error==="string"?value.error:"OFFICIAL_PUBLIC_HISTORY_UNAVAILABLE";
}
export default function OriginalHistoryRecoveryR89Client({rows}:{rows:Row[]}){
 const [histories,setHistories]=useState<Record<string,Readback>>({});
 const [versions,setVersions]=useState<Record<string,VersionReadback>>({});
 async function loadHistory(nct:string){
  setHistories(x=>({...x,[nct]:{status:"loading"}}));
  try{
   const resp=await fetch("/predictions/source-recovery/history?nct="+nct,{
     cache:"no-store",headers:{"Accept":"application/json"}});
   const json:unknown=await resp.json();
   if(!resp.ok||!json||typeof json!=="object"||!("nct" in json)||
      json.nct!==nct||!("historyVersionCount" in json)||
      typeof json.historyVersionCount!=="number"){
    setHistories(x=>({...x,[nct]:{status:"error",error:errMessage(json)}}));return;
   }
   setHistories(x=>({...x,[nct]:{status:"ok",data:json as HistoryIndex}}));
  }catch{
   setHistories(x=>({...x,[nct]:{status:"error",
     error:"UNABLE_TO_CHECK_OFFICIAL_HISTORY_NOT_PROOF_OF_ABSENCE"}}));
  }
 }
 async function loadVersion(nct:string,index:number){
  const key=nct+":"+index;
  setVersions(x=>({...x,[key]:{status:"loading"}}));
  try{
   const resp=await fetch("/predictions/source-recovery/history?nct="+nct+
    "&version="+index,{cache:"no-store",headers:{"Accept":"application/json"}});
   const json:unknown=await resp.json();
   if(!resp.ok||!json||typeof json!=="object"||!("nct" in json)||
     json.nct!==nct||!("apiIndex" in json)||json.apiIndex!==index){
    setVersions(x=>({...x,[key]:{status:"error",error:errMessage(json)}}));return;
   }
   setVersions(x=>({...x,[key]:{status:"ok",data:json as HistoricalVersion}}));
  }catch{
   setVersions(x=>({...x,[key]:{status:"error",
     error:"OFFICIAL_ORIGINAL_VERSION_NOT_AVAILABLE_NO_SOURCE_CLAIM"}}));
  }
 }
 return <div className={styles.coverageGrid}>
 {rows.map(row=>{
   const history=histories[row.nct],indexed=row.originalIndexedPivotalPublication;
   const versionList=history?.data?.versions??[];
   return <article key={row.nct} className={styles.coverageGroup}>
     <strong>{row.ticker} · {row.nct}</strong>
     {row.researchPilot&&<div><b>Original-source priority:</b> {
       row.researchPilot==="ACACIA_HCM"?"ACACIA-HCM":"Launch-HTN"}</div>}
     <p><b>Research lane:</b> {indexed?
       "Published pivotal journal lead; original signed protocol/SAP still missing":
       "Search historical registry and original sponsor/publisher/regulator sources"}</p>
     <div><b>Reported trial phase:</b> {row.reportedPhase}</div>
     <div><b>Application grouping:</b> {row.cycleIds.join(", ")}</div>
     {indexed&&<p>
      <a href={indexed.articleUrl} target="_blank" rel="noopener noreferrer">
       Existing pivotal article lead · PMID {indexed.pmid}
      </a>
      {" · "}
      <a href={indexed.journalUrl} target="_blank" rel="noopener noreferrer">
       Journal original
      </a>
      <small>Publication access: {indexed.sourceAccess}.
       Original signed SAP chronology and independent clinical assessment:
       NOT VERIFIED.</small>
     </p>}
     {row.nct===R89_ARCHIVED_ACACIA_SOURCE_HISTORY.nct&&
       <details className={styles.coverageDetails}>
        <summary>Four original ACACIA-HCM registry versions already preserved and checked in Revision 36</summary>
        <p><small>Recovered in {R89_ARCHIVED_ACACIA_SOURCE_HISTORY.recoveredInPriorRevision}
         and retained here; not newly retrieved by this source check.
         The change in listed primary endpoints from one to two is original
         registry text history, not a verdict on plan prespecification.</small></p>
        <ul>{R89_ARCHIVED_ACACIA_SOURCE_HISTORY.previousVersionFiles.map(v=><li key={v.uiVersion}>
         Version {v.uiVersion}: submitted {v.submittedDate},
         first posted {v.publiclyPostedDate}; {v.primaryEndpointsListed} listed
         primary endpoint{v.primaryEndpointsListed===1?"":"s"}.
         {" "}<a target="_blank" rel="noopener noreferrer"
          href={"https://github.com/pdufa/pdufa-command-center/blob/feature/main-r83-evidence-gap-export-20261109/"+v.originalRepoPath}>
          View archived exact original JSON source
         </a>
         <div>Source byte SHA-256: <code>{v.sourceSha256}</code></div>
        </li>)}</ul>
        <p><small>Original prospective SAP signatures, source custodian approvals,
         database lock, blind break and independent scientific signoff:
         NOT VERIFIED. FDA forecast: ABSTAIN.</small></p>
       </details>}
     <p><button type="button" onClick={()=>{void loadHistory(row.nct);}}
        disabled={history?.status==="loading"} style={{cursor:"pointer",
          padding:"9px 12px",background:"#fff",color:"#155c47",
          border:"1px solid #75a592",borderRadius:7,fontWeight:700}}>
        {history?.status==="loading"?
         "Checking official historical records…":
         "Check original registry version index"}
       </button>
       {" · "}
       <a href={"https://clinicaltrials.gov/study/"+row.nct+"?tab=history"}
        target="_blank" rel="noopener noreferrer">
        Open official public study record history
       </a>
       {" · "}
       <a href={row.exactStudyUrl} target="_blank" rel="noopener noreferrer">
        Current registry study
       </a>
     </p>
     {history?.status==="error"&&<p role="alert">
       Original history check unavailable: {history.error}.
       This is an access or source-validation blocker, not proof documents do not exist.
     </p>}
     {history?.status==="ok"&&<details className={styles.coverageDetails} open>
       <summary>{history.data?.historyVersionCount} official submitted-date version records.
        Inspect exact historical version</summary>
       <p><small>Submission dates do not establish public posting dates or SAP
        approvals. Recovered original versions must be inspected separately.</small></p>
       <div style={{maxHeight:280,overflowY:"auto"}}>
        <ul>{versionList.map(v=>{
          const key=row.nct+":"+v.apiIndex;
          const check=versions[key];
          return <li key={key}>
            <button type="button" onClick={()=>{void loadVersion(row.nct,v.apiIndex);}}
             disabled={check?.status==="loading"} style={{cursor:"pointer",
              background:"#fff",border:"1px solid #accdbc",borderRadius:6,
              color:"#174c3c",padding:"5px 9px"}}>
              Version {v.uiVersion} · submitted {v.submittedDate}
            </button>
            {check?.status==="error"&&<div role="alert">
              Exact version unavailable: {check.error}</div>}
            {check?.data&&<div>
               Primary outcome entries: {check.data.originalPrimaryOutcomeCount??"unavailable"};
               protocol/SAP public file listings: {check.data.listedProtocolOrSapDocuments.length}.
               Original signoff: NOT VERIFIED.
               {check.data.listedProtocolOrSapDocuments.map(d=><div key={d.filename}>
                {d.filename} · {d.typeAbbrev??"unknown type"} · document date
                {" "}{d.documentDate??"not reported"} · registry upload
                {" "}{d.registryUploadDate??"not reported"}.
                Historical listing is not signed-source custody.
               </div>)}
             </div>}
          </li>;
        })}</ul>
       </div>
     </details>}
     <details className={styles.coverageDetails}>
       <summary>Independent original source-recovery requirements</summary>
       <ul>{row.nextDocumentTasks.map(s=><li key={s}>{s}</li>)}</ul>
     </details>
     <p><small>Signed original pre-unblinding SAPs: 0.
      Independent clinical reviews: 0.
      Validated FDA forecasts: ABSTAIN. No model training writes.</small></p>
   </article>;
 })}
 </div>;
}
