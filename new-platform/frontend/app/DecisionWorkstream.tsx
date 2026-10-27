"use client";

import {useEffect, useState} from "react";
import type {AssessmentDetail, AssessmentStage} from "../lib/candidate-assessments";
import {assessDecisionWorkstream} from "../lib/decision-workstream";

type Props={exactKey:string; programId:string; trialId:string; ticker:string; stage:AssessmentStage; detail:AssessmentDetail|null};
type Sources={key:string; historical:unknown; main:unknown; errors:string[]};

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
      const [historical,main]=await Promise.all([
        read("/api/hop/readiness","Historical FDA"),
        stage!=="PIPELINE" && /^PDUFA-\d{6,}$/.test(programId)
          ? read("/api/review/program-decision-readiness/"+encodeURIComponent(programId)+"?"+query,"MAIN")
          : Promise.resolve(null),
      ]);
      if(!controller.signal.aborted)setSources({key,historical,main,errors});
    }
    void load();
    return ()=>controller.abort();
  },[key,programId,exactKey,stage]);
  // Effects run after render: withhold old trial/stage responses immediately.
  const current=sources?.key===key?sources:null;
  const result=assessDecisionWorkstream({exactKey,programId,trialId,ticker,stage},detail,current?.historical,current?.main);
  const archive=result.historicalSource;
  return <details className="assessment-ledger" aria-label="Historical FDA PDUFA comparisons">
    <summary>SCIENCE → Historical FDA → OUTCOME → MAIN → DECISION · {result.status}</summary>
    <p>{programId || "Program identity unavailable"} · {trialId || "Trial identity unavailable"} · {stage.replaceAll("_"," ")}</p>
    <p><strong>Historical PDUFA comparisons:</strong> {result.historicalMatches} reviewed matches connected to this trial.</p>
    <p>SCIENCE and OUTCOME each require an independent 20-level review. The existing seven-category candidate scores do not satisfy those reviews.</p>
    <table><caption>Decision evidence readiness for this exact trial</caption><thead><tr><th>Evidence</th><th>Status</th><th>Remaining requirements</th></tr></thead>
      <tbody>{result.stages.map(s=><tr key={s.name}><th scope="row">{s.name}</th><td>{s.status.replaceAll("_"," ")}</td><td>{s.issues.length?<ul>{s.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>:"Evidence requires independent review"}</td></tr>)}</tbody>
    </table>
    <p role="status">{!current?"Checking read-only evidence connections…":archive
      ? `Archived FDA source progress: ${archive.publishedLetters ?? "unknown"} published CRL records · ${archive.approvedApplications ?? "unknown"} approved applications · ${archive.independentlyVerifiedReviewCycles} independently verified review cycles · ${archive.modelEligibleReviewCycles} model-eligible cycles. Source checked ${archive.checkedAt}.`
      : "Historical FDA source progress unavailable; counts withheld."}</p>
    <p>Archive counts cover the source collection, not this trial or a complete historical outcome denominator. Close analogues require matched disease subtype, indication, mechanism and primary endpoint, with independently reviewed pre-cutoff sources.</p>
    {[...new Set([...(current?.errors ?? []),...result.sourceIssues])].map(issue=><p key={issue} className="subtle">{issue}</p>)}
    <p><strong>Approval probability: unavailable. Model validation: incomplete. Trading authorization: disabled.</strong> Historical frequencies and synthetic regression fixtures are not validated prediction accuracy.</p>
  </details>;
}
