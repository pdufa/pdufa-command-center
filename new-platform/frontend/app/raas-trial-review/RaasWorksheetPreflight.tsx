"use client";
import {useState,type ChangeEvent} from "react";
import type {TrialMetricReviewDossier}
 from "../../lib/raas-trial-metric-review-dossier";
import {auditReviewerWorksheetCsv,type WorksheetPreflight}
 from "../../lib/raas-review-worksheet-preflight";
import css from "./ReviewDossierClient.module.css";

/** Local-only file inspection: NEVER sends, stores or signs reviewer evidence. */
export default function RaasWorksheetPreflight({
 dossier
}:{dossier:TrialMetricReviewDossier}){
 const [result,setResult]=useState<WorksheetPreflight|null>(null);
 const [failure,setFailure]=useState("");
 const [fileName,setFileName]=useState("");
 const [running,setRunning]=useState(false);
 const onFile=async(e:ChangeEvent<HTMLInputElement>)=>{
  const file=e.target.files?.[0];
  setResult(null);setFailure("");setFileName("");
  if(!file)return;
  setRunning(true);
  try{
   if(file.size>2_000_000||file.size===0)throw Error(
    "Worksheet must be a nonempty CSV smaller than 2 MB.");
   const contents=await file.text();
   const audit=auditReviewerWorksheetCsv(contents,dossier);
   setResult(audit);setFileName(file.name);
  }catch(error){
   setFailure(error instanceof Error?error.message:"Worksheet could not be inspected.");
  }finally{
   setRunning(false);
   e.target.value="";
  }
 };
 const downloadReport=()=>{
  if(!result)return;
  const safeReport={
   ...result,checkedAgainst:"REPOSITORY_SAVED_EXACT_TRIAL_DOSSIER",
   note:"Local structural preflight only. Not a source-quality validation, signed review, approved RAAS grade or FDA forecast.",
   noWorkbookOrReviewerTextStored:true
  };
  const blob=new Blob([JSON.stringify(safeReport,null,2)],{
   type:"application/json"});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement("a");
  anchor.href=url;
  anchor.download="raas-unsigned-preflight-"+dossier.trial.nctId+".json";
  anchor.click();
  URL.revokeObjectURL(url);
 };
 return <section data-raas-local-review-worksheet-preflight="browser-only-no-upload"
  className={css.info} style={{display:"grid",gap:12}}>
  <strong style={{fontSize:15}}>Check a completed 60-metric worksheet</strong>
  <p style={{margin:0,fontSize:12,lineHeight:1.65}}>
   Select the CSV downloaded for <strong>{dossier.trial.ticker} · {dossier.trial.nctId}</strong>.
   The checker reads it <strong>only in this browser</strong>: there is no
   server upload, database write, reviewer certification or change to the RAAS
   scoring ledger. It checks all 60 exact metric IDs, source checksum,
   catalog identity, readout-stage lead, proposed research bands, primary and
   benchmark URLs, observed result, uncertainty, critical risks, and methods.
  </p>
  <label className={css.control} style={{maxWidth:360}}>
   Select completed CSV worksheet
   <input type="file" accept=".csv,text/csv"
    data-raas-local-review-file="true"
    onChange={onFile}
    aria-label="Inspect completed RAAS 60-metric reviewer CSV locally"
    style={{padding:9,border:"1px solid #afcebb",
     borderRadius:7,background:"white",maxWidth:"100%"}}/>
  </label>
  {running&&<p role="status">Checking local worksheet structure…</p>}
  {failure&&<p role="alert" className={css.warn}>
   <strong>Worksheet rejected:</strong> {failure}
   {" "}No data was submitted. Download the current worksheet if its
   columns or trial source snapshot have changed.</p>}
  {result&&<div data-raas-preflight-result={result.schemaValid?"schema-valid":"blocked"}
   style={{display:"grid",gap:9}}>
   <p style={{fontSize:12,margin:0}}><strong>Checked:</strong> {fileName}.
    {" "}Exact source ID {result.registrySourceHash.slice(0,16)}…</p>
   <div className={css.stats}>
    {[
     [result.receivedMetricRows+"/60","Metric rows received"],
     [result.completedEvidenceFields,"Rows with all evidence fields filled"],
     [result.readyForExternalReview,"Structurally ready for external review"],
     [result.blockedRows,"Rows with blocking issues"],
     [result.independentlyAuthenticatedMetrics,"Authenticated independent reviews"],
     [result.approvedRaasScores,"Approved RAAS scores"]
    ].map(([n,label])=><div className={css.stat} key={label}>
     <strong>{n}</strong><span>{label}</span>
    </div>)}
   </div>
   <p role="status" className={result.issues.length?css.warn:css.info}
    style={{margin:0,fontSize:12}}>
    <strong>{result.schemaValid?"Exact 60-metric source identity matches.":
     "Source schema or immutable trial identity needs correction."}</strong>
    {" "}{result.issues.length} validation finding(s).
    {" "}A structurally ready row still requires independent verification of
    source truth, program/indication, reviewer identity, conflicts, competence
    and signature. Even 60 complete rows do not authorize an approved rating.
   </p>
   {result.issues.length>0&&<details>
    <summary style={{fontWeight:750,cursor:"pointer",fontSize:12}}>
     See validation findings ({result.issues.length})
    </summary>
    <div style={{display:"grid",gap:5,maxHeight:320,overflow:"auto",paddingTop:8}}>
     {result.issues.slice(0,100).map((issue,i)=>
      <p key={i} style={{fontSize:11,margin:0,
       padding:7,borderBottom:"1px solid #e5eee7"}}>
       <strong>{issue.metricId} · {issue.code}</strong>
       {" "}{issue.description}</p>)}
     {result.issues.length>100&&<p>
      Showing first 100 of {result.issues.length} findings.
      Download the complete local structural report.</p>}
    </div>
   </details>}
   <button type="button" onClick={downloadReport}
    data-raas-download-local-preflight-report="true"
    style={{justifySelf:"start",padding:"9px 12px",background:"white",
     border:"1px solid #b1cbb9",color:"#225739",borderRadius:7,
     cursor:"pointer",fontWeight:750}}>
    Download local preflight report (JSON)
   </button>
  </div>}
  <p className={css.warn} style={{fontSize:11,margin:0}}>
   <strong>Restricted review boundary:</strong> Do not upload private reviewer
   identities, signed documents or confidential assessments to this public
   website. The checker does not receive, authenticate or archive them.
   All trial and reviewer decisions remain unapproved until a separately
   controlled review and evidence-adjudication process exists.
  </p>
 </section>;
}
