"use client";
import {Fragment,useEffect,useMemo,useState} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";
import type {ToolsSpreadsheetRow} from "./ToolsResultsSpreadsheet";
import {SPECIAL_DESIGNATION_CATEGORIES} from "../lib/trial-designations";
import css from "./ToolsOpeningTrialGrid.module.css";
import {TOOLS_CLEAR_EVENT,TOOLS_RATINGS_STORAGE_KEY,readToolsPreference,saveToolsPreference}
  from "../lib/tools-selection-persistence";
type Props={
  rows:ToolsSpreadsheetRow[];total:number;offset:number;nextOffset:number|null;
  inventoryMode:boolean;loading:boolean;error:string;
  selectedStages:number;selectedDesignations:number;noVerifiedNctLinks:boolean;
  sourceDate:string;sourceState:string;regulatorySourcesAvailable:boolean;
  onPrevious:()=>void;onNext:()=>void;
};
const format=(n:number)=>n.toLocaleString("en-US");
const safe=(v:string)=>v?.trim()||"Not recorded";
const designationNames=new Map(SPECIAL_DESIGNATION_CATEGORIES.map(({key,label})=>[key,label]));
const extraColumns=3;
const RATING_GROUPS=[
 {key:"M",name:"Missing",ingredients:[{key:"VER",name:"Verified inputs"},{key:"MOD",name:"Modeled inputs"},{key:"MISS",name:"Missing inputs"},{key:"CRIT",name:"Critical gaps"}]},
 {key:"A",name:"Evidence",ingredients:[{key:"ER",name:"Evidence readiness"},{key:"FDA",name:"Regulatory readiness"}]},
 {key:"B",name:"Medical",ingredients:[{key:"CL",name:"Clinical benefit"},{key:"SAF",name:"Safety"},{key:"COMP",name:"Competitive advantage"}]},
 {key:"C",name:"Commercial",ingredients:[{key:"POP",name:"Patient opportunity"},{key:"ACCESS",name:"Commercial access"},{key:"REV",name:"Revenue potential"}]},
 {key:"D",name:"Stock",ingredients:[{key:"VAL",name:"Valuation opportunity"},{key:"CASH",name:"Financial strength"},{key:"MOM",name:"Stock momentum"},{key:"FLOW",name:"Ownership and trading"},{key:"CAT",name:"Catalyst setup"}]},
 {key:"E",name:"Final",ingredients:[{key:"APP",name:"Appreciation opportunity"},{key:"READY",name:"Research readiness"},{key:"GRADE",name:"Opportunity grade"}]}
] as const;
type RatingGroupKey=typeof RATING_GROUPS[number]["key"];
const NO_DATES:TimelineDates={phase3DataRelease:null,pdufaTarget:null};
type Field="nctId"|"ticker"|"company"|"s"|"d"|"drug"|"indication"|"stage";
const columns:{key:Field;label:string;hint?:string}[]=[
  {key:"nctId",label:"NCT Trial ID"},
  {key:"ticker",label:"Ticker"},
  {key:"company",label:"Company"},
  {key:"s",label:"S",hint:"Days since Phase 3 data release"},
  {key:"d",label:"D",hint:"Days to PDUFA"},
  {key:"drug",label:"Drug / therapy"},
  {key:"indication",label:"Disease / indication"},
  {key:"stage",label:"Recorded stage"}
];
function DayCell({count,date,url,description}:{count:number|null;date?:string;url?:string;description:string}){
  if(count===null)return <span className={css.dateUnknown} title={description+" date not source-verified"}>Not verified</span>;
  return <a href={url} target="_blank" rel="noopener noreferrer"
    title={description+" · verified date "+date+" · calculated in Pacific calendar days"}
    aria-label={description+": "+count+" days; source date "+date}>{count.toLocaleString("en-US")}</a>;
}
export default function ToolsOpeningTrialGrid({
  rows,total,offset,nextOffset,inventoryMode,loading,error,
  selectedStages,selectedDesignations,noVerifiedNctLinks,sourceDate,sourceState,regulatorySourcesAvailable,onPrevious,onNext
}:Props){
  const [sortKey,setSortKey]=useState<Field>("nctId");
  const [desc,setDesc]=useState(false);
  const [today,setToday]=useState("");
  const [expandedRatings,setExpandedRatings]=useState<RatingGroupKey[]>([]);
  const [selectionsRestored,setSelectionsRestored]=useState(false);
  useEffect(()=>{
    const raw=readToolsPreference(TOOLS_RATINGS_STORAGE_KEY);
    if(Array.isArray(raw)){
      const allowed=new Set<string>(RATING_GROUPS.map(group=>group.key));
      setExpandedRatings([...new Set(raw.filter((key):key is RatingGroupKey=>
        typeof key==="string"&&allowed.has(key)))]);
    }
    setSelectionsRestored(true);
  },[]);
  useEffect(()=>{
    if(!selectionsRestored)return;
    saveToolsPreference(TOOLS_RATINGS_STORAGE_KEY,expandedRatings);
  },[expandedRatings,selectionsRestored]);
  useEffect(()=>{
    const clear=()=>setExpandedRatings([]);
    window.addEventListener(TOOLS_CLEAR_EVENT,clear);
    return ()=>window.removeEventListener(TOOLS_CLEAR_EVENT,clear);
  },[]);
  const toggleRating=(key:RatingGroupKey)=>setExpandedRatings(current=>current.includes(key)
    ?current.filter(value=>value!==key):[...current,key]);
  const columnsCount=1+columns.length+extraColumns+RATING_GROUPS.reduce((n,g)=>
    n+1+(expandedRatings.includes(g.key)?g.ingredients.length:0),0);
  useEffect(()=>{const update=()=>setToday(pacificToday());update();const timer=setInterval(update,60000);return ()=>clearInterval(timer);},[]);
  const ordered=useMemo(()=>[...rows].sort((a,b)=>{
    if(sortKey==="s"||sortKey==="d"){
      const field=sortKey==="s"?"daysSincePhase3Release":"daysToPdufa";
      const x=pipelineDayCounts(a.timeline||NO_DATES,today)[field];
      const y=pipelineDayCounts(b.timeline||NO_DATES,today)[field];
      // Missing source dates stay below known numbers, even when sort reverses.
      if(x===null)return y===null?0:1;
      if(y===null)return -1;
      return desc?y-x:x-y;
    }
    const n=(a[sortKey]||"").localeCompare(b[sortKey]||"",undefined,{numeric:true,sensitivity:"base"});
    return desc?-n:n;
  }),[rows,sortKey,desc,today]);
  const hasSelection=selectedStages+selectedDesignations>0;
  // FDA and PDUFA attributes belong to each NCT row; neither creates a second trial.
  const countUnverified=hasSelection&&selectedDesignations>0&&noVerifiedNctLinks&&!loading&&!error;
  return <section className={css.root} aria-label="Live trial inventory spreadsheet">
    <div className={css.heading}>
      <div>
        <h2>Step 5 · {inventoryMode?"Final Trials Spreadsheet — awaiting selection":"Final Trials Spreadsheet — filtered trial matches"}</h2>
        <p>{inventoryMode
          ?"No trial rows are displayed until you select at least one Phase or Special Designation in Step 3. The restricted POOL and PIPELINE counts remain available above."
          :"One NCT per row from the $300M–$10B issuer-cap subset, across all recorded phases. Phase and FDA options filter this same universe; FDA/PDUFA coverage remains partial."}</p>
      </div>
      <strong className={css.count} role="status">{!hasSelection?"0 trials shown · no selections":loading?"Loading…":error?"Unavailable":format(total)+" restricted NCT matches"}</strong>
    </div>
    <div className={css.scroll} role="region" aria-label="Scrollable clinical trial spreadsheet" tabIndex={0}>
      <table>
        <thead><tr><th className={css.rowNum}>#</th>
          {columns.map(col=><th key={col.key} className={col.key==="s"||col.key==="d"?css.dayHeading:undefined}
            title={col.hint||col.label}>
            <button type="button" aria-label={"Sort visible trials by "+(col.hint||col.label)}
              onClick={()=>{if(sortKey===col.key)setDesc(v=>!v);else{setSortKey(col.key);setDesc(false);}}}>
              {col.label}{sortKey===col.key?(desc?" ↓":" ↑"):" ↕"}
            </button>
            {col.hint&&<small>{col.hint}</small>}
          </th>)}
          {RATING_GROUPS.map(group=>{
            const open=expandedRatings.includes(group.key);
            const outer=[css.ratingCell,open?css.ratingOpen:"",css.ratingStart,
              !open?css.ratingEnd:""].filter(Boolean).join(" ");
            return <Fragment key={group.key}>
              <th className={outer} data-rating-group={group.key}
                title={group.name+" combined rating; "+(open?"hide":"show")+" ingredient columns to the right"}>
                <button type="button" aria-expanded={open}
                  aria-label={(open?"Collapse ":"Expand ")+group.key+" "+group.name+" rating ingredients to the right"}
                  onClick={()=>toggleRating(group.key)}>
                  {group.key} <span aria-hidden="true">{open?"◀":"▶"}</span>
                </button>
                <small className={css.ratingGroupLabel}>{group.name}</small>
              </th>
              {open&&group.ingredients.map((ingredient,i)=><th key={ingredient.key}
                data-rating-ingredient={ingredient.key}
                className={[css.ratingCell,css.ratingOpen,
                  i===group.ingredients.length-1?css.ratingEnd:""].filter(Boolean).join(" ")}
                title={ingredient.name}>
                <span className={css.ratingIngredientHeading}>{ingredient.key}</span>
              </th>)}
            </Fragment>;
          })}
          <th>FDA designations <small>Documented subset</small></th>
          <th>PDUFA applications <small>Saved targets, not trial deadlines</small></th>
          <th>Study role</th>
        </tr></thead>
        <tbody>
          {!hasSelection?<tr><td colSpan={columnsCount} className={css.empty}>Select at least one Phase or Special Designation in Step 3 to populate this spreadsheet.</td></tr>
          :loading?<tr><td colSpan={columnsCount} className={css.empty}>Loading matching trial records…</td></tr>
          :error?<tr><td colSpan={columnsCount} className={css.empty}>Cannot verify the trial inventory: {error}. No zero count assumed.</td></tr>
          :ordered.length===0?<tr><td colSpan={columnsCount} className={css.empty}>
            {countUnverified?"No documented NCT matches within the restricted research subset. Full FDA trial coverage remains unknown."
              :hasSelection?"No documented trials match these selected criteria. Try a different Phase or FDA category."
              :"No trial records are available from the published source."}
          </td></tr>
          :ordered.map((row,i)=>{const days=pipelineDayCounts(row.timeline||NO_DATES,today);return <tr key={row.id}>
            <td className={css.rowNum}>{offset+i+1}</td>
            <td><a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(row.nctId)} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
            <td>{safe(row.ticker)}</td>
            <td className={css.longTextCell}>{safe(row.company)}</td>
            <td className={css.dayCell}><DayCell count={days.daysSincePhase3Release}
              date={row.timeline?.phase3DataRelease?.date} url={row.timeline?.phase3DataRelease?.sourceUrl}
              description="S · Days since verified Phase 3 data release"/></td>
            <td className={css.dayCell}><DayCell count={days.daysToPdufa}
              date={row.timeline?.pdufaTarget?.date} url={row.timeline?.pdufaTarget?.sourceUrl}
              description="D · Days to verified PDUFA target"/></td>
            {RATING_GROUPS.map(group=>{
              const open=expandedRatings.includes(group.key);
              return <Fragment key={group.key}>
                <td className={[css.ratingCell,open?css.ratingOpen:"",
                    css.ratingStart,!open?css.ratingEnd:""].filter(Boolean).join(" ")}
                    title={group.name+" combined rating not yet calculated from verified research"}>
                  <span className={css.ratingUnscored}>N/A</span>
                </td>
                {open&&group.ingredients.map((ingredient,i)=><td key={ingredient.key}
                  className={[css.ratingCell,css.ratingOpen,
                    i===group.ingredients.length-1?css.ratingEnd:""].filter(Boolean).join(" ")}
                  title={ingredient.name+": not yet scored from verified source data"}>
                  <span className={css.ratingUnscored}>N/A</span>
                </td>)}
              </Fragment>;
            })}
            <td className={css.longTextCell}>{safe(row.drug)}</td>
            <td className={css.longTextCell}>{safe(row.indication)}</td>
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
              </details>:<span>{regulatorySourcesAvailable?"Not documented":"FDA source unavailable"}</span>;
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
            </details>:<span>{regulatorySourcesAvailable?"No exact linked application recorded":"PDUFA source unavailable"}</span>}</td>
            <td>Not established</td>
          </tr>;})}
        </tbody>
      </table>
    </div>
    <div className={css.ratingHelp}>
      <strong>Ratings:</strong> M (Missing), A (Evidence), B (Medical), C (Commercial), D (Stock), E (Final).
      Tap any rating heading to expand its ingredient columns <strong>to the right</strong> inside one outline.
      <button type="button" onClick={()=>setExpandedRatings(RATING_GROUPS.map(g=>g.key))}>Expand all ratings</button>
      <button type="button" onClick={()=>setExpandedRatings([])}>Collapse all ratings</button>
      <span>N/A means no source-verified score has been computed; it does not mean zero.</span>
    </div>
    <div className={css.footer}>
      <span>{!hasSelection?"Showing 0 of 0 · No trial filters selected":!loading&&!error?("Showing "+(total?offset+1:0)+"–"+Math.min(offset+rows.length,total)+" of "+format(total)):"Awaiting matching records"} · Page sort only</span>
      <div className={css.pager}>
        <button type="button" disabled={!hasSelection||loading||!!error||offset===0} onClick={onPrevious}>Previous 50</button>
        <button type="button" disabled={!hasSelection||loading||!!error||nextOffset===null} onClick={onNext}>Next 50</button>
      </div>
    </div>
    <p className={css.source}><strong>S</strong> = whole days since a source-verified public Phase 3 data release; <strong>D</strong> = whole days until a source-verified FDA PDUFA target (negative means the target date passed). Dates are Pacific-calendar-based; Not verified is not zero. Linked applications alone do not establish an exact trial's PDUFA date. {!regulatorySourcesAvailable?"FDA/PDUFA enrichment source unavailable for this request; absence of a link is not established. ":""}FDA designation and PDUFA application coverage is incomplete. A PDUFA target is application-level; the linked NCT is not automatically pivotal. Published source: {sourceDate||"Not recorded"} · State: {sourceState||"Unverified"}.
      {inventoryMode?" This inventory is the restricted dated research subset, not the unrestricted published POOL or a verified trade-ready Pipeline.":""}
      {hasSelection&&selectedDesignations>0?" FDA program records lacking NCT links cannot be treated as zero trials.":""}
    </p>
  </section>;
}
