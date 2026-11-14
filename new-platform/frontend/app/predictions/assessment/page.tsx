import Link from "next/link";
import type {Metadata} from "next";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";
import {CLINICAL_SPECIALTY_PROFILES,getSpecialtyProfile,getSpecialtyTasks} from "../../../lib/medical-intelligence-specialty";
import {getFullSpecialistCase} from "../../../lib/medical-intelligence-specialist-all";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE,FOCUS_SPECIALTY_SUMMARY} from "../../../lib/focus-specialty-assessment";
import AssessmentStatusPies from "../../AssessmentStatusPies";
import FocusLevelThreeResearchForecasts from "../../FocusLevelThreeResearchForecasts";
import AssessmentLevelChart from "../../AssessmentLevelChart";
import LevelOneFocusScores from "../../LevelOneFocusScores";
import LevelSixAssessmentRunner from "../../LevelSixAssessmentRunner";
import HistoricalTestingChart from "../../HistoricalTestingChart";
import HistoricalMonthlyLevelTrend from "../../HistoricalMonthlyLevelTrend";
import October2026HistoricalAuditPanel from "../../October2026HistoricalAuditPanel";
import UltomirisHistoricalLevelThreePanel from "../../UltomirisHistoricalLevelThreePanel";
import {getAssessmentPieData} from "../../../lib/focus-assessment-chart";

export const metadata:Metadata={
  title:"FOCUS Scientific Assessment Readiness | PDUFA",
  description:"Run phase-first Levels 1–6 owner research for one FOCUS trial or all 32, with source-linked findings, uncertainty and evidence gaps."
};
type Params={nct?:string;cycle?:string};
const section={border:"1px solid #c3d9d5",background:"#fff",borderRadius:13,padding:"clamp(13px,2vw,20px)"} as const;
const badge={padding:"6px 10px",border:"1px solid #c48e4c",background:"#fff6e8",borderRadius:7,color:"#825013",fontSize:12,fontWeight:800} as const;
const label={fontSize:11,letterSpacing:".075em",fontWeight:800,color:"#216258"} as const;

