"use client";

import {useMemo,useState} from "react";
import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import {buildPhase3ReviewQueue,type QueueStatus} from "../../../lib/acacia-phase3-review-queue";
import PilotOriginalHistoryEvidence from "./PilotOriginalHistoryEvidence";

const card={border:"1px solid #a6c8bd",borderRadius:12,padding:13,background:"#fff",margin:"12px 0"} as const;
type Filter="ALL"|QueueStatus;
const filters:Record<Filter,string>={
  ALL:"All 18 mapped leads",
  DOCUMENT_CHECKLIST:"3 source checklists",
  PUBLISHED_NUMERIC_RECALCULATION:"2 numerical research calculations",
  SOURCE_LEAD_ONLY:"13 research leads only"
};
function name(status:QueueStatus){
  if(status==="DOCUMENT_CHECKLIST")return "Document checklist";
  if(status==="PUBLISHED_NUMERIC_RECALCULATION")return "Numerical research";
  return "Research lead only";
}
export default function PilotResearchReviewQueue({nct}:{nct:string}){
  const [status,setStatus]=useState<Filter>("ALL");
  const [search,setSearch]=useState("");
  const queue=useMemo(()=>buildPhase3ReviewQueue(pilot),[]);
  const matches=useMemo(()=>{
    if(!queue)return [];
    const q=search.trim().toLowerCase();
    return queue.positions.filter(p=>(status==="ALL"||p.evidenceStatus===status)&&
      (!q||[p.id,p.assessmentLabel,p.missingOriginalEvidence,...p.sourceIds].join(" ").toLowerCase().includes(q)));
  },[queue,search,status]);
  if(nct!=="NCT06081894"||pilot.nct!==nct)return null;
  return <section style={{...card,background:"#f3f9f6"}} aria-label="Prioritized Phase III scientific research review queue">
    <h3 style={{margin:"0 0 8px"}}>Phase III scientific review queue · 18 research method leads</h3>
    {!queue?<p role="alert" style={{fontWeight:800}}>Research source queue withheld: evidence identity, original source or clinical review status changed.</p>:<>
      <PilotOriginalHistoryEvidence/>
      <details style={{border:"1px solid #c9b98b",borderRadius:9,padding:11,background:"#fffaf0",marginBottom:12}}
        aria-label="Original source gap audit and scientific safety reconciliation">
        <summary style={{cursor:"pointer",fontWeight:800}}>
          Original-source gap audit · final SAP and heart-failure safety
        </summary>
        <p style={{fontSize:12,margin:"9px 0"}}>
          <strong>Archived November 9 UTC research check:</strong> the official registry and sponsor safety
          disclosure were retrieved. The registry response did not list a statistical analysis plan.
          The automated fetch of both NEJM supplements was unavailable. Neither observation establishes
          that an original final locked SAP or supplement does not exist elsewhere.
        </p>
        <p style={{fontSize:12,margin:"9px 0"}}>
          <strong>Safety source detail:</strong> the sponsor describes two treated serious heart-failure
          cases associated with reduced LVEF and ten additional treated cases, totaling
          <strong> 12 versus 3 on placebo</strong>. The secondary report's <strong>11 versus 1</strong>
          comparison is <strong>NOT RECONCILED</strong> by this breakdown. Original event definitions,
          observation windows and treatment populations remain required.
        </p>
        <p style={{fontSize:12,margin:"9px 0"}}>
          <a href="https://github.com/pdufa/pdufa-command-center/actions/runs/42555289486"
            target="_blank" rel="noopener noreferrer" style={{fontWeight:750}}>
            View audited source receipts and statuses
          </a>{" "}·{" "}
          <a href="https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx"
            target="_blank" rel="noopener noreferrer">October 12 sponsor statement</a>
          {" "}·{" "}
          <a href="https://clinicaltrials.gov/study/NCT06081894"
            target="_blank" rel="noopener noreferrer">Original registry</a>
        </p>
        <p style={{fontSize:11,margin:"9px 0 0"}}>
          This is a dated source-discovery receipt, not a live independent SAP or safety adjudication.
          No clinical grades, FDA outcome probabilities, or accuracy values were created.
        </p>
      </details>
      <details style={{border:"1px solid #b7cad6",borderRadius:9,padding:11,background:"#f3f8fb",marginBottom:12}}
        aria-label="Alternate public sources and formal study data request route">
        <summary style={{cursor:"pointer",fontWeight:800}}>
          Alternative source recovery · original SAP, secondary analyses and data access
        </summary>
        <p style={{fontSize:12,margin:"9px 0"}}>
          <strong>Archived November 9 alternative retrieval:</strong> the NEJM publisher article endpoint
          and two Europe PMC full-text API endpoints were unavailable to the isolated automated checker.
          These are <strong>access failures, not evidence that the source articles or supplements do not exist</strong>.
          The publisher publicly lists a protocol supplement, appendix, and data-sharing statement,
          but an exact final locked primary SAP has <strong>not been authenticated</strong>.
        </p>
        <p style={{fontSize:12,margin:"9px 0"}}>
          The secondary responder analysis describes prespecified statistical methods and missing-data
          handling, but these are <strong>secondary research methods</strong>, not full original co-primary
          missingness/sensitivity results. Serious-heart-failure comparisons across the sponsor and
          secondary study are <strong>still unreconciled</strong>.
        </p>
        <ul style={{fontSize:12,paddingLeft:20,margin:"10px 0"}}>
          <li><a href={queue.alternativeSourceRecovery.originalArticleUrl} target="_blank" rel="noopener noreferrer">
            Original NEJM article and listed supplements
          </a></li>
          <li><a href={queue.alternativeSourceRecovery.officialDataSharingUrl} target="_blank" rel="noopener noreferrer">
            Published study data-sharing statement
          </a></li>
          <li><a href={queue.alternativeSourceRecovery.secondaryResponderUrl} target="_blank" rel="noopener noreferrer">
            Public responder-analysis article
          </a></li>
          <li><a href={queue.alternativeSourceRecovery.secondaryEchoUrl} target="_blank" rel="noopener noreferrer">
            Public echocardiography-analysis article
          </a></li>
          <li><a href={"https://github.com/pdufa/pdufa-command-center/actions/runs/"+queue.alternativeSourceRecovery.archivedAuditRun}
            target="_blank" rel="noopener noreferrer">Audited automated retrieval receipt and source statuses</a></li>
        </ul>
        <p style={{fontSize:12,margin:"9px 0"}}>
          <strong>Original data-access route:</strong> the study's published statement describes a
          qualified-researcher application reviewed by sponsor advisers, subject to access timing and
          marketing-authorization conditions. Contact{" "}
          <a href={"mailto:"+queue.alternativeSourceRecovery.sponsorResearchContact}>
            {queue.alternativeSourceRecovery.sponsorResearchContact}
          </a>{" "}to inquire about eligibility and the final SAP. This link opens an email composer;
          <strong> no request has been sent</strong> by MAIN.
        </p>
        <p style={{fontSize:11,margin:"8px 0 0"}}>
          Research access status dated {queue.alternativeSourceRecovery.sourceCheckDate}.
          Official clinical grades: 0/800. Final FDA prediction: ABSTAIN. A retrieved protocol, paper,
          supplementary title, or email response must still be verified against the correct trial and version.
        </p>
      </details>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(115px,1fr))",gap:8}}>
        {[
          ["18","Mapped source leads"],
          ["5","Research calculations or checklists"],
          ["13","Source leads pending"],
          ["782","Not source mapped"],
          ["0","Authorized clinical grades"]
        ].map(([v,label])=><div key={label} style={{border:"1px solid #c6ddd4",borderRadius:8,padding:9,background:"#fff"}}>
          <div style={{fontSize:23,fontWeight:900}}>{v}</div>
          <div style={{fontSize:11}}>{label}</div>
        </div>)}
      </div>
      <p style={{fontSize:12,margin:"10px 0"}}>
        This is an <strong>investigation order within 11 critical Phase III assessment headings</strong>,
        not a scientific outcome ranking or a prediction of FDA risk. Original sources must be
        checked independently before an evidence lead becomes a scored clinical method.
      </p>
      <details style={{border:"1px solid #b6d3ca",borderRadius:9,padding:11,background:"#fff"}}>
        <summary style={{cursor:"pointer",fontWeight:800}}>Open all 18 research method leads, missing documents and source links</summary>
        <div style={{display:"flex",gap:8,flexWrap:"wrap",margin:"11px 0"}}>
          <label style={{display:"grid",gap:5,flex:"1 1 180px",fontSize:12,fontWeight:750}}>
            Find method or missing evidence
            <input aria-label="Search scientific research queue" value={search}
              onChange={e=>setSearch(e.target.value)} placeholder="SAP, safety, 5.3:L19…"
              style={{padding:"8px 10px",borderRadius:7,border:"1px solid #8eb4a8"}}/>
          </label>
          <label style={{display:"grid",gap:5,flex:"1 1 195px",fontSize:12,fontWeight:750}}>
            Research status
            <select aria-label="Filter research queue status" value={status}
              onChange={e=>setStatus(e.target.value as Filter)}
              style={{padding:"8px 10px",borderRadius:7,border:"1px solid #8eb4a8",background:"#fff"}}>
              {(Object.keys(filters) as Filter[]).map(k=><option key={k} value={k}>{filters[k]}</option>)}
            </select>
          </label>
          <button type="button" onClick={()=>{setSearch("");setStatus("ALL");}}
            style={{alignSelf:"end",borderRadius:7,border:"1px solid #7caa9b",padding:"8px 11px",background:"#fff",fontWeight:700}}>Clear filters</button>
        </div>
        <p role="status" style={{fontSize:12,margin:"8px 0"}}>Showing {matches.length} of {queue.summary.mappedSourceLeads} source-mapped scientific methods · research only</p>
        <div style={{maxHeight:520,overflowY:"auto",display:"grid",gap:9}}>
          {matches.map(p=><article key={p.id} style={{border:"1px solid #cddbd6",borderRadius:9,padding:11}}>
            <div style={{display:"flex",gap:8,justifyContent:"space-between",flexWrap:"wrap",alignItems:"baseline"}}>
              <strong>#{p.reviewOrder} · {p.id} — {p.assessmentLabel}</strong>
              <span style={{fontSize:11,fontWeight:800}}>{name(p.evidenceStatus)}</span>
            </div>
            <p style={{fontSize:12,margin:"6px 0"}}><strong>Required next:</strong> {p.missingOriginalEvidence}</p>
            {p.sourceGapAuditNote?<p style={{fontSize:12,margin:"6px 0",padding:7,
              border:"1px solid #d8c594",background:"#fffaf1",borderRadius:6}}>
              <strong>Source audit finding (dated):</strong> {p.sourceGapAuditNote}{" "}
              <a href={"https://github.com/pdufa/pdufa-command-center/actions/runs/"+p.sourceGapAuditRun}
                target="_blank" rel="noopener noreferrer">Original receipt</a>
            </p>:null}
            <div style={{fontSize:12,margin:"5px 0"}}>
              <strong>Official 0–5 grade:</strong> Unscored · <strong>Reviewer:</strong> Not signed
            </div>
            <details style={{fontSize:12,marginTop:6}}>
              <summary style={{cursor:"pointer",fontWeight:700}}>Original research sources · {p.sourceIds.length}</summary>
              <ul style={{paddingLeft:19}}>
                {p.sourceIds.map((id,i)=><li key={id}>
                  <a href={p.sourceUrls[i]} target="_blank" rel="noopener noreferrer">{id}</a>
                </li>)}
              </ul>
              <p>These are source leads, not inspected scientific findings or verified clinical outcomes.</p>
            </details>
          </article>)}
          {!matches.length?<p>No matches. Try clearing filters or searching a different assessment.</p>:null}
        </div>
        <p style={{fontSize:12,margin:"10px 0 4px"}}>
          <a href="/api/predictions/medical-phase3-review-queue?nct=NCT06081894&format=csv"
            target="_blank" rel="noopener noreferrer" style={{fontWeight:750}}>
            Export all 18 source leads as CSV
          </a>{" "}·{" "}
          <a href="/api/predictions/medical-phase3-review-queue?nct=NCT06081894"
            target="_blank" rel="noopener noreferrer" style={{fontWeight:750}}>
            Open versioned review queue JSON
          </a>
        </p>
      </details>
      <p style={{fontSize:12,margin:"10px 0 0"}}>Evidence snapshot {queue.sourceSnapshotAsOf}. The existing 800-position
        clinical ledger remains the only official record of reviewer-authorized grades.
        FDA prediction: <strong>ABSTAIN</strong>. Accuracy: <strong>NOT CALIBRATED</strong>.</p>
    </>}
  </section>;
}
