"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import {FOCUS_PRELIMINARY_R39} from "../../lib/focus-preliminary-application-research";
const card={border:"1px solid #b9d4ca",borderRadius:12,padding:15,background:"#fff"} as const;
const small={fontSize:12,color:"#475e55",lineHeight:1.65} as const;
type AppRow=(typeof FOCUS_PRELIMINARY_R39.applications)[number];
const text={
  APPROVAL_LEAN:"Preliminary approval-lean · RESEARCH ONLY",
  CRL_LEAN:"Preliminary CRL-lean · RESEARCH ONLY",
  ABSTAIN:"ABSTAIN · evidence insufficient",
  OBSERVED_APPROVAL:"Observed FDA approval · NOT a prediction"
} as const;
function sortedApps(a:readonly AppRow[]){
  return [...a].sort((x,y)=>(x.reportedGoal??"9999").localeCompare(y.reportedGoal??"9999")
    ||x.ticker.localeCompare(y.ticker)||x.id.localeCompare(y.id));
}
export default function FocusPreliminaryApplicationBoard(){
  const data=FOCUS_PRELIMINARY_R39;
  const [needle,setNeedle]=useState("");
  const [kind,setKind]=useState("ALL");
  const n=needle.trim().toLowerCase();
  const apps=useMemo(()=>sortedApps(data.applications).filter(a=>
    (!n||[a.ticker,a.drug,a.indication,a.id,...a.ncts].join(" ").toLowerCase().includes(n))&&
    (kind==="ALL"||a.preliminaryResearchLean===kind)),[n,kind,data.applications]);
  const ids=new Set(apps.map(a=>a.id));
  const trials=data.trials.filter(t=>t.applicationCycleIds.some(id=>ids.has(id)));
  return <section aria-label="All FOCUS trials and source-based FDA application preliminary research" style={{...card,margin:"16px 0 20px",background:"#f6faf7"}}>
    <div style={{fontSize:11,letterSpacing:1.2,fontWeight:800,color:"#086a50"}}>
      MAIN · NOVEMBER 9 2026 · PRIORITY 1 · SOURCE-LINKED RESEARCH</div>
    <h2 style={{fontSize:23,margin:"8px 0 4px"}}>29 FOCUS trials / 23 provisional FDA application assessments</h2>
    <p style={{...small,margin:"4px 0 12px"}}>
      This is a dated <strong>research-only preliminary assessment</strong> across all applications using already authored Phase 3 evidence dossiers and issuer/regulator links.
      Research leans are <strong>not validated FDA outcome predictions</strong>. No probability, accuracy, certainty grade or independent clinical authorization is claimed.
      Earlier FDA approvals are observed, never forecast again.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(130px,1fr))",gap:8}}>
      {[
        ["FOCUS trials",data.summary.ncts],
        ["Application cycles",data.summary.applicationCycles],
        ["Approval-lean research",data.summary.researchLeanApprovals],
        ["CRL-lean research",data.summary.researchLeanCrls],
        ["Research abstains",data.summary.abstainResearchCalls],
        ["Past FDA approvals",data.summary.observedPastApprovals],
        ["Validated forecasts",data.summary.independentlyValidatedFDAForecasts]
      ].map(([k,v])=><div key={k} style={{background:"#fff",padding:10,border:"1px solid #bed3c7",borderRadius:8}}>
        <div style={{fontSize:10,color:"#587063"}}>{k}</div>
        <strong style={{fontSize:22}}>{v}</strong>
      </div>)}
    </div>
    <p style={{...small,margin:"11px 0 10px"}}>
      <strong>Official model approval / CRL / delay predictions:</strong> ABSTAIN for all future cycles. Accuracy: NOT CALIBRATED.
      Clinical adjudications: 0. Outcome timing and formal extensions are separate from efficacy judgments.
    </p>
    <div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:9,margin:"12px 0"}}>
      <label style={{fontSize:13,fontWeight:700}}>
        Find ticker, drug, indication or NCT
        <input aria-label="Filter all FOCUS trial and application research" value={needle} onChange={e=>setNeedle(e.target.value)}
          placeholder="e.g., CAPR, HCM or NCT..." style={{display:"block",marginTop:4,padding:"8px 10px",border:"1px solid #9fb9b0",borderRadius:8,minWidth:240,maxWidth:"100%",background:"#fff",color:"#182e29"}}/>
      </label>
      <label style={{fontSize:13,fontWeight:700}}>
        Preliminary outcome
        <select aria-label="Filter by preliminary research lean" value={kind} onChange={e=>setKind(e.target.value)}
          style={{display:"block",marginTop:4,padding:"8px 10px",border:"1px solid #9fb9b0",borderRadius:8,background:"#fff",color:"#182e29"}}>
          <option value="ALL">All 23 applications</option>
          <option value="APPROVAL_LEAN">Approval-lean research</option>
          <option value="CRL_LEAN">CRL-lean research</option>
          <option value="ABSTAIN">Abstains</option>
          <option value="OBSERVED_APPROVAL">Observed completed approval</option>
        </select>
      </label>
    </div>
    <h3 style={{fontSize:17,margin:"16px 0 5px"}}>29-trial roster and application linkage</h3>
    <p style={small}>Every NCT links to its corresponding application assessment. Shared pivotal evidence is not counted as separate independent FDA decisions.</p>
    <div style={{overflowX:"auto",background:"#fff",borderRadius:9}}>
      <table style={{borderCollapse:"collapse",minWidth:780,width:"100%",fontSize:12}}>
        <thead><tr style={{background:"#e8f3ed",textAlign:"left"}}>
          {["Ticker","Exact NCT","Recorded Phase 3 readout","Application group(s)","FDA outcome model"].map(x=>
            <th key={x} style={{padding:"9px 8px",borderBottom:"2px solid #bed2c8"}}>{x}</th>)}
        </tr></thead>
        <tbody>{trials.map(t=><tr key={t.nct}>
          <td style={{padding:8,borderBottom:"1px solid #e0ebe5",fontWeight:800}}>{t.ticker}</td>
          <td style={{padding:8,borderBottom:"1px solid #e0ebe5"}}><Link href={"/predictions/assessment?nct="+t.nct} style={{color:"#14695b"}}>{t.nct}</Link></td>
          <td style={{padding:8,borderBottom:"1px solid #e0ebe5"}}>{t.recordedReleaseDate??"Not verified"}<div style={{fontSize:10}}><a href={t.registrySource} target="_blank" rel="noopener noreferrer">Trial registry</a></div></td>
          <td style={{padding:8,borderBottom:"1px solid #e0ebe5"}}>{t.applicationCycleIds.filter(id=>ids.has(id)).map(id=>
            <div key={id}><a href={"#research-"+id} style={{color:"#14695b",fontWeight:650}}>{id}</a></div>)}</td>
          <td style={{padding:8,borderBottom:"1px solid #e0ebe5",fontWeight:750}}>{t.FDAForecast}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <h3 style={{fontSize:17,margin:"20px 0 5px"}}>23 application-specific evidence judgments</h3>
    <p style={small}>Sorted by the <strong>sponsor-reported</strong> PDUFA target where available. Dates require ongoing regulator/issuer rechecking. Expand an application to read supporting and opposing evidence, primary source pointers and precise remaining uncertainties.</p>
    <div style={{display:"grid",gap:9}}>
      {apps.map(a=><details key={a.id} id={"research-"+a.id} style={{border:"1px solid #a9c9bc",borderRadius:10,background:"#fff",padding:12}}>
        <summary style={{cursor:"pointer",lineHeight:1.6}}>
          <div style={{display:"inline-flex",gap:8,flexWrap:"wrap",alignItems:"baseline"}}>
            <strong>{a.ticker} · {a.drug}</strong>
            <span style={{fontSize:12}}>{a.indication}</span>
            <strong style={{fontSize:12,color:a.preliminaryResearchLean==="CRL_LEAN"?"#974322":"#12604a"}}>{text[a.preliminaryResearchLean]}</strong>
          </div>
          <div style={{fontSize:11,color:"#65766d"}}>{a.ncts.join(" + ")} · {a.applicationType} · {a.reportedGoal?"Recorded target "+a.reportedGoal:"Target not confirmed"} · Source status: {a.originalStage.replaceAll("_"," ")}</div>
        </summary>
        <div style={{padding:"10px 2px 2px"}}>
          <p style={small}><strong>Clinical efficacy and supporting signal:</strong> {a.clinicalEvidence.observation}</p>
          <p style={small}><strong>Counterevidence or limitations:</strong> {a.opposingEvidence.observation}</p>
          <p style={small}><strong>Regulatory / CMC question:</strong> {a.regulatoryRisk}</p>
          <p style={small}><strong>Scientific checks still required:</strong> {a.uncertaintyReasons.join(" | ")}</p>
          <p style={small}><strong>Approval / CRL research lean:</strong> {text[a.preliminaryResearchLean]}. <strong>Official FDA prediction:</strong> {a.releasedRegulatoryPrediction}.
            {" "}<strong>Uncertainty:</strong> {a.leanConfidence.replaceAll("_"," ").toLowerCase()}.</p>
          <p style={small}><strong>Review delay/extension prediction:</strong> {a.reviewDelayOrExtensionPrediction}.
            {" "}<strong>Observed timing information:</strong> {a.reviewTimingStatus.replaceAll("_"," ")}.
            {a.observedFormalReviewExtension?" A previous formal extension is documented; this is not a new predicted extension.":""}</p>
          <p style={{fontSize:11,color:"#6c786f"}}>Application source dated {a.sourceDate}; external source check {a.sourceRecheckedOn??"pending"}; cutoff {a.evidenceCutoff}; method {a.methodVersion}. No independent clinical reviewer signoff, historical calibration or numerical FDA probability.</p>
          <div style={{display:"flex",gap:12,flexWrap:"wrap",fontSize:12}}>
            {a.sourceLinks.map((s,i)=><a key={i} target="_blank" rel="noopener noreferrer" href={s.url} style={{color:"#086c59",fontWeight:700}}>{s.title}</a>)}
            {a.ncts.map(n=><Link href={"/predictions/assessment?nct="+n+"&cycle="+a.id} key={n} style={{color:"#086c59"}}>Review {n}</Link>)}
          </div>
        </div>
      </details>)}
    </div>
    {apps.length===0&&<p style={small}>No matching application groups. Clear the filters to restore the complete 29-trial / 23-application view.</p>}
    <p style={{...small,margin:"15px 0 0"}}><strong>Audit restriction:</strong> these research leans are based on the retained public evidence dossiers, not a validated predictive model. Application identities are provisional, and original FDA CMC or nonpublic communications remain unknown. Forecast history must not be edited or overwritten by this view.</p>
  </section>;
}