export default async function AssessmentPage({searchParams}:{searchParams:Promise<Params>}){
  const q=await searchParams;
  const pies=getAssessmentPieData();
  const selected=FOCUS_SPECIALTY_ASSESSMENT_QUEUE.find(x=>x.nct===q.nct)??FOCUS_SPECIALTY_ASSESSMENT_QUEUE[0];
  const cycle=selected?.applications.find(x=>x.cycleId===q.cycle)??selected?.applications[0]??null;
  const specialty=cycle?getSpecialtyProfile(cycle.cycleId):null;
  const fullCase=cycle?getFullSpecialistCase(cycle.cycleId):null;
  const tasks=cycle?getSpecialtyTasks(cycle.cycleId):[];
  const apps=APPLICATION_CYCLES.filter(a=>a.ticker===selected?.ticker&&a.ncts.includes(selected.nct));
  const link=(nct:string,cycleId?:string)=>"/predictions/assessment?nct="+encodeURIComponent(nct)+(cycleId?"&cycle="+encodeURIComponent(cycleId):"");
  return <main style={{maxWidth:1300,margin:"0 auto",padding:"26px 15px 60px",color:"#122f32"}}>
    <div style={{...label,letterSpacing:".12em"}}>PDUFA COMMAND CENTER · PHASE-FIRST RESEARCH INTAKE</div>
    <h1 style={{fontSize:"clamp(25px,4vw,36px)",margin:"8px 0 4px"}}>Deep Clinical Subspecialty Intelligence</h1>
    <p style={{fontSize:17,fontWeight:700,margin:"4px 0"}}>FOCUS — Run Scientific Levels 1–6</p>
    <section aria-label="Owner-only assessment policy" data-testid="owner-only-assessments"
      style={{...section,margin:"10px 0 16px",background:"#eefaf5"}}>
      <strong>OWNER-ONLY ASSESSMENTS · LEVELS 1–20</strong>
      <p style={{margin:"7px 0 0",fontSize:14,lineHeight:1.6}}>
        You review and accept your own trial assessments. No outside clinician, statistician,
        independent challenger, source attestor or third-party signoff is required.
        Source citations, phase checks, scientific uncertainties and prediction history
        remain available for your own assessment. No owner approval is implied before you record it.
      </p>
    </section>
    <p style={{maxWidth:1030,lineHeight:1.6,color:"#435f60",fontSize:14}}>
      Run all six levels for one trial or the complete 32-trial FOCUS roster below. The document-coverage
      scores and older research for 29 mapped trials / 23 provisional cycles remain separate.
      <strong>A completed automated run is not owner acceptance or a validated FDA probability.</strong>
      The first step in every actual review is to verify current trial phase, status, intervention and indication.
    </p>
    <LevelSixAssessmentRunner selectedNct={selected?.nct}/>
    <LevelOneFocusScores/>
    <HistoricalMonthlyLevelTrend/>
    <section aria-label="Future prospective FDA predictions"
      style={{background:"#eefaf5",border:"1px solid #9bcdb9",borderRadius:13,
        padding:"13px 16px",margin:"0 0 10px"}}>
      <div style={{fontSize:16,fontWeight:850,color:"#0d684f"}}>
        FUTURE PREDICTIONS · LIVE / PROSPECTIVE
      </div>
      <p style={{fontSize:13,color:"#3d6558",margin:"5px 0 0",lineHeight:1.55}}>
        Verified accuracy counts only a frozen forecast followed by a sourced FDA decision.
        This is separate from the historical Level 3–20 selector above, so zero verified
        decisions does not mean zero historical research.
      </p>
    </section>
    <FocusLevelThreeResearchForecasts selectedCycleId={cycle?.cycleId}/>
    <AssessmentStatusPies {...pies}/>
    <AssessmentLevelChart/>
    {pies.latest?.researchOnly&&pies.latest.ticker==="SMMT"&&
      <section style={{...section,margin:"0 0 22px",background:"#f7faf9"}} aria-label="First prospective 2026 FDA research prediction">
        <div style={{...label,marginBottom:7}}>FIRST PROSPECTIVE 2026 PDUFA PREDICTION PILOT</div>
        <h2 style={{fontSize:21,margin:"0 0 5px"}}>SMMT · HARMONi · NCT06396065</h2>
        <p data-testid="smmt-assessment-level" style={{fontSize:13,margin:"7px 0",fontWeight:700,color:"#285e56"}}>
          Assessment level: <strong>Level 1-style · Preliminary original forecast</strong> (not a validated engine level).
        </p>
        <p style={{fontSize:14,lineHeight:1.6,margin:"5px 0"}}>
          <strong>Predecision research call: CRL lean.</strong> Ivonescimab + chemotherapy
          for EGFR-mutated advanced nonsquamous NSCLC after EGFR TKI.
          FDA target action: <strong>November 14, 2026</strong>.
          Actual FDA decision: <strong>pending verification</strong>.
        </p>
        <p style={{fontSize:13,lineHeight:1.6,margin:"7px 0",color:"#516764"}}>
          Primary OS: HR 0.79, p=0.057 (not statistically significant).
          Follow-up OS: HR 0.76, nominal p=0.0151.
          FDA reportedly requires a statistically significant survival benefit;
          positive PFS and follow-up OS temper uncertainty.
          This is an uncalibrated, research-only directional forecast, not a completed
          completed owner review, validated FDA outcome probability or trading signal.
        </p>
        <p style={{fontSize:12,lineHeight:1.7,margin:"9px 0 0"}}>
          <a href="https://www.sec.gov/Archives/edgar/data/1599298/000159929826000090/smmt-20260930.htm" target="_blank" rel="noopener noreferrer">
            SEC evidence and FDA-review disclosures
          </a>
          {" · "}
          <a href="https://clinicaltrials.gov/study/NCT06396065" target="_blank" rel="noopener noreferrer">
            Exact ClinicalTrials.gov trial
          </a>
          {" · "}
          <a href="https://github.com/pdufa/pdufa-command-center/blob/main/new-platform/frontend/docs/2026-harmoni-first-prospective-forecast.md" target="_blank" rel="noopener noreferrer">
            Frozen assessment dossier
          </a>
        </p>
        <p style={{fontSize:12,lineHeight:1.5,color:"#895923",margin:"8px 0 0"}}>
          This pilot is outside the preserved 29-trial FOCUS list.
          The roster-gated automatic source worker was not started; no FOCUS membership changed.
        </p>
      </section>}
    <details data-testid="fixed-historical-level-3-archives"
      style={{border:"1px solid #d5dfe0",borderRadius:12,padding:"12px 14px",
        margin:"5px 0 22px",background:"#f8fbfa"}}>
      <summary style={{cursor:"pointer",fontWeight:800,color:"#2c5c54",fontSize:14}}>
        Archived Level 3 case studies · fixed original results (not affected by dropdown)
      </summary>
      <p style={{fontSize:12,color:"#536b66",lineHeight:1.6}}>
        These archived studies preserve their original Level 3 methodology; they must
        not change merely because another assessment level is selected in the historical chart.
      </p>
      <HistoricalTestingChart/>
      <October2026HistoricalAuditPanel/>
      <UltomirisHistoricalLevelThreePanel/>
    </details>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:10,margin:"15px 0 20px"}}>
      {[
        ["Legacy specialty-intake NCTs",FOCUS_SPECIALTY_SUMMARY.ncts],
        ["Stock tickers",FOCUS_SPECIALTY_SUMMARY.tickers],
        ["Mapped FDA cycles",FOCUS_SPECIALTY_SUMMARY.mappedApplicationCycles],
        ["Specialty profiles",CLINICAL_SPECIALTY_PROFILES.length],
        ["Partial clinical dimensions",FOCUS_SPECIALTY_SUMMARY.partialClinicalDimensions],
        ["Owner-reviewed trials",FOCUS_SPECIALTY_SUMMARY.ownerReviewedTrials]
      ].map(([name,number])=><div key={String(name)} style={{...section,padding:15}}>
        <div style={{fontSize:11,color:"#4f6969"}}>{name}</div><strong style={{fontSize:27}}>{number}</strong>
      </div>)}
    </div>
    <div style={{...section,marginBottom:18,background:"#fff8ea",borderColor:"#d8ae6f"}}>
      <strong>Research-only checkpoint — not a completed trial assessment</strong>
      <p style={{fontSize:13,lineHeight:1.6,margin:"7px 0 0"}}>
        The older {FOCUS_SPECIALTY_SUMMARY.ncts}-NCT specialty-intake snapshot is in this queue.
        The {FOCUS_SPECIALTY_SUMMARY.partialClinicalDimensions} specialty positions are authored research interpretations,
        not yet checked and accepted by the owner. Owner-reviewed completions: 0 recorded.
        For the FOCUS research queue only: approved numerical FDA forecasts: 0.
        The validated production engine remains <strong>ABSTAIN</strong>;
        certainty remains <strong>NOT VALIDATED</strong>.
        Separate provisional approval/CRL research calls are listed above and do not
        enter validated production predictions or accuracy. Roster snapshot: {FOCUS_SPECIALTY_SUMMARY.rosterAsOf}.
      </p>
      <p style={{fontSize:13,margin:"9px 0 0"}}>
        <Link href="/api/focus-assessment-intake" style={{color:"#08695c",fontWeight:750}}>Download older 29-trial specialty intake manifest</Link>
        {" · "}<Link href="/predictions" style={{color:"#08695c"}}>Back to FDA predictions</Link>
      </p>
    </div>
    <div style={{display:"grid",gridTemplateColumns:"minmax(0,1fr)",gap:17}}>
      <section style={section} aria-label="All FOCUS research intake trials">
        <h2 style={{fontSize:21,margin:"0 0 4px"}}>Earlier specialty intake snapshot · {FOCUS_SPECIALTY_SUMMARY.ncts} exact-NCT records</h2>
        <p style={{color:"#5d7270",fontSize:13,margin:"0 0 12px"}}>
          Select any row for its exact trial's clinical subspecialty questions and source-linked dossier.
          Each row is a research intake entry, not a prediction.
        </p>
        <div style={{overflowX:"auto"}}>
          <table style={{borderCollapse:"collapse",width:"100%",minWidth:650,fontSize:13}}>
            <thead><tr style={{background:"#eaf3ef",textAlign:"left"}}>
              {["Ticker","Exact NCT","Reported application cycle(s)","Partial evidence dimensions","Assessment level","Clinical review"].map(h=><th key={h} style={{padding:"11px 9px",borderBottom:"2px solid #a3c7bb"}}>{h}</th>)}
            </tr></thead>
            <tbody>{FOCUS_SPECIALTY_ASSESSMENT_QUEUE.map(item=><tr key={item.nct} style={{background:item.nct===selected?.nct?"#e3f7ec":"transparent"}}>
              <td style={{padding:"10px 9px",borderBottom:"1px solid #d5e4df"}}><strong>{item.ticker}</strong></td>
              <td style={{padding:"10px 9px",borderBottom:"1px solid #d5e4df"}}><Link style={{fontWeight:700,color:"#086b60"}} href={link(item.nct)}>{item.nct}</Link></td>
              <td style={{padding:"10px 9px",borderBottom:"1px solid #d5e4df"}}>{item.applications.length?item.applications.map(a=>a.drug+" — "+a.indication).join(" / "):"Application mapping missing"}</td>
              <td style={{padding:"10px 9px",borderBottom:"1px solid #d5e4df"}}>{item.applications.reduce((n,a)=>n+a.partialCaseDimensions,0)} · research only</td>
              <td style={{padding:"10px 9px",borderBottom:"1px solid #d5e4df",fontWeight:700,color:"#6d7772"}}>Not yet assessed</td>
              <td style={{padding:"10px 9px",borderBottom:"1px solid #d5e4df",color:"#8b5b20",fontWeight:700}}>OWNER NOT REVIEWED</td>
            </tr>)}</tbody>
          </table>
        </div>
      </section>
      {selected&&<section style={section} aria-label={"Selected trial "+selected.nct}>
        <span style={label}>SELECTED EXACT TRIAL</span>
        <h2 style={{margin:"7px 0",fontSize:24}}>{selected.ticker} · {selected.nct}</h2>
        <p style={{color:"#496765",marginTop:2}}>{selected.company} · <a href={selected.registryUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov original study</a></p>
        <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center",marginBottom:15}}>
          <span style={badge}>PHASE / STATUS: VERIFY AT SOURCE</span>
          <span style={badge}>ASSESSMENT LEVEL: NOT YET ASSESSED</span>
          <span style={badge}>ASSESSMENT: INSUFFICIENT VERIFIED EVIDENCE</span>
          <span style={badge}>FDA PREDICTION: ABSTAIN</span>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(220px,1fr))",gap:10,marginBottom:15}}>
          {[
            ["Roster-recorded FDA status",selected.reportedFilingStatus??"Not recorded"],
            ["Roster-recorded PDUFA date",selected.recordedPdufaDate??"Not recorded"],
            ["FOCUS acceptance checks requiring review",String(selected.reviewRequiredGates)],
            ["FOCUS acceptance checks with missing evidence",String(selected.missingEvidenceGates)]
          ].map(([title,value])=><div key={title} style={{padding:13,background:"#f4f9f6",borderRadius:9}}>
            <div style={{fontSize:11,color:"#5d706a"}}>{title}</div>
            <strong style={{fontSize:14,overflowWrap:"anywhere"}}>{value}</strong>
          </div>)}
        </div>
        <h3 style={{fontSize:18}}>Select an exact FDA application cycle</h3>
        <div style={{display:"flex",flexWrap:"wrap",gap:10,marginBottom:17}}>
          {selected.applications.map(app=><Link key={app.cycleId} href={link(selected.nct,app.cycleId)} style={{padding:"10px 12px",border:"1px solid "+(app.cycleId===cycle?.cycleId?"#007e68":"#bdcfc9"),borderRadius:8,background:app.cycleId===cycle?.cycleId?"#dcf8eb":"#fff",color:"#135d52",fontSize:13,fontWeight:700}}>{app.drug} — {app.indication}</Link>)}
          {!selected.applications.length&&<p>No exact application-cycle mapping has been reconstructed. Do not infer one from the ticker.</p>}
        </div>
        {cycle&&<div style={{padding:"16px",border:"1px solid #bad4ca",background:"#f7fbf9",borderRadius:12}}>
          <span style={label}>PARTIAL CLINICAL SUBSPECIALTY DOSSIER</span>
          <h3 style={{fontSize:21,margin:"6px 0"}}>{cycle.drug} · {cycle.indication}</h3>
          <p style={{fontSize:13,lineHeight:1.6}}>
            <strong>Specialty:</strong> {specialty?.specialty??"Not mapped"}.
            <strong> Dated sponsor-reported stage:</strong> {cycle.recordedStage.replaceAll("_"," ")}.
            <strong> Dossier:</strong> {cycle.partialCaseDimensions} partial clinical dimensions;
            {cycle.sourceLinkedDimensions} with individual source URLs.
          </p>
          <p style={{fontSize:13}}>Review-cycle source (reported {cycle.sourceDate}):{" "}
            <a href={cycle.sourceUrl} target="_blank" rel="noopener noreferrer">Original issuer/regulatory reference</a>.
            Owner source and current-cycle reconciliation remains to be completed. No outside verifier is required.
          </p>
          {specialty&&<div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))",gap:10}}>
            {[
              ["Patient-important outcomes",specialty.meaningfulOutcomes],
              ["Disease phenotype and context",specialty.clinicalContext],
              ["Serious risks requiring review",specialty.seriousRisks],
              ["Subgroups requiring verification",specialty.subgroups],
              ["Central skeptical specialty question",specialty.coreChallenge]
            ].map(([title,detail])=><div key={title} style={{padding:12,background:"#fff",border:"1px solid #d4e4de",borderRadius:8}}>
              <strong style={{fontSize:13}}>{title}</strong>
              <p style={{fontSize:12,lineHeight:1.55,margin:"6px 0 0"}}>{detail}</p>
            </div>)}
          </div>}
          {fullCase&&<div style={{marginTop:15}}>
            <strong style={{fontSize:16}}>Seven partial scientific investigations — source review required</strong>
            <p style={{fontSize:13}}>{fullCase.medicalQuestion}</p>
            {fullCase.dimensions.map((d,i)=><details key={i} style={{padding:"12px 0",borderTop:"1px solid #d0e1d9"}}>
              <summary style={{cursor:"pointer",fontWeight:750,fontSize:14}}>{i+1}. {d.topic} · Owner not reviewed</summary>
              <div style={{fontSize:13,lineHeight:1.65,margin:"10px 0"}}>
                <p><strong>Research source summary:</strong> {d.observedClinicalEvidence}</p>
                <p><strong>Specialty-style interpretation:</strong> {d.specialistInterpretation}</p>
                <p><strong>Unresolved verification:</strong> {d.neededToResolve}</p>
                {d.sourceUrl?<p><a href={d.sourceUrl} target="_blank" rel="noopener noreferrer">Dated source{d.sourceDate?" ("+d.sourceDate+")":""}</a></p>:
                  <p><a href={fullCase.source} target="_blank" rel="noopener noreferrer">Dossier lead reference (specific finding unverified)</a></p>}
              </div>
            </details>)}
          </div>}
          <details style={{marginTop:16,padding:12,background:"#fff",borderRadius:8}}>
            <summary style={{cursor:"pointer",fontWeight:750}}>Ten disease-specific specialty research questions (not completed)</summary>
            <ol style={{paddingLeft:21}}>
              {tasks.map(task=><li key={task.id} style={{padding:"8px 0",fontSize:13}}>
                <strong>{task.prompt}</strong>
                <p>Required: {task.requiredEvidence}</p>
              </li>)}
            </ol>
          </details>
          <p style={{fontSize:12,color:"#526c63",lineHeight:1.6}}>
            Dossier links and interpretations are staged public-source research,
            not an owner-accepted review, full source-data reconciliation, clinical advice,
            or calibrated FDA outcome probability.
          </p>
        </div>}
      </section>}
    </div>
    <p style={{fontSize:12,color:"#58746c",lineHeight:1.6,marginTop:20}}>
      The queue contains the dated FOCUS research population, not proof of live trial eligibility or source freshness.
      Different NCTs can support the same FDA application; one NCT can support more than one distinct application.
      Do not count correlated evidence as independent validation or carry an approval from one indication to another.
    </p>
  </main>;
}
