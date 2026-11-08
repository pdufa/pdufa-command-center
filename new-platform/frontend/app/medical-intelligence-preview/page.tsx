import type {Metadata} from "next";
import Link from "next/link";
import type {CSSProperties} from "react";
import focus from "../../data/p3PostDataActive.json";
import {
  FAILURE_INVESTIGATIONS, INITIAL_DECISION,
  summarizeRegistryStudy, type TrialEvidence
} from "../../lib/medical-intelligence-preview";
import {findingsForNct,REVIEW_COVERAGE,REVIEW_AS_OF} from "../../lib/medical-intelligence-reviewed-findings";

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

async function getRegistryStudy(nct:string):Promise<{evidence:TrialEvidence|null;error:string|null}>{
  try{
    const r=await fetch("https://clinicaltrials.gov/api/v2/studies/"+nct,{
      headers:{Accept:"application/json"},next:{revalidate:21600},signal:AbortSignal.timeout(12000)
    });
    if(!r.ok)throw new Error("Registry returned HTTP "+r.status);
    const evidence=summarizeRegistryStudy(await r.json(),nct);
    return {evidence,error:null};
  }catch(e){
    return {evidence:null,error:e instanceof Error?e.message:"Registry retrieval unavailable"};
  }
}
function Source({href,children}:{href:string;children:React.ReactNode}){
  return <a href={href} target="_blank" rel="noopener noreferrer" style={{color:palette.teal,textDecoration:"underline"}}>{children}</a>;
}
function Info({label,value}:{label:string;value:string|number}){
  return <div style={{minWidth:0}}><div style={small}>{label}</div><strong style={{display:"block",overflowWrap:"anywhere",marginTop:3}}>{value}</strong></div>;
}
function EndpointList({items}:{items:string[]}){
  return items.length?
    <ol style={{paddingLeft:22,margin:"8px 0"}}>{items.map((s,i)=><li key={i} style={{marginBottom:6}}>{s}</li>)}</ol>:
    <p style={small}>No endpoint description retrieved. This is an evidence gap, not an FDA deficiency.</p>;
}
export default async function MedicalIntelligencePreview({searchParams}:{searchParams:Promise<SearchParams>}){
  const query=await searchParams;
  const requested=typeof query.nct==="string"?query.nct:"";
  const record=rows.find(r=>r.nct===requested)||rows[0];
  const {evidence,error}=await getRegistryStudy(record.nct);
  const sourceUrl="https://clinicaltrials.gov/study/"+record.nct;
  const candidateIndex=rows.findIndex(r=>r.nct===record.nct)+1;
  const trialResults=evidence?.resultsPosted;
  const identity=evidence?("ClinicalTrials.gov exact NCT matched: "+record.nct):"Registry details not independently loaded";
  const domains=FAILURE_INVESTIGATIONS;
  const reviewed=findingsForNct(record.nct);
  const queue=rows.map(r=>{
    const f=findingsForNct(r.nct);
    return {...r,findings:f.length,
      objections:f.filter(x=>x.type==="REGULATORY_OBJECTION"||x.type==="PREVIOUS_CRL").length,
      extensions:f.filter(x=>x.type==="EXTENSION_CONFIRMED").length};
  }).sort((a,b)=>(a.recordedPdufaDate||"9999-12-31").localeCompare(b.recordedPdufaDate||"9999-12-31")||a.nct.localeCompare(b.nct));
  return <main style={{maxWidth:1260,margin:"24px auto",padding:"0 16px 36px",color:palette.ink,fontFamily:"system-ui,sans-serif"}}>
    <div style={{fontSize:12,letterSpacing:1,color:palette.teal,fontWeight:750}}>POOL → FOCUS → DEEP MEDICAL INTELLIGENCE → DECISION</div>
    <h1 style={{margin:"10px 0 6px",fontSize:"clamp(1.6rem,4vw,2.5rem)"}}>Deep Medical Intelligence</h1>
    <p style={{lineHeight:1.55,maxWidth:1000}}>Independent, failure-first research preview. It investigates what could prevent FDA approval, produce a Complete Response Letter (CRL), or cause a PDUFA extension or missed goal date. The preview is <strong>read-only</strong>; it does not modify POOL or FOCUS and does not issue an unsupported prediction.</p>
    <p style={{fontSize:14,fontWeight:700}}><Link href="/medical-intelligence-preview/coverage">Open the full 29-trial registry coverage audit</Link></p>
    <p style={{...small,marginTop:4}}><strong>Evidence boundary:</strong> FOCUS roster is a dated spreadsheet snapshot ({focus.asOf}); selected study details are retrieved from ClinicalTrials.gov when available. Company links and recorded PDUFA dates are pointers pending independent verification.</p>

    <section style={panel} aria-label="FOCUS trial selection">
      <h2 style={{marginTop:0,fontSize:19}}>Select a FOCUS trial</h2>
      <form action="/medical-intelligence-preview" method="get" style={{display:"flex",gap:10,alignItems:"end",flexWrap:"wrap"}}>
        <label style={{flex:"1 1 360px",display:"grid",gap:5,fontSize:13,fontWeight:700}}>Exact NCT / Company
          <select name="nct" defaultValue={record.nct} style={{width:"100%",minHeight:43,border:"1px solid #9ab7a7",borderRadius:8,padding:"7px 9px",background:"#fff",color:palette.ink}}>
            {rows.map(r=><option value={r.nct} key={r.nct}>{r.ticker} · {r.nct} · {r.company}</option>)}
          </select>
        </label>
        <button type="submit" style={{minHeight:43,border:0,borderRadius:8,background:palette.teal,color:"white",padding:"10px 18px",fontWeight:700,cursor:"pointer"}}>Investigate</button>
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
          <p style={{margin:"5px 0",fontWeight:600}}>{record.nct} · {evidence?.title || "Registry title not retrieved"}</p>
        </div>
        <div style={{border:"1px solid "+palette.line,borderRadius:8,padding:"9px 12px",background:palette.cream,fontSize:13}}><strong>Not adjudicated</strong><br/>No blocker has been verified in this preview</div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(190px,1fr))",gap:16,marginTop:17}}>
        <Info label="Conditions (registry)" value={evidence?.conditions.join("; ")||"Not retrieved"}/>
        <Info label="Investigational interventions" value={evidence?.interventions.join("; ")||"Not retrieved"}/>
        <Info label="Study phase / status" value={evidence?(evidence.phases.join(", ")||"Not stated")+" · "+(evidence.status||"Unknown"):"Not retrieved"}/>
        <Info label="Enrollment (registry)" value={evidence?.enrollment??"Not retrieved"}/>
        <Info label="Sponsor-reported FDA path" value={record.fdaStatus}/>
        <Info label="Recorded PDUFA date" value={record.recordedPdufaDate||"Not recorded — do not infer"}/>
      </div>
      <p style={{...small,marginBottom:0}}>{identity}. {record.recordedPdufaDate?"The PDUFA date is recorded in FOCUS but not independently confirmed here.":"An application review goal date has not been established by this snapshot."}</p>
      <div style={{display:"flex",flexWrap:"wrap",gap:16,marginTop:9,fontSize:13}}>
        <Source href={sourceUrl}>Registry study</Source>
        <Source href={record.resultsUrl}>FOCUS clinical source</Source>
        <Source href={record.regulatoryUrl}>FOCUS regulatory source</Source>
        <Source href={focus.source}>Source FOCUS spreadsheet</Source>
      </div>
      {error&&<p role="status" style={{color:palette.red,fontSize:13}}>ClinicalTrials.gov retrieval not available: {error}. Original FOCUS identity and links remain visible; the investigation cannot be marked complete.</p>}
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
      <h2 style={{marginTop:0}}>Trial-level evidence captured so far</h2>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",gap:14}}>
        <Info label="Randomization / allocation" value={evidence?.allocation||"Not retrieved"}/>
        <Info label="Masking" value={evidence?.masking||"Not retrieved"}/>
        <Info label="Results in retrieved registry record" value={evidence?(trialResults?"Results section present — requires independent review":"No posted results section found"):"Not retrieved"}/>
      </div>
      <details style={{marginTop:16,borderTop:"1px solid "+palette.line,paddingTop:12}} open>
        <summary style={{cursor:"pointer",fontWeight:700}}>Primary endpoints ({evidence?.primaryEndpoints.length??"unknown"})</summary>
        <EndpointList items={evidence?.primaryEndpoints||[]}/>
      </details>
      <details style={{marginTop:12,borderTop:"1px solid "+palette.line,paddingTop:12}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>Secondary endpoints ({evidence?.secondaryEndpoints.length??"unknown"})</summary>
        <EndpointList items={evidence?.secondaryEndpoints||[]}/>
      </details>
      <p style={small}>Registry presence does not establish that an endpoint was achieved, that an analysis is statistically robust, or that the FDA accepted the sponsor&apos;s evidence. Full results, trial protocols, and statistical analysis plans require separate review.</p>
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
    <p style={{...small,marginTop:20}}>Preview only · Registry data are fetched when a candidate is selected · No spreadsheet writes, no historical score dependencies, no asserted approval forecasts. <Link href="/focus">Return to FOCUS</Link>.</p>
  </main>;
}
