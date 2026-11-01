"use client";

import {useEffect,useMemo,useState,type FormEvent} from "react";
import {SPECIAL_DESIGNATION_CATEGORIES,type DesignationKey} from "../lib/trial-designations";
import styles from "./FunnelWorkspace.module.css";
import PoolDesignationSelector from "./PoolDesignationSelector";
import ToolsResultsSpreadsheet, {type ToolsSpreadsheetRow,type SelectedFiltersSummary} from "./ToolsResultsSpreadsheet";
import ToolsFunnel from "./ToolsFunnel";
import ToolsOptionNumber from "./ToolsOptionNumber";
import ToolsOpeningTrialGrid from "./ToolsOpeningTrialGrid";

type StageCount={trials:number;standaloneResults:number;regulatoryEvents:number;total:number};
type StageStats={
  total:number;trials:number;standaloneResults:number;regulatoryEvents:number;
  stages:Record<string,StageCount>;
};
type PoolRow={id:string;ticker:string;company?:string;drug?:string;indication?:string;stage?:string};
type ProgramCoverage={
  sourcePrograms:number;linkedPrograms:number;unlinkedPrograms:number;
  linkedNcts:number;noVerifiedNctLinks:boolean;
  programRows:{
    eventKey:string;ticker:string;drug:string;indication:string;
    designations:{key:DesignationKey;label:string;source:string}[];
    linkedNcts:string[];
  }[];
};
type PoolResponse={
  view:string;total:number;limit:number;offset:number;nextOffset:number|null;
  inventoryMode?:boolean;
  stageStats:StageStats;rows:PoolRow[];
  overview?:{poolAsOf:string|null;poolSourceState:string};
  designationLinkage?:{basis:string;sourceLinkedTrials:number}|null;
  designationCoverage?:ProgramCoverage|null;
  spreadsheetRows?:ToolsSpreadsheetRow[];
  selectionSummary?:SelectedFiltersSummary|null;
  pipelineResearch?:{screenedTrials:number;screenDate:string;qualification:"NOT_VERIFIED"}|null;
};
const groups=[
  {label:"Early clinical",stages:["Early Phase 1","Phase 1","Phase 1/2","Phase 2","Phase 2/3"]},
  {label:"Phase 3 and results",stages:["Phase 3","Phase 3 Results"]},
  {label:"FDA regulatory and later",stages:["NDA/BLA Submission","FDA Acceptance","PDUFA Decision","Post-Decision","Phase 4"]},
  {label:"Unknown / N.A.",stages:["Not Applicable","Unknown"]},
] as const;
const stages=groups.flatMap(group=>[...group.stages]);
const count=(n:number)=>n.toLocaleString("en-US");
const value=(v?:string)=>v?.trim()||"Not recorded";
const stageCount=(stat:StageCount|undefined)=>stat?.trials??0;

