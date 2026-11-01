"use client";
import {useMemo,useState} from "react";
import type {ToolsSpreadsheetRow} from "./ToolsResultsSpreadsheet";
import {SPECIAL_DESIGNATION_CATEGORIES} from "../lib/trial-designations";
import css from "./ToolsOpeningTrialGrid.module.css";
type Props={
  rows:ToolsSpreadsheetRow[];total:number;offset:number;nextOffset:number|null;
  inventoryMode:boolean;loading:boolean;error:string;
  selectedStages:number;selectedDesignations:number;noVerifiedNctLinks:boolean;
  sourceDate:string;sourceState:string;
  onPrevious:()=>void;onNext:()=>void;
};
const format=(n:number)=>n.toLocaleString("en-US");
const safe=(v:string)=>v?.trim()||"Not recorded";
const designationNames=new Map(SPECIAL_DESIGNATION_CATEGORIES.map(({key,label})=>[key,label]));
const extraColumns=3;
const columnsCount=7+extraColumns;
type Field="nctId"|"ticker"|"company"|"drug"|"indication"|"stage";
const columns:{key:Field;label:string}[]=[
  {key:"nctId",label:"NCT Trial ID"},
  {key:"ticker",label:"Ticker"},
  {key:"company",label:"Company"},
  {key:"drug",label:"Drug / therapy"},
  {key:"indication",label:"Disease / indication"},
  {key:"stage",label:"Recorded stage"}
];
export default function ToolsOpeningTrialGrid({
  rows,total,offset,nextOffset,inventoryMode,loading,error,
  selectedStages,selectedDesignations,noVerifiedNctLinks,sourceDate,sourceState,onPrevious,onNext
}:Props){
  const [sortKey,setSortKey]=useState<Field>("nctId");
  const [desc,setDesc]=useState(false);
  const ordered=useMemo(()=>[...rows].sort((a,b)=>{
    const n=(a[sortKey]||"").localeCompare(b[sortKey]||"",undefined,{numeric:true,sensitivity:"base"});
    return desc?-n:n;
  }),[rows,sortKey,desc]);
  const hasSelection=selectedStages+selectedDesignations>0;
  // FDA and PDUFA attributes belong to each NCT row; neither creates a second trial.
  const countUnverified=hasSelection&&selectedDesignations>0&&noVerifiedNctLinks&&!loading&&!error;
  return <section className={css.root} aria-label="Live trial inventory spreadsheet">
    <div className={css.heading}>
      <div>
        <h2>{inventoryMode?"Published POOL — trial spreadsheet":"Filtered trials — spreadsheet"}</h2>
        <p>{inventoryMode
          ?"One master NCT POOL with documented FDA designations and saved PDUFA application links on the same trial rows. Phase/FDA selections narrow this table."
          :"One NCT per row. Phase and FDA filters use documented exact matches; linked PDUFA targets are application records, not a separate set of trials."}</p>
      </div>
      <strong className={css.count} role="status">{loading?"Loading…":error?"Unavailable":countUnverified?"NCT count not established":format(total)+" trials"}</strong>
    </div>
    <div className={css.scroll} role="region" aria-label="Scrollable clinical trial spreadsheet" tabIndex={0}>
      <table>
        <thead><tr><th className={css.rowNum}>#</th>
          {columns.map(col=><th key={col.key}>
            <button type="button" aria-label={"Sort visible trials by "+col.label}
              onClick={()=>{if(sortKey===col.key)setDesc(v=>!v);else{setSortKey(col.key);setDesc(false);}}}>
              {col.label}{sortKey===col.key?(desc?" ↓":" ↑"):" ↕"}
            </button>
          </th>)}
          <th>FDA designations <small>Documented subset</small></th>
          <th>PDUFA applications <small>Saved targets, not trial deadlines</small></th>
          <th>Study role</th>
        </tr></thead>
        <tbody>
          {loading?<tr><td colSpan={columnsCount} className={css.empty}>Loading published trial records…</td></tr>
          :error?<tr><td colSpan={7} className={css.empty}>Cannot verify the trial inventory: {error}. No zero count assumed.</td></tr>
          :ordered.length===0?<tr><td colSpan={7} className={css.empty}>
            {countUnverified?"Selected FDA programs have no verified NCT links; a clinical-trial count cannot be established."
              :hasSelection?"No documented trials match these selected criteria. Try a different Phase or FDA category."
              :"No trial records are available from the published source."}
          </td></tr>
          :ordered.map((row,i)=><tr key={row.id}>
            <td className={css.rowNum}>{offset+i+1}</td>
            <td><a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(row.nctId)} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
            <td>{safe(row.ticker)}</td>
            <td>{safe(row.company)}</td>
            <td>{safe(row.drug)}</td>
            <td>{safe(row.indication)}</td>
            <td>{safe(row.stage)}</td>
            <td>{(()=>{
              const linked=Object.entries(row.designationMatches||{}).filter(([,items])=>!!items?.length);
              return linked.length?<details>
                <summary>{linked.length} documented</summary>
                {linked.map(([key,items])=><div key={key}>
                  {designationNames.get(key as typeof SPECIAL_DESIGNATION_CATEGORIES[number]["key"])||key}
                  {" · "}{items?.[0]?.source
                    ?<a href={items[0].source} target="_blank" rel="noopener noreferrer">Evidence</a>:"Source not available"}
                </div>)}
              </details>:<span>Not documented</span>;
            })()}</td>
            <td>{row.pdufaApplications?.length?<details>
              <summary>{row.pdufaApplications.length} saved application{row.pdufaApplications.length===1?"":"s"}</summary>
              {row.pdufaApplications.map(application=><div key={application.eventKey}>
                <strong>{application.targetDate||"Target not recorded"}</strong>
                {" · "}{application.targetConfirmation||"Unverified target"}
                {application.savedCheckStatus?" · Saved status: "+application.savedCheckStatus:""}
                {application.savedOutcome?" · Recorded outcome: "+application.savedOutcome:""}
                {application.decisionDate?" · Recorded decision: "+application.decisionDate:""}
                {application.checkedAt?" · Source checked: "+application.checkedAt.slice(0,10):""}
                {application.evidenceUrl?<a href={application.evidenceUrl} target="_blank" rel="noopener noreferrer"> · Source</a>:null}
              </div>)}
            </details>:<span>No exact linked application recorded</span>}</td>
            <td>Not established</td>
          </tr>)}
        </tbody>
      </table>
    </div>
    <div className={css.footer}>
      <span>{!loading&&!error?countUnverified?"No verified NCT trial count":("Showing "+(total?offset+1:0)+"–"+Math.min(offset+rows.length,total)+" of "+format(total)):"Awaiting published records"} · Page sort only</span>
      <div className={css.pager}>
        <button type="button" disabled={loading||!!error||offset===0} onClick={onPrevious}>Previous 50</button>
        <button type="button" disabled={loading||!!error||nextOffset===null} onClick={onNext}>Next 50</button>
      </div>
    </div>
    <p className={css.source}>FDA designation and PDUFA application coverage is incomplete. A PDUFA target is application-level; the linked NCT is not automatically pivotal. Published source: {sourceDate||"Not recorded"} · State: {sourceState||"Unverified"}.
      {inventoryMode?" This is the full clinical POOL inventory, not a Pipeline qualification or an FDA designation match.":""}
      {hasSelection&&selectedDesignations>0?" FDA program records lacking NCT links cannot be treated as zero trials.":""}
    </p>
  </section>;
}
