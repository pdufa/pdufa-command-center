import type {Metadata} from "next";
import Link from "next/link";
import type {CSSProperties} from "react";
import focus from "../../data/p3PostDataActive.json";
import {FAILURE_INVESTIGATIONS, INITIAL_DECISION} from "../../lib/medical-intelligence-preview";
import OnDemandRegistryResearch from "./OnDemandRegistryResearch";
import ContinuousMedicalAnalysis from "./ContinuousMedicalAnalysis";
import {findingsForNct,REVIEW_COVERAGE,REVIEW_AS_OF} from "../../lib/medical-intelligence-reviewed-findings";
import {conditionForNct} from "../../lib/medical-intelligence-conditions";
import {applicationsForNct,CYCLE_COUNTS} from "../../lib/medical-intelligence-applications";

export const metadata:Metadata={
  title:"Deep Medical Intelligence — Read-only preview | PDUFA",
  description:"Independent failure-first clinical and FDA decision preview for exact FOCUS trials."
};
export const dynamic="force-dynamic";
type SearchParams={nct?:string};
const palette={
  ink:"#17352d",muted:"#52665c",line:"#cbdad0",cream:"#f5faf6",teal:"#005e52",red:"#8d352e",white:"#fff"
};
const panel:CSSProperties={background:"#fff",border:"1px solid "+palette.line,borderRadius:12,padding:18,marginTop:16};
const small:CSSProperties={color:palette.muted,fontSize:13,lineHeight:1.55};
const rows=focus.records;

