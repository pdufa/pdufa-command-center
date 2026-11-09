import {evaluateAdditionalPilotReadiness,evaluatePilotReadiness} from "../../../lib/pilot-research-readiness";
import PilotLiveEvidenceRefresh from "./PilotLiveEvidenceRefresh";
import PilotScientificSignalPanel from "./PilotScientificSignalPanel";
import PilotProvisionalResearchModel from "./PilotProvisionalResearchModel";
import PilotResearchReviewQueue from "./PilotResearchReviewQueue";
import PilotEvidenceAcquisitionPacket from "./PilotEvidenceAcquisitionPacket";
import PilotEvidenceIntakePrecheck from "./PilotEvidenceIntakePrecheck";
import PilotEncryptedEvidenceVaultStatus from "./PilotEncryptedEvidenceVaultStatus";
import pilot from "../../../data/acacia-pilot-prediction-workup-20261108.json";

const frame={border:"1px solid #8bb4a8",background:"#fff",borderRadius:12,padding:16,margin:"12px 0"} as const;
const facts={
  efficacy:"PIVOTAL_EFFICACY_POSITIVE_SAFETY_AND_REGULATORY_UNCERTAINTY",
  nct:"NCT06081894",
};
export default function PilotPredictionWorkup({nct}:{nct:string}){
  if(nct!==facts.nct || nct!==pilot.nct)return null;
  const sourceList=Object.entries(pilot.sources);
  const readiness=evaluatePilotReadiness(pilot);
  const additionalReadiness=evaluateAdditionalPilotReadiness(pilot);
  return <section aria-label="ACACIA preliminary scientific prediction workup" style={{...frame,background:"#f6fbf8"}}>
    <h2 style={{margin:"2px 0 10px"}}>ACACIA-HCM · Pilot prediction workup</h2>
    <p style={{fontSize:12,color:"#476258"}}>Historical evidence snapshot — the live prediction, grade counts and accuracy state are shown in the monitor above.</p>
    <p style={{marginTop:12}}><strong>Research-only directional finding:</strong> published pivotal efficacy is positive, while meaningful-benefit thresholds, safety, protocol statistics and indication-specific regulatory review remain uncertain. This is a qualitative scientific synthesis, <strong>not a validated FDA forecast</strong>.</p>
    <PilotProvisionalResearchModel nct={nct}/>
    <PilotScientificSignalPanel nct={nct}/>
    <PilotResearchReviewQueue nct={nct}/>
    <PilotEvidenceAcquisitionPacket nct={nct}/>
    <PilotEvidenceIntakePrecheck nct={nct}/>
    <PilotEncryptedEvidenceVaultStatus nct={nct}/>
    <section aria-label="First provisional research score" style={{...frame,background:"#eef7fc",border:"1px solid #8ab4cc"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12,flexWrap:"wrap"}}>
        <div>
          <strong>FIRST PRELIMINARY RESEARCH SCORE</strong>
          <div style={{fontSize:13,marginTop:5}}>Assessment 5.1 / Method 1 · Pivotal efficacy source verification readiness</div>
        </div>
        <div style={{fontSize:30,fontWeight:900,color:"#173d56"}}>
          {readiness?readiness.points+" / "+readiness.outOf:"WITHHELD"}
        </div>
      </div>
      <p style={{fontSize:13,margin:"8px 0"}}>This is an <strong>automated documentary-readiness checklist</strong> counting five equally weighted source-verification gates.
        It is <strong>not</strong> an official 0–5 scientific grade, a treatment-effect rating, a probability of FDA approval or calibrated accuracy.
        As-of evidence date: {readiness?.sourceDate??"Not verified"}.</p>
      {readiness?<details style={{...frame,margin:"9px 0 0"}}>
        <summary style={{cursor:"pointer",fontWeight:800}}>Show five scoring rules, sources and missing evidence</summary>
        <ol style={{paddingLeft:22,marginBottom:0}}>{readiness.checks.map(g=><li key={g.id} style={{margin:"9px 0"}}>
          <strong>{g.state==="RESEARCH_OBSERVED"?"1 point · Research source observed":"Not verified · No point counted"}: {g.title}</strong>
          <div style={{fontSize:12}}>{g.detail}</div>
          {g.sourceId&&Object.hasOwn(pilot.sources,g.sourceId)?
            <a style={{fontSize:12}} target="_blank" rel="noopener noreferrer" href={pilot.sources[g.sourceId as keyof typeof pilot.sources].url}>Open supporting source</a>:null}
        </li>)}</ol>
      </details>:<p role="alert">Incomplete or inconsistent pilot evidence: provisional number withheld.</p>}
      <p style={{fontSize:12,marginBottom:0}}>The live 800-method ledger below remains the sole source of independently authorized clinical grades. Its current grade count is separate.</p>
    </section>
    <section aria-label="Additional provisional documentary research scores" style={{...frame,background:"#f2f9fc",border:"1px solid #83b1c4"}}>
      <h3 style={{margin:"0 0 8px"}}>Additional preliminary research scores</h3>
      <p style={{fontSize:13,margin:"0 0 12px"}}>
        {readiness&&additionalReadiness?"3 of 18 source-mapped research positions have documentary checklists; the other 15 are not scored.": "Additional research scorecards withheld until their exact public evidence checks pass."}
        {" "}These are <strong>document availability/readiness indices</strong>, not official scientific method grades.
        The independent clinical ledger still has its own scores and history below.
      </p>
      {additionalReadiness?additionalReadiness.map(card=><article key={card.assessmentId} style={{
        padding:12,border:"1px solid #9fc3d4",borderRadius:9,background:"#fff",marginTop:10}}>
        <div style={{display:"flex",flexWrap:"wrap",gap:12,justifyContent:"space-between",alignItems:"center"}}>
          <div>
            <strong>Assessment {card.assessmentId} · Method {card.methodIndex}</strong>
            <p style={{fontSize:13,margin:"4px 0"}}>{card.label}</p>
          </div>
          <div style={{fontSize:27,fontWeight:900,color:"#153e5a"}}>{card.points} / {card.outOf}</div>
        </div>
        <p style={{fontSize:12,margin:"5px 0 9px"}}>As-of: {card.sourceDate} · Not verified clinically · FDA prediction remains ABSTAIN</p>
        <details style={{...frame,margin:0,padding:10}}>
          <summary style={{cursor:"pointer",fontWeight:700}}>View the five documented criteria and source gaps</summary>
          <ol style={{paddingLeft:20,marginBottom:0}}>{card.checks.map(g=><li key={g.id} style={{margin:"8px 0"}}>
            <strong>{g.state==="RESEARCH_OBSERVED"?"Source observed · +1 documentary point":"Not verified · 0 documentary points"}</strong>
            <div>{g.title}</div>
            <p style={{fontSize:12,margin:"3px 0"}}>{g.detail}</p>
            {g.sourceId&&Object.hasOwn(pilot.sources,g.sourceId)?
              <a target="_blank" rel="noopener noreferrer" href={pilot.sources[g.sourceId as keyof typeof pilot.sources].url}>Open original source</a>:null}
          </li>)}</ol>
        </details>
      </article>):null}
      <p style={{fontSize:12,marginBottom:0}}>
        An unverified documentary criterion counts zero **for this checklist only**. It does not mean the drug or trial failed that scientific method. No source completeness points are carried into the FDA forecast.
      </p>
    </section>
    <PilotLiveEvidenceRefresh nct={nct}/>
    <p style={{fontSize:13}}><strong>Phase 3 evidence:</strong> week-36 KCCQ-CSS placebo-adjusted difference +{pilot.publishedPrimary.kccq.difference.toFixed(1)} points (95% CI {pilot.publishedPrimary.kccq.ci95[0]}–{pilot.publishedPrimary.kccq.ci95[1]}); peak VO₂ +{pilot.publishedPrimary.peakVo2.difference} mL/kg/min (95% CI {pilot.publishedPrimary.peakVo2.ci95[0]}–{pilot.publishedPrimary.peakVo2.ci95[1]}). Both met the sponsor-reported initial statistical criteria, which is not the same as validated clinical benefit or FDA approval.</p>
    <div style={{padding:12,border:"1px solid #d8c1a4",borderRadius:8,background:"#fffaf2"}}>
      <strong>Descriptive safety signal — not a risk-adjusted prediction</strong>
      <p style={{fontSize:13}}>LVEF below 50%: {pilot.descriptiveSafety[0].treated}/{pilot.descriptiveSafety[0].treatedN} ({pilot.descriptiveSafety[0].treatedPct}%) vs {pilot.descriptiveSafety[0].control}/{pilot.descriptiveSafety[0].controlN} ({pilot.descriptiveSafety[0].controlPct}%) — unadjusted difference +{pilot.descriptiveSafety[0].unadjustedRiskDifferencePp} percentage points. All-cause serious adverse events: {pilot.descriptiveSafety[1].treatedPct}% vs {pilot.descriptiveSafety[1].controlPct}%. Source-discordant heart-failure SAE reporting requires separate review.</p>
    </div>
    <div style={{border:"1px solid #8bb4a8",borderRadius:9,padding:12,margin:"12px 0",background:"#edf8f4"}} aria-label="Research source handoff progress">
      <strong>Phase III research source handoffs · {pilot.scientificFramework.mappedCandidateMethodLeads} of {pilot.scientificFramework.positions} method positions</strong>
      <p style={{fontSize:13,margin:"6px 0"}}>Source leads in {pilot.scientificFramework.criticalHeadingsWithSourceLeads}/{pilot.scientificFramework.criticalPhase3AssessmentHeadings} priority assessment headings; <strong>{pilot.scientificFramework.methodPositionsUnexamined} positions still unexamined</strong> and {pilot.scientificFramework.researchBoundedFindings} bounded research findings. The evidence packet contains {pilot.scientificFramework.packetSourceReceiptCount} captured source responses and {pilot.scientificFramework.packetBlockedOriginalSourceRequests} blocked retrieval.</p>
      <p style={{fontSize:13,margin:"6px 0"}}><strong>{pilot.scientificFramework.methodGradeRecommendations} numeric grade recommendations; {pilot.scientificFramework.independentlyGradedMethodPositions} authorized scientific grades.</strong> These counts are from the dated research packet, not from a completed live analysis. A mapped research handoff is neither an independently examined clinical test nor an FDA prediction.</p>
      <a href={pilot.scientificFramework.revision16Packet} target="_blank" rel="noopener noreferrer">Open the original Revision 16 evidence packet and all 800 research positions</a>
    </div>
    <details style={frame}>
      <summary style={{fontWeight:800,cursor:"pointer"}}>Open 11 critical assessment evidence leads and gaps</summary>
      <div style={{display:"grid",gap:8,marginTop:12}}>
      {pilot.criticalAssessmentEvidence.map(a=><article key={a.id} style={{padding:10,border:"1px solid #d5e6df",borderRadius:8,background:"#fff"}}>
        <strong>{a.id} · {a.label}</strong>
        <div style={{fontSize:12,marginTop:3}}>Method source leads: {a.candidateMethodIndices.map(i=>"L"+i).join(", ")} · Sources: {a.sourceLeadIds.join(", ")} · <strong>NOT GRADED</strong></div>
        <div style={{fontSize:13,marginTop:5}}>Needs review: {a.remaining}</div>
      </article>)}
      </div>
    </details>
    <details style={frame}>
      <summary style={{fontWeight:800,cursor:"pointer"}}>Safety discrepancy audit — source counts require independent reconciliation</summary>
      <p style={{fontSize:13}}>The peer-reviewed secondary responder analysis reports serious heart-failure adverse events in 11 treated participants and 1 placebo participant; later sponsor disclosures report 12 and 3. The exact time windows, analysis populations and event definitions have not been reconciled. Neither figure should be silently substituted for the other.</p>
      <p style={{fontSize:13}}>The secondary report also prints treatment-interruption values of 14 (2.7%) and 1 (0.8%), which do not match the corresponding 258/259 randomized denominators by simple percentage arithmetic. That may reflect a separate denominator or reporting/transcription issue; the original safety populations and correction notices require review.</p>
      <p style={{fontSize:12}}>Sources: <a href={pilot.sources.RESPONDER_ANALYSIS.url} target="_blank" rel="noopener noreferrer">peer-reviewed secondary analysis</a> and <a href={pilot.sources.SEC_10Q.url} target="_blank" rel="noopener noreferrer">sponsor SEC filing</a>. Both are research evidence; no clinical grade or causal conclusion is issued here.</p>
    </details>
    <details style={frame}>
      <summary style={{fontWeight:800,cursor:"pointer"}}>Conditional regulatory scenarios (not forecast probabilities)</summary>
      <ul>
        <li><strong>Approval pathway:</strong> FDA accepts the strength and clinical relevance of co-primary benefits and finds the ejection-fraction and heart-failure safety profile manageable.</li>
        <li><strong>CRL pathway:</strong> the filed application fails efficacy sufficiency, safety, label, CMC, or other regulatory review standards.</li>
        <li><strong>Review-delay pathway:</strong> a filed/accepted application needs additional analyses, inspections or major amendments. No ACACIA nHCM PDUFA date has been verified.</li>
      </ul>
      <p style={{fontSize:12}}>These are conditional mechanisms to investigate. No ranking or likelihood is assigned; the validated engine remains ABSTAIN.</p>
    </details>
    <details style={frame}>
      <summary style={{fontWeight:800,cursor:"pointer"}}>Source provenance · {sourceList.length} public references</summary>
      <ul>{sourceList.map(([id,value])=><li key={id}><a href={value.url} target="_blank" rel="noopener noreferrer">{value.label}</a> ({id})</li>)}</ul>
    </details>
    <p style={{fontSize:12,color:"#476258",marginBottom:0}}>Source cutoff: {pilot.asOf} · Exact trial {pilot.nct} · {pilot.protocolCode} · Clinical signoff and prospective accuracy calibration still required.</p>
  </section>;
}
