"use client";
import {useState} from "react";
import type {EvidenceRun,EvidenceTest,TestState} from "../../lib/prediction-source-tests";
import {TEST_NAMES} from "../../lib/prediction-source-tests";
import styles from "./FocusPredictionNavigator.module.css";

const stateText:Record<TestState,string>={
  SOURCE_FIELD_PRESENT:"SOURCE FIELD FOUND — NOT REVIEWED",
  SOURCE_FIELD_MISSING:"MISSING FROM REGISTRY RESPONSE",
  INDEPENDENT_REVIEW_REQUIRED:"INDEPENDENT REVIEW REQUIRED",
  NOT_AUTOMATED:"NOT AUTOMATED"
};

export default function PredictionSourceRunControls({nct}:{nct:string}){
  const [busy,setBusy]=useState<"FULL"|"SINGLE"|null>(null);
  const [next,setNext]=useState(0);
  const [tests,setTests]=useState<EvidenceTest[]>([]);
  const [lastRun,setLastRun]=useState<EvidenceRun|null>(null);
  const [error,setError]=useState("");
  async function execute(mode:"FULL"|"SINGLE"){
    if(busy||(mode==="SINGLE"&&next>=TEST_NAMES.length))return;
    const selected=mode==="SINGLE"?next:undefined;
    setBusy(mode);
    setError("");
    try{
      const response=await fetch("/api/predictions/source-analysis",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({nct,mode,testIndex:selected}),
        cache:"no-store"
      });
      const raw:unknown=await response.json();
      const result=raw&&typeof raw==="object"&&!Array.isArray(raw)?raw as Record<string,unknown>:{};
      if(!response.ok)throw Error(typeof result.error==="string"?result.error:"Source inspection could not start");
      const data=result as EvidenceRun;
      if(data.nct!==nct||data.mode!==mode||!Array.isArray(data.tests)||
         data.tests.length!==(mode==="FULL"?TEST_NAMES.length:1)||
         data.tests.some(t=>!Number.isInteger(t.index)||t.index<0||t.index>=TEST_NAMES.length))
        throw Error("Source inspection returned an invalid trial or test sequence.");
      setTests(current=>mode==="FULL"?data.tests:
        [...current.filter(t=>t.index!==data.tests[0].index),...data.tests].sort((a,b)=>a.index-b.index));
      setLastRun(data);
      setNext(mode==="FULL"?TEST_NAMES.length:next+1);
    }catch(cause){
      setError(cause instanceof Error?cause.message:"Source inspection failed");
    }finally{
      setBusy(null);
    }
  }
  function reset(){
    if(busy)return;
    setNext(0);setTests([]);setLastRun(null);setError("");
  }
  return <section className={styles.analysisPanel} aria-label={"Run FDA evidence analyses for "+nct}>
    <div className={styles.analysisIntro}>
      <div>
        <strong>Start an analysis for {nct}</strong>
        <p>These controls actively inspect the official ClinicalTrials.gov record. All 12 research checks run for <em>this trial only</em>.
           Full clinical/FDA adjudication and validated outcome prediction are not operational.</p>
      </div>
      <span className={styles.analysisProgress}>{tests.length} / {TEST_NAMES.length} checks displayed</span>
    </div>
    <div className={styles.analysisButtons}>
      <button className={styles.analysisPrimary} disabled={busy!==null} type="button"
        onClick={()=>void execute("FULL")}>
        {busy==="FULL"?"Inspecting source…":"Start Full Analysis — 12 Checks"}
      </button>
      <button className={styles.analysisSecondary} disabled={busy!==null||next>=TEST_NAMES.length} type="button"
        onClick={()=>void execute("SINGLE")}>
        {busy==="SINGLE"?"Running test…":next<TEST_NAMES.length?"Run One Test — #"+(next+1):"All 12 tests displayed"}
      </button>
      <button className={styles.analysisReset} disabled={busy!==null||(!tests.length&&!error)} type="button" onClick={reset}>
        Reset test sequence
      </button>
    </div>
    {next<TEST_NAMES.length&&<p className={styles.analysisNext}>Next individual test: <strong>{next+1}. {TEST_NAMES[next]}</strong></p>}
    {error&&<p className={styles.analysisError} role="alert">{error} <span>No prediction was generated.</span></p>}
    {lastRun&&<p className={styles.analysisRunInfo} role="status">
      {lastRun.mode==="FULL"?"Full source-check pass":"One individual source test"} executed for <strong>{lastRun.nct}</strong> at{" "}
      {new Date(lastRun.executedAt).toLocaleString()}.{" "}
      <a href={lastRun.registrySourceUrl} target="_blank" rel="noopener noreferrer">Inspect official registry record</a>.
      Results are an unsaved browser-session view, not a persisted medical dossier.
    </p>}
    {tests.length>0&&<div className={styles.analysisResults} aria-label="Individual scientific evidence checks">
      {tests.map(t=><details key={t.key} className={styles.analysisTest} open={t.index===(lastRun?.mode==="SINGLE"?next-1:-1)}>
        <summary>
          <span>{t.index+1}. {t.title}</span>
          <small data-source-state={t.state}>{stateText[t.state]}</small>
        </summary>
        <div>
          <p><strong>What the source actually showed:</strong> {t.summary}</p>
          <p><strong>Next scientific verification:</strong> {t.nextRequired}</p>
          <a href={t.sourceUrl} target="_blank" rel="noopener noreferrer">Review the source</a>
        </div>
      </details>)}
    </div>}
    {tests.length>0&&<p className={styles.analysisWarning}>
      <strong>FDA Approval: ABSTAIN · CRL: ABSTAIN · Review Delay: ABSTAIN · Certainty: NOT VALIDATED.</strong>
      {" "}Recorded registry fields and source pointers do not establish clinical success or FDA approval odds.
      Even a completed 12-check sequence is not a full validated prediction.
    </p>}
  </section>;
}