function Source({href,children}:{href:string;children:React.ReactNode}){
  return <a href={href} target="_blank" rel="noopener noreferrer" style={{color:palette.teal,textDecoration:"underline"}}>{children}</a>;
}
function Info({label,value}:{label:string;value:string|number}){
  return <div style={{minWidth:0}}><div style={small}>{label}</div><strong style={{display:"block",overflowWrap:"anywhere",marginTop:3}}>{value}</strong></div>;
}
export default async function MedicalIntelligencePreview({searchParams}:{searchParams:Promise<SearchParams>}){
  const query=await searchParams;
  const requested=typeof query.nct==="string"?query.nct:"";
  const record=rows.find(r=>r.nct===requested)||rows[0];
  const sourceUrl="https://clinicaltrials.gov/study/"+record.nct;
  const candidateIndex=rows.findIndex(r=>r.nct===record.nct)+1;
  const domains=FAILURE_INVESTIGATIONS;
  const reviewed=findingsForNct(record.nct);
  const conditionDossier=conditionForNct(record.nct);
  const applicationCycles=applicationsForNct(record.nct);
  const queue=rows.map(r=>{
    const f=findingsForNct(r.nct);
    return {...r,findings:f.length,
      objections:f.filter(x=>x.type==="REGULATORY_OBJECTION"||x.type==="PREVIOUS_CRL").length,
      extensions:f.filter(x=>x.type==="EXTENSION_CONFIRMED").length};
  }).sort((a,b)=>(a.recordedPdufaDate||"9999-12-31").localeCompare(b.recordedPdufaDate||"9999-12-31")||a.nct.localeCompare(b.nct));
  return <main style={{maxWidth:1260,margin:"24px auto",padding:"0 16px 36px",color:palette.ink,fontFamily:"system-ui,sans-serif"}}>
    <div style={{fontSize:12,letterSpacing:1,color:palette.teal,fontWeight:750}}>POOL → FOCUS → DEEP MEDICAL INTELLIGENCE → DECISION</div>
    <h1 style={{margin:"10px 0 6px",fontSize:"clamp(1.6rem,4vw,2.5rem)"}}>Deep Medical Intelligence</h1>
    <p style={{fontWeight:700,margin:"6px 0"}}><Link href="/medical-intelligence-preview/specialist-review">Clinical Subspecialty Review (medical specialist depth)</Link> · <Link href="/medical-intelligence-preview/master-depth">Open Medical Master Depth — 20 levels × 40 assessments</Link></p>
    <p style={{lineHeight:1.55,maxWidth:1000}}>Independent, failure-first research preview. It investigates what could prevent FDA approval, produce a Complete Response Letter (CRL), or cause a PDUFA extension or missed goal date. The preview is <strong>read-only</strong>; it does not modify POOL or FOCUS and does not issue an unsupported prediction.</p>
    <p style={{fontSize:14,fontWeight:700,display:"flex",flexWrap:"wrap",gap:18}}><Link href="/medical-intelligence-preview/coverage">All-FOCUS registry coverage</Link><Link href="/medical-intelligence-preview/applications">All FDA application cycles</Link><Link href="/medical-intelligence-preview/failure-desk">Failure-first decision desk</Link></p>
    <p style={{...small,marginTop:4}}><strong>Evidence boundary:</strong> FOCUS roster is a dated spreadsheet snapshot ({focus.asOf}); live registry data are fetched only if the Run External Source Check button is pressed. Company links and recorded PDUFA dates are pointers pending independent verification.</p>

    <section style={panel} aria-label="FOCUS trial selection">
      <h2 style={{marginTop:0,fontSize:19}}>Select a FOCUS trial</h2>
      <form action="/medical-intelligence-preview" method="get" style={{display:"flex",gap:10,alignItems:"end",flexWrap:"wrap"}}>
        <label style={{flex:"1 1 360px",display:"grid",gap:5,fontSize:13,fontWeight:700}}>Exact NCT / Company
          <select name="nct" defaultValue={record.nct} style={{width:"100%",minHeight:43,border:"1px solid #9ab7a7",borderRadius:8,padding:"7px 9px",background:"#fff",color:palette.ink}}>
            {rows.map(r=><option value={r.nct} key={r.nct}>{r.ticker} · {r.nct} · {r.company}</option>)}
          </select>
        </label>
        <button type="submit" style={{minHeight:43,border:0,borderRadius:8,background:palette.teal,color:"white",padding:"10px 18px",fontWeight:700,cursor:"pointer"}}>View saved research</button>
      </form>
      <p style={{...small,marginBottom:0}}><strong>{rows.length} FOCUS NCT records loaded</strong> · Candidate {candidateIndex} of {rows.length}. These are initialized dossiers, not {rows.length} completed scientific reviews.</p>
    </section>

    <details style={panel} aria-label="FOCUS-wide investigation queue">
      <summary style={{cursor:"pointer",fontSize:19,fontWeight:750}}>FOCUS research queue — all {rows.length} trials <span style={{fontSize:13,fontWeight:400,color:palette.muted}}>(expand)</span></summary>
      <p style={small}>Sorted by the FOCUS-recorded PDUFA date where available. Dates are not independently certified here. Research status means curated source findings exist, not that scientific review is complete.</p>
      <div style={{overflowX:"auto"}}>
        <table style={{width:"100%",minWidth:640,borderCollapse:"collapse",fontSize:13}}>
          <thead style={{background:palette.cream}}><tr>
            <th style={{textAlign:"left",padding:9}}>Trial</th>
            <th style={{textAlign:"left",padding:9}}>Recorded goal</th>
            <th style={{textAlign:"left",padding:9}}>Source-reviewed findings</th>
            <th style={{textAlign:"left",padding:9}}>Documented regulatory context</th>
          </tr></thead>
          <tbody>{queue.map(q=><tr key={q.nct} style={{borderTop:"1px solid "+palette.line}}>
            <td style={{padding:9}}><Link href={"/medical-intelligence-preview?nct="+q.nct}>{q.ticker} · {q.nct}</Link></td>
            <td style={{padding:9}}>{q.recordedPdufaDate||"Not established"}</td>
            <td style={{padding:9}}>{q.findings ? q.findings+" source-backed finding(s) — review incomplete":"Not yet independently reviewed"}</td>
            <td style={{padding:9}}>{q.objections ? q.objections+" historical/FDA concern(s)" : "No curated FDA objection"}
              {q.extensions ? " · "+q.extensions+" confirmed extension event(s)" : ""}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <p style={small}>A blank or zero count is a research-coverage gap, not evidence that a drug has no risk. Multiple trials can feed one FDA application decision.</p>
    </details>

    <section style={panel}>
      <div style={{display:"flex",gap:14,justifyContent:"space-between",alignItems:"start",flexWrap:"wrap"}}>
        <div><p style={{...small,margin:0}}>FOCUS candidate · {record.ticker}</p>
          <h2 style={{margin:"5px 0"}}>{record.company}</h2>
          <p style={{margin:"5px 0",fontWeight:600}}>{record.nct} · External evidence check available on demand</p>
        </div>
        <div style={{border:"1px solid "+palette.line,borderRadius:8,padding:"9px 12px",background:palette.cream,fontSize:13}}><strong>Not adjudicated</strong><br/>No blocker has been verified in this preview</div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(190px,1fr))",gap:16,marginTop:17}}>
        <Info label="Sponsor-reported FDA path" value={record.fdaStatus}/>
        <Info label="Recorded PDUFA date" value={record.recordedPdufaDate||"Not independently verified"}/>
        <Info label="Live clinical source check" value="Not started — click the Run button below"/>
      </div>
      <p style={{...small,marginBottom:0}}>FOCUS identity, saved clinical findings and existing source links are shown without a live external lookup.</p>
      <div style={{display:"flex",flexWrap:"wrap",gap:16,marginTop:9,fontSize:13}}>
        <Source href={sourceUrl}>Registry study</Source>
        <Source href={record.resultsUrl}>FOCUS clinical source</Source>
        <Source href={record.regulatoryUrl}>FOCUS regulatory source</Source>
        <Source href={focus.source}>Source FOCUS spreadsheet</Source>
      </div>
    </section>

    <ContinuousMedicalAnalysis key={"continuous-"+record.nct} nct={record.nct}/>

    <OnDemandRegistryResearch key={record.nct} nct={record.nct}/>

    <section style={panel} aria-label="Disease-specific scientific investigation">
      <h2 style={{marginTop:0}}>Condition and disease intelligence</h2>
      {conditionDossier ? <>
        <h3 style={{fontSize:17,margin:"0 0 12px"}}>{conditionDossier.indication}</h3>
        <p style={{lineHeight:1.6,fontSize:14}}><strong>Disease mechanism:</strong> {conditionDossier.mechanism}</p>
        <p style={{lineHeight:1.6,fontSize:14}}><strong>Natural history and confounders:</strong> {conditionDossier.naturalHistory}</p>
        <p style={{lineHeight:1.6,fontSize:14}}><strong>Patient-important outcomes:</strong> {conditionDossier.patientOutcomes}</p>
        <p style={{lineHeight:1.6,fontSize:14}}><strong>Trial interpretation:</strong> {conditionDossier.trialInterpretation}</p>
        <details style={{border:"1px solid "+palette.line,borderRadius:8,padding:"11px 13px",marginTop:10}} open>
          <summary style={{cursor:"pointer",fontWeight:700}}>Condition-specific failure investigations ({conditionDossier.failureFirstQuestions.length})</summary>
          <ol style={{paddingLeft:24,marginBottom:0,fontSize:14,lineHeight:1.6}}>
            {conditionDossier.failureFirstQuestions.map((q,i)=><li key={i} style={{marginBottom:6}}>{q}</li>)}
          </ol>
        </details>
        <p style={{...small,marginBottom:0}}>Medical source: <Source href={conditionDossier.sourceUrl}>{conditionDossier.sourceTitle}</Source>. These questions are hypotheses to investigate, not documented drug defects.</p>
      </>:<p style={small}>A complete, sourced disease-specific dossier has not yet been curated for this indication. Registry condition names remain available above; absence of a dossier does not establish clinical safety or FDA readiness.</p>}
    </section>

    <section style={panel} aria-label="FDA application cycle mapping">
      <h2 style={{marginTop:0}}>Matching FDA application cycles</h2>
      <p style={small}><strong>{CYCLE_COUNTS.total} distinct application/review-cycle records</strong> across FOCUS. A trial is not an FDA application: multiple NCTs can support one application, and one NCT can contribute to two distinct supplemental applications.</p>
      {applicationCycles.length ? <div style={{display:"grid",gap:11}}>
        {applicationCycles.map(a=><div key={a.id} style={{border:"1px solid "+palette.line,borderRadius:9,padding:13,background:palette.cream}}>
          <strong>{a.drug} — {a.applicationType}</strong>
          <div style={{...small,marginTop:4}}>Indication: {a.indication}</div>
          <div style={{...small,marginTop:4}}>Source-reported cycle: <strong>{a.stage.replace(/_/g," ")}</strong> · goal: <strong>{a.reportedGoal||"Not assigned in cited source"}</strong></div>
          <div style={{...small,marginTop:4}}>Connected trials: {a.ncts.join(", ")}</div>
          <p style={{fontSize:14,margin:"10px 0 6px"}}><strong>Decision-critical question:</strong> {a.criticalQuestion}</p>
          <div style={{fontSize:13}}><Source href={a.sourceUrl}>Review supporting disclosure ({a.sourceDate})</Source></div>
        </div>)}
      </div>:<p style={small}>No cycle has been reconciled for this exact NCT; application prediction is blocked until matching evidence exists.</p>}
      <p style={{...small,marginBottom:0}}>Each application-outcome and review-timing judgment remains <strong>indeterminate</strong> until current-cycle sources, full evidence and unresolved regulatory deficiencies are independently assessed. <Link href="/medical-intelligence-preview/applications">View all application cycles</Link>.</p>
    </section>

    <section style={panel} aria-label="Source-adjudicated findings">
      <div style={{display:"flex",justifyContent:"space-between",gap:12,flexWrap:"wrap",alignItems:"baseline"}}>
        <h2 style={{marginTop:0,marginBottom:4}}>Documented FDA and clinical findings</h2>
        <span style={small}>Research snapshot: {REVIEW_AS_OF}</span>
      </div>
      <p style={small}><strong>{REVIEW_COVERAGE.reviewedNcts} of {rows.length} FOCUS trials</strong> currently have manually curated source-backed findings across {REVIEW_COVERAGE.reviewedPrograms} application/indication programs. There are {REVIEW_COVERAGE.documentedFindings} findings in the source ledger. Other dossiers still need substantive review. Findings are not equivalent to completed assessments or predictions.</p>
      {reviewed.length ? <>
        <p style={{fontSize:14}}><strong>{reviewed.length} published findings</strong> associated with {record.nct}. Each preserves its source type, FDA relevance, contrary evidence, and the next question to resolve.</p>
        <div style={{display:"grid",gap:9}}>
          {reviewed.map((f,i)=><details key={f.id} open={i===0}
            style={{border:"1px solid "+(f.type==="REGULATORY_OBJECTION"||f.type==="PREVIOUS_CRL"?"#c8988f":palette.line),borderRadius:10,padding:"13px 15px",background:"#fff"}}>
            <summary style={{cursor:"pointer",fontWeight:700,fontSize:15}}>
              <span style={{display:"block",fontSize:12,fontWeight:600,color:f.type==="REGULATORY_OBJECTION"||f.type==="PREVIOUS_CRL"?palette.red:palette.muted,marginBottom:4}}>{f.type.replace(/_/g," ")} · {f.evidence.replace(/_/g," ")} · {f.published}</span>
              {f.headline}
            </summary>
            <div style={{fontSize:14,lineHeight:1.55,paddingTop:12}}>
              <p style={{margin:"0 0 9px"}}><strong>Published evidence:</strong> {f.detail}</p>
              <p style={{margin:"0 0 9px"}}><strong>FDA consequence / interpretation:</strong> {f.fdaRelevance}</p>
              <p style={{margin:"0 0 9px"}}><strong>Counterevidence or limitation:</strong> {f.counterpoint}</p>
              <p style={{margin:"0 0 9px"}}><strong>Still to investigate:</strong> {f.remainingQuestion}</p>
              <p style={{margin:0}}><Source href={f.sourceUrl}>{f.sourceTitle}</Source></p>
            </div>
          </details>)}
        </div>
        <p style={{...small,marginBottom:0}}>Note: Confirmed historical CRLs, documented FDA objections, sponsor statements, and reported extensions are distinguished from new unresolved FDA deficiencies. No historical event is automatically treated as a future CRL prediction.</p>
      </>:<div style={{background:palette.cream,padding:14,borderRadius:8}}>
        <strong>Source review not yet completed for this NCT.</strong>
        <p style={{...small,marginBottom:0}}>The registry and FOCUS source links remain available. Do not mistake absence of reviewed findings for an absence of safety, clinical or FDA risks.</p>
      </div>}
    </section>

    <section style={panel}>
      <h2 style={{marginTop:0}}>Independent FDA decision</h2>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(210px,1fr))",gap:12}}>
        <div style={{background:palette.cream,borderRadius:8,padding:14}}><div style={small}>Application outcome</div><strong>INDETERMINATE</strong><p style={small}>Approval / accelerated approval / CRL / withdrawal not established</p></div>
        <div style={{background:palette.cream,borderRadius:8,padding:14}}><div style={small}>Review timing</div><strong>INDETERMINATE</strong><p style={small}>On-time / extension / missed date not established</p></div>
        <div style={{background:palette.cream,borderRadius:8,padding:14}}><div style={small}>Decision confidence</div><strong>NOT ASSESSED</strong><p style={small}>No calibrated probability or approval percentage inferred</p></div>
      </div>
      <p style={{...small,marginBottom:0}}>{INITIAL_DECISION.note} A CRL and a PDUFA extension are different events; an extension is not a final application disposition.</p>
    </section>

    <section style={panel}>
      <h2 style={{marginTop:0}}>FDA failure investigations · {domains.length} research domains</h2>
      <p style={small}>Each expandable domain specifies what investigators must test. These are <strong>open investigation questions</strong>, not identified defects. No fabricated risk probabilities or implicit zero-risk assessments.</p>
      <div style={{display:"grid",gap:8}}>
        {domains.map((d,i)=><details key={d.id} open={i===0||i===3} style={{border:"1px solid "+palette.line,borderRadius:9,padding:"12px 14px",background:"#fff"}}>
          <summary style={{cursor:"pointer",fontWeight:700}}>{i+1}. {d.title} <span style={{fontWeight:400,fontSize:12,color:palette.muted}}>· {d.scope} · Not yet independently adjudicated</span></summary>
          <div style={{paddingTop:10,lineHeight:1.55,fontSize:14}}>
            <p style={{margin:"4px 0 9px"}}><strong>Failure-first question:</strong> {d.question}</p>
            <p style={{margin:"4px 0 9px"}}><strong>Potential FDA consequence:</strong> {d.fdaConsequence}</p>
            <p style={{margin:"4px 0 9px"}}><strong>Evidence to obtain:</strong> {d.evidenceNeeded}</p>
            <p style={{...small,margin:0}}><strong>Evidence status:</strong> Not reviewed; a missing public document is not proof that the candidate has this deficiency.</p>
          </div>
        </details>)}
      </div>
    </section>

    <section style={panel}>
      <h2 style={{marginTop:0}}>Decision challenge and next investigations</h2>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(235px,1fr))",gap:16}}>
        <div><h3 style={{fontSize:16,margin:"0 0 6px"}}>Strongest approval case</h3><p style={small}>Not yet established. Obtain full efficacy and safety data, independently confirm endpoints, and evaluate whether benefits outweigh risks for the intended indication.</p></div>
        <div><h3 style={{fontSize:16,margin:"0 0 6px"}}>Strongest CRL case</h3><p style={small}>Not yet established. Search for conflicting trial results, deficiencies in statistics or safety, adverse FDA communications, and verified CMC/inspection problems.</p></div>
        <div><h3 style={{fontSize:16,margin:"0 0 6px"}}>Strongest extension case</h3><p style={small}>Not yet established. Independently verify the accepted application, review cycle, goal date, and any FDA-announced major amendment or schedule change.</p></div>
      </div>
      <div style={{borderLeft:"3px solid "+palette.teal,padding:"8px 12px",background:palette.cream,borderRadius:4}}>
        <strong>Next defensible action:</strong> Match the drug and indication to the exact FDA application; inspect complete published results and FDA/issuer regulatory communications; then document evidence for or against each proposed blocker. Preserve source dates and a traceable prediction history.
      </div>
    </section>
    <p style={{...small,marginTop:20}}>Preview only · Live registry data are only collected on button click · No spreadsheet writes, no historical score dependencies, no asserted approval forecasts. <Link href="/focus">Return to FOCUS</Link>.</p>
  </main>;
}
