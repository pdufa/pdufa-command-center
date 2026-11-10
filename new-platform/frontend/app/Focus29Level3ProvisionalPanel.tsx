import manifest from "../data/focus29Level3ProvisionalResearch20261110.json";
import focusRoster from "../data/p3PostDataActive.json";

const keyLabels:Record<string,string>={
  APPROVAL_LEAN:"Approval lean",
  CRL_LEAN:"CRL lean",
  ABSTAIN:"Abstain — not yet assessable",
  ALREADY_APPROVED:"Already approved — excluded"
};
const pillColor:Record<string,{background:string;color:string;border:string}>={
  APPROVAL_LEAN:{background:"#e9f8f0",color:"#0c6a48",border:"1px solid #86c8a1"},
  CRL_LEAN:{background:"#fff0ee",color:"#a13d30",border:"1px solid #e4aca5"},
  ABSTAIN:{background:"#fff7e6",color:"#805916",border:"1px solid #d9bc75"},
  ALREADY_APPROVED:{background:"#f0f4f7",color:"#526477",border:"1px solid #bdcdd6"}
};
const cell={padding:"10px 9px",borderBottom:"1px solid #d8e5df",verticalAlign:"top"} as const;
const url=(nct:string)=>"/predictions/assessment?nct="+encodeURIComponent(nct);

