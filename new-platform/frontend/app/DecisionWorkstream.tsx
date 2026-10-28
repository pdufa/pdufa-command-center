"use client";

import {useEffect, useState} from "react";
import type {AssessmentDetail, AssessmentStage} from "../lib/candidate-assessments";
import {assessDecisionWorkstream} from "../lib/decision-workstream";
import type {ReviewedDecisionEvidence} from "../lib/decision-workstream";
import {parseReviewedDecisionManifest,validateDecisionIdentity} from "../lib/decision-reviewed-manifest";

type Props={exactKey:string; programId:string; trialId:string; ticker:string; stage:AssessmentStage; detail:AssessmentDetail|null};
type Sources={key:string; historical:unknown; main:unknown; reviewed:ReviewedDecisionEvidence|null; errors:string[]};

export default function DecisionWorkstream({exactKey,programId,trialId,ticker,stage,detail}:Props) {
  const key=JSON.stringify([exactKey,programId,trialId,ticker,stage]);
  const [sources,setSources]=useState<Sources|null>(null);
  useEffect(()=>{
    const controller=new AbortController();
    setSources(null);
    async function load() {
      const errors:string[]=[];
      const read=async(url:string,label:string)=>{
        try {
          const response=await fetch(url,{cache:"no-store",signal:controller.signal});
          if(!response.ok)throw new Error("unavailable");
          return await response.json() as unknown;
        } catch { errors.push(label+" source unavailable; no evidence inferred"); return null; }
      };
      const query=new URLSearchParams({stage,identity:exactKey});
      const expected={exactKey,programId,trialId,ticker,stage};
      let identityValid=false;try{validateDecisionIdentity(expected);identityValid=true;}catch{}
      const evidenceQuery=new URLSearchParams({stage,identity:exactKey,trialId,ticker});
      const [historical,main,rawReviewed]=await Promise.all([
        read("/api/hop/readiness","Historical FDA"),
        stage!=="PIPELINE" && /^PDUFA-\d{6,}$/.test(programId)
          ? read("/api/review/program-decision-readiness/"+encodeURIComponent(programId)+"?"+query,"MAIN")
          : Promise.resolve(null),
        identityValid?read("/api/decision-evidence/"+encodeURIComponent(programId)+"?"+evidenceQuery,"Reviewed evidence"):Promise.resolve(null),
      ]);
      let reviewed:ReviewedDecisionEvidence|null=null;
      if(rawReviewed!=null)try{
        if(typeof rawReviewed!=="object"||!("manifestSha256" in rawReviewed)||typeof rawReviewed.manifestSha256!=="string"||!/^[a-f0-9]{64}$/.test(rawReviewed.manifestSha256))throw new Error("Fingerprint missing");
        reviewed=parseReviewedDecisionManifest(rawReviewed,expected);
      }catch{errors.push("Reviewed evidence identity or format could not be verified; records withheld");}
      if(!controller.signal.aborted)setSources({key,historical,main,reviewed,errors});
    }
    void load();
    return ()=>controller.abort();
  },[key,programId,exactKey,stage]);
  // Effects run after render: withhold old trial/stage responses immediately.
  const current=sources?.key===key?sources:null;
  const result=assessDecisionWorkstream({exactKey,programId,trialId,ticker,stage},detail,current?.historical,current?.main,current?.reviewed);
  const archive=result.historicalSource;
  const science=result.scienceInvestigation;
  const groups=result.stages.filter(s=>s.name!=="Identity");
  const readyGroups=groups.filter(s=>s.issues.length===0&&(s.status==="EVIDENCE_READY_FOR_REVIEW"||s.status==="RESEARCH_ONLY")).length;
  const dossier=current?.reviewed?.scienceDossier;
  const scienceReady=result.stages.find(s=>s.name==="SCIENCE")?.status==="EVIDENCE_READY_FOR_REVIEW";
  return <details className="assessment-ledger" aria-label="Historical FDA PDUFA comparisons">
    <summary>SCIENCE → Historical FDA → OUTCOME → MAIN → DECISION · {result.status}</summary>
    <p>{programId || "Program identity unavailable"} · {trialId || "Trial identity unavailable"} · {stage.replaceAll("_"," ")}</p>
    <p><strong>Historical PDUFA comparisons:</strong> {result.historicalMatches} reviewed matches connected to this trial.</p>
    <p>SCIENCE requires 20 investigation levels, 40 source-cited assessments and eight scientific subject layers. OUTCOME requires an independent review and historical validation. The existing seven-category candidate scores do not satisfy those reviews.</p>
    <div aria-label="Separate system evidence progress">
      <p><strong>SCIENCE:</strong> {science.readiness?`${science.completedAssessments}/40 assessments and ${science.completedLevels}/20 levels reviewed · ${science.coveredLayers}/8 layers represented · recorded at ${science.readiness.asOf}.`:"Completion not measured; a source-cited investigation dossier is required."} Current ready-for-analysis grade: {scienceReady?science.readyForAnalysis.replaceAll("_"," "):"NOT READY"}. Current reluctant assessment: {scienceReady?science.reluctantAssessment.replaceAll("_"," "):"WITHHELD"}.</p>
      <p><strong>OUTCOME:</strong> {result.stages.find(s=>s.name==="OUTCOME")?.status.replaceAll("_"," ")}. Completion percentage unavailable without an independently reviewed, complete historical denominator.</p>
      <p><strong>MAIN:</strong> {result.stages.find(s=>s.name==="MAIN")?.status.replaceAll("_"," ")}. Current-trial market, financing and risk evidence remain separate from the dated platform acceptance baseline.</p>
      <p><strong>DECISION integration:</strong> {readyGroups}/{groups.length} evidence prerequisite groups ready for research review. This counts reviewed prerequisite groups, not project completion or prediction accuracy. Estimated completion time: unavailable without comparable verified progress observations.</p>
    </div>
    <table><caption>Decision evidence readiness for this exact trial</caption><thead><tr><th>Evidence</th><th>Status</th><th>Remaining requirements</th></tr></thead>
      <tbody>{result.stages.map(s=><tr key={s.name}><th scope="row">{s.name}</th><td>{s.status.replaceAll("_"," ")}</td><td>{s.issues.length?<ul>{s.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>:"Evidence requires independent review"}</td></tr>)}</tbody>
    </table>
    <p role="status">{!current?"Checking read-only evidence connections…":archive
      ? `Archived FDA source progress: ${archive.publishedLetters ?? "unknown"} published CRL records · ${archive.approvedApplications ?? "unknown"} approved applications · ${archive.independentlyVerifiedReviewCycles} independently verified review cycles · ${archive.modelEligibleReviewCycles} model-eligible cycles. Source checked ${archive.checkedAt}.`
      : "Historical FDA source progress unavailable; counts withheld."}</p>
    <p>Archive counts cover the source collection, not this trial or a complete historical outcome denominator. Close analogues require matched disease subtype, indication, mechanism and primary endpoint, with independently reviewed pre-cutoff sources.</p>
    {[...new Set([...(current?.errors ?? []),...result.sourceIssues])].map(issue=><p key={issue} className="subtle">{issue}</p>)}
    {dossier&&science.readiness&&<details aria-label="Scientific trial dossier and original sources"><summary>Scientific trial dossier · {science.completedAssessments}/40 reviewed assessments</summary>
      <p>{dossier.drug} · {dossier.indication} · Company CIK {dossier.companyCik} · FDA application {dossier.fdaApplication||"not reconciled"} · As of {dossier.asOf}</p>
      <p>{science.warnings.join(" ")}</p>
      <p><strong>Adversarial challenge:</strong> {science.adversarialReviewStatus.replaceAll("_"," ")}. A recorded reviewer declaration still requires independent verification.</p>
      {dossier.levels.map((level,i)=><details key={level.id+":"+i}><summary>{level.label} · {dossier.layers.find(layer=>layer.id===level.layerId)?.label||"Subject layer missing"}</summary>
        {level.assessments.map((assessment,j)=><article key={assessment.id+":"+j}><h4>{assessment.id} · {assessment.status}</h4>
          <p><strong>Critical evaluation:</strong> {assessment.criticalEvaluation||"Missing"}</p><p><strong>Uncertainty:</strong> {assessment.uncertainty||"Missing"}</p>
          <p><strong>Approval direction:</strong> {assessment.approvalDirection?.replaceAll("_"," ")||"UNDETERMINED"}. {assessment.directionRationale||"Source-grounded direction rationale missing."} This is a qualitative reviewer inference.</p>
          <p>Reviewer: {assessment.reviewer||"not recorded"} · Unresolved critical findings: {assessment.unresolvedCriticalFindings}</p>
          <ul>{assessment.sources.map((source,k)=><li key={source.url+":"+k}><a href={source.url} target="_blank" rel="noopener noreferrer">Original source</a> · Published {source.publishedAt} · Observed {source.observedAt} · {source.independentlyReviewed?"Independent review declared":"Independent review pending"}</li>)}</ul>
        </article>)}
      </details>)}
      {dossier.adversarialReview&&<details aria-label="Supporting and opposing scientific arguments"><summary>Strongest supporting and opposing arguments · {science.adversarialReviewStatus.replaceAll("_"," ")}</summary>
        <p>Declared reviewer: {dossier.adversarialReview.reviewer||"Missing"} · Reviewed {dossier.adversarialReview.reviewedAt} · Unresolved critical findings: {dossier.adversarialReview.unresolvedCriticalFindings}. Independence is not authenticated by this record.</p>
        {(["supporting","opposing"] as const).map(side=><article key={side}><h4>{side==="supporting"?"Supporting approval":"Opposing approval"}</h4>
          <p>{dossier.adversarialReview?.[side].rationale||"Missing argument"}</p>
          <p>Referenced assessments: {dossier.adversarialReview?.[side].assessmentIds.join(", ")||"Missing"}</p>
          <ul>{dossier.adversarialReview?.[side].sources.map((source,k)=><li key={source.url+":"+k}><a href={source.url} target="_blank" rel="noopener noreferrer">Challenge source</a> · Published {source.publishedAt} · Observed {source.observedAt} · {source.independentlyReviewed?"Independent review declared":"Independent review pending"}</li>)}</ul>
        </article>)}
      </details>}
    </details>}
    <p><strong>Predicted outcome: {result.prediction.predictedOutcome.replaceAll("_"," ")}</strong>. This is an abstention, not a third FDA regulatory outcome. Reliable prediction readiness: {result.prediction.readyForReliablePrediction?"Ready":"Not ready"}.</p>
    <p>Nonapproval probability: unavailable. Prediction confidence: unavailable. Scientific review-record completeness is separate from prediction probability and confidence.</p>
    <p><strong>Approval probability: unavailable. Model validation: incomplete. Trading authorization: disabled.</strong> Historical frequencies and synthetic regression fixtures are not validated prediction accuracy.</p>
  </details>;
}
