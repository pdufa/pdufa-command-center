"use client";
import {useMemo} from "react";
import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import {buildPhase3ReviewQueue} from "../../../lib/acacia-phase3-review-queue";
import {buildAcaciaAcquisitionHandoff} from "../../../lib/acacia-evidence-acquisition-handoff";

const base={border:"1px solid #b3c9c2",background:"#f6faf8",borderRadius:12,padding:14,margin:"12px 0"} as const;
export default function PilotEvidenceAcquisitionPacket({nct}:{nct:string}){
  const handoff=useMemo(()=>buildAcaciaAcquisitionHandoff(buildPhase3ReviewQueue(pilot)),[]);
  if(nct!=="NCT06081894"||pilot.nct!==nct)return null;
  return <section style={base} aria-label="Original source acquisition and independent review requirements">
    <h3 style={{margin:"0 0 8px"}}>Original evidence acquisition · six review requirements</h3>
    {!handoff?<p role="alert">Original evidence packet withheld because trial, clinical-grade or source provenance validation failed.</p>:<>
      <p style={{fontSize:13,margin:"5px 0 10px"}}>
        Six precise original-document requests now cover all <strong>18 source-mapped scientific method positions</strong>.
        They identify what must be acquired, why it matters, and how an independent reviewer must verify it.
        <strong> This is a draft research worklist. No request has been sent, no new source has been authenticated,
        and no official clinical grade has been created.</strong>
      </p>
      <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
        <a href="/api/predictions/medical-evidence-acquisition?nct=NCT06081894&format=txt"
          target="_blank" rel="noopener noreferrer"
          style={{border:"1px solid #82a899",borderRadius:8,padding:"8px 10px",fontSize:12,fontWeight:750,background:"#fff"}}>
          Download unsent inquiry draft (TXT)
        </a>
        <a href="/api/predictions/medical-evidence-acquisition?nct=NCT06081894"
          target="_blank" rel="noopener noreferrer"
          style={{border:"1px solid #82a899",borderRadius:8,padding:"8px 10px",fontSize:12,fontWeight:750,background:"#fff"}}>
          Open versioned acquisition packet (JSON)
        </a>
      </div>
      <details style={{border:"1px solid #c5d9ce",background:"#fff",borderRadius:9,padding:11}}>
        <summary style={{fontSize:13,cursor:"pointer",fontWeight:800}}>Expand six original evidence requests and affected methods</summary>
        <div style={{display:"grid",gap:9,marginTop:12}}>
          {handoff.requests.map(item=><article key={item.requestId}
            style={{border:"1px solid #d5e0db",borderRadius:8,padding:11}}>
            <div style={{display:"flex",gap:8,justifyContent:"space-between",alignItems:"baseline",flexWrap:"wrap"}}>
              <strong style={{fontSize:13}}>{item.title}</strong>
              <span style={{fontWeight:750,fontSize:11}}>Priority {item.priority} · {item.category}</span>
            </div>
            <p style={{fontSize:12,margin:"7px 0"}}><strong>Original evidence required:</strong> {item.preciseOriginalEvidenceNeeded}</p>
            <p style={{fontSize:12,margin:"7px 0"}}><strong>Independent verification:</strong> {item.howToIndependentlyVerify}</p>
            <p style={{fontSize:12,margin:"7px 0"}}>
              <strong>Linked scientific methods:</strong> {item.mappedMethodPositions.join(", ")}
            </p>
            <p style={{fontSize:12,margin:"7px 0"}}>
              <strong>Evidence:</strong> Not authenticated for current review.
              {" "}<strong>Acquisition:</strong> Draft, not sent.
              {" "}<strong>Clinical grade:</strong> Unscored.
            </p>
          </article>)}
        </div>
      </details>
      <details style={{marginTop:10,padding:10,borderRadius:9,border:"1px solid #c5d9ce",background:"#fff"}}>
        <summary style={{cursor:"pointer",fontSize:12,fontWeight:800}}>Original research-source access and approval boundary</summary>
        <p style={{fontSize:12,margin:"8px 0"}}>
          Published research-data requests are subject to sponsor eligibility, timing, review and a data-access agreement.
          The recipient for eligibility inquiries is <strong>{handoff.recipientForResearchEligibilityInquiry}</strong>.
          The TXT file is an editable <strong>unsent draft</strong>. Neither opening nor downloading the packet
          contacts the sponsor or discloses trial data.
        </p>
        <p style={{fontSize:12,margin:"8px 0"}}>
          Source research audits:{" "}
          <a target="_blank" rel="noopener noreferrer"
            href={"https://github.com/pdufa/pdufa-command-center/actions/runs/"+handoff.sourceAuditRuns.safetyAndSap}>SAP/safety source receipt</a>
          {" "}·{" "}
          <a target="_blank" rel="noopener noreferrer"
            href={"https://github.com/pdufa/pdufa-command-center/actions/runs/"+handoff.sourceAuditRuns.alternativePublisher}>Alternate publisher source receipt</a>.
          These are dated research observations, not signed primary evidence reviews.
        </p>
      </details>
      <p style={{fontSize:12,margin:"10px 0 0"}}>
        <strong>Current status:</strong> {handoff.requestDeliveryStatus.replaceAll("_"," ")} ·
        {" "}{handoff.approvedClinicalGrades}/800 authorized scientific method grades ·
        FDA prediction <strong>ABSTAIN</strong> · Accuracy <strong>NOT CALIBRATED</strong>.
      </p>
    </>}
  </section>;
}