export default function PoolStageExplorer(){
  const [selectedStages,setSelectedStages]=useState<string[]>([]);
  const [expandedStageGroup,setExpandedStageGroup]=useState<string|null>(null);
  const [activeFilter,setActiveFilter]=useState<"phase"|"designation"|null>(null);
  const [selectedDesignations,setSelectedDesignations]=useState<DesignationKey[]>([]);
  const [queryInput,setQueryInput]=useState("");
  const [query,setQuery]=useState("");
  const [offset,setOffset]=useState(0);
  const [page,setPage]=useState<PoolResponse|null>(null);
  const [lastStats,setLastStats]=useState<StageStats|null>(null);
  const [sourceState,setSourceState]=useState("");
  const [sourceDate,setSourceDate]=useState("");
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const hasSelections=selectedStages.length>0||selectedDesignations.length>0;
  const params=useMemo(()=>{
    const p=new URLSearchParams({view:"pool",recordKind:"trials",tools:"1",offset:String(offset),limit:"50"});
    if(selectedStages.length)p.set("stages",selectedStages.join(","));
    if(selectedDesignations.length)p.set("designations",selectedDesignations.join(","));
    if(query.trim()&&(selectedStages.length||selectedDesignations.length))p.set("query",query.trim());
    if(!selectedStages.length&&!selectedDesignations.length)p.set("inventory","1");
    return p.toString();
  },[selectedStages,selectedDesignations,offset,query]);
  const downloadUrl=useMemo(()=>{
    const p=new URLSearchParams(params);
    p.set("format","csv");
    p.set("offset","0");
    return "/api/scope-funnel?"+p.toString();
  },[params]);
  useEffect(()=>{
    const controller=new AbortController();
    setPage(null);
    setLoading(true);setError("");
    void fetch("/api/scope-funnel?"+params,{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok){
          const detail=await response.json().catch(()=>null) as {error?:string}|null;
          throw Error(response.status===401?"Sign in to view the saved POOL.":detail?.error||"Source verification unavailable (HTTP "+response.status+").");
        }
        return response.json() as Promise<PoolResponse>;
      })
      .then(result=>{
        if(controller.signal.aborted)return;
        if(result.view!=="pool"||!result.stageStats||!Array.isArray(result.rows)||
          !Number.isSafeInteger(result.total)||!Number.isSafeInteger(result.stageStats.trials)||
          !result.stageStats.stages||result.rows.length>50||
          !Array.isArray(result.spreadsheetRows)||result.spreadsheetRows.length!==result.rows.length||
          !result.selectionSummary)throw Error("Filtered spreadsheet data could not be validated.");
        setLastStats(result.stageStats);
        setSourceState(result.overview?.poolSourceState||"Unknown");
        setSourceDate(result.overview?.poolAsOf||"Not recorded");
        setPage(result);
      })
      .catch(reason=>{if(!controller.signal.aborted){setPage(null);setError(reason instanceof Error?reason.message:"Unable to load POOL stage data");}})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[params]);
  const stats=page?.stageStats||lastStats;
  function toggleStage(stage:string){
    const next=selectedStages.includes(stage)?selectedStages.filter(item=>item!==stage):[...selectedStages,stage];
    setSelectedStages(next);
    setExpandedStageGroup(groups.find(group=>group.stages.some(item=>item===stage))?.label||null);
    setOffset(0);
  }
  function changeStages(next:string[]){setSelectedStages(next);if(next.length===1)setExpandedStageGroup(groups.find(g=>g.stages.some(item=>next.includes(item)))?.label||null);setOffset(0);}
  function changeDesignations(next:DesignationKey[]){setSelectedDesignations(next);setOffset(0);}
  function findPhase3OrphanTrials(){
    setSelectedStages(["Phase 3"]);
    setExpandedStageGroup("Phase 3 and results");
    setSelectedDesignations(["orphan_drug"]);
    setOffset(0);
    setQuery("");
    setQueryInput("");
  }
  function clearAllTrialSelectors(){
    setActiveFilter(null);
    setSelectedStages([]);
    setExpandedStageGroup(null);
    setSelectedDesignations([]);
    setOffset(0);
    setQuery("");
    setQueryInput("");
  }
  function clearAllToolsSelections(){
    // Clear both filter branches and the locally saved research-ranking checklists,
    // including those unmounted while the full POOL inventory is visible.
    clearAllTrialSelectors();
    try{window.localStorage.removeItem("pdufa-tools-ranking-checklists-v1");}catch{/* Optional storage. */}
    window.dispatchEvent(new Event("pdufa-tools-clear-all-selections"));
  }
  function clearPhaseSection(){
    changeStages([]);
    setExpandedStageGroup(null);
  }
  function selectPhase3Trials(){
    setSelectedStages(["Phase 3"]);
    setExpandedStageGroup("Phase 3 and results");
    setSelectedDesignations([]);
    setOffset(0);
    setQuery("");
    setQueryInput("");
  }
  function submitSearch(event:FormEvent<HTMLFormElement>){event.preventDefault();setQuery(queryInput);setOffset(0);}
  return <section className={styles.panel} aria-label="POOL stage and FDA designation tools" style={{margin:"18px 0"}}>
    <div className={styles.toolsStart} aria-label="Step 1 — choose a filter">
      <div className={styles.toolsStepHeader}>
        <h2>Step 1 · What would you like to select?</h2>
        <button type="button" className={styles.toolsClearAll} onClick={clearAllToolsSelections}
          aria-label="Clear all selections throughout TOOLS">Clear All Selections</button>
      </div>
      <p>Choose Phase or Special Designation. Only that choice opens its next options.</p>
      <div className={styles.toolsStartChoices}>
        <button type="button" className={styles.toolsStartChoice} aria-expanded={activeFilter==="phase"}
          aria-controls="tools-first-phase" onClick={()=>setActiveFilter(open=>open==="phase"?null:"phase")}>
          <ToolsOptionNumber level={1} index={0} total={2}/>
          <span>Phase<small>{selectedStages.length?selectedStages.length+" selected":"Select clinical stages"}</small></span>
          <span aria-hidden="true">{activeFilter==="phase"?"▴":"▾"}</span>
        </button>
        <button type="button" className={styles.toolsStartChoice} aria-expanded={activeFilter==="designation"}
          aria-controls="tools-first-designation" onClick={()=>setActiveFilter(open=>open==="designation"?null:"designation")}>
          <ToolsOptionNumber level={1} index={1} total={2}/>
          <span>Special Designation<small>{selectedDesignations.length?selectedDesignations.length+" selected":"Select FDA categories"}</small></span>
          <span aria-hidden="true">{activeFilter==="designation"?"▴":"▾"}</span>
        </button>
      </div>
      {activeFilter==="phase"&&<div id="tools-first-phase" className={styles.toolsStartPanel}>
        <div className={styles.toolsStepHeader}>
          <h3>Step 2 · Choose a phase category</h3>
          <button type="button" className={styles.toolsClearSection} onClick={clearPhaseSection}
            disabled={selectedStages.length===0}>Clear This Section</button>
        </div>
        <p className={styles.muted}>Tap a numbered category to reveal its Phase options. Check one or more phases to show matching trials.</p>
        <div className={styles.stageDesignationPane}>
          <div className={styles.stageDesignationBody}>
            <div className={styles.stageDropdownActions}>
              <button type="button" onClick={()=>changeStages([...stages])}>Select all</button>
            </div>
            <div className={styles.stageDesignationList} role="group" aria-label="Clinical development stages">
              {groups.map((group,groupIndex)=>{
                const open=expandedStageGroup===group.label;
                const selectedInGroup=group.stages.filter(stage=>selectedStages.includes(stage)).length;
                return <div key={group.label}>
                  <button type="button" className={styles.stageDesignationGroup+" "+styles.toolsCascadeGroup}
                    aria-expanded={open} aria-controls={"tools-stage-group-"+groupIndex}
                    onClick={()=>setExpandedStageGroup(open?null:group.label)}>
                    <ToolsOptionNumber level={2} index={groupIndex} total={groups.length}/>
                    <span>{group.label}{selectedInGroup>0?" · "+selectedInGroup+" selected":""}</span>
                    <strong>{stats?count(group.stages.reduce((sum,name)=>sum+stageCount(stats.stages[name]),0)):"—"} {open?"▴":"▾"}</strong>
                  </button>
                  {open&&<div id={"tools-stage-group-"+groupIndex} className={styles.toolsCascadeChildren} role="group" aria-label={group.label+" stage choices"}>
                    {group.stages.map((stage,stageIndex)=><label key={stage} className={styles.stageCheckboxRow}>
                      <input type="checkbox" checked={selectedStages.includes(stage)} onChange={()=>toggleStage(stage)}/>
                      <ToolsOptionNumber level={3} index={stageIndex} total={group.stages.length}/>
                      <span>{stage}</span>
                      <strong>{stats?count(stageCount(stats.stages[stage])):"—"}</strong>
                    </label>)}
                  </div>}
                </div>;
              })}
            </div>
            <p className={styles.muted}>Unchecked stages have no active selection. Counts alongside stage names describe the complete POOL, not the current combined matches.</p>
          </div>

        </div>
      </div>}
      {activeFilter==="designation"&&<div id="tools-first-designation" className={styles.toolsStartPanel}>
        <div className={styles.toolsStepHeader}>
          <h3>Step 2 · Choose an FDA special designation</h3>
          <button type="button" className={styles.toolsClearSection}
            onClick={()=>changeDesignations([])} disabled={selectedDesignations.length===0}>
            Clear This Section
          </button>
        </div>
        <PoolDesignationSelector guided selected={selectedDesignations} onChange={changeDesignations} poolTrialCount={stats?.trials??null}/>
      </div>}
      <ToolsOpeningTrialGrid
        rows={page?.spreadsheetRows||[]}
        total={page?.total??0}
        offset={offset}
        nextOffset={page?.nextOffset??null}
        inventoryMode={!hasSelections}
        selectedStages={selectedStages.length}
        selectedDesignations={selectedDesignations.length}
        noVerifiedNctLinks={!!page?.designationCoverage?.noVerifiedNctLinks}
        loading={loading}
        error={error}
        sourceDate={sourceDate}
        sourceState={sourceState}
        onPrevious={()=>setOffset(Math.max(0,offset-50))}
        onNext={()=>{if(page?.nextOffset!==null&&page?.nextOffset!==undefined)setOffset(page.nextOffset);}}
      />
      {hasSelections&&<div className={styles.toolsStartSelected} role="status">
        <strong>{selectedStages.length} Phase selected · {selectedDesignations.length} Special Designation selected</strong>
      </div>}
    </div>
    {hasSelections&&<>
    <ToolsFunnel
      poolNcts={stats?.trials??null}
      pipelineResearch={page?.pipelineResearch??null}
      selectedTrials={!hasSelections?0:loading||!!error?null:page?.total??null}
      selectedPhasePoolTrials={selectedStages.length&&stats?selectedStages.reduce((sum,stage)=>sum+stageCount(stats.stages[stage]),0):null}
      selectedStages={selectedStages.length}
      totalStages={stages.length}
      selectedStageLabels={selectedStages}
      selectedDesignationLabels={selectedDesignations.map(key=>SPECIAL_DESIGNATION_CATEGORIES.find(item=>item.key===key)?.label||key)}
      selectedDesignations={selectedDesignations.length}
      designationUniqueTrials={page?.selectionSummary?.designationUniqueTrials??null}
      designationCoverage={page?.designationCoverage??null}
      loading={loading}
      error={error}
      searchActive={Boolean(query.trim())}
      sourceDate={sourceDate}
      sourceState={sourceState}
    />

    <details className={styles.toolsAdvanced}>
      <summary>Quick filters and shortcuts</summary>
    <div className={styles.toolsQuickFilter}>
      <button type="button" onClick={selectPhase3Trials} aria-label="Select Phase 3 clinical stage to display screened trial matches">
        Select Phase 3 trials
      </button>
      <button type="button" onClick={findPhase3OrphanTrials} aria-label="Select Phase 3 and Orphan Drug Designation together">
        Find Phase 3 + Orphan Drug trials
      </button>
      <small>TRIALS shows 0 until a clinical stage or FDA designation is selected. PIPELINE retains its separate historical screened candidate total.</small>
    </div>

    </details>
    <form onSubmit={submitSearch} className={styles.search} style={{margin:"16px 0"}}>
      <input aria-label="Search trial NCT, ticker, company, drug or disease" type="search"
        value={queryInput} onChange={e=>setQueryInput(e.target.value)} maxLength={100}
        placeholder="Search selected results by NCT, ticker, drug or disease"/>
      <button type="submit">Search results</button>
      <button type="button" onClick={()=>{setQueryInput("");setQuery("");setOffset(0)}}>Clear search</button>
    </form>
    <p className={styles.muted}><strong>Filter logic:</strong> Selected stages are OR; selected designations are OR; choosing from both applies AND. A designation-only selection covers any recorded stage. A stage-only selection does not require a known designation. All counts are read-only.</p>
    {stats&&<p className={styles.muted}>Published POOL: {count(stats.trials)} unique NCT trials, plus {count(stats.standaloneResults+stats.regulatoryEvents)} separate source/event records. Source state: {value(sourceState)} · as of {value(sourceDate)}.</p>}
    {hasSelections&&loading&&<p role="status">Calculating matching trial records from saved sources…</p>}
    {error&&<p className={styles.error} role="alert">Results unavailable: {error} (not a verified zero).</p>}
    {!hasSelections&&<p role="status"><strong>0 selected · 0 matching trials.</strong> Choose at least one stage or FDA designation above to populate TRIALS.</p>}
    {hasSelections&&page&&!loading&&selectedDesignations.length>0&&!page.designationCoverage?.noVerifiedNctLinks&&<p className={styles.muted}>
      FDA-filtered results: {count(page.designationLinkage?.sourceLinkedTrials??0)} documented linked NCT trials before stage filtering (partial evidence coverage).
    </p>}
    <ToolsResultsSpreadsheet
      rows={page?.spreadsheetRows||[]}
      summary={page?.selectionSummary||null}
      designationCoverage={page?.designationCoverage??null}
      stages={selectedStages}
      designations={selectedDesignations}
      total={page?.total||0}
      offset={offset}
      loading={hasSelections&&loading}
      error={hasSelections?error:""}
      downloadUrl={downloadUrl}
      onPrevious={()=>setOffset(Math.max(0,offset-50))}
      onNext={()=>{if(page?.nextOffset!==null&&page?.nextOffset!==undefined)setOffset(page.nextOffset);}}
      nextOffset={page?.nextOffset??null}
    />
    </>}
  </section>;
}
