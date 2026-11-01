"use client";

import {useMemo,useState} from "react";
import {SPECIAL_DESIGNATION_CATEGORIES,type DesignationKey} from "../lib/trial-designations";
import styles from "./FunnelWorkspace.module.css";

export type ToolSourceEvidence={
  eventKey:string;source:string;designationDate:string;checkedAt:string;
  verification:"FDA_VERIFIED"|"SOURCE_RECORDED"|"UNVERIFIED";note:string;
};
export type ToolsSpreadsheetRow={
  id:string;nctId:string;ticker:string;company:string;drug:string;indication:string;
  stage:string;selectedStage:string;
  designationMatches:Partial<Record<DesignationKey,ToolSourceEvidence[]>>;
};
export type SelectedFiltersSummary={
  selectedCount:number;stageSelectedCount:number;designationSelectedCount:number;
  stageTotal:number;designationCountSum:number;designationUniqueTrials:number|null;
  matchingUniqueTrials:number;
  sourceProgramRecords?:number;
  unlinkedSourceProgramRecords?:number;
  noVerifiedNctLinks?:boolean;
  stageSelectors:{label:string;trials:number}[];
  designationSelectors:{key:DesignationKey;label:string;linkedTrials:number}[];
};
type Props={
  rows:ToolsSpreadsheetRow[];
  summary:SelectedFiltersSummary|null;
  designationCoverage:{
    sourcePrograms:number;linkedPrograms:number;unlinkedPrograms:number;
    linkedNcts:number;noVerifiedNctLinks:boolean;
    programRows:{eventKey:string;ticker:string;drug:string;indication:string;
      designations:{key:DesignationKey;label:string;source:string}[];
      linkedNcts:string[]}[];
  }|null;
  stages:string[];
  designations:DesignationKey[];
  total:number;
  offset:number;
  loading:boolean;
  error:string;
  downloadUrl:string;
  onPrevious:()=>void;
  onNext:()=>void;
  nextOffset:number|null;
};
const names=new Map(SPECIAL_DESIGNATION_CATEGORIES.map(category=>[category.key,category.label]));
const fmt=(number:number)=>number.toLocaleString("en-US");
const display=(text:string)=>text?.trim()||"Not recorded";
type SortField="nctId"|"ticker"|"company"|"drug"|"indication"|"stage";
const sortFields:{key:SortField;label:string}[]=[
  {key:"nctId",label:"NCT / Trial ID"},
  {key:"ticker",label:"Ticker"},
  {key:"company",label:"Company"},
  {key:"drug",label:"Drug / therapy"},
  {key:"indication",label:"Disease / indication"},
  {key:"stage",label:"Recorded stage"},
];
export default function ToolsResultsSpreadsheet({
  rows,summary,designationCoverage,stages,designations,total,offset,loading,error,downloadUrl,
  onPrevious,onNext,nextOffset
}:Props){
  const [sortKey,setSortKey]=useState<SortField>("nctId");
  const [descending,setDescending]=useState(false);
  const ordered=useMemo(()=>[...rows].sort((a,b)=>{
    const result=(a[sortKey]||"").localeCompare(b[sortKey]||"",undefined,{numeric:true,sensitivity:"base"});
    return descending?-result:result;
  }),[rows,sortKey,descending]);
  function sort(key:SortField){
    if(sortKey===key)setDescending(prev=>!prev);
    else {setSortKey(key);setDescending(false);}
  }
  const hasSelection=stages.length+designations.length>0;
  const selectedCount=stages.length+designations.length;
  const trialCountUnverified=!!designationCoverage?.noVerifiedNctLinks&&designations.length>0&&!loading&&!error;
  const displayTrialCount=trialCountUnverified?"Not established":fmt(total);
  const pageFirst=total>0?offset+1:0;
  const pageLast=Math.min(offset+rows.length,total);
  return <section className={styles.toolsSheet} aria-label="Selected filters and matching clinical trials spreadsheet">
    <div className={styles.toolsSheetHeading}>
      <div>
        <h2>SELECTED TRIALS — SPREADSHEET</h2>
        <p className={styles.muted}>Every checked selector appears in the selection totals and as a column in the table below. The sheet refreshes when you change either dropdown.</p>
      </div>
      <a className={styles.toolsSheetExport} href={hasSelection&&!loading&&!error?downloadUrl:undefined}
        aria-disabled={!hasSelection||loading||!!error}
        onClick={e=>{if(!hasSelection||loading||!!error)e.preventDefault()}}
        download={trialCountUnverified?"pdufa-tools-fda-program-records-unlinked.csv":"pdufa-tools-selected-trials.csv"}>
        {trialCountUnverified?"Export FDA program records (CSV)":"Export all matches (CSV)"}</a>
    </div>
    <div className={styles.toolsSheetMetrics} aria-live="polite">
      <div><span>Selectors clicked</span><strong>{selectedCount}</strong><small>{stages.length} stages + {designations.length} FDA categories</small></div>
      <div><span>Selected stage totals</span><strong>{summary?fmt(summary.stageTotal):hasSelection?"—":"0"}</strong><small>Distinct NCTs within selected stage categories</small></div>
      <div><span>{designations.length?"FDA source program records":"Verified linked NCT counts"}</span><strong>{designations.length
        ?loading||error?"—":designationCoverage?fmt(designationCoverage.sourcePrograms):"—"
        :summary?fmt(summary.designationCountSum):hasSelection?"—":"0"}</strong>
        <small>{designations.length?"Source-backed applications/program events; these are NOT trial counts":"Only reviewed FDA-to-NCT links; categories may overlap"}</small></div>
      <div><span>{designations.length?"Matching NCT trial count":"Final matching trials"}</span>
        <strong>{hasSelection?(loading||error?"—":trialCountUnverified?"Not established":summary?fmt(summary.matchingUniqueTrials):"—"):"0"}</strong>
        <small>{trialCountUnverified?"No source-verified trial IDs for these programs; zero must not be inferred":designations.length?"Partial FDA-to-trial coverage":"Unique NCT records after selected clinical-stage filters"}</small></div>
    </div>
    <div className={styles.toolsSheetTotals}>
      <h3>Selected selectors &amp; individual trial totals</h3>
      {selectedCount===0?<p className={styles.muted}>No selectors selected. Choose a stage or FDA designation above to populate this spreadsheet.</p>:<>
        <div className={styles.toolsSheetTableScroll}>
          <table className={styles.toolsSheetSummaryTable}>
            <thead><tr><th>Type</th><th>Clicked selector</th><th>Unique NCTs in source</th><th>Interpretation</th></tr></thead>
            <tbody>
              {stages.map(stage=>{
                const entry=summary?.stageSelectors.find(item=>item.label===stage);
                return <tr key={"stage:"+stage}><td>Stage</td><td>{stage}</td>
                  <td>{entry?fmt(entry.trials):"—"}</td><td>Recorded POOL stage</td></tr>;
              })}
              {designations.map(key=>{
                const entry=summary?.designationSelectors.find(item=>item.key===key);
                return <tr key={"designation:"+key}><td>FDA program</td><td>{names.get(key)||key}</td>
                  <td>{entry?trialCountUnverified?"Not established":fmt(entry.linkedTrials):"—"}</td><td>{entry&&trialCountUnverified?"Source program records exist; no verified NCT linkage": "Exact NCT + ticker and source-linked positive evidence"}</td></tr>;
              })}
            </tbody>
            <tfoot>
              <tr><th colSpan={2}>TOTAL CLICKED SELECTORS</th><th>{selectedCount}</th><th>Number of checkboxes checked, not number of unique trials</th></tr>
              <tr><th colSpan={2}>UNIQUE TRIALS MATCHING COMBINED FILTERS</th><th>{trialCountUnverified?"Not established":summary?fmt(summary.matchingUniqueTrials):"—"}</th><th>OR within each list; AND across the two lists. Counts require verified NCT links.</th></tr>
            </tfoot>
          </table>
        </div>
        <p className={styles.muted}>Designation categories may refer to the same trial. Their per-category counts are not added to the final unique-trial total. FDA-selected totals cover only the documented NCT links, not the entire 11,623-trial POOL.</p>
      </>}
    </div>
    <div className={styles.toolsSheetTableHeading}>
      <h3>Matching trial records</h3>
      <span>{hasSelection&&!loading&&!error?(trialCountUnverified?"NCT count not established":fmt(total)+(designations.length?" documented linked trial matches (partial)":" matching NCT trials")):hasSelection&&loading?"Calculating…":hasSelection&&error?"Unavailable":"0 matching trials"}</span>
    </div>
    <div className={styles.toolsSheetTableScroll} role="region" aria-label="Scrollable spreadsheet containing selected trial matches" tabIndex={0}>
      <table className={styles.toolsSheetGrid}>
        <thead><tr>
          <th className={styles.toolsSheetRowNumber}>#</th>
          {sortFields.map(item=><th key={item.key}>
            <button type="button" className={styles.toolsSheetSort} onClick={()=>sort(item.key)}
              aria-label={"Sort visible page by "+item.label}>
              {item.label}{sortKey===item.key?(descending?" ↓":" ↑"):" ↕"}
            </button>
          </th>)}
          {stages.map(stage=><th key={"stage:"+stage} title="Selected stage criterion">{stage}<small>Selected stage</small></th>)}
          {designations.map(key=><th key={"designation:"+key} title="Selected FDA designation category">{names.get(key)||key}<small>FDA designation evidence</small></th>)}
        </tr></thead>
        <tbody>
          {!hasSelection?<tr><td colSpan={7+stages.length+designations.length} className={styles.toolsSheetEmpty}>Select a clinical stage or FDA designation to populate rows.</td></tr>:
          loading?<tr><td colSpan={7+stages.length+designations.length} className={styles.toolsSheetEmpty}>Loading matching trial rows…</td></tr>:
          error?<tr><td colSpan={7+stages.length+designations.length} className={styles.toolsSheetEmpty}>Trial evidence could not be verified. No result total is asserted.</td></tr>:
          ordered.length===0?<tr><td colSpan={7+stages.length+designations.length} className={styles.toolsSheetEmpty}>
            {trialCountUnverified
              ?"These FDA program records have no verified NCT clinical-trial links. Trial count and development stages cannot yet be determined; no zero-trial conclusion is justified."
              :"No documented NCT links match the selected filters. FDA evidence coverage is incomplete; other qualifying trials may exist."}
          </td></tr>:
          ordered.map((row,i)=><tr key={row.id}>
            <td className={styles.toolsSheetRowNumber}>{offset+i+1}</td>
            <td><a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(row.nctId)}
              target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
            <td>{display(row.ticker)}</td>
            <td>{display(row.company)}</td>
            <td>{display(row.drug)}</td>
            <td>{display(row.indication)}</td>
            <td>{display(row.stage)}</td>
            {stages.map(stage=><td key={"stage:"+stage}>
              <span className={row.stage===stage?styles.toolsSheetMatch:styles.toolsSheetNoMatch}>
                {row.stage===stage?"✓ MATCH":"—"}
              </span>
            </td>)}
            {designations.map(key=>{
              const evidence=row.designationMatches[key]||[];
              return <td key={"designation:"+key}>
                {evidence.length?<details className={styles.toolsSheetEvidence}>
                  <summary>✓ Granted ({evidence.length})</summary>
                  {evidence.map(item=><div key={item.eventKey} className={styles.toolsSheetEvidenceDetail}>
                    <span>{item.verification==="FDA_VERIFIED"?"FDA verified":"Source recorded"}</span>
                    <span>{item.designationDate||"Date not recorded"}</span>
                    <a href={item.source} target="_blank" rel="noopener noreferrer">Evidence</a>
                  </div>)}
                </details>:<span className={styles.toolsSheetNoMatch}>—</span>}
              </td>;
            })}
          </tr>)}
        </tbody>
        {hasSelection&&!loading&&!error&&<tfoot><tr>
          <th colSpan={7+stages.length+designations.length}>
            {trialCountUnverified?"Matching unique NCT trials: not established":"Total matching unique NCT trials: "+fmt(total)} · Selected filters: {selectedCount}
          </th>
        </tr></tfoot>}
      </table>
    </div>
    <div className={styles.pagination}>
      <button type="button" disabled={loading||!!error||offset===0} onClick={onPrevious}>Previous 50</button>
      <span>{trialCountUnverified?"NCT record count unavailable — "+fmt(designationCoverage!.sourcePrograms)+" source programs documented":"Showing "+pageFirst+"–"+pageLast+" of "+(hasSelection&&!error?fmt(total):"0")+" · sorting affects the visible page only"}</span>
      <button type="button" disabled={loading||!!error||nextOffset===null} onClick={onNext}>Next 50</button>
    </div>
    {designations.length>0&&designationCoverage&&designationCoverage.programRows.length>0&&<section className={styles.toolsSheetTotals} aria-label="FDA source programs not yet assigned to clinical trial stages">
      <h3>FDA source program records — not clinical trial counts</h3>
      <p className={styles.muted}>
        <strong>{fmt(designationCoverage.sourcePrograms)} source-backed FDA program records</strong> match the selected FDA categories.
        Of these, <strong>{fmt(designationCoverage.unlinkedPrograms)} program records</strong> have no verified NCT link in this POOL.
        Selecting all stages cannot classify those records. Program records are shown below so no known FDA source disappears from the results.
      </p>
      <div className={styles.toolsSheetTableScroll} role="region" aria-label="FDA program records with source evidence" tabIndex={0}>
        <table className={styles.toolsSheetSummaryTable}>
          <thead><tr><th>Company ticker</th><th>Program / regulatory event</th><th>Drug</th><th>Indication</th><th>FDA category</th><th>Linked NCTs</th><th>Evidence</th></tr></thead>
          <tbody>{designationCoverage.programRows.map(program=><tr key={program.eventKey}>
            <td>{display(program.ticker)}</td>
            <td>{program.eventKey}</td>
            <td>{display(program.drug)}</td>
            <td>{display(program.indication)}</td>
            <td>{program.designations.map(d=>d.label).join(", ")}</td>
            <td>{program.linkedNcts.length?program.linkedNcts.join(", "):"NCT link not established"}</td>
            <td>{program.designations.map(d=><a key={d.key} href={d.source} target="_blank" rel="noopener noreferrer" style={{display:"block"}}>{d.label} source</a>)}</td>
          </tr>)}</tbody>
        </table>
      </div>
      <p className={styles.muted}>These rows are source-backed FDA program findings. They are not proven to match the selected clinical stages, and they must not be counted as distinct NCT trials.</p>
    </section>}
    <p className={styles.muted}>{trialCountUnverified
      ?"CSV export contains the FDA program records shown above, labeled as regulatory programs rather than clinical trials. Their trial IDs and phase assignments have not been established."
      :"This is a read-only web spreadsheet. CSV export includes all documented matching rows (not just this page) and opens in Excel or Google Sheets. FDA designation-to-trial coverage remains incomplete; missing evidence is not a denial or proof of no designation."}</p>
  </section>;
}
