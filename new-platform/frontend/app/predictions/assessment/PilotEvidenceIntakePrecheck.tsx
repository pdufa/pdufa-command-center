"use client";
import {useMemo,useState} from "react";
import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import {buildPhase3ReviewQueue} from "../../../lib/acacia-phase3-review-queue";
import {buildAcaciaAcquisitionHandoff} from "../../../lib/acacia-evidence-acquisition-handoff";
import {intakeDocumentTypes,type IntakeDraft,type IntakePrecheck} from "../../../lib/acacia-evidence-intake-precheck";

const frame={border:"1px solid #a8c4cf",borderRadius:12,padding:14,margin:"12px 0",background:"#f5f9fc"} as const;
const field={padding:"9px 10px",border:"1px solid #8eaaba",borderRadius:8,
  width:"100%",boxSizing:"border-box" as const,background:"#fff",fontSize:14};
const initial:Omit<IntakeDraft,"nct">={
  requestId:"LOCKED_PRIMARY_SAP",documentType:"STATISTICAL_ANALYSIS_PLAN",
  documentTitle:"",documentVersion:"",documentDate:"",sourceUrl:"",claimedSha256:""
};
export default function PilotEvidenceIntakePrecheck({nct}:{nct:string}){
  const packet=useMemo(()=>buildAcaciaAcquisitionHandoff(buildPhase3ReviewQueue(pilot)),[]);
  const [draft,setDraft]=useState(initial);
  const [report,setReport]=useState<IntakePrecheck|null>(null);
  const [message,setMessage]=useState("");
  const [loading,setLoading]=useState(false);
  const [localHashState,setLocalHashState]=useState("");
  const types=useMemo(()=>intakeDocumentTypes(),[]);
  if(nct!=="NCT06081894"||pilot.nct!==nct)return null;
  const update=(key:keyof typeof draft,value:string)=>{
    setDraft(old=>({...old,[key]:value}));
    setReport(null);setMessage("");
  };
  const onFile=async(file:File|undefined)=>{
    setLocalHashState("");setReport(null);setMessage("");
    if(!file)return;
    if(file.size>25*1024*1024){
      setLocalHashState("File too large for browser-only hashing (limit 25 MB); no file uploaded.");
      return;
    }
    if(typeof crypto==="undefined"||!crypto.subtle){
      setLocalHashState("Browser hashing unavailable. Use independently calculated SHA-256 metadata.");
      return;
    }
    try{
      const bytes=await file.arrayBuffer();
      const hash=await crypto.subtle.digest("SHA-256",bytes);
      const hex=Array.from(new Uint8Array(hash)).map(b=>b.toString(16).padStart(2,"0")).join("");
      setDraft(old=>({...old,claimedSha256:hex}));
      setLocalHashState("SHA-256 calculated locally from selected file. File bytes and filename were NOT uploaded or stored. Source authenticity still requires independent review.");
    }catch{
      setLocalHashState("Unable to calculate local file hash. Nothing was uploaded.");
    }
  };
  const submit=async(event:React.FormEvent<HTMLFormElement>)=>{
    event.preventDefault();setLoading(true);setReport(null);setMessage("");
    try{
      const candidate:IntakeDraft={nct:"NCT06081894",...draft};
      const response=await fetch("/api/predictions/medical-evidence-intake-precheck?nct=NCT06081894",{
        method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json","Accept":"application/json"},
        body:JSON.stringify(candidate)
      });
      const body:unknown=await response.json();
      if(!body||typeof body!=="object"||
         !("schema" in body)||body.schema!=="MAIN_ACACIA_EVIDENCE_INTAKE_PRECHECK_V1"||
         !("issueCodes" in body)||!Array.isArray(body.issueCodes))
        throw Error("Precheck unavailable. No metadata was saved.");
      setReport(body as IntakePrecheck);
      if(response.status!==200&&response.status!==422)
        setMessage("Precheck could not be completed. No metadata was saved.");
    }catch{
      setMessage("Precheck unavailable. No source documents or metadata were saved.");
    }finally{setLoading(false);}
  };
  return <section style={frame} aria-label="Original document metadata intake precheck">
    <h3 style={{margin:"0 0 8px"}}>Original document intake · local SHA-256 + evidence precheck</h3>
    <p style={{fontSize:13,margin:"6px 0 10px"}}>
      Inspect whether an original-document <strong>metadata record</strong> is linked to one of the six
      outstanding research requirements. You can optionally select a public, authorized local document
      to compute its SHA-256 <strong>inside your browser only</strong>.
      <strong> No file upload, server-side source retrieval, saved intake, completed source verification,
      independent reviewer signature, or clinical scoring occurs here.</strong>
    </p>
    {!packet?<p role="alert">Intake precheck withheld: pilot source or clinical review state changed.</p>:
    <details style={{border:"1px solid #c9d9df",borderRadius:9,padding:11,background:"#fff"}}>
      <summary style={{cursor:"pointer",fontWeight:750}}>Open original-document metadata precheck (not a submission)</summary>
      <form onSubmit={submit} style={{marginTop:11}}>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",gap:11}}>
          <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
            Evidence requirement
            <select aria-label="Original evidence requirement" style={field} value={draft.requestId}
              onChange={e=>{
                const chosen=e.target.value;
                const expected=types.find(x=>x.requestId===chosen);
                setDraft(old=>({...old,requestId:chosen,documentType:expected?.documentType||""}));
                setReport(null);setMessage("");
              }}>
              {packet.requests.map(x=><option key={x.requestId} value={x.requestId}>{x.title}</option>)}
            </select>
          </label>
          <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
            Source document title (no patient identifiers)
            <input aria-label="Original source document title" style={field} value={draft.documentTitle}
              onChange={e=>update("documentTitle",e.target.value)} maxLength={160} placeholder="Original source title" />
          </label>
          <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
            Document version
            <input aria-label="Original source document version" style={field} value={draft.documentVersion}
              onChange={e=>update("documentVersion",e.target.value)} maxLength={48} placeholder="e.g. Final 1.0" />
          </label>
          <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
            Document date
            <input aria-label="Original source document date" type="date" style={field}
              value={draft.documentDate} onChange={e=>update("documentDate",e.target.value)} />
          </label>
          <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
            Public source URL (exact trusted host only; no tokens)
            <input aria-label="Exact public source URL" type="url" style={field} value={draft.sourceUrl}
              onChange={e=>update("sourceUrl",e.target.value)} maxLength={320}
              placeholder="https://clinicaltrials.gov/study/NCT06081894" />
          </label>
          <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
            Claimed SHA-256 of original document
            <input aria-label="Claimed document SHA256" style={field} value={draft.claimedSha256}
              onChange={e=>update("claimedSha256",e.target.value.trim().toLowerCase())}
              maxLength={64} placeholder="64 lowercase hex characters" spellCheck={false} />
          </label>
        </div>
        <label style={{display:"grid",gap:5,fontSize:12,fontWeight:750,marginTop:10}}>
          Optional: choose a public, authorized file to hash locally (up to 25 MB)
          <input aria-label="Hash local original document without upload" type="file"
            accept=".pdf,.txt,.csv,.docx"
            onChange={e=>{void onFile(e.target.files?.[0]);e.target.value="";}}
            style={{fontSize:12}}/>
        </label>
        <p style={{fontSize:12,margin:"7px 0"}}>
          Do not use patient-level records, private health information or confidential files in this trial
          precheck. The SHA-256 and document metadata—not file contents—are sent for a transient format check.
        </p>
        {localHashState?<p role="status" style={{fontSize:12}}>{localHashState}</p>:null}
        <button type="submit" disabled={loading}
          style={{border:"1px solid #426c63",background:"#19574a",color:"#fff",
            padding:"9px 13px",borderRadius:8,cursor:loading?"wait":"pointer",
            fontWeight:800,marginTop:6}}>
          {loading?"Checking metadata…":"Check metadata only — do not save"}
        </button>
      </form>
      {message?<p role="alert" style={{fontSize:12,fontWeight:700}}>{message}</p>:null}
      {report?<div role="status" style={{border:"1px solid #b5d2c4",borderRadius:9,
        padding:10,marginTop:11,background:"#f5fbf7",fontSize:13}}>
        <strong>Metadata precheck: {report.inputCheck.replaceAll("_"," ")}</strong>
        {report.issueCodes.length?<p>Still needed: {report.issueCodes.join(", ").replaceAll("_"," ")}</p>:
          <p>Required metadata format checks passed. <strong>The original source was NOT retrieved, independently verified, saved or assigned a grade.</strong></p>}
        <p><strong>Linked methods:</strong> {report.linkedMethodPositions.join(", ")||"Not mapped"}</p>
        <p><strong>Independent verification still required:</strong></p>
        <ol style={{paddingLeft:20}}>{report.reviewerActionRequired.map((x,i)=><li key={i}>{x}</li>)}</ol>
        <p style={{fontWeight:750,marginBottom:0}}>
          Grade: UNSCORED · Documents stored: 0 · Source identity unverified · FDA: ABSTAIN
        </p>
      </div>:null}
    </details>}
  </section>;
}
