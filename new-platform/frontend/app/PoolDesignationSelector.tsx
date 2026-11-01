"use client";

import {useMemo, useState} from "react";
import {useTrialDesignations} from "./TrialDesignations";
import {
  SPECIAL_DESIGNATION_CATEGORIES,
  type DesignationKey,
  type DesignationProgram,
} from "../lib/trial-designations";
import styles from "./FunnelWorkspace.module.css";

type PositiveRecord={program:DesignationProgram;linkedNcts:string[]};
type DesignationSummary={available:boolean;records:PositiveRecord[];linkedTrials:number};

export default function PoolDesignationSelector(){
  const {index,loading,error,retry}=useTrialDesignations();
  const [selected,setSelected]=useState<DesignationKey|null>(null);
  const entries=useMemo(()=>{
    const links=new Map<string,Set<string>>();
    if(index)for(const [nct,keys] of Object.entries(index.trialEvents)){
      if(!/^NCT\d{8}$/.test(nct))continue;
      for(const key of keys){
        if(!links.has(key))links.set(key,new Set());
        links.get(key)!.add(nct);
      }
    }
    const result={} as Record<DesignationKey,DesignationSummary>;
    for(const item of SPECIAL_DESIGNATION_CATEGORIES){
      const records:PositiveRecord[]=[];
      if(index)for(const program of Object.values(index.programs)){
        const evidence=program.designations[item.key];
        if(evidence?.status==="GRANTED" && evidence.verification!=="UNVERIFIED" && evidence.source){
          records.push({program,linkedNcts:[...(links.get(program.eventKey)||[])]});
        }
      }
      records.sort((a,b)=>a.program.ticker.localeCompare(b.program.ticker));
      const linkedTrials=new Set(records.flatMap(r=>r.linkedNcts)).size;
      result[item.key]={
        available:!!index?.availableKeys?.[item.key],
        records,
        linkedTrials,
      };
    }
    return result;
  },[index]);
  const chosen=selected?entries[selected]:null;
  const category=SPECIAL_DESIGNATION_CATEGORIES.find(item=>item.key===selected);
  const availableCount=index?SPECIAL_DESIGNATION_CATEGORIES.filter(item=>entries[item.key].available).length:null;
  return <details className={styles.stageDesignationPane}>
    <summary className={styles.stageDesignationSummary}>
      <span>FDA Special Designations &amp; Pathways</span>
      <strong>13 categories</strong>
    </summary>
    <div className={styles.stageDesignationBody}>
      <p className={styles.muted}>Select a category to inspect source-linked records. Numbers count saved application/program records, <strong>not</strong> all POOL trials. Categories with no usable source field show —.</p>
      <div className={styles.stageDesignationList} role="group" aria-label="FDA designation choices">
        {SPECIAL_DESIGNATION_CATEGORIES.map(item=>{
          const d=entries[item.key];
          const active=selected===item.key;
          return <button type="button" key={item.key} className={styles.stageDesignationRow}
            aria-pressed={active} onClick={()=>setSelected(active?null:item.key)}>
            <span>{item.label}</span>
            <strong title="Saved positive, source-linked application/program records">{!index?"—":d.available?d.records.length.toLocaleString("en-US"):"—"}</strong>
          </button>;
        })}
      </div>
      {loading&&<p role="status" className={styles.muted}>Loading saved designation evidence…</p>}
      {error&&<p role="alert" className={styles.muted}>Saved designation evidence unavailable: {error} <button type="button" onClick={retry}>Retry</button></p>}
      {availableCount!==null&&<p className={styles.muted}>Saved source fields available for {availableCount} of 13 categories. — indicates unavailable coverage, not zero granted.</p>}
      {selected&&chosen&&<div className={styles.designationSelection}>
        <h3>{category?.label}</h3>
        {!index?<p>Designation evidence not loaded.</p>:
        !chosen.available?<p>No tracked source field for this category. A count cannot be established.</p>:
        chosen.records.length===0?<p>No linked positive application records in the saved source. This does not imply the designation was denied.</p>:
        <>
          <p>{chosen.records.length.toLocaleString("en-US")} source-linked programs · {chosen.linkedTrials.toLocaleString("en-US")} explicitly linked NCT trial IDs. Programs may share trials or have no NCT link.</p>
          <ol className={styles.designationResults}>{chosen.records.slice(0,50).map(({program,linkedNcts})=>{
            const evidence=program.designations[selected];
            return <li key={program.eventKey}>
              <strong>{program.ticker}</strong> · {program.drug||program.eventKey}
              {program.indication&&<span> · {program.indication}</span>}
              <small>{evidence.verification==="FDA_VERIFIED"?"FDA-verified source":"Saved source report"}{evidence.designationDate?" · "+evidence.designationDate:""} · {linkedNcts.length?linkedNcts.join(", "):"No exact NCT linkage"}</small>
              <a href={evidence.source} target="_blank" rel="noopener noreferrer">Supporting source ↗</a>
            </li>;
          })}</ol>
          {chosen.records.length>50&&<p className={styles.muted}>Showing first 50 application records.</p>}
        </>}
      </div>}
      <p className={styles.muted}>Fast Track, Orphan Drug and related labels refer to FDA programs or pathways; not all 13 are statutory designations. An evidence record is not proof of current candidate eligibility.</p>
    </div>
  </details>;
}
