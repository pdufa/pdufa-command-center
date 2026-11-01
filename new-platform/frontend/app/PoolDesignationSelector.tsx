"use client";

import {useMemo,useState} from "react";
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
  const [selected,setSelected]=useState<DesignationKey[]>([]);
  const entries=useMemo(()=>{
    const trialLinks=new Map<string,Set<string>>();
    if(index)for(const [nct,keys] of Object.entries(index.trialEvents)){
      if(!/^NCT\d{8}$/.test(nct))continue;
      for(const key of keys){
        if(!trialLinks.has(key))trialLinks.set(key,new Set());
        trialLinks.get(key)!.add(nct);
      }
    }
    const result={} as Record<DesignationKey,DesignationSummary>;
    for(const category of SPECIAL_DESIGNATION_CATEGORIES){
      const records:PositiveRecord[]=[];
      if(index)for(const program of Object.values(index.programs)){
        const evidence=program.designations[category.key];
        if(evidence?.status==="GRANTED" && evidence.verification!=="UNVERIFIED" && evidence.source){
          records.push({program,linkedNcts:[...(trialLinks.get(program.eventKey)||[])]});
        }
      }
      records.sort((a,b)=>a.program.ticker.localeCompare(b.program.ticker));
      result[category.key]={
        available:!!index?.availableKeys?.[category.key],
        records,
        linkedTrials:new Set(records.flatMap(record=>record.linkedNcts)).size
      };
    }
    return result;
  },[index]);
  const supported=SPECIAL_DESIGNATION_CATEGORIES.filter(category=>entries[category.key].available);
  const combined=useMemo(()=>{
    const m=new Map<string,{row:PositiveRecord;labels:string[];sources:string[]}>();
    for(const category of SPECIAL_DESIGNATION_CATEGORIES){
      if(!selected.includes(category.key))continue;
      for(const record of entries[category.key].records){
        const key=record.program.eventKey;
        if(!m.has(key))m.set(key,{row:record,labels:[],sources:[]});
        const v=m.get(key)!;
        v.labels.push(category.label);
        const source=record.program.designations[category.key].source;
        if(source&&!v.sources.includes(source))v.sources.push(source);
      }
    }
    return [...m.values()].sort((a,b)=>a.row.program.ticker.localeCompare(b.row.program.ticker));
  },[entries,selected]);
  function toggle(key:DesignationKey){
    setSelected(old=>old.includes(key)?old.filter(item=>item!==key):[...old,key]);
  }
  return <div className={styles.stageDropdownColumn}>
    <label className={styles.stageDropdownLabel}>Saved FDA source coverage</label>
    <p className={styles.stageDropdownSubline}>{index?supported.length+" of 13 categories have a tracked source field":"Checking saved evidence…"}</p>
    <details className={styles.stageDesignationPane}>
      <summary className={styles.stageDesignationSummary}>
        <span>{selected.length===0?"Select FDA designations":selected.length+" designations selected"}</span>
        <strong>13</strong>
      </summary>
      <div className={styles.stageDesignationBody}>
        <div className={styles.stageDropdownActions}>
          <button type="button" disabled={!index||supported.length===0}
            onClick={()=>setSelected(supported.map(item=>item.key))}>Select all available</button>
          <button type="button" onClick={()=>setSelected([])}>Clear</button>
        </div>
        <div className={styles.stageDesignationList} role="group" aria-label="FDA special designations and pathways">
          {SPECIAL_DESIGNATION_CATEGORIES.map(category=>{
            const d=entries[category.key];
            return <label className={styles.stageCheckboxRow} key={category.key}
              title={index&&!d.available?"No source field available for this category":undefined}>
              <input type="checkbox" checked={selected.includes(category.key)}
                disabled={!index||!d.available} onChange={()=>toggle(category.key)}/>
              <span>{category.label}</span>
              <strong title="Source-linked application/program records">
                {index&&d.available?d.records.length.toLocaleString("en-US"):"—"}
              </strong>
            </label>;
          })}
        </div>
        <p className={styles.muted}>Choose multiple categories (OR). A dash means not tracked, not zero grants. Counts represent source-linked application/program records.</p>
      </div>
    </details>
    {loading&&<p role="status" className={styles.muted}>Loading FDA source evidence…</p>}
    {error&&<p role="alert" className={styles.error}>FDA source unavailable: {error} <button type="button" onClick={retry}>Retry</button></p>}
    {selected.length>0&&index&&<details className={styles.designationSelection}>
      <summary style={{cursor:"pointer",fontWeight:700}}>
        View {combined.length.toLocaleString("en-US")} matching application/program records
      </summary>
      {combined.length===0?<p>No verified positive source-linked records in these categories; missing evidence is not a denial.</p>:
        <>
          <p>{selected.length} categories selected. A program counted in several categories appears once in this list. These are not unique POOL trial counts.</p>
          <ol className={styles.designationResults}>
            {combined.slice(0,50).map(({row,labels,sources})=><li key={row.program.eventKey}>
              <strong>{row.program.ticker}</strong> · {row.program.drug||row.program.eventKey}
              {row.program.indication&&<span> · {row.program.indication}</span>}
              <small>{labels.join(" · ")} · {row.linkedNcts.length?row.linkedNcts.join(", "):"No exact NCT link recorded"}</small>
              {sources.map(source=><a key={source} href={source} target="_blank" rel="noopener noreferrer"
                style={{marginRight:10}}>Source ↗</a>)}
            </li>)}
          </ol>
          {combined.length>50&&<p className={styles.muted}>Showing first 50 matching records.</p>}
        </>
      }
    </details>}
    <p className={styles.muted}>The FDA categories are saved source findings; not all 13 are formal statutory designations. No selection changes underlying POOL or Pipeline eligibility.</p>
  </div>;
}
