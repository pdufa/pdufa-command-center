"use client";

import {useMemo} from "react";
import {useTrialDesignations} from "./TrialDesignations";
import {
  SPECIAL_DESIGNATION_CATEGORIES,
  type DesignationKey,
  type DesignationProgram,
} from "../lib/trial-designations";
import styles from "./FunnelWorkspace.module.css";
import ToolsOptionNumber from "./ToolsOptionNumber";
import type {ToolsDesignationTotals,ToolsContextualDesignationCounts} from "../lib/tools-pool-inventory";

type PositiveRecord={program:DesignationProgram;linkedNcts:string[]};
type DesignationSummary={available:boolean;records:PositiveRecord[]};

export default function PoolDesignationSelector({selected,onChange,poolTrialCount,poolTotals=null,contextCounts=null,scopeStages=[],scopeQuery="",scopeLoading=false,scopeError="",guided=false}:{
  selected:DesignationKey[];onChange:(next:DesignationKey[])=>void;
  poolTrialCount:number|null;poolTotals?:ToolsDesignationTotals|null;contextCounts?:ToolsContextualDesignationCounts|null;
  scopeStages?:readonly string[];scopeQuery?:string;scopeLoading?:boolean;scopeError?:string;guided?:boolean
}){
  const {index,loading,error,retry}=useTrialDesignations();
  const entries=useMemo(()=>{
    const result={} as Record<DesignationKey,DesignationSummary>;
    for(const category of SPECIAL_DESIGNATION_CATEGORIES){
      const records:PositiveRecord[]=[];
      if(index)for(const program of Object.values(index.programs)){
        const evidence=program.designations[category.key];
        if(evidence?.status==="GRANTED" && evidence.verification!=="UNVERIFIED" && evidence.source){
          records.push({program,linkedNcts:poolTotals?.[category.key]?.programNctIds?.[program.eventKey]||[]});
        }
      }
      records.sort((a,b)=>a.program.ticker.localeCompare(b.program.ticker));
      result[category.key]={
        available:!!index?.availableKeys?.[category.key],
        records
      };
    }
    return result;
  },[index,poolTotals]);
  const supported=SPECIAL_DESIGNATION_CATEGORIES.filter(category=>entries[category.key].available);
  const positiveProgramIds=new Set<string>();
  for(const category of SPECIAL_DESIGNATION_CATEGORIES)
    for(const record of entries[category.key].records)positiveProgramIds.add(record.program.eventKey);
  const auditedNcts=index?.linkageCoverage?.verifiedNctCount??Object.keys(index?.trialEvents||{}).length;

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
    onChange(selected.includes(key)?selected.filter(item=>item!==key):[...selected,key]);
  }
  if(guided)return <div className={styles.toolsGuidedDesignation}>
    <p className={styles.muted}>Counts at right show distinct NCT trials matching each FDA category <strong>within your current Phase and search filters</strong>. They use the same exact NCT/ticker evidence and full trial set as the resultant spreadsheet, not FDA program totals or just the visible 50 rows. Multiple FDA categories are OR combined, so their counts can overlap. ? means source-linked trial coverage is unknown.</p>
    <p className={styles.muted}><strong>Count scope:</strong> {scopeStages.length?scopeStages.join(", "):"All recorded phases"}{scopeQuery.trim()?" · Search: "+scopeQuery.trim():""} · Individual FDA categories evaluated separately.</p>
    {loading&&<p role="status" className={styles.muted}>Loading FDA source evidence…</p>}
    {error&&<p role="alert" className={styles.error}>FDA source unavailable: {error} <button type="button" onClick={retry}>Retry</button></p>}
    <div className={styles.stageDesignationList} role="group" aria-label="FDA special designations and pathways">
      {SPECIAL_DESIGNATION_CATEGORIES.map((category,categoryIndex)=>{
        const d=entries[category.key],checked=selected.includes(category.key),total=poolTotals?.[category.key]??null,
          contextual=contextCounts?.[category.key]??null;
        return <div key={category.key} className={styles.toolsCascadeFdaItem}>
          <label className={styles.stageCheckboxRow}
            title={index&&!d.available?"No source field available for this category":undefined}>
            <input type="checkbox" checked={checked} disabled={!index||!d.available}
              onChange={()=>toggle(category.key)}/>
            <ToolsOptionNumber level={2} index={categoryIndex} total={SPECIAL_DESIGNATION_CATEGORIES.length}/>
            <span>{category.label}</span>
            <strong className={styles.toolsFdaRowCount}
              title={index&&d.available&&!scopeLoading&&!scopeError&&contextual
                ?contextual.matchingTrials+" exact-NCT matches with current Phase/search; FDA categories OR together"
                :"Current resultant trial count not established"}>
              {index&&d.available?(scopeLoading?"…":contextual?contextual.matchingTrials.toLocaleString("en-US"):"?"):"—"}
              <small>{index&&d.available?(scopeLoading?"updating":contextual?"trial matches":"NCTs unknown"):"Not tracked"}</small>
            </strong>
          </label>
          {checked&&index&&<div className={styles.toolsCascadeFdaEvidence}
              aria-label={category.label+" source evidence"} role="group">
            <div><strong>{d.records.length.toLocaleString("en-US")} source programs</strong>
              <small>Across source evidence, not filtered clinical trials</small></div>
            <div><strong>{scopeLoading?"Updating…":contextual?contextual.matchingTrials.toLocaleString("en-US")+" matching NCTs":"NCT count unknown"}</strong>
              <small>Within selected Phase/search, before pagination; exact links only</small></div>
            {contextual&&contextual.matchingTrials>0&&<details className={styles.toolsFdaLinkedTrials}>
              <summary>View {contextual.matchingTrials.toLocaleString("en-US")} matching trial IDs in selected scope</summary>
              <ul>{contextual.nctIds.map(nct=>
                <li key={nct}><a href={"https://clinicaltrials.gov/study/"+nct}
                  target="_blank" rel="noopener noreferrer">{nct}</a></li>)}</ul>
              {contextual.matchingTrials>40&&<p>Showing the first 40 matching NCT IDs.</p>}
              <p>Matches use current Phase/search filters. FDA program evidence is incomplete, so missing links do not prove absence.</p>
            </details>}
          </div>}
        </div>;
      })}
    </div>
    <div className={styles.stageDropdownActions}>
      <button type="button" disabled={!index||supported.length===0}
        onClick={()=>onChange(supported.map(item=>item.key))}>Select all available</button>
    </div>
    {selected.length>0&&index&&<details className={styles.designationSelection}>
      <summary>View {combined.length.toLocaleString("en-US")} source-linked application/program records</summary>
      {combined.length===0?<p>No source-linked positive records in selected categories. Missing evidence is not denial.</p>:
        <ol className={styles.designationResults}>
          {combined.slice(0,50).map(({row,labels,sources})=><li key={row.program.eventKey}>
            <strong>{row.program.ticker}</strong> · {row.program.drug||row.program.eventKey}
            {row.program.indication&&<span> · {row.program.indication}</span>}
            <small>{labels.join(" · ")} · {row.linkedNcts.length?row.linkedNcts.join(", "):"No matching NCT link in published POOL"}</small>
            {sources.map(source=><a key={source} href={source} target="_blank" rel="noopener noreferrer">Source ↗</a>)}
          </li>)}
        </ol>}
      {combined.length>50&&<p className={styles.muted}>Showing first 50 source programs.</p>}
    </details>}
    <details className={styles.designationCoverageWarning}>
      <summary>FDA evidence coverage and limitations</summary>
      <p>{index?supported.length+" of 13 FDA categories have a tracked source field":"Source availability not established"}.
        {index?" Source-index NCT crosswalk coverage (not matched POOL): "+auditedNcts.toLocaleString("en-US"):""}
        {poolTrialCount!==null?" of "+poolTrialCount.toLocaleString("en-US")+" in POOL":""}.</p>
      <p>FDA program counts are not distinct clinical-trial counts. The NCT figures use the same POOL, NCT-ID and ticker match as the trial spreadsheet. FDA-to-trial coverage is partial; missing evidence is unknown, not zero.</p>
    </details>
  </div>;
  return <div className={styles.stageDropdownColumn}>
    <label className={styles.stageDropdownLabel}>Saved FDA source coverage</label>
    <p className={styles.stageDropdownSubline}>
      {index?supported.length+" of 13 FDA categories have a tracked source field":"Checking saved evidence…"}
    </p>
    {index && <details className={styles.designationCoverageWarning}>
      <summary><strong>FDA coverage limited:</strong> {auditedNcts.toLocaleString("en-US")} linked NCT trials
        {poolTrialCount!==null?" of "+poolTrialCount.toLocaleString("en-US")+" in POOL":""}
        <span> · Details</span></summary>
      <p><strong>Incomplete FDA-to-trial coverage.</strong> Only <strong>{auditedNcts.toLocaleString("en-US")} reviewed NCT links</strong> are recorded
        {poolTrialCount!==null?" against "+poolTrialCount.toLocaleString("en-US")+" trials in the POOL":""}.
        The FDA source contains <strong>{positiveProgramIds.size.toLocaleString("en-US")} source-linked positive application/program records</strong>,
        many without any verified trial ID link.</p>
      <p>Counts beside FDA choices distinguish source programs from linked trial IDs.
        Combining FDA designations with clinical stages searches <strong>documented matches only</strong>, not every eligible trial.
        An unlinked result is unknown, not a negative finding.</p>
    </details>}
    {index && Object.keys(index.trialEvents).length===0&&<p className={styles.error} role="status">
      No reviewed trial-to-designation links are available. Combined trial counts cannot be verified yet.
    </p>}
    <details className={styles.stageDesignationPane}>
      <summary className={styles.stageDesignationSummary}>
        <ToolsOptionNumber level={1} index={1} total={2}/>
        <span>{selected.length===0?"Select FDA designations":selected.length+" designations selected"}</span>
        <strong>{selected.length} selected</strong>
      </summary>
      <div className={styles.stageDesignationBody}>
        <div className={styles.stageDropdownActions}>
          <button type="button" disabled={!index||supported.length===0}
            onClick={()=>onChange(supported.map(item=>item.key))}>Select all available</button>
          <button type="button" onClick={()=>onChange([])}>Clear</button>
        </div>
        <div className={styles.stageDesignationList} role="group" aria-label="FDA special designations and pathways">
          {SPECIAL_DESIGNATION_CATEGORIES.map((category,categoryIndex)=>{
            const d=entries[category.key],total=poolTotals?.[category.key]??null;
            const checked=selected.includes(category.key);
            return <div key={category.key} className={styles.toolsCascadeFdaItem}>
              <label className={styles.stageCheckboxRow}
                title={!d.available?"No source field available for this category":undefined}>
                <input type="checkbox" checked={checked}
                  disabled={!index||!d.available} onChange={()=>toggle(category.key)}/>
                <ToolsOptionNumber level={2} index={categoryIndex} total={SPECIAL_DESIGNATION_CATEGORIES.length}/>
                <span>{category.label}</span>
                <strong className={styles.toolsFdaRowCount}
                title={index&&d.available&&total?total.linkedNcts+" POOL-matched NCT trial IDs (partial FDA coverage)": "FDA category not source-tracked"}>
                {index&&d.available?(total?.linkedNcts?total.linkedNcts.toLocaleString("en-US"):"?"):"—"}
                <small>{index&&d.available?(total?.linkedNcts?"linked NCTs":"NCTs unknown"):"Not tracked"}</small>
            </strong>
              </label>
              {checked&&index&&<div className={styles.toolsCascadeFdaEvidence} role="group"
                aria-label={category.label+" source evidence"}>
                <div><strong>{d.records.length.toLocaleString("en-US")} source programs</strong>
                  <small>FDA applications/program events, not distinct trials</small></div>
                <div><strong>{total?.linkedNcts?total.linkedNcts.toLocaleString("en-US")+" linked NCTs":"NCT count unknown"}</strong>
                  <small>Exact POOL-matched trial links only</small></div>
              </div>}
            </div>;
          })}
        </div>
        <p className={styles.muted}>The top number counts positive source programs; the smaller number counts the few trial IDs matched to them. They are not interchangeable. “NCT count unknown” means research is incomplete, not zero trials.</p>
      </div>
    </details>
    {loading&&<p role="status" className={styles.muted}>Loading FDA source evidence…</p>}
    {error&&<p role="alert" className={styles.error}>FDA source unavailable: {error} <button type="button" onClick={retry}>Retry</button></p>}
    {selected.length>0&&index&&<details className={styles.designationSelection}>
      <summary style={{cursor:"pointer",fontWeight:700}}>
        View {combined.length.toLocaleString("en-US")} source-linked application/program records (all stages)
      </summary>
      {combined.length===0?<p>No verified positive source-linked records in these categories; missing evidence is not a denial.</p>:
        <>
          <p>{selected.length} categories selected. A program counted in several categories appears once in this list. These are not unique POOL trial counts.</p>
          <ol className={styles.designationResults}>
            {combined.slice(0,50).map(({row,labels,sources})=><li key={row.program.eventKey}>
              <strong>{row.program.ticker}</strong> · {row.program.drug||row.program.eventKey}
              {row.program.indication&&<span> · {row.program.indication}</span>}
              <small>{labels.join(" · ")} · {row.linkedNcts.length?row.linkedNcts.join(", "):"No matching NCT link in published POOL"}</small>
              {sources.map(source=><a key={source} href={source} target="_blank" rel="noopener noreferrer"
                style={{marginRight:10}}>Source ↗</a>)}
            </li>)}
          </ol>
          {combined.length>50&&<p className={styles.muted}>Showing first 50 matching records.</p>}
        </>
      }
    </details>}
    <p className={styles.muted}>Partial coverage: the crosswalk contains researched therapy/indication-to-NCT links, not a complete FDA designation inventory. No verified linked trial for a category does not prove the designation was absent. Some categories are regulatory pathways rather than statutory designations.</p>
  </div>;
}
