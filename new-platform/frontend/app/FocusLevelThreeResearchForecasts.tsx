import Link from "next/link";
import snapshot from "../data/calFocusResearchOverlay20261110.json";
import roster from "../data/p3PostDataActive.json";
import {APPLICATION_CYCLES} from "../lib/medical-intelligence-applications";

/** Frozen original research only. This panel is not the production prediction engine.
 * Never enter these calls into prospective verified accuracy, chart calibration,
 * FDA decision, trading, or trial eligibility state.
 */
type Cycle=(typeof snapshot.cycles)[number];
type LabelKey="APPROVAL_LEAN"|"CRL_LEAN"|"ABSTAIN"|"ALREADY_APPROVED";
const labels:Record<LabelKey,string>={
  APPROVAL_LEAN:"Approval lean",CRL_LEAN:"CRL lean",
  ABSTAIN:"Abstain · evidence incomplete",ALREADY_APPROVED:"Already approved · not pending"
};
const colors:Record<LabelKey,{background:string;color:string;border:string}>={
  APPROVAL_LEAN:{background:"#e8f8ef",color:"#0b6747",border:"1px solid #9ecfb5"},
  CRL_LEAN:{background:"#fff0ed",color:"#9d392f",border:"1px solid #eab6a9"},
  ABSTAIN:{background:"#fff6df",color:"#795512",border:"1px solid #e5ce91"},
  ALREADY_APPROVED:{background:"#edf1f5",color:"#556678",border:"1px solid #c0cdd7"}
};
/** Subjective agreement estimates from November 10 conversation; not calibrated probabilities. */
const subjectiveAgreement:Record<string,number|null>={
  "abvx-uc": 75,
  "achv-cytisinicline": 80,
  "apmd-ad109": 60,
  "axsm-axs12": 65,
  "blte-stargardt": 60,
  "capr-deramiocel": 60,
  "cldx-barzolvolimab": 80,
  "cogt-gist": 75,
  "cort-relacorilant": 60,
  "cytk-aficamten-ohcm": null,
  "cytk-aficamten-nhcm": 80,
  "imnm-desmoid": 75,
  "mltx-sonelokimab": 60,
  "mlys-lorundrostat": 75,
  "phvs-ondemand": 60,
  "phvs-prophylaxis": 80,
  "prax-ulixacaltamide": 60,
  "srpt-casimersen": 75,
  "srpt-golodirsen": 75,
  "svra-molgramostim": 60,
  "urgn-ugn103": 60,
  "vera-trutakna": 80,
  "zbio-obexelimab": 75
};
const box={background:"#fff",border:"1px solid #d2dcd5",borderRadius:9,padding:"12px 11px"} as const;
const linkTo=(nct:string,cycleId:string)=>
  "/predictions/assessment?nct="+encodeURIComponent(nct)+"&cycle="+encodeURIComponent(cycleId);
const cell={padding:"10px 9px",borderBottom:"1px solid #e0e9e2",verticalAlign:"top"} as const;
const validDate=(value:string|null)=>value===null||/^\d{4}-\d{2}-\d{2}$/.test(value);
function researchSnapshotPasses():boolean {
  if(snapshot.schemaVersion!==1||
    snapshot.kind!=="CAL_FOCUS_LEVEL3_STYLE_RESEARCH_FREEZE_NOT_VALIDATED_FDA_FORECAST"||
    snapshot.asOf!=="2026-11-10"||snapshot.policy.notActivePredictionEngine!==true||
    snapshot.policy.immutableHypothesisSnapshot!==true||
    snapshot.policy.independentScientificSignoff!==false||
    snapshot.policy.numericalProbabilities!==null||
    snapshot.policy.notForTrading!==true||
    snapshot.cycles.length!==23||snapshot.summary.applicationCycles!==23||
    snapshot.summary.exactNcts!==29||
    snapshot.summary.approvalLeans!==12||snapshot.summary.crlLeans!==5||
    snapshot.summary.abstentions!==5||snapshot.summary.alreadyApproved!==1)
    return false;
  const byNct=new Map(roster.records.map(r=>[r.nct,r.ticker]));
  const canonical=new Map(APPLICATION_CYCLES.map(c=>[c.id,c]));
  const ids=new Set<string>(),ncts=new Set<string>();
  for(const cycle of snapshot.cycles){
    const original=canonical.get(cycle.cycleId);
    if(!original||ids.has(cycle.cycleId)||cycle.ticker!==original.ticker||
      cycle.level!==3||cycle.asOf!==snapshot.asOf||
      cycle.independentSignoff!==false||cycle.calibratedProbability!==null||
      !validDate(cycle.reportedPdufaGoal)||
      cycle.scientificStatus!=="PRELIMINARY_SOURCE_LINKED_RESEARCH_NOT_INDEPENDENTLY_VALIDATED"||
      !Object.prototype.hasOwnProperty.call(labels,cycle.call)||
      JSON.stringify([...cycle.associatedNcts].sort())!==JSON.stringify([...original.ncts].sort())||
      cycle.associatedNcts.some(nct=>byNct.get(nct)!==cycle.ticker))
      return false;
    ids.add(cycle.cycleId);
    cycle.associatedNcts.forEach(nct=>ncts.add(nct));
  }
  return ids.size===23&&ncts.size===29&&
    snapshot.cycles.filter(c=>c.call==="APPROVAL_LEAN").length===12&&
    snapshot.cycles.filter(c=>c.call==="CRL_LEAN").length===5&&
    snapshot.cycles.filter(c=>c.call==="ABSTAIN").length===5&&
    snapshot.cycles.filter(c=>c.call==="ALREADY_APPROVED").length===1;
}
function callTag(call:LabelKey){
  return <span style={{...colors[call],borderRadius:7,padding:"5px 8px",
    display:"inline-block",fontSize:11,fontWeight:800,lineHeight:1.3}}>
    {labels[call]}</span>;
}

