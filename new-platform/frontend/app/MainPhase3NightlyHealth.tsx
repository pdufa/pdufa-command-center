"use client";

import {useCallback, useEffect, useRef, useState} from "react";
import {parseNightlyHealth, unavailableNightlyHealth, WORKFLOW_HISTORY_URL,
  type NightlyHealth, type NightlyHealthState} from "../lib/main-phase3-nightly-health";
import styles from "./MainPhase3NightlyHealth.module.css";

const LABEL:Record<NightlyHealthState,string>={
  FULL_SCAN_CONFIRMED:"Full scheduled scan completed; research artifact confirmed",
  FULL_SCAN_STALE:"Last full scan completed, but the result is stale",
  FULL_SCAN_FAILED:"The last full scheduled scan did not complete successfully",
  FULL_SCAN_RUNNING:"Scheduled research scan is in progress or queued",
  REPORT_ARTIFACT_MISSING:"Job completed, but the required research artifact is missing",
  NO_FULL_SCHEDULED_RUN_YET:"No full scheduled research scan observed yet",
  SOURCE_UNAVAILABLE:"Scheduled scan status cannot be verified from GitHub",
};

const formatted=(value:string|null)=>{
  if(!value)return "Not yet observed";
  const instant=new Date(value);
  if(!Number.isFinite(instant.getTime()))return "Unverified";
  return new Intl.DateTimeFormat("en-US",{
    timeZone:"America/Los_Angeles",month:"short",day:"numeric",year:"numeric",
    hour:"numeric",minute:"2-digit",timeZoneName:"short"
  }).format(instant);
};

/** Refreshable CURRENT job status, separate from archival gate scores. */
export default function MainPhase3NightlyHealth(){
  const [health,setHealth]=useState<NightlyHealth|null>(null);
  const [loading,setLoading]=useState(true);
  const request=useRef(0);
  const refresh=useCallback(async()=>{
    const id=++request.current;
    setLoading(true);
    try{
      const res=await fetch("/api/main-phase3-nightly-health",{cache:"no-store"});
      if(!res.ok)throw new Error("GitHub source status unavailable");
      const status=parseNightlyHealth(await res.json());
      if(id===request.current)setHealth(status);
    }catch{
      if(id===request.current)setHealth(unavailableNightlyHealth());
    }finally{
      if(id===request.current)setLoading(false);
    }
  },[]);
  useEffect(()=>{
    void refresh();
    return ()=>{request.current++;};
  },[refresh]);

  return <section className={styles.health} aria-label="MAIN nightly source scan status">
    <div className={styles.heading}>
      <div>
        <h3>Nightly research scan · GitHub status</h3>
        <p>Scheduled near 8:00 PM Pacific daily · source status checked separately from the archived scores</p>
      </div>
      <button type="button" onClick={()=>void refresh()} disabled={loading}>
        {loading?"Checking…":"Refresh status"}
      </button>
    </div>
    <p className={styles.status} role="status" aria-live="polite">
      <strong>{loading&&!health?"Checking scheduled run and artifact…":
        health?LABEL[health.state]:"Status has not been checked"}</strong>
    </p>
    {health&&<>
      <p className={styles.small}>
        Last scheduled trigger observed: {formatted(health.latestScheduleObservedAtUtc)}.
        {health.intentionallySkippedAlternates>0&&
          " "+health.intentionallySkippedAlternates+" intentional DST alternate(s) skipped in checked history."}
      </p>
      {health.runId&&<p className={styles.small}>
        Selected full-run attempt: #{health.runId} ·
        {health.jobCompletedAtUtc?" completed "+formatted(health.jobCompletedAtUtc):
          " started "+formatted(health.runStartedAtUtc)}.
        {" "}<a href={health.runUrl||WORKFLOW_HISTORY_URL} rel="noopener noreferrer" target="_blank">
          Inspect this exact GitHub run
        </a>
      </p>}
      <p className={styles.small}>Checked: {formatted(health.checkedAtUtc)}.
        {health.artifactConfirmed?" Research artifact present; these are job checks, not verified candidate qualifications.":
          " No source-backed complete scan is asserted by this status."}
      </p>
    </>}
    <p className={styles.small}>
      <a href={WORKFLOW_HISTORY_URL} rel="noopener noreferrer" target="_blank">View all scheduled and manual GitHub runs</a>.
      The daily scan does not automatically update the dated historical scorecard, Pipeline, GEM JR, GEM, or FS/FA presets.
      A delayed GitHub schedule or a skipped daylight-saving alternate is not proof of a completed scan.
    </p>
  </section>;
}
