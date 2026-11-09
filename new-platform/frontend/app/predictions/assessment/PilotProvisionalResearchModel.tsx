"use client";
import {useState} from "react";
import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";
import {evaluateProvisionalEvidence,simulateHypotheticalPath,type ScenarioInputs} from "../../../lib/acacia-provisional-decision";

const defaults:ScenarioInputs={filing:"PLANNED",sap:"UNVERIFIED",safety:"UNRESOLVED",review:"PENDING"};
const base={background:"#092d39",color:"#e6f8f2",border:"1px solid #357e76",borderRadius:12,padding:16,margin:"12px 0"} as const;
const mini={fontSize:13,color:"#cbdfdb",lineHeight:1.55} as const;
const input={color:"#143b42",background:"#ffffff",width:"100%",padding:9,borderRadius:7} as const;
export default function PilotProvisionalResearchModel({nct}:{nct:string}){
  const [scenarioInputs,setScenarioInputs]=useState<ScenarioInputs>(defaults);
  if(nct!=="NCT06081894"||pilot.nct!==nct)return null;
  const report=evaluateProvisionalEvidence(pilot);
  const simulation=simulateHypotheticalPath(scenarioInputs);
  const set=<K extends keyof ScenarioInputs>(key:K,value:ScenarioInputs[K])=>
    setScenarioInputs(last=>({...last,[key]:value}));
  return <section aria-label="Provisional evidence and hypothetical FDA pathway" style={base}>
    <div style={{color:"#89dfca",fontWeight:800,fontSize:12,letterSpacing:".06em"}}>PROVISIONAL RESEARCH ASSESSMENT · NOT AN FDA PROBABILITY</div>
    <h3 style={{margin:"7px 0",fontSize:22}}>ACACIA-HCM · Initial scientific evidence direction</h3>
    {!report?<p role="alert">SOURCE OR REVIEW LEDGER MISMATCH — provisional findings withheld.</p>:<>
      <p style={mini}>Source snapshot {report.asOf}. Favorable published co-primary outcomes, with significant unresolved benefit-risk, statistical-plan and exact indication filing uncertainties. No clinical signoff.</p>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:9,margin:"12px 0"}}>
        {[
          ["Published positive primary endpoints",String(report.positivePrimaryEndpoints)+"/2"],
          ["Mapped research positions",String(report.sourceMappedMethods)+"/800"],
          ["Independent clinical grades",String(report.officialGrades)+"/800"],
          ["Uncertainty",report.uncertainty.replaceAll("_"," ")]
        ].map(([label,value])=><div key={label} style={{background:"#164755",border:"1px solid #337c76",borderRadius:8,padding:11}}>
          <div style={{fontSize:11,color:"#b7dcd7"}}>{label}</div><strong style={{fontSize:19}}>{value}</strong>
        </div>)}
      </div>
      <details style={{border:"1px solid #3a7872",borderRadius:8,padding:11}}>
        <summary style={{fontWeight:800,cursor:"pointer"}}>Six source-backed scientific domains and remaining gaps</summary>
        {report.findings.map(x=><div key={x.domain} style={{borderBottom:"1px solid #3a7872",padding:"9px 0"}}>
          <strong>{x.domain}</strong> · <small>{x.status.replaceAll("_"," ")}</small>
          <p style={{...mini,margin:"5px 0"}}>{x.description} {x.sourceUrl?<a style={{color:"#92ecd2"}} href={x.sourceUrl} target="_blank" rel="noopener noreferrer">Read original source</a>:null}</p>
        </div>)}
      </details>
      <div style={{padding:12,marginTop:12,border:"1px solid #3a7872",borderRadius:8,background:"#123d4a"}}>
        <strong>Hypothetical FDA pathway simulator</strong>
        <p style={mini}>Test assumptions without altering original evidence, authorized scores, regulatory status or prediction history. These controls are hypothetical, never live evidence.</p>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(205px,1fr))",gap:9}}>
          <label style={{fontSize:12}}>FDA filing assumption
            <select aria-label="Assumed nHCM filing" style={input} value={scenarioInputs.filing} onChange={e=>set("filing",e.target.value as ScenarioInputs["filing"])}>
              <option value="PLANNED">Planned only · observed snapshot</option><option value="FDA_ACCEPTED">Assume FDA-accepted filing</option>
            </select>
          </label>
          <label style={{fontSize:12}}>Locked statistical plan
            <select aria-label="Assumed locked SAP" style={input} value={scenarioInputs.sap} onChange={e=>set("sap",e.target.value as ScenarioInputs["sap"])}>
              <option value="UNVERIFIED">Unverified · observed</option><option value="RECONCILED">Assume reconciled</option><option value="MATERIAL_ISSUE">Assume material issue</option>
            </select>
          </label>
          <label style={{fontSize:12}}>Safety assessment
            <select aria-label="Assumed safety review" style={input} value={scenarioInputs.safety} onChange={e=>set("safety",e.target.value as ScenarioInputs["safety"])}>
              <option value="UNRESOLVED">Unresolved · observed</option><option value="MANAGEABLE">Assume manageable</option><option value="MATERIAL_CONCERN">Assume material concern</option>
            </select>
          </label>
          <label style={{fontSize:12}}>Independent scientific review
            <select aria-label="Assumed independent review" style={input} value={scenarioInputs.review} onChange={e=>set("review",e.target.value as ScenarioInputs["review"])}>
              <option value="PENDING">Pending · observed</option><option value="SUPPORTIVE">Assume supportive</option><option value="ADVERSE">Assume adverse</option>
            </select>
          </label>
        </div>
        <div role="status" aria-live="polite" style={{paddingTop:10,marginTop:12,borderTop:"1px solid #3a7872"}}>
          <strong>Conditional pathway: {simulation?.class.replaceAll("_"," ")??"UNAVAILABLE"}</strong>
          <p style={mini}>{simulation?.meaning??"Invalid scenario — no output."}</p>
          <button type="button" onClick={()=>setScenarioInputs(defaults)} style={{background:"#d5f5e9",border:0,borderRadius:7,color:"#123b42",padding:"8px 12px",fontWeight:800,cursor:"pointer"}}>Reset to observed state</button>
        </div>
      </div>
      <p style={{...mini,marginBottom:0}}><strong>Actual FDA prediction: ABSTAIN</strong> for approval, CRL and delay. <strong>Accuracy: NOT CALIBRATED.</strong> No numeric probabilities or confidence intervals. Scenario pathways are decision-rule demonstrations, not a trained or validated predictive model.</p>
    </>}
  </section>;
}