export default function FocusLevelThreeResearchForecasts({selectedCycleId}:{
  selectedCycleId?:string|null
}){
  if(!researchSnapshotPasses()){
    return <section role="alert" data-testid="focus-level3-research-safety-block"
      style={{...box,margin:"14px 0",color:"#8a432e"}}>
      The Level 3 FOCUS research snapshot no longer matches the source-linked
      application and exact-NCT roster. No provisional calls are being displayed
      until it is reconciled. Validated FDA prediction records remain unchanged.
    </section>;
  }
  const entries=[...snapshot.cycles].sort((a,b)=>
    (a.call==="ALREADY_APPROVED"?1:0)-(b.call==="ALREADY_APPROVED"?1:0)||
    (a.reportedPdufaGoal===null?1:0)-(b.reportedPdufaGoal===null?1:0)||
    (a.reportedPdufaGoal||"").localeCompare(b.reportedPdufaGoal||"")||
    a.ticker.localeCompare(b.ticker)||a.cycleId.localeCompare(b.cycleId));
  const selected=snapshot.cycles.find(c=>c.cycleId===selectedCycleId);
  return <section id="focus-level3-provisional-forecasts"
    aria-label="Historical FOCUS preliminary Level 3 research"
    data-testid="focus-level3-provisional-forecasts"
    style={{border:"2px solid #d4ba7e",background:"#fffaf1",
      borderRadius:14,padding:"clamp(13px,2vw,20px)",margin:"12px 0 24px"}}>
    <div style={{fontSize:11,fontWeight:900,letterSpacing:".09em",color:"#886018"}}>
      HISTORICAL FOCUS · 29 EXACT NCTS · 23 FDA APPLICATION CYCLES
    </div>
    <h2 style={{fontSize:22,margin:"7px 0",color:"#254335"}}>
      Level 3 preliminary FDA outcome research · November 10, 2026
    </h2>
    <p style={{fontSize:13,lineHeight:1.65,color:"#5d503a",margin:"8px 0 13px"}}>
      <strong>Directional hypotheses only; NOT independently validated FDA forecasts.</strong>
      Agreement percentages are subjective estimates, not independently reviewed or calibrated. These are source-linked three-layer research calls about clinical efficacy,
      benefit/risk, and FDA/manufacturing issues. They are <strong>not</strong> completed
      800-assessment scientific grades, calibrated probabilities, verified FDA outcomes,
      or buy/sell signals. The production engine and verified-accuracy charts remain
      unchanged. This is a frozen record and will not silently change with new evidence.
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(125px,1fr))",
      gap:9,margin:"15px 0"}}>
      {([
        ["Tracked FOCUS NCTs",29],["FDA application cycles",23],
        ["Approval leans",12],["CRL leans",5],["Abstain",5],
        ["Already approved",1],["Validated calls",0]
      ] as const).map(([name,count])=><div key={name} style={box}>
        <div style={{fontSize:11,color:"#66776c"}}>{name}</div>
        <strong style={{fontSize:25,color:"#305542"}}>{count}</strong>
      </div>)}
    </div>
    {selected&&<p style={{border:"1px solid #c5dacb",background:"#eff8f1",
      borderRadius:8,padding:12,fontSize:13,lineHeight:1.5}}>
      <strong>Selected application:</strong> {selected.ticker} · {selected.drug} ·{" "}
      {callTag(selected.call as LabelKey)}. This research call is not the validated
      FDA prediction for the application.
    </p>}
    <div style={{overflowX:"auto",background:"#fff",borderRadius:10,
      border:"1px solid #ded8c8"}}>
      <table data-testid="focus-level3-cycle-prediction-table"
        style={{borderCollapse:"collapse",width:"100%",minWidth:770,fontSize:12}}>
        <thead>
          <tr style={{background:"#f2efe6",textAlign:"left"}}>
            {["Ticker","FDA drug/application","Reported PDUFA target",
              "Level 3 preliminary call","My agreement","Exact supporting trials","Scientific evidence"].map(head=>
              <th key={head} scope="col"
                style={{padding:"11px 9px",borderBottom:"2px solid #c9cfbf"}}>{head}</th>)}
          </tr>
        </thead>
        <tbody>{entries.map(c=><tr key={c.cycleId} data-cycle-id={c.cycleId}
          style={{background:selectedCycleId===c.cycleId?"#eef9f0":"#fff"}}>
          <td style={{...cell,fontWeight:800}}>{c.ticker}</td>
          <td style={cell}><strong>{c.drug}</strong>
            <div style={{fontSize:11,color:"#62776b",marginTop:4}}>
              {c.indication} · {c.applicationType}</div>
            <div style={{fontSize:10,color:"#738077",marginTop:4}}>
              {c.applicationStatusAsRecorded.replaceAll("_"," ")}</div>
          </td>
          <td style={cell}><strong>{c.reportedPdufaGoal||"Not assigned"}</strong>
            {c.reportedPdufaGoal===null&&
              <div style={{fontSize:10,color:"#725d3a"}}>No invented date</div>}</td>
          <td style={cell}>{callTag(c.call as LabelKey)}
            <div style={{marginTop:6,color:"#6c7468",fontSize:11}}>
              Research confidence: {c.confidenceDescription.replaceAll("_"," ").toLowerCase()}
            </div>
          </td>
          <td style={cell}><strong>{subjectiveAgreement[c.cycleId] == null ? "N/A" : `${subjectiveAgreement[c.cycleId]}%`}</strong><div style={{fontSize:10,color:"#6c7468",marginTop:5}}>Subjective agreement · not FDA approval probability</div></td>
          <td style={cell}>{c.associatedNcts.map(nct=><div key={nct} style={{marginBottom:5}}>
            <Link href={linkTo(nct,c.cycleId)}
              style={{color:"#075a50",fontWeight:700}}>{nct}</Link>
          </div>)}</td>
          <td style={cell}>
            <details>
              <summary style={{cursor:"pointer",fontWeight:800,color:"#116e50"}}>
                Evidence, risks and sources
              </summary>
              <div style={{paddingTop:8,minWidth:210,lineHeight:1.6}}>
                <p><strong>Clinical:</strong> {c.clinicalRationale}</p>
                <p><strong>Safety / benefit:</strong> {c.benefitRiskRationale}</p>
                <p><strong>FDA / CMC:</strong> {c.fdaCmcRationale}</p>
                <p><strong>Unresolved:</strong> {c.evidenceGap}</p>
                <p><strong>Source dated:</strong> {c.sourceDate}</p>
                <p><a href={c.clinicalEvidenceReferenceUrl} target="_blank"
                  rel="noopener noreferrer">Clinical evidence</a>{" · "}
                  <a href={c.applicationReferenceUrl} target="_blank"
                    rel="noopener noreferrer">Application evidence</a></p>
              </div>
            </details>
            <Link href={linkTo(c.associatedNcts[0],c.cycleId)}
              style={{color:"#075b52",fontSize:11,display:"inline-block",marginTop:8}}>
              Open exact-cycle assessment
            </Link>
          </td>
        </tr>)}</tbody>
      </table>
    </div>
    <p style={{fontSize:12,color:"#786244",lineHeight:1.6,margin:"12px 0 0"}}>
      Historical research snapshot: {snapshot.asOf} · Source commit{" "}
      <a href={"https://github.com/pdufa/pdufa-command-center/commit/"+snapshot.sourceResearchCommit}
        target="_blank" rel="noopener noreferrer">view frozen original</a>.
      Reassessment requires independently verified new evidence, a separately
      versioned research record, and preserved earlier calls. Only validated,
      time-locked prospective predictions may enter accuracy or calibration metrics.
    </p>
  </section>;
}
