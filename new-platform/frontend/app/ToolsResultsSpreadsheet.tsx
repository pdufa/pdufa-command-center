"use client";

import {useEffect,useMemo,useState} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";
import TrialTimelineSummary from "./TrialTimelineSummary";
import {parseBenefitFeed,type BenefitFeed} from "../lib/benefit-assessments";
import {SPECIAL_DESIGNATION_CATEGORIES,type DesignationKey} from "../lib/trial-designations";
import type {ToolPdufaApplication} from "../lib/tools-pdufa-links";
import styles from "./FunnelWorkspace.module.css";
import ToolsRankingChecklists from "./ToolsRankingChecklists";

export type ToolSourceEvidence={
  eventKey:string;source:string;designationDate:string;checkedAt:string;
  verification:"FDA_VERIFIED"|"SOURCE_RECORDED"|"UNVERIFIED";note:string;
};
export type ToolsSpreadsheetRow={
  id:string;nctId:string;ticker:string;company:string;drug:string;indication:string;
  stage:string;selectedStage:string;
  timeline?:TimelineDates|null;
  designationMatches:Partial<Record<DesignationKey,ToolSourceEvidence[]>>;
  pdufaApplications?:ToolPdufaApplication[];
  studyRole?:"NOT_ESTABLISHED";
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
const NO_DATES:TimelineDates={phase3DataRelease:null,pdufaTarget:null};
type SortField="nctId"|"ticker"|"company"|"s"|"d"|"drug"|"indication"|"stage";
const sortFields:{key:SortField;label:string;hint?:string}[]=[
  {key:"nctId",label:"NCT / Trial ID"},
  {key:"ticker",label:"Ticker"},
  {key:"company",label:"Company"},
  {key:"s",label:"S",hint:"Days since Phase 3 data release"},
  {key:"d",label:"D",hint:"Days to PDUFA"},
  {key:"drug",label:"Drug / therapy"},
  {key:"indication",label:"Disease / indication"},
  {key:"stage",label:"Recorded stage"},
];
export default function ToolsResultsSpreadsheet({
  rows,summary,designationCoverage,stages,designations,total,offset,loading,error,downloadUrl,
  onPrevious,onNext,nextOffset
}:Props){
  const [sortKey,setSortKey]=useState<SortField>("nctId");
  const [benefitFeed,setBenefitFeed]=useState<BenefitFeed|null>(null);
  const [benefitError,setBenefitError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    void fetch("/api/benefit-assessments",{cache:"no-store",signal:controller.signal})
     .then(async response=>{if(!response.ok)throw Error("BENEFIT_FEED_UNAVAILABLE");return parseBenefitFeed(await response.json());})
     .then(result=>{if(!controller.signal.aborted)setBenefitFeed(result);})
     .catch(()=>{if(!controller.signal.aborted)setBenefitError("Competitive research source unavailable; no edge can be verified.");});
    return ()=>controller.abort();
  },[]);
  const [descending,setDescending]=useState(false);
  const [today,setToday]=useState("");
  useEffect(()=>{const update=()=>setToday(pacificToday());update();const timer=setInterval(update,60000);return ()=>clearInterval(timer);},[]);
  const ordered=useMemo(()=>[...rows].sort((a,b)=>{
    if(sortKey==="s"||sortKey==="d"){
      const key=sortKey==="s"?"daysSincePhase3Release":"daysToPdufa";
      const x=pipelineDayCounts(a.timeline||NO_DATES,today)[key];
      const y=pipelineDayCounts(b.timeline||NO_DATES,today)[key];
      if(x===null)return y===null?0:1;
      if(y===null)return -1;
      return descending?y-x:x-y;
    }
    const result=(a[sortKey]||"").localeCompare(b[sortKey]||"",undefined,{numeric:true,sensitivity:"base"});
    return descending?-result:result;
  }),[rows,sortKey,descending,today]);
  function sort(key:SortField){
    if(sortKey===key)setDescending(prev=>!prev);
    else {setSortKey(key);setDescending(false);}
  }
  const hasSelection=stages.length+designations.length>0;
  const selectedCount=stages.length+designations.length;
  const trialCountUnverified=!!designationCoverage?.noVerifiedNctLinks&&designations.length>0&&!loading&&!error;
  const pageFirst=total>0?offset+1:0;
  const pageLast=Math.min(offset+rows.length,total);
  return <section className={styles.toolsSheet} aria-label="Selected filters and matching clinical trials spreadsheet">
    <div className={styles.toolsSheetHeading}>
      <div>
        <h2>SELECTED TRIALS — SPREADSHEET</h2>
        <p className={styles.muted}>One NCT per trial in the dated $300M–$10B issuer-cap subset across all recorded phases. Both Phase and FDA selectors use this same restricted pool. Documented designations and PDUFA application records attach to these same rows. Phase selections OR, FDA selections OR, and both groups combine AND. PDUFA dates belong to applications; a linked study is not automatically pivotal.</p>
      </div>
      <a className={styles.toolsSheetExport} href={hasSelection&&!loading&&!error?downloadUrl:undefined}
        aria-disabled={!hasSelection||loading||!!error}
        onClick={e=>{if(!hasSelection||loading||!!error)e.preventDefault()}}
        download="pdufa-tools-restricted-trials.csv">
        Export restricted trial matches (CSV)</a>
    </div>
    <div className={styles.toolsSheetMetrics} aria-live="polite">
      <div><span>Selectors clicked</span><strong>{selectedCount}</strong><small>{stages.length} stages + {designations.length} FDA categories</small></div>
      <div><span>Selected restricted stage totals</span><strong>{summary?fmt(summary.stageTotal):hasSelection?"—":"0"}</strong><small>Distinct NCTs within the $300M–$10B issuer-cap subset</small></div>
      <div><span>{designations.length?"FDA source program records":"Verified linked NCT counts"}</span><strong>{designations.length
        ?loading||error?"—":designationCoverage?fmt(designationCoverage.sourcePrograms):"—"
        :summary?fmt(summary.designationCountSum):hasSelection?"—":"0"}</strong>
        <small>{designations.length?"Unscoped source-catalog program records, NOT counts within the restricted trial screen":"Only reviewed FDA-to-NCT links; categories may overlap"}</small></div>
      <div><span>{designations.length?"Verified NCT matches (incomplete)":"Final matching trials"}</span>
        <strong>{hasSelection?(loading||error?"—":summary?fmt(summary.matchingUniqueTrials):"—"):"0"}</strong>
        <small>{trialCountUnverified?"Zero documented NCT matches in the restricted subset; full FDA population remains unknown":designations.length?"Documented FDA-linked subset only; full designation total unknown":"Unique NCT records from restricted issuer-cap screen"}</small></div>
    </div>
    <div className={styles.toolsSheetTotals}>
      <h3>Selected selectors &amp; documented trial matches</h3>
      {selectedCount===0?<p className={styles.muted}>No selectors selected. Choose a stage or FDA designation above to populate this spreadsheet.</p>:<>
        <div className={styles.toolsSheetTableScroll}>
          <table className={styles.toolsSheetSummaryTable}>
            <thead><tr><th>Type</th><th>Clicked selector</th><th>Recorded NCT matches</th><th>Interpretation</th></tr></thead>
            <tbody>
              {stages.map(stage=>{
                const entry=summary?.stageSelectors.find(item=>item.label===stage);
                return <tr key={"stage:"+stage}><td>Stage</td><td>{stage}</td>
                  <td>{entry?fmt(entry.trials):"—"}</td><td>Recorded restricted research stage</td></tr>;
              })}
              {designations.map(key=>{
                const entry=summary?.designationSelectors.find(item=>item.key===key);
                return <tr key={"designation:"+key}><td>FDA program</td><td>{names.get(key)||key}</td>
                  <td>{entry?fmt(entry.linkedTrials):"—"}</td><td>Exact NCT + ticker source-linked positive evidence within restricted subset; full FDA coverage unknown</td></tr>;
              })}
            </tbody>
            <tfoot>
              <tr><th colSpan={2}>TOTAL CLICKED SELECTORS</th><th>{selectedCount}</th><th>Number of checkboxes checked, not number of unique trials</th></tr>
              <tr><th colSpan={2}>{designations.length?"DOCUMENTED NCT MATCHES — TOTAL UNKNOWN":"UNIQUE TRIALS MATCHING COMBINED FILTERS"}</th><th>{summary?fmt(summary.matchingUniqueTrials):"—"}</th><th>OR within each list; AND across the two lists. FDA matches are incomplete and require verified NCT links.</th></tr>
            </tfoot>
          </table>
        </div>
        <p className={styles.muted}>Designation categories may refer to the same trial. Their per-category counts are not added to the final unique-trial total. FDA-selected totals cover only the documented NCT links, not the entire unrestricted source POOL.</p>
      </>}
    </div>
    <div className={styles.toolsSheetTableHeading}>
      <h3>Matching trial records</h3>
      <span>{hasSelection&&!loading&&!error?fmt(total)+(designations.length?" documented FDA-linked matches in restricted subset (partial coverage)":" restricted trial matches"):hasSelection&&loading?"Calculating…":hasSelection&&error?"Unavailable":"0 matching trials"}</span>
    </div>
    <p className={styles.muted}><strong>S</strong> is days since verified public Phase 3 data release; <strong>D</strong> is days to the verified PDUFA target (negative after the target date). Missing source evidence stays Not verified, never zero.</p>
    <ToolsRankingChecklists/>
    <div className={styles.toolsSheetTableScroll} role="region" aria-label="Scrollable spreadsheet containing selected trial matches" tabIndex={0}>
      <table className={styles.toolsSheetGrid}>
        <thead><tr>
          <th className={styles.toolsSheetRowNumber}>#</th>
          {sortFields.map(item=><th key={item.key} title={item.hint||item.label}>
            <button type="button" className={styles.toolsSheetSort} onClick={()=>sort(item.key)}
              aria-label={"Sort visible page by "+(item.hint||item.label)}>
              {item.label}{sortKey===item.key?(descending?" ↓":" ↑"):" ↕"}
            </button>
            {item.hint&&<small>{item.hint}</small>}
          </th>)}
          <th>FDA links <small>Source-recorded, partial</small></th>
          <th>PDUFA application <small>Linked program, not a trial deadline</small></th>
          <th>Study role <small>Pivotal status</small></th>
          {stages.map(stage=><th key={"stage:"+stage} title="Selected stage criterion">{stage}<small>Selected stage</small></th>)}
          {designations.map(key=><th key={"designation:"+key} title="Selected FDA designation category">{names.get(key)||key}<small>FDA designation evidence</small></th>)}
        </tr></thead>
        <tbody>
          {!hasSelection?<tr><td colSpan={12+stages.length+designations.length} className={styles.toolsSheetEmpty}>Select a clinical stage or FDA designation to populate rows.</td></tr>:
          loading?<tr><td colSpan={12+stages.length+designations.length} className={styles.toolsSheetEmpty}>Loading matching trial rows…</td></tr>:
          error?<tr><td colSpan={12+stages.length+designations.length} className={styles.toolsSheetEmpty}>Trial evidence could not be verified. No result total is asserted.</td></tr>:
          ordered.length===0?<tr><td colSpan={12+stages.length+designations.length} className={styles.toolsSheetEmpty}>
            {trialCountUnverified
              ?"No documented FDA-linked NCT matched in this dated restricted research screen. Other source programs remain unlinked; comprehensive trial counts are not established."
              :designations.length>0?"No documented NCT-linked POOL trials match both the chosen phases and FDA categories. Unlinked FDA programs remain visible separately below.":"No restricted-screen NCT trials match the selected phases or text search. Clear the text search or choose other phases."}
          </td></tr>:
          ordered.map((row,i)=>{const days=pipelineDayCounts(row.timeline||NO_DATES,today);return <tr key={row.id}>
            <td className={styles.toolsSheetRowNumber}>{offset+i+1}</td>
            <td><a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(row.nctId)}
              target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
            <td><div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:8,minWidth:295}}>
              <strong>{display(row.ticker)}</strong>
              <TrialTimelineSummary timeline={row.timeline} today={today} compact trial={row} benefitFeed={benefitFeed}/>
            </div></td>
            <td>{display(row.company)}</td>
            <td className={styles.toolsSheetDateValue} title="S: Days since source-verified public Phase 3 results release">
              {days.daysSincePhase3Release===null?<span title="Phase 3 data release not source-verified">Not verified</span>:
                <a href={row.timeline?.phase3DataRelease?.sourceUrl} target="_blank" rel="noopener noreferrer"
                  title={"Verified Phase 3 release: "+row.timeline?.phase3DataRelease?.date}>{days.daysSincePhase3Release.toLocaleString("en-US")}</a>}
            </td>
            <td className={styles.toolsSheetDateValue} title="D: Days to source-verified PDUFA target; negative means target date passed">
              {days.daysToPdufa===null?<span title="PDUFA target date not source-verified">Not verified</span>:
                <a href={row.timeline?.pdufaTarget?.sourceUrl} target="_blank" rel="noopener noreferrer"
                  title={"Verified FDA PDUFA target: "+row.timeline?.pdufaTarget?.date}>{days.daysToPdufa.toLocaleString("en-US")}</a>}
            </td>
            <td>{display(row.drug)}</td>
            <td>{display(row.indication)}</td>
            <td>{display(row.stage)}</td>
            <td>{(()=>{
              const linked=Object.entries(row.designationMatches||{}).filter(([,claims])=>!!claims?.length);
              return linked.length?<details className={styles.toolsSheetEvidence}>
                <summary>{linked.length} documented</summary>
                {linked.map(([key,claims])=><div key={key}>
                  {names.get(key as DesignationKey)||key}
                  {claims?.[0]?.source?<a href={claims[0].source} target="_blank" rel="noopener noreferrer"> · Evidence</a>:null}
                </div>)}
              </details>:<span className={styles.toolsSheetNoMatch}>Not documented</span>;
            })()}</td>
            <td>{row.pdufaApplications?.length?<details className={styles.toolsSheetEvidence}>
              <summary>{row.pdufaApplications.length} saved application{row.pdufaApplications.length===1?"":"s"}</summary>
              {row.pdufaApplications.map(application=><div key={application.eventKey}>
                <strong>{application.targetDate||"Target not recorded"}</strong>
                {" · "}{application.targetConfirmation||"Unverified"}
                {application.savedCheckStatus?" · Status: "+application.savedCheckStatus:""}
                {application.savedOutcome?" · Recorded outcome: "+application.savedOutcome:""}
                {application.decisionDate?" · Recorded decision: "+application.decisionDate:""}
                {application.checkedAt?" · Source checked: "+application.checkedAt.slice(0,10):""}
                {application.evidenceUrl?<a href={application.evidenceUrl} target="_blank" rel="noopener noreferrer"> · Evidence</a>:null}
              </div>)}
            </details>:<span className={styles.toolsSheetNoMatch}>None source-linked</span>}</td>
            <td>Not established</td>
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
          </tr>;})}
        </tbody>
        {hasSelection&&!loading&&!error&&<tfoot><tr>
          <th colSpan={12+stages.length+designations.length}>
            {(designations.length?"Documented FDA-linked NCT matches within restricted subset: ":"Matching restricted NCT trials: ")+fmt(total)} · Selected filters: {selectedCount}
          </th>
        </tr></tfoot>}
      </table>
    </div>
    <div className={styles.pagination}>
      <button type="button" disabled={loading||!!error||offset===0} onClick={onPrevious}>Previous 50</button>
      <span>{"Showing "+pageFirst+"–"+pageLast+" of "+(hasSelection&&!error?fmt(total):"0")+" restricted NCT matches · sorting affects the visible page only"}</span>
      <button type="button" disabled={loading||!!error||nextOffset===null} onClick={onNext}>Next 50</button>
    </div>
    {designations.length>0&&designationCoverage&&designationCoverage.programRows.length>0&&<section className={styles.toolsSheetTotals} aria-label="FDA source programs not yet assigned to clinical trial stages">
      <h3>FDA source program records — not clinical trial counts</h3>
      <p className={styles.muted}>
        <strong>{fmt(designationCoverage.sourcePrograms)} FDA program records in the separate, UNRESTRICTED source catalog</strong> match these FDA categories.
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
      ?"CSV exports only documented NCT matches within the restricted research screen. Unscoped FDA program records appear separately below and are never exported as eligible trials."
      :"This is a read-only web spreadsheet. CSV export includes all documented matching rows (not just this page) and opens in Excel or Google Sheets. FDA designation-to-trial coverage remains incomplete; missing evidence is not a denial or proof of no designation."}</p>
  </section>;
}
