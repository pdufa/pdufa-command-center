"use client";
import {Fragment,useEffect,useMemo,useState} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";
import type {ToolsSpreadsheetRow} from "./ToolsResultsSpreadsheet";
import {SPECIAL_DESIGNATION_CATEGORIES} from "../lib/trial-designations";
import css from "./ToolsOpeningTrialGrid.module.css";
import TrialColumnFilterBar,{applyColumnFilters,type ColumnFilterState,type ColumnFilterField} from "./TrialColumnFilterBar";
import {TOOLS_CLEAR_EVENT,TOOLS_RATINGS_STORAGE_KEY,TOOLS_COMPETITION_STORAGE_KEY,
  readToolsPreference,saveToolsPreference} from "../lib/tools-selection-persistence";
import {COMPETITIVE_STRATEGY_TOPICS} from "../lib/tools-competitive-strategy";
import {parseBenefitFeed,benefitForTrial,type BenefitFeed,type BenefitFact} from "../lib/benefit-assessments";
import {competitiveReadiness,type CompetitivePopulationScan}
  from "../lib/tools-competitive-readiness";
import {auditTrialRatings,type RatingAuditCell,type RatingIngredientKey} from "../lib/tools-rating-engine";
import type {RegistryCoverage} from "../lib/registry-benefit-coverage";
import type {RegistryBenefitResearch} from "../lib/registry-benefit-research";
import {observedSeriousEventRate} from "../lib/registry-observation-math";
import type {RegistryPeerLeads,RegistryPeerDiscoverySummary} from "../lib/registry-competitor-leads";
type Props={
  rows:ToolsSpreadsheetRow[];total:number;offset:number;nextOffset:number|null;
  inventoryMode:boolean;loading:boolean;error:string;
  selectedStages:number;selectedDesignations:number;noVerifiedNctLinks:boolean;
  sourceDate:string;sourceState:string;regulatorySourcesAvailable:boolean;
  competitiveScan?:CompetitivePopulationScan|null;
  onPrevious:()=>void;onNext:()=>void;
};
const format=(n:number)=>n.toLocaleString("en-US");
const safe=(v:string)=>v?.trim()||"Not recorded";
const designationNames=new Map(SPECIAL_DESIGNATION_CATEGORIES.map(({key,label})=>[key,label]));
const extraColumns=3;
function ResearchAuditCell({cell}:{cell:RatingAuditCell}){
  const text=<span className={cell.kind==="unscored"?css.ratingUnscored:css.ratingEvidenceValue}
    title={cell.explanation}>{cell.label}</span>;
  return <div className={css.ratingAudit}>
    {text}
    {cell.kind!=="unscored"&&<details><summary aria-label={"Evidence details for "+cell.label}>Why?</summary>
      <p>{cell.explanation}</p>
      {cell.links.map(link=><p key={link.field+"|"+link.url}>
        <strong>{link.field}</strong> · {link.status.toLowerCase()}
        {" · "}<a href={link.url} target="_blank" rel="noopener noreferrer">
          Source {link.date}</a>
      </p>)}
    </details>}
  </div>;
}
/** On-demand exact-NCT primary-source observations, not treatment effects. */
function RegistryMeasuredDetail({nctId,mode}:{nctId:string;mode:"CL"|"SAF"}){
  const [open,setOpen]=useState(false);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState(false);
  const [packet,setPacket]=useState<RegistryBenefitResearch|null>(null);
  const toggle=()=>{
    setOpen(v=>!v);
    if(open||loading||packet)return;
    setLoading(true);setError(false);
    void fetch("/api/tools-trial-evidence?nct="+encodeURIComponent(nctId),
      {cache:"no-store"}).then(async response=>{
      if(!response.ok)throw Error("REGISTRY_DATA_UNAVAILABLE");
      const item=await response.json() as RegistryBenefitResearch;
      if(item.nctId!==nctId||item.sourceUrl!=="https://clinicaltrials.gov/study/"+nctId
         ||!Array.isArray(item.primary)||!Array.isArray(item.secondary)
         ||!Array.isArray(item.seriousAdverseEvents))throw Error("REGISTRY_DATA_INVALID");
      return item;
    }).then(item=>setPacket(item)).catch(()=>setError(true)).finally(()=>setLoading(false));
  };
  return <div className={css.registryDetail}>
    <button type="button" onClick={toggle} aria-expanded={open}>
      {open?"Hide registry observations":mode==="CL"?"Check trial endpoints":"Check serious-event counts"}
    </button>
    {open&&<div className={css.registryDetailContent}>
      {loading&&<p>Checking exact-NCT source…</p>}
      {error&&<p>Registry measurements unavailable or stale. No result inferred.</p>}
      {packet&&<div>
        {!packet.resultsPosted&&<p>ClinicalTrials.gov has no posted outcome results for this NCT;
          registry completion alone cannot establish a Phase 3 public readout.</p>}
        <p><a href={packet.sourceUrl} target="_blank" rel="noopener noreferrer">
          ClinicalTrials.gov · {nctId}</a></p>
        {mode==="CL"?<>
          {([["Primary",packet.primary],["Secondary",packet.secondary]] as const).map(([label,items])=>
            <div key={label}><strong>{label} reported outcomes ({items.length})</strong>
              {items.slice(0,6).map((outcome,i)=><div key={label+i}>
                <p>{outcome.title} · {outcome.timeFrame||"Time frame not stated"}
                  {" · "}{outcome.unit||"Unit not stated"}</p>
                {outcome.measurements.slice(0,8).map((m,j)=>
                  <p key={j}>{m.group}: {m.value}{m.spread?" (spread "+m.spread+")":""}</p>)}
                {outcome.measurements.length===0&&<p>Measurement not reported</p>}
              </div>)}
              {items.length>6&&<p>Additional outcomes available at source.</p>}
            </div>)}
        </>:<>
          <strong>Reported serious adverse event terms ({packet.seriousAdverseEvents.length})</strong>
          {packet.seriousAdverseEvents.slice(0,12).map((event,i)=><div key={i}>
            <p>{event.term}</p>
            {event.groups.slice(0,8).map((group,j)=>{
              const percent=observedSeriousEventRate(group.affected,group.atRisk);
              return <p key={j}>{group.group}: {group.affected}/{group.atRisk}
                {percent===null?" · frequency unavailable":" · "+percent.toFixed(1)+"% observed"}</p>;
            })}
          </div>)}
          {packet.seriousAdverseEvents.length>12&&
            <p>Additional reported events available at source.</p>}
        </>}
        <p>Raw registry observations only. Population, exposure, adverse-event
          attribution, statistical significance and comparability require review.
          No effectiveness or stock ranking is calculated from these values.</p>
      </div>}
    </div>}
  </div>;
}
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
const filterFields:ColumnFilterField[]=[
 ...columns.map(c=>({key:c.key,label:c.hint||c.label})),
 ...RATING_GROUPS.map(g=>({key:"rating:"+g.key,label:g.key+" — "+g.name})),
 ...RATING_GROUPS.flatMap(g=>g.ingredients.map(v=>({key:"ingredient:"+v.key,label:g.key+" · "+v.name}))),
 {key:"fdaLinks",label:"FDA designation count"},
 {key:"pdufaLinks",label:"PDUFA application count"},
 {key:"studyRole",label:"Study role"},
];
function DayCell({count,date,url,description}:{count:number|null;date?:string;url?:string;description:string}){
  if(count===null)return <span className={css.dateUnknown} title={description+" date not source-verified"}>Not verified</span>;
  return <a href={url} target="_blank" rel="noopener noreferrer"
    title={description+" · verified date "+date+" · calculated in Pacific calendar days"}
    aria-label={description+": "+count+" days; source date "+date}>{count.toLocaleString("en-US")}</a>;
}
export default function ToolsOpeningTrialGrid({
  rows,total,offset,nextOffset,inventoryMode,loading,error,
  selectedStages,selectedDesignations,noVerifiedNctLinks,sourceDate,sourceState,regulatorySourcesAvailable,competitiveScan=null,onPrevious,onNext
}:Props){
  const [sortKey,setSortKey]=useState<Field>("nctId");
  const [columnFilters,setColumnFilters]=useState<ColumnFilterState>({});
  const [desc,setDesc]=useState(false);
  const [today,setToday]=useState("");
  const [expandedRatings,setExpandedRatings]=useState<RatingGroupKey[]>([]);
  const [competitiveOpen,setCompetitiveOpen]=useState(false);
  const [competitionEvidence,setCompetitionEvidence]=useState<BenefitFeed|null>(null);
  const [competitionError,setCompetitionError]=useState(false);
  const [registryCoverage,setRegistryCoverage]=useState<RegistryCoverage|null>(null);
  const [registryUnavailable,setRegistryUnavailable]=useState(false);
  const [peerLeads,setPeerLeads]=useState<Record<string,RegistryPeerLeads>|null>(null);
  const [peerSummary,setPeerSummary]=useState<RegistryPeerDiscoverySummary|null>(null);
  const [peerUnavailable,setPeerUnavailable]=useState(false);
  const [selectionsRestored,setSelectionsRestored]=useState(false);
  useEffect(()=>{
    const raw=readToolsPreference(TOOLS_RATINGS_STORAGE_KEY);
    if(Array.isArray(raw)){
      const allowed=new Set<string>(RATING_GROUPS.map(group=>group.key));
      setExpandedRatings([...new Set(raw.filter((key):key is RatingGroupKey=>
        typeof key==="string"&&allowed.has(key)))]);
    }
    setCompetitiveOpen(readToolsPreference(TOOLS_COMPETITION_STORAGE_KEY)===true);
    setSelectionsRestored(true);
  },[]);
  useEffect(()=>{
    if(!selectionsRestored)return;
    saveToolsPreference(TOOLS_RATINGS_STORAGE_KEY,expandedRatings);
    saveToolsPreference(TOOLS_COMPETITION_STORAGE_KEY,competitiveOpen);
  },[expandedRatings,competitiveOpen,selectionsRestored]);
  useEffect(()=>{
    if(selectedStages+selectedDesignations===0){
      setCompetitionEvidence(null);setCompetitionError(false);return;
    }
    const controller=new AbortController();
    setCompetitionError(false);
    // Rating inputs load whenever trials are selected: opening CS is NOT required.
    void fetch("/api/benefit-assessments",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error("BENEFIT_FEED_UNAVAILABLE");
        return parseBenefitFeed(await response.json());
      })
      .then(data=>{if(!controller.signal.aborted)setCompetitionEvidence(data);})
      .catch(()=>{if(!controller.signal.aborted){setCompetitionEvidence(null);setCompetitionError(true);}});
    return ()=>controller.abort();
  },[selectedStages,selectedDesignations]);
  useEffect(()=>{
    if(selectedStages+selectedDesignations===0){
      setRegistryCoverage(null);setRegistryUnavailable(false);return;
    }
    const controller=new AbortController();
    setRegistryUnavailable(false);
    void fetch("/api/registry-benefit-coverage",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error("REGISTRY_SOURCE_UNAVAILABLE");
        const payload=await response.json() as RegistryCoverage;
        if(payload.schemaVersion!==1||!Array.isArray(payload.records)
          ||!Number.isSafeInteger(payload.scanned)||!Number.isSafeInteger(payload.postedResults))
          throw Error("REGISTRY_SOURCE_INVALID");
        return payload;
      })
      .then(data=>{if(!controller.signal.aborted)setRegistryCoverage(data);})
      .catch(()=>{if(!controller.signal.aborted){setRegistryCoverage(null);setRegistryUnavailable(true);}});
    return ()=>controller.abort();
  },[selectedStages,selectedDesignations]);
  const registryByNct=useMemo(()=>
    new Map(registryCoverage?.records.map(record=>[record.nctId,record])||[]),
    [registryCoverage]);
  useEffect(()=>{
    if(selectedStages+selectedDesignations===0){
      setPeerLeads(null);setPeerSummary(null);setPeerUnavailable(false);return;
    }
    const controller=new AbortController();
    setPeerUnavailable(false);
    void fetch("/api/registry-competitor-leads",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error("PEER_LEADS_UNAVAILABLE");
        const result=await response.json() as {schemaVersion:number;status:string;
          summary:RegistryPeerDiscoverySummary;records:Record<string,RegistryPeerLeads>};
        if(result.schemaVersion!==1||result.status!=="UNVERIFIED_DISCOVERY_ONLY"||
          !result.records||typeof result.records!=="object"||
          result.summary?.scope!=="HISTORICAL_375_PHASE3_REGISTRY_ARCHIVE"||
          !Number.isSafeInteger(result.summary.studiesInArchive)||
          result.summary.studiesInArchive!==Object.keys(result.records).length||
          result.summary.validatedClinicalComparisons!==0||
          result.summary.stockAppreciationRanks!==0)throw Error("PEER_LEADS_INVALID");
        return result;
      })
      .then(data=>{if(!controller.signal.aborted){
        setPeerLeads(data.records);setPeerSummary(data.summary);
      }})
      .catch(()=>{if(!controller.signal.aborted){
        setPeerLeads(null);setPeerSummary(null);setPeerUnavailable(true);
      }});
    return ()=>controller.abort();
  },[selectedStages,selectedDesignations]);
  useEffect(()=>{
    if(typeof window==="undefined")return;
    const clear=()=>{setExpandedRatings([]);setCompetitiveOpen(false);};
    window.addEventListener(TOOLS_CLEAR_EVENT,clear);
    return ()=>window.removeEventListener(TOOLS_CLEAR_EVENT,clear);
  },[]);
  const toggleRating=(key:RatingGroupKey)=>setExpandedRatings(current=>current.includes(key)
    ?current.filter(value=>value!==key):[...current,key]);
  const columnsCount=1+columns.length+extraColumns+1+
    (competitiveOpen?COMPETITIVE_STRATEGY_TOPICS.length:0)+RATING_GROUPS.reduce((n,g)=>
    n+1+(expandedRatings.includes(g.key)?g.ingredients.length:0),0);
  useEffect(()=>{const update=()=>setToday(pacificToday());update();const timer=setInterval(update,60000);return ()=>clearInterval(timer);},[]);
  const filteredPageRows=useMemo(()=>applyColumnFilters(rows,columnFilters,(row,key)=>{
    if(key==="s"||key==="d"){
      const day=pipelineDayCounts(row.timeline||NO_DATES,today);
      return (key==="s"?day.daysSincePhase3Release:day.daysToPdufa)??null;
    }
    if(key==="fdaLinks")return Object.values(row.designationMatches||{}).filter(x=>!!x?.length).length;
    if(key==="pdufaLinks")return row.pdufaApplications?.length||0;
    if(key==="studyRole")return row.studyRole||"Not established";
    if(key.startsWith("rating:")||key.startsWith("ingredient:")){
      const audit=auditTrialRatings(row,today,competitionEvidence,competitionError,
        registryByNct.get(row.nctId)||null,peerLeads?.[row.nctId]||null);
      return key.startsWith("rating:")?
        audit.group[key.slice(7) as RatingGroupKey]?.label||"":
        audit.ingredient[key.slice(11) as RatingIngredientKey]?.label||"";
    }
    const value=row[key as keyof ToolsSpreadsheetRow];
    return typeof value==="string"?value:"";
  }),[rows,columnFilters,today,competitionEvidence,competitionError,registryByNct,peerLeads]);
  const ordered=useMemo(()=>[...filteredPageRows].sort((a,b)=>{
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
  }),[filteredPageRows,sortKey,desc,today]);
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
    {hasSelection&&competitiveScan&&<div className={css.competitionScan} role="status"
      aria-label="Full restricted-pool competitive research eligibility scan">
      <strong>CS Research Readiness Scan · Entire restricted POOL</strong>
      <span>{format(competitiveScan.populationCount)} market-cap-screened NCTs</span>
      <span>{format(competitiveScan.verifiedPublicReadouts)} with source-recorded public Phase 3 readouts</span>
      <span>{format(competitiveScan.openResearchWindow)} in the readout-to-PDUFA-minus-three-day window</span>
      <span>{format(competitiveScan.unknownPdufa)} with readout but PDUFA unverified</span>
      <span>{format(competitiveScan.pastResearchCutoff)} at or past cutoff</span>
      <span>{format(competitiveScan.withoutVerifiedReadout)} without verified readout date</span>
      {competitiveScan.topicSourceAudit?<div className={css.peerSummary}
        aria-label="Full research-window competitive topic evidence coverage">
        <strong>Six-topic source audit · all screened eligible NCTs</strong>
        <span>{format(competitiveScan.topicSourceAudit.verifiedSlots)} /
          {format(competitiveScan.topicSourceAudit.topicSlots)} source-verified topic inputs
          {" · "}{competitiveScan.topicSourceAudit.verifiedPercent===null
            ?"percentage unavailable (no verified open-window trials)"
            :competitiveScan.topicSourceAudit.verifiedPercent.toFixed(1)+"% verified coverage"}</span>
        <span>{format(competitiveScan.topicSourceAudit.modeledOnlySlots)} modeled-only topic inputs
          {" · "}{format(competitiveScan.topicSourceAudit.missingSlots)} without recorded topic evidence</span>
        <span>{format(competitiveScan.topicSourceAudit.trialsWithSixVerifiedTopics)} /
          {format(competitiveScan.topicSourceAudit.eligibleTrials)} trials have at least one
          verified input in all six topics</span>
        <small>Research ledger dated {competitiveScan.topicSourceAudit.sourceFeedAsOf||"not established"}.
          Covers the entire restricted public-readout-to-PDUFA-minus-three-day
          research window, not just 50 visible rows. Unreviewed registry
          packets are not source-verified comparative facts. Evidence-input
          coverage only; not clinical superiority, FDA probability or stock upside.</small>
      </div>:<small>Full research-window topic-input coverage is unavailable.
        No missing-input percentage is inferred.</small>}
      <small>The verified release date is not proof of a complete results dataset
        or pivotal-program qualification. No competitive ranking is established
        by source-field counts.</small>
      {competitiveOpen&&peerSummary&&<div className={css.peerSummary} role="status">
        <strong>Archived competitor discovery · research leads only</strong>
        <span>{format(peerSummary.studiesWithConditionMatchedLeads)} / {format(peerSummary.studiesInArchive)}
          {" "}historical studies have at least one condition-matched research lead</span>
        <span>{format(peerSummary.postedResultStudiesWithLeads)} studies have both posted results
          and at least one peer lead</span>
        <span>{format(peerSummary.totalMatchedStudyLinks)} source-linked study pairings
          across the archive</span>
        <small>Not a complete current competitor inventory. No peer in this count is
          verified as an active, directly comparable or FDA-approved commercial competitor.
          No comparative ranks have been established.</small>
      </div>}
    </div>}
    <TrialColumnFilterBar title="Final trials spreadsheet" fields={filterFields}
      filters={columnFilters} onChange={setColumnFilters}
      hint="Filter the currently loaded trial page, including M–E ratings and every rating ingredient. Multiple filters combine; missing evidence is not a zero score.">
      <span role="status" style={{fontSize:12,color:"#34583f"}}>
        {filteredPageRows.length} of {rows.length} loaded rows visible
      </span>
    </TrialColumnFilterBar>
    <div className={css.scroll} role="region" aria-label="Scrollable clinical trial spreadsheet" tabIndex={0}>
      <table>
        <thead><tr><th className={css.rowNum}>#</th>
          {columns.map(col=><Fragment key={col.key}>
            {col.key==="drug"&&<Fragment>
              <th className={[css.competitionCell,css.competitionStart,
                competitiveOpen?css.competitionOpen:css.competitionEnd].join(" ")}
                data-competition-group="CS"
                title="Competitive Strategy · source-linked monitoring and ranking topics">
                <button type="button" aria-expanded={competitiveOpen}
                  aria-label={(competitiveOpen?"Collapse":"Expand")+" Competitive Strategy monitoring columns after S and D"}
                  onClick={()=>setCompetitiveOpen(v=>!v)}>
                  CS <span aria-hidden="true">{competitiveOpen?"◀":"▶"}</span>
                </button>
                <small>Competitive Strategy</small>
              </th>
              {competitiveOpen&&COMPETITIVE_STRATEGY_TOPICS.map((topic,i)=><th
                key={topic.key} data-competition-topic={topic.key}
                className={[css.competitionCell,css.competitionOpen,
                  i===COMPETITIVE_STRATEGY_TOPICS.length-1?css.competitionEnd:""].join(" ")}
                title={"Monitor: "+topic.monitor+" Ranking: "+topic.rank}>
                <strong>{topic.key}</strong><small>{topic.name}</small>
              </th>)}
            </Fragment>}
            <th className={col.key==="s"||col.key==="d"?css.dayHeading:undefined}
              title={col.hint||col.label}>
              <button type="button" aria-label={"Sort visible trials by "+(col.hint||col.label)}
                onClick={()=>{if(sortKey===col.key)setDesc(v=>!v);else{setSortKey(col.key);setDesc(false);}}}>
                {col.label}{sortKey===col.key?(desc?" ↓":" ↑"):" ↕"}
              </button>
              {col.hint&&<small>{col.hint}</small>}
            </th>
          </Fragment>)}
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
          :ordered.map((row,i)=>{const days=pipelineDayCounts(row.timeline||NO_DATES,today);
            const readiness=competitiveReadiness(row,today,competitionEvidence);
            const audit=auditTrialRatings(row,today,competitionEvidence,competitionError,
              registryByNct.get(row.nctId)||null,peerLeads?.[row.nctId]||null);
            const statusLabel=readiness.status==="NO_VERIFIED_PUBLIC_READOUT"
              ?"Readout not verified":readiness.status==="PDUFA_DATE_UNVERIFIED"
              ?"PDUFA unverified":readiness.status==="PDUFA_CUTOFF_REACHED"
              ?"Past cutoff":"Window open";
            return <tr key={row.id}>
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
            <td className={[css.competitionCell,css.competitionStart,
                competitiveOpen?css.competitionOpen:css.competitionEnd].join(" ")}
                title="Competitive Strategy: source and PDUFA gates are shown, but a validated ranking is not yet available">
              <div className={css.competitionStatus}>
                <strong>Not ranked</strong>
                <small>{statusLabel}</small>
                <details><summary>{readiness.verifiedTopics}/6 CS topics verified</summary>
                  <p>{readiness.evidence.replaceAll("_"," ").toLowerCase()}.
                    Not a verified comparative superiority or stock-appreciation score.</p>
                  <ul>{readiness.reasons.map(reason=><li key={reason}>{reason}</li>)}</ul>
                  {row.timeline?.phase3DataRelease&&<p>
                    <a href={row.timeline.phase3DataRelease.sourceUrl}
                      target="_blank" rel="noopener noreferrer">Source for public Phase 3 readout date</a>
                  </p>}
                </details>
              </div>
            </td>
            {competitiveOpen&&COMPETITIVE_STRATEGY_TOPICS.map((topic,i)=>{
              const record=benefitForTrial(competitionEvidence,row);
              const facts=topic.fields.flatMap(field=>{
                const fact=record?.facts[field] as BenefitFact|undefined;
                return fact?[{field,fact}]:[];
              });
              const verified=facts.filter(f=>f.fact.status==="VERIFIED").length;
              const modeled=facts.filter(f=>f.fact.status==="MODELED").length;
              return <td key={topic.key} data-competition-value={topic.key}
                className={[css.competitionCell,css.competitionOpen,
                  i===COMPETITIVE_STRATEGY_TOPICS.length-1?css.competitionEnd:""].join(" ")}
                title={topic.name+": "+topic.monitor}>
                {!facts.length?<span className={css.ratingUnscored}>{competitionError?"Evidence unavailable":"Not assessed"}</span>:
                  <details className={css.competitionEvidence}>
                    <summary>{verified} verified · {modeled} modeled</summary>
                    {facts.map(({field,fact})=><p key={field}>
                      <strong>{field}</strong> · {String(fact.value)} ({fact.status.toLowerCase()})
                      <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Evidence · {fact.sourceDate}</a>
                    </p>)}
                  </details>}
                {topic.key==="PIPE"&&peerLeads?.[row.nctId]&&
                  peerLeads[row.nctId].totalCandidates>0&&
                  <details className={css.competitionEvidence}>
                    <summary>{peerLeads[row.nctId].totalCandidates} registry peer leads · unverified</summary>
                    <p>Studies share an exact registry condition term and have a distinct recorded
                      intervention. They are NOT confirmed treatment-line competitors,
                      directly comparable therapies, active programs or investment candidates.</p>
                    {peerLeads[row.nctId].displayed.map(peer=><p key={peer.nctId}>
                      <strong>{peer.therapy}</strong> · {peer.sharedConditions.join(" / ")}
                      · {peer.resultsPosted?"Results posted":"Results not posted"}
                      <a href={peer.sourceUrl} target="_blank" rel="noopener noreferrer">
                        {peer.nctId} · Registry source</a>
                    </p>)}
                    {peerLeads[row.nctId].truncated&&<p>Additional unreviewed leads omitted from this view.</p>}
                  </details>}
                {topic.key==="PIPE"&&peerUnavailable&&<span className={css.ratingUnscored}>
                  Registry peer-lead source unavailable</span>}
              </td>;
            })}
            <td className={css.longTextCell}>{safe(row.drug)}</td>
            <td className={css.longTextCell}>{safe(row.indication)}</td>
            <td>{safe(row.stage)}</td>
            {RATING_GROUPS.map(group=>{
              const open=expandedRatings.includes(group.key);
              return <Fragment key={group.key}>
                <td className={[css.ratingCell,open?css.ratingOpen:"",
                    css.ratingStart,!open?css.ratingEnd:""].filter(Boolean).join(" ")}
                    title={group.name+": research input audit, not a validated benefit or investment score"}>
                  <ResearchAuditCell cell={audit.group[group.key]}/>
                </td>
                {open&&group.ingredients.map((ingredient,i)=><td key={ingredient.key}
                  className={[css.ratingCell,css.ratingOpen,
                    i===group.ingredients.length-1?css.ratingEnd:""].filter(Boolean).join(" ")}
                  title={ingredient.name+": source-backed input coverage or explicit unscored status"}>
                  <ResearchAuditCell cell={audit.ingredient[ingredient.key]}/>
                  {(ingredient.key==="CL"||ingredient.key==="SAF")&&
                   /^NCT\d{8}$/.test(row.nctId)&&
                   <RegistryMeasuredDetail nctId={row.nctId} mode={ingredient.key}/>}
                </td>)}
              </Fragment>;
            })}

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
    <div className={css.competitionHelp}>
      <strong>CS — Competitive Strategy:</strong> Tap the CS heading after S and D to reveal six monitoring columns.
      The CS cell now identifies each trial's readout/PDUFA evidence gate and topic readiness.
      It remains Not ranked until comparator-specific conclusions are validated.
      <button type="button" onClick={()=>setCompetitiveOpen(v=>!v)}>
        {competitiveOpen?"Collapse competitive strategy":"Expand competitive strategy"}
      </button>
      <details><summary>What the six columns monitor and how they could rank trials</summary>
        <ol>{COMPETITIVE_STRATEGY_TOPICS.map(topic=><li key={topic.key}>
          <strong>{topic.key} · {topic.name}.</strong> Monitor: {topic.monitor} Rank: {topic.rank}
        </li>)}</ol>
        <p>Monitoring definitions are not scores. A defensible comparative ranking requires
          verified evidence matched to the drug, NCT, indication, treatment line and population,
          with direct comparisons distinguished from indirect evidence.
          Missing values remain Not assessed; source fields are not proof of clinical superiority
          or price appreciation.</p>
      </details>
    </div>
    <div className={css.ratingHelp}>
      <strong>Ratings:</strong> M (Missing), A (Evidence), B (Medical), C (Commercial), D (Stock), E (Final).
      Tap any rating heading to expand its ingredient columns <strong>to the right</strong> inside one outline.
      <button type="button" onClick={()=>setExpandedRatings(RATING_GROUPS.map(g=>g.key))}>Expand all ratings</button>
      <button type="button" onClick={()=>setExpandedRatings([])}>Collapse all ratings</button>
      <span><strong>Research inputs are now connected:</strong> ClinicalTrials.gov primary outcome
        measurements and serious-adverse-event records are shown for exact-matched NCTs when
        the source archive is current; neither is proof of superiority. M counts sourced/modeled/missing inputs;
        A reports evidence and date-gate readiness; B/C/D show supporting evidence coverage where available.
        These are not efficacy, approval-probability, competitive superiority or stock-return scores.
        E's appreciation/grade remains N/A until the ranking method has been validated.
        N/A does not mean zero.</span>
      {registryCoverage&&<span><strong>Historical registry research packets:</strong>{" "}
        {registryCoverage.postedResults} of {registryCoverage.scanned} have posted results.
        <strong> Average four-field coverage:{" "}
          {registryCoverage.meanRegistryCoveragePercent===null?"Not measurable":
            registryCoverage.meanRegistryCoveragePercent.toFixed(1)+"%"}.</strong>{" "}
        {registryCoverage.coverageBuckets.allFour} have all four data categories;
        {registryCoverage.coverageBuckets.partial} have partial data;
        {registryCoverage.coverageBuckets.noMeasurements} have no available
        result measurements; {registryCoverage.coverageBuckets.incompleteExtract}
        have truncated extracts and are excluded from the average.
        Coverage is based on result posting, measured primary outcomes, measured
        secondary outcomes, and serious-event counts. This measures source
        availability only, not efficacy, FDA approval, a competitive rank or stock
        appreciation. This dated 375-trial archive is not your full qualified Pipeline.
      </span>}
      {registryUnavailable&&<span role="status">Registry evidence archive unavailable or stale;
        clinical inputs remain unscored until reverified.</span>}
      {competitiveOpen&&<span>PIPE competitor discovery displays source-linked historical
        trial leads with shared conditions, not validated comparative therapy ratings.
        Those leads are deliberately excluded from CS rankings.</span>}
      {competitionError&&<span role="alert">Research evidence feed unavailable; no unverified result is scored.</span>}
    </div>
    <div className={css.footer}>
      <span>{!hasSelection?"Showing 0 of 0 · No trial filters selected":!loading&&!error?("Showing "+(total?offset+1:0)+"–"+Math.min(offset+rows.length,total)+" of "+format(total)):"Awaiting matching records"} · Page sorting and column filters only</span>
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
