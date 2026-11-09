import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import history from "../../../data/acacia-original-history-revision36.json";
import {buildAcaciaMethodReadiness} from "../../../lib/acacia-method-evidence-readiness";

const panel={border:"1px solid #aac9c4",background:"#f0f9f8",borderRadius:11,padding:13,margin:"10px 0"} as const;
export default function PilotMethodEvidenceReadiness(){
  const ready=buildAcaciaMethodReadiness(pilot,history);
  return <section aria-label="Revision 37 evidence-to-reviewer handoff for all 800 pilot methods" style={panel}>
    <h4 style={{margin:"2px 0 8px",fontSize:17}}>Revision 37 · Evidence-to-reviewer gates · 800 methods</h4>
    {!ready?<p role="alert"><strong>Source identity or original-history packet changed — method readiness withheld.</strong></p>:<>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(125px,1fr))",gap:9}}>
        {[
          [ready.counts.originalRegistryDocumentaryReferences,"Original registry references"],
          [ready.counts.mappedLeadsWithoutNewOriginalRegistryPacket,"Other mapped leads"],
          [ready.counts.unmapped,"Not source mapped"],
          [ready.counts.clinicallyGraded,"Authorized grades"],
          [ready.counts.verifiedHistoricalFdaCohortCases,"Verified FDA cohort cases"]
        ].map(([value,label])=><div key={label} style={{border:"1px solid #b9d7cd",borderRadius:8,padding:9,background:"#fff"}}>
          <div style={{fontSize:23,fontWeight:850}}>{value}</div>
          <div style={{fontSize:11}}>{label}</div>
        </div>)}
      </div>
      <p style={{fontSize:12,lineHeight:1.6}}>
        The three verified original registry references are linked to <strong>existing research positions</strong>, not three completed clinical tests. All 800 clinical method grades remain <strong>UNASSIGNED</strong>. Original SAP, safety/CONSORT reconciliation, independent phase signoff and authorized medical review are still required.
      </p>
      <details style={{background:"#fff",border:"1px solid #bfd4cd",borderRadius:9,padding:11}}>
        <summary style={{cursor:"pointer",fontWeight:800}}>Inspect all 18 prioritized method handoffs and original documents</summary>
        <p style={{fontSize:12}}>The other 782 phase/method positions have no source handoff, not a zero score. Source versions are dated by their public posting date for temporal research.</p>
        <div style={{display:"grid",gap:8}}>
          {ready.prioritizedResearchHandoffs.map(item=><article key={item.id}
            style={{border:"1px solid #d3e1dd",padding:10,borderRadius:8,minWidth:0}}>
            <strong>{item.id}</strong> — {item.sourceState.replaceAll("_"," ")}
            <div style={{fontSize:12}}>Research category: {item.researchEvidenceStatus}</div>
            <p style={{fontSize:12,margin:"5px 0"}}><strong>Original evidence still needed:</strong> {item.missingOriginalEvidence}</p>
            {item.originalDocumentLinks.length?<details style={{fontSize:12}}>
              <summary style={{cursor:"pointer"}}>Four preserved ClinicalTrials.gov original versions</summary>
              <ul style={{paddingLeft:18}}>{item.originalDocumentLinks.map((url,i)=><li key={url}>
                <a href={url} target="_blank" rel="noopener noreferrer">v{[26,27,29,30][i]} preserved original record</a>
              </li>)}</ul>
            </details>:null}
            <p style={{fontSize:12,margin:"5px 0 0"}}><strong>Reviewer gate:</strong> independent phase + method review pending · clinical grade unassigned</p>
          </article>)}
        </div>
      </details>
      <p style={{fontSize:11,marginBottom:0}}>Research-only snapshot. FDA approval/CRL/delay ABSTAIN · accuracy NOT CALIBRATED. No grade writes, learned probabilities or production changes.</p>
    </>}
  </section>;
}