export default function Focus29Level3ProvisionalPanel(){
  if(manifest.kind!=="FOCUS_29_LEVEL3_STYLE_PROVISIONAL_APPLICATION_RESEARCH_NOT_PRODUCTION_FORECAST"||
     manifest.policy.notActivePredictionEngine!==true||
     manifest.policy.notEligibleForLiveProspectiveAccuracy!==true||
     manifest.policy.approvedNumericProbabilities!==0||
     manifest.policy.independentLevel3ScientificReviewsComplete!==false||
     manifest.trials.length!==29||manifest.cycles.length!==23||
     focusRoster.records.length!==29||
     manifest.summary.linkedTrialApplicationPairs!==30||
     manifest.summary.approvalLeans!==12||
     manifest.summary.crlLeans!==5||
     manifest.summary.abstentions!==5||
     manifest.summary.alreadyApprovedApplications!==1||
     new Set(manifest.trials.map(t=>t.nct)).size!==29){
    throw new Error("FOCUS_29_PROVISIONAL_RESEARCH_SAFETY_GATE_FAILED");
  }
  const cycleIds=new Set(manifest.cycles.map(c=>c.cycleId));
  const byNct=new Map(focusRoster.records.map(t=>[t.nct,t]));
  if(cycleIds.size!==23||manifest.trials.some(t=>byNct.get(t.nct)?.ticker!==t.ticker||
    t.applicationCycleIds.some(id=>!cycleIds.has(id)))||
    manifest.cycles.some(c=>c.assessmentStyleLevel!==3||
      c.independentSignoff!==false||c.proposedForecastProbability!==null||
      c.validatedAsProspectivePrediction!==false)){
    throw new Error("FOCUS_29_APPLICATION_PROVENANCE_OR_STATUS_MISMATCH");
  }
  return <section id="focus-29-level3-research" data-testid="focus-29-level3-provisional-research"
    style={{border:"2px solid #d7bd7b",background:"#fffcf6",borderRadius:13,
      padding:"clamp(14px,2vw,22px)",margin:"0 0 23px"}}>
    <div style={{fontWeight:900,letterSpacing:".08em",color:"#825616",fontSize:11}}>
      CURRENT FOCUS · 29 EXACT TRIALS · LEVEL 3-STYLE RESEARCH PREVIEW
    </div>
    <h2 style={{fontSize:23,margin:"8px 0 7px",color:"#2e473e"}}>
      Preliminary FDA application forecasts · 10 November 2026
    </h2>
    <p style={{fontSize:13,lineHeight:1.65,color:"#5d604c",margin:"6px 0 14px"}}>
      <strong>These are directional research hypotheses, NOT completed independent Level 3
      scientific grades or calibrated FDA probabilities.</strong> Each forecast belongs to
      an exact FDA application cycle. Two or more trials may support one application, and
      one NCT may support multiple separate applications. The production prediction engine
      continues to show ABSTAIN where independent review is incomplete.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(128px,1fr))",gap:9,marginBottom:16}}>
      {[
        ["Exact trials",29],["FDA cycles",23],
        ["Approval leans",12],["CRL leans",5],["Abstentions",5],
        ["Already decided",1],["Validated forecasts",0]
      ].map(([label,value])=><div key={label}
        style={{border:"1px solid #e4dabc",background:"#fff",borderRadius:9,padding:"11px 9px"}}>
        <div style={{fontSize:11,color:"#6c7364"}}>{label}</div>
        <strong style={{fontSize:24,color:"#374a41"}}>{value}</strong>
      </div>)}
    </div>
    <div style={{overflowX:"auto",border:"1px solid #e1dccb",borderRadius:9,background:"#fff"}}>
      <table data-testid="focus29-level3-cycle-table" style={{width:"100%",minWidth:760,borderCollapse:"collapse",fontSize:12}}>
        <thead><tr style={{background:"#f0efe6",textAlign:"left"}}>
          {["Company","Drug / application","Associated trials","Reported FDA goal","Level 3-style research call","Scientific rationale"].map(h=>
            <th scope="col" key={h} style={{padding:"11px 9px",borderBottom:"2px solid #ccd4c7"}}>{h}</th>)}
        </tr></thead>
        <tbody>{manifest.cycles.map(c=><tr key={c.cycleId} data-cycle-id={c.cycleId}>
          <td style={{...cell,fontWeight:800}}>{c.ticker}</td>
          <td style={cell}>
            <strong>{c.drug}</strong>
            <div style={{color:"#64746e",marginTop:3}}>{c.indication}</div>
            <small style={{color:"#6b786f"}}>{c.applicationStatusAsRecorded.replaceAll("_"," ")}</small>
          </td>
          <td style={cell}>{c.associatedNcts.map(nct=><div key={nct}>
            <a href={url(nct)} style={{color:"#006f5e",fontWeight:700}}>{nct}</a>
          </div>)}</td>
          <td style={cell}>{c.reportedPdufaGoal??"Not assigned"}</td>
          <td style={cell}><span data-testid={"research-call-"+c.cycleId}
            style={{...pillColor[c.call],display:"inline-block",borderRadius:8,padding:"5px 7px",
              whiteSpace:"nowrap",fontWeight:800,fontSize:11}}>
            {keyLabels[c.call]}
          </span>
            <div style={{fontSize:11,marginTop:5,color:"#677366"}}>
              Confidence: {c.confidenceDescription==="NOT_RATED"?"Unrated":c.confidenceDescription.toLowerCase()}
            </div>
          </td>
          <td style={cell}>
            <details>
              <summary style={{cursor:"pointer",fontWeight:750,color:"#166658"}}>
                Evidence, risks and sources
              </summary>
              <div style={{minWidth:240,lineHeight:1.55,paddingTop:8}}>
                <p><strong>1. Clinical:</strong> {c.level1ClinicalEvidence}</p>
                <p><strong>2. Benefit/safety:</strong> {c.level2BenefitRisk}</p>
                <p><strong>3. FDA/CMC:</strong> {c.level3RegulatoryManufacturing}</p>
                <p><strong>Missing:</strong> {c.additionalEvidenceNeeded}</p>
                <p>
                  <a href={c.clinicalEvidenceReferenceUrl} target="_blank"
                    rel="noopener noreferrer">Research evidence</a>
                  {" · "}
                  <a href={c.applicationReferenceUrl} target="_blank"
                    rel="noopener noreferrer">Application status</a>
                </p>
              </div>
            </details>
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <details style={{marginTop:13,fontSize:12,color:"#496258"}}>
      <summary style={{cursor:"pointer",fontWeight:850}}>
        Show all 29 NCT-to-application research mappings
      </summary>
      <div style={{overflowX:"auto",marginTop:8}}>
        <table data-testid="focus29-level3-exact-nct-table"
          style={{width:"100%",borderCollapse:"collapse",minWidth:560,fontSize:12}}>
          <thead><tr style={{textAlign:"left",background:"#f0f7f1"}}>
            {["Ticker","NCT","Registry phase","Application(s) and corresponding research call"].map(x=>
              <th scope="col" key={x} style={cell}>{x}</th>)}
          </tr></thead>
          <tbody>{manifest.trials.map(t=><tr key={t.nct}>
            <td style={cell}><strong>{t.ticker}</strong></td>
            <td style={cell}><a href={t.sourceRegistryUrl} target="_blank" rel="noopener noreferrer">{t.nct}</a></td>
            <td style={cell}>{t.reportedPhaseAtScan}</td>
            <td style={cell}>{t.calls.map(x=><div key={x.cycleId}>
              <strong>{x.cycleId}</strong>: {keyLabels[x.call]}
            </div>)}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </details>
    <p style={{fontSize:12,lineHeight:1.6,color:"#8b5b23",margin:"13px 0 0",fontWeight:700}}>
      The 29-trial research file does not alter the live FDA prediction record, accuracy
      counter, Level 3–20 historical chart, or automated trading. It requires independent
      phase/protocol/SAP review, safety reconciliation, current CMC and regulatory verification,
      and outcome calibration before release as a completed Level 3 prediction.
    </p>
  </section>;
}
