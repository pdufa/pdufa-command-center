"use client";

import {useCallback,useEffect,useMemo,useRef,useState} from "react";
import type {MonitorSnapshot,Stage} from "../../lib/main-install-progress";
import focusRoster from "../../data/p3PostDataActive.json";
import styles from "./Console.module.css";

type TickerGroup={ticker:string;company:string;ncts:string[]};
const groups:TickerGroup[]=Array.from(new Set(focusRoster.records.map(row=>row.ticker)))
  .sort((a,b)=>a.localeCompare(b))
  .map(ticker=>{
    const rows=focusRoster.records.filter(row=>row.ticker===ticker);
    return {ticker,company:rows[0]?.company??ticker,ncts:rows.map(row=>row.nct)};
  });
type Status="VERIFIED"|"COMPLETE"|"PENDING"|"BLOCKED"|"FAILED"|"UNKNOWN";
const stateName=(state:string|undefined)=>state==="COMPLETE"?"VERIFIED":state??"UNKNOWN";
const asDate=(value:string|undefined)=>{
  if(!value)return "Unavailable";
  const date=new Date(value);
  return Number.isNaN(date.valueOf())?"Unavailable":date.toLocaleString();
};
const value=(input:unknown)=>input===null||input===undefined?"not recorded":String(input);
const numeric=(input:unknown)=>typeof input==="number"&&Number.isFinite(input)?input:null;
function StatusPill({state}:{state:Status|string|undefined}){
  const title=stateName(state);
  return <span className={styles.pill} data-state={title}>{title}</span>;
}
function MiniProgress({stage}:{stage:Stage|undefined}){
  const done=stage?.percent??0;
  return <div className={styles.progressBox}>
    <div className={styles.progressRing} style={{background:stage?
      "conic-gradient(#21e9a4 "+done+"%, #344f61 "+done+"% 100%)":undefined}}>
      <span>{stage?done+"%":"—"}</span>
    </div>
    <div className={styles.progressCopy}>
      <strong>{stage?.title??"Waiting for verified checkpoint data"}</strong>
      <small>{stage?stage.verified+" / "+stage.total+" verified":"No live status available"}</small>
      <StatusPill state={stage?.status}/>
    </div>
  </div>;
}
export default function PrecisionMonitoringConsole(){
  const [snapshot,setSnapshot]=useState<MonitorSnapshot|null>(null);
  const [error,setError]=useState("");
  const [fetching,setFetching]=useState(false);
  const [ticker,setTicker]=useState(groups.find(g=>g.ticker==="CYTK")?.ticker??groups[0]?.ticker??"");
  const buttons=useRef<Record<string,HTMLButtonElement|null>>({});
  const refresh=useCallback(async()=>{
    setFetching(true);
    try{
      const response=await fetch("/api/main/installation-progress",{cache:"no-store",credentials:"same-origin"});
      if(!response.ok)throw new Error(response.status===401?"Sign in to view authenticated operational telemetry.":"Operational telemetry could not be retrieved (HTTP "+response.status+").");
      const next:MonitorSnapshot=await response.json();
      if(next.schemaVersion!==1||!Array.isArray(next.stages)||!Array.isArray(next.trials)||!next.overall?.total)
        throw new Error("The monitoring response did not pass schema checks.");
      setSnapshot(next);
      setError("");
    }catch(cause){
      setError(cause instanceof Error?cause.message:"Operational telemetry unavailable.");
      setSnapshot(null);
    }finally{setFetching(false);}
  },[]);
  useEffect(()=>{
    void refresh();
    const timer=window.setInterval(()=>{
      if(document.visibilityState==="visible")void refresh();
    },45000);
    return ()=>window.clearInterval(timer);
  },[refresh]);
  useEffect(()=>{
    buttons.current[ticker]?.scrollIntoView({behavior:"smooth",block:"nearest",inline:"center"});
  },[ticker]);
  const selected=groups.find(g=>g.ticker===ticker)??groups[0];
  const selectedTrials=useMemo(()=>snapshot?.trials.filter(t=>t.ticker===ticker)??[],[snapshot,ticker]);
  const stage=(id:string)=>snapshot?.stages.find(s=>s.id===id);
  const combined=(ids:string[])=>{
    const checks=snapshot?.stages.filter(s=>ids.includes(s.id)).flatMap(s=>s.checks)??[];
    const verified=checks.filter(c=>c.status==="VERIFIED").length;
    return {verified,total:checks.length,percent:checks.length?Math.floor(verified*100/checks.length):null};
  };
  const first=combined(["pool","focus","infrastructure"]);
  const second=combined(["medical",...Array.from({length:12},(_,i)=>"advanced-"+(i+1))]);
  const third=combined(["predictions","certainty","calibration"]);
  const sourceRuns=numeric(snapshot?.signals.research?.finishedSourceRuns);
  const analysisSaved=numeric(snapshot?.signals.analysisNow?.completedSavedRuns);
  const revisionCount=numeric(snapshot?.signals.research?.immutableRevisions);
  const phase3=snapshot?.signals.scans?.phase3Ingestion as {state?:string;lastSuccessAt?:string}|undefined;
  const stream=snapshot?.signals.scans?.nctStream as {totalRuns?:number;failedRuns?:number}|undefined;
  const telegram=snapshot?.signals.alerts?.lastDelivery as {state?:string}|undefined;
  const registry=snapshot?.signals.scans?.registryWatch as {enabled?:boolean;lastCheckedAt?:string}|undefined;
  const monitoring=[
    ["Phase 3 ingestion",phase3?.state??"UNKNOWN","Last success: "+value(phase3?.lastSuccessAt)],
    ["Registry evidence",registry?.enabled?"PENDING":"UNKNOWN","Last check: "+value(registry?.lastCheckedAt)],
    ["NCT evidence runs",stream?.totalRuns!==undefined?"OBSERVED":"UNKNOWN","Runs: "+value(stream?.totalRuns)+" · failed: "+value(stream?.failedRuns)],
    ["Saved research runs",sourceRuns!==null&&sourceRuns>0?"OBSERVED":"UNKNOWN","Completed: "+value(sourceRuns)+" · revisions: "+value(revisionCount)],
    ["Analyze Now",analysisSaved!==null&&analysisSaved>0?"OBSERVED":"UNKNOWN","Saved runs: "+value(analysisSaved)],
    ["FDA / SEC / literature watches","UNKNOWN","Full cross-source monitoring not independently certified"],
    ["Telegram delivery",telegram?.state==="SENT"?"VERIFIED":"UNKNOWN","Last delivery: "+value(telegram?.state)]
  ];
  const advanced=snapshot?.stages.filter(s=>/^advanced-\d+$/.test(s.id))??[];
  const flow=[["New evidence","Source observations"],["Reanalysis","Saved research revision"],["Validation","Evidence and calibration gates"],["Alerts","Verified deliveries"],["Refresh","Live dashboard"]];
  const choose=(direction:number)=>{
    const index=Math.max(0,groups.findIndex(g=>g.ticker===ticker));
    setTicker(groups[(index+direction+groups.length)%groups.length]?.ticker??ticker);
  };
  return <div className={styles.console}>
    <header className={styles.hero}>
      <div className={styles.eyebrow}>PDUFA COMMAND CENTER · MAIN</div>
      <h1>PDUFA Precision Monitoring System</h1>
      <p>Deep Medical Intelligence · Installation Health · Evidence Monitoring · Prediction Readiness</p>
      <div className={styles.heroActions}>
        <span className={styles.liveWord}>Evidence-linked, read-only status</span>
        <button type="button" className={styles.refresh} onClick={()=>void refresh()} disabled={fetching}>
          {fetching?"Checking…":"↻ Check now"}
        </button>
      </div>
    </header>
    {error&&<p className={styles.warning} role="alert">{error} All unobserved indicators remain UNKNOWN.</p>}
    <section className={styles.metrics} aria-label="Current system indicators">
      <article className={styles.metric}>
        <small>System Health</small>
        <strong>{snapshot?.health.level??"UNKNOWN"}</strong>
        <span>{snapshot?.health.issues.length?String(snapshot.health.issues.length)+" unresolved issue(s)":"No live health verification when telemetry is absent"}</span>
      </article>
      <article className={styles.metric}>
        <small>Verified Checkpoints</small>
        <strong>{snapshot?snapshot.overall.verified+" / "+snapshot.overall.total:"— / —"}</strong>
        <span>{snapshot?snapshot.overall.percent+"% of fixed checkpoints":"Not yet retrieved"}</span>
      </article>
      <article className={styles.metric}>
        <small>Saved Evidence Runs</small>
        <strong>{sourceRuns===null?"Unknown":sourceRuns}</strong>
        <span>{revisionCount===null?"Saved revision history not verified":revisionCount+" source revisions observed"}</span>
      </article>
      <article className={styles.metric}>
        <small>Prediction Status</small>
        <strong className={styles.abstain}>ABSTAIN</strong>
        <span>FDA outcomes not independently calibrated</span>
      </article>
      <article className={styles.metric}>
        <small>Last Checked</small>
        <strong className={styles.metricDate}>{asDate(snapshot?.observedAt)}</strong>
        <span>Observation time, not certification date</span>
      </article>
    </section>
    <section className={styles.tickerPanel} aria-label="FOCUS ticker scroller">
      <div className={styles.sectionHeading}>
        <div><h2>FOCUS · Ticker Navigator</h2>
          <p>{groups.length} tickers · {focusRoster.records.length} source-listed trials · FOCUS roster {focusRoster.asOf}</p>
        </div>
        <div className={styles.railControls}>
          <button type="button" onClick={()=>choose(-1)} aria-label="Previous ticker">‹</button>
          <button type="button" onClick={()=>choose(1)} aria-label="Next ticker">›</button>
        </div>
      </div>
      <div className={styles.tickerRail} role="group" aria-label="Scrollable FOCUS tickers">
        {groups.map(g=><button key={g.ticker} type="button"
          ref={node=>{buttons.current[g.ticker]=node;}}
          className={styles.ticker}
          aria-pressed={g.ticker===ticker}
          onClick={()=>setTicker(g.ticker)}>
          <span className={styles.tickerIcon}>⌁</span>
          <strong>{g.ticker}</strong>
          <small>{g.ncts.length} {g.ncts.length===1?"trial":"trials"}</small>
        </button>)}
      </div>
      <div className={styles.selectedTrial}>
        <div className={styles.company}><strong>{selected?.ticker??"No ticker"}</strong><span>{selected?.company??""}</span>
          <small>{selected?.ncts.length??0} associated clinical trial(s)</small>
        </div>
        <div className={styles.trialList}>
          {(selected?.ncts??[]).map(nct=>{
            const trial=selectedTrials.find(t=>t.nct===nct);
            return <details key={nct} className={styles.trialCard}>
              <summary><span>◈ {nct}</span><span className={styles.trialInfo}>{trial?"Source review: "+trial.review+" · missing: "+trial.missing:"Evidence status unavailable"} ⌄</span></summary>
              <p>{trial?"Evidence pointers "+trial.pointers+"; independently verified "+trial.independentlyVerified+". Saved history: "+trial.sourceState+".":"This trial is in the dated FOCUS roster. Authenticated evidence is not yet loaded."}</p>
              <div className={styles.trialLinks}>
                <a href={"https://clinicaltrials.gov/study/"+nct} target="_blank" rel="noopener noreferrer">Original registry source</a>
                <a href="/focus">FOCUS trial workspace</a>
              </div>
            </details>;
          })}
        </div>
      </div>
    </section>
    <div className={styles.columns}>
      <section className={styles.panel} aria-label="End-to-end pipeline">
        <h2>System Pipeline (End-to-End)</h2>
        {[
          ["POOL",stage("pool"),"Master evidence inventory"],
          ["FOCUS",stage("focus"),"Trial identity and eligibility"],
          ["Deep Medical Intelligence",stage("medical"),"12-stage evidence analysis"],
          ["Prediction Engine",stage("predictions"),"Independent outcome modeling"],
          ["Certainty & Calibration",stage("calibration"),"Historical validation"]
        ].map(([name,s,description])=>{
          const st=s as Stage|undefined;
          return <div className={styles.pipelineRow} key={name as string}>
            <div><strong>{name as string}</strong><small>{description as string}</small></div>
            <StatusPill state={st?.status}/>
          </div>;
        })}
      </section>
      <section className={styles.panel} aria-label="Installation coverage">
        <h2>Installation Progress &amp; Stage Coverage</h2>
        <div className={styles.threeStages}>
          {[["Stage 1","Infrastructure · POOL · FOCUS",first],["Stage 2","Medical intelligence · 12 levels",second],["Stage 3","Prediction · certainty · calibration",third]].map(([name,detail,stats])=>{
            const item=stats as {verified:number;total:number;percent:number|null};
            return <div className={styles.stageCard} key={name as string}>
              <small>{name as string}</small>
              <strong>{item.percent===null?"—":item.percent+"%"}</strong>
              <span>{detail as string}</span>
              <small>{item.total?item.verified+" / "+item.total+" verified":"Unverified"}</small>
            </div>;
          })}
        </div>
        <p className={styles.hint}>Checkpoint completion is not FDA prediction accuracy. Missing evidence remains unfinished.</p>
      </section>
      <section className={styles.panel} aria-label="Live monitoring signals">
        <h2>Live Monitoring Signals</h2>
        {monitoring.map(([name,state,detail])=><div className={styles.signalRow} key={name}>
          <div><strong>{name}</strong><small>{detail}</small></div>
          <span className={styles.signalState} data-state={state}>{state}</span>
        </div>)}
      </section>
    </div>
    <div className={styles.columnsSecondary}>
      <section className={styles.panel} aria-label="12 analysis levels">
        <h2>12 Advanced Medical Analysis Levels</h2>
        {advanced.length===0?<p className={styles.hint}>Awaiting authenticated medical checkpoint evidence.</p>:
          <div className={styles.levelGrid}>{advanced.map(s=><div className={styles.levelCard} key={s.id}>
            <strong>{s.title}</strong><StatusPill state={s.status}/>
          </div>)}</div>}
      </section>
      <section className={styles.panel} aria-label="Prediction governance">
        <h2>Prediction Governance</h2>
        {["Approval probability","CRL risk","Review-delay risk"].map(name=><div className={styles.governanceRow} key={name}><span>{name}</span><strong>Not released</strong></div>)}
        <div className={styles.certainty}>Certainty Rating: NOT VALIDATED</div>
        <p className={styles.hint}>Predictions remain ABSTAIN until independent evidence, historical backtests and calibration pass their release gates.</p>
      </section>
    </div>
    <section className={styles.feedback} aria-label="Automated feedback workflow">
      <h2>Automated Feedback Loop</h2>
      <div className={styles.feedbackRail}>
        {flow.map(([title,detail],i)=><div className={styles.feedbackStep} key={title}>
          <strong>{title}</strong><small>{detail}</small>
          {i<flow.length-1&&<span aria-hidden="true">→</span>}
        </div>)}
      </div>
      <p>Workflow architecture only. Automatic reanalysis, delivery and persistence are not confirmed without saved backend events.</p>
    </section>
  </div>;
}
