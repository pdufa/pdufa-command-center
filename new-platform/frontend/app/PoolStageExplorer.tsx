"use client";

import {useEffect,useMemo,useState,type FormEvent} from "react";
import {SPECIAL_DESIGNATION_CATEGORIES,type DesignationKey} from "../lib/trial-designations";
import type {ToolsDesignationTotals,ToolsContextualDesignationCounts} from "../lib/tools-pool-inventory";
import styles from "./FunnelWorkspace.module.css";
import PoolDesignationSelector from "./PoolDesignationSelector";
import ToolsResultsSpreadsheet, {type ToolsSpreadsheetRow,type SelectedFiltersSummary} from "./ToolsResultsSpreadsheet";
import ToolsFunnel from "./ToolsFunnel";
import ToolsOptionNumber from "./ToolsOptionNumber";
import ToolsOpeningTrialGrid from "./ToolsOpeningTrialGrid";
import ToolsAssessmentSection from "./ToolsAssessmentSection";
import {TOOLS_CLEAR_EVENT,TOOLS_FILTERS_STORAGE_KEY,readToolsPreference,saveToolsPreference,
  parseToolsFilterSelections,clearToolsPreferences} from "../lib/tools-selection-persistence";

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
  regulatorySourcesAvailable?:boolean;
  restrictedScope?:{
    scope:"DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN";
    qualification:"NOT_VERIFIED";capAsOf:string;unverifiedCapTrials:number;outsideCapTrials:number;excludedIssuerTrials:number;eligibleIssuers:number;
    originalPoolTrials:number;screenedTrials:number;outstanding:string[];
  };
  view:string;total:number;limit:number;offset:number;nextOffset:number|null;
  inventoryMode?:boolean;
  stageStats:StageStats;rows:PoolRow[];
  overview?:{poolAsOf:string|null;poolSourceState:string};
  designationLinkage?:{basis:string;sourceLinkedTrials:number}|null;
  designationTotals?:ToolsDesignationTotals|null;
  designationScopeSummary?:{documentedCategoryLinks:number;documentedUniqueTrials:number;coverage:"PARTIAL"}|null;
  contextualDesignationCounts?:ToolsContextualDesignationCounts|null;
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
  const [selectionsRestored,setSelectionsRestored]=useState(false);
  // Read saved checkboxes and search before the first filtered API request. Do not
  // persist initial empty React defaults over the saved selections on hydration.
  useEffect(()=>{
    const saved=parseToolsFilterSelections(readToolsPreference(TOOLS_FILTERS_STORAGE_KEY),stages);
    if(saved){
      setSelectedStages(saved.selectedStages);
      setSelectedDesignations(saved.selectedDesignations);
      setActiveFilter(saved.activeFilter);
      setQuery(saved.query);
      setQueryInput(saved.queryInput);
      setOffset(saved.offset);
    }
    setSelectionsRestored(true);
  },[]);
  useEffect(()=>{
    if(!selectionsRestored)return;
    saveToolsPreference(TOOLS_FILTERS_STORAGE_KEY,{
      selectedStages,selectedDesignations,activeFilter,query,queryInput,offset
    });
  },[selectionsRestored,selectedStages,selectedDesignations,activeFilter,query,queryInput,offset]);
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
    if(!selectionsRestored)return;
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
        if(result.view!=="pool"||!result.restrictedScope||
          result.restrictedScope.scope!=="DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN"||
          !result.stageStats||!Array.isArray(result.rows)||
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
  },[params,selectionsRestored]);
  const stats=page?.stageStats||lastStats;
  const selectedPhaseTrials=selectedStages.reduce((sum,stage)=>sum+stageCount(stats?.stages[stage]),0);
  function toggleStage(stage:string){
    const next=selectedStages.includes(stage)?selectedStages.filter(item=>item!==stage):[...selectedStages,stage];
    setSelectedStages(next);
    setOffset(0);
  }
  function changeStages(next:string[]){setSelectedStages(next);setOffset(0);}
  function changeDesignations(next:DesignationKey[]){setSelectedDesignations(next);setOffset(0);}
  function findPhase3OrphanTrials(){
    setSelectedStages(["Phase 3"]);
    setSelectedDesignations(["orphan_drug"]);
    setOffset(0);
    setQuery("");
    setQueryInput("");
  }
  function clearAllTrialSelectors(){
    setActiveFilter(null);
    setSelectedStages([]);
    setSelectedDesignations([]);
    setOffset(0);
    setQuery("");
    setQueryInput("");
  }
  function clearAllToolsSelections(){
    // Clear both filter branches and the locally saved research-ranking checklists,
    // including those unmounted while the full POOL inventory is visible.
    clearAllTrialSelectors();
    // Explicit global clear is the only action that forgets selections in all
    // TOOLS sections. Individual "Clear This Section" buttons remain scoped.
    clearToolsPreferences();
    window.dispatchEvent(new Event(TOOLS_CLEAR_EVENT));
  }
  function clearPhaseSection(){
    changeStages([]);
  }
  function selectPhase3Trials(){
    setSelectedStages(["Phase 3"]);
    setSelectedDesignations([]);
    setOffset(0);
    setQuery("");
    setQueryInput("");
  }
  function submitSearch(event:FormEvent<HTMLFormElement>){event.preventDefault();setQuery(queryInput);setOffset(0);}
  return <section className={styles.panel} aria-label="POOL stage and FDA designation tools" style={{margin:"18px 0"}}>
    {/* Always-visible source-backed POOL → PIPELINE → TRIALS flow. Show it first,
        before Step 3 controls, and keep it live as selections change. */}
    <ToolsFunnel
      poolNcts={page?.restrictedScope?.originalPoolTrials??null}
      pipelineResearch={page?.pipelineResearch??null}
      selectedTrials={!hasSelections?0:loading||!!error?null:page?.total??null}
      selectedPhasePoolTrials={selectedStages.length&&stats?selectedPhaseTrials:null}
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

    <div className={styles.toolsStart} aria-label="Step 3 — filter by phase or FDA designation">
      <div className={styles.toolsStepHeader}>
        <h2>Step 3 · What would you like to select?</h2>
        <button type="button" className={styles.toolsClearAll} onClick={clearAllToolsSelections}
          aria-label="Clear all selections throughout TOOLS">Clear All Selections</button>
      </div>
      <p><strong>Correct sequence:</strong> Published POOL → publicly listed issuer with saved verified $300M–$10B market cap → analyze <strong>Phase</strong> and <strong>Special Designation</strong> separately. No Phase 3 restriction is applied before you choose a Phase.</p>
      {page?.restrictedScope&&<p className={styles.muted}>Scope: {count(page.restrictedScope.screenedTrials)} NCT trials from {count(page.restrictedScope.originalPoolTrials)} published POOL NCTs · {count(page.restrictedScope.eligibleIssuers)} issuers · cap values checked {page.restrictedScope.capAsOf.slice(0,10)}.</p>}
      {page?.restrictedScope&&<p className={styles.muted}><strong>POOL → market-cap reconciliation:</strong> {count(page.restrictedScope.screenedTrials)} inside $300M–$10B · {count(page.restrictedScope.outsideCapTrials)} outside range · {count(page.restrictedScope.unverifiedCapTrials)} missing/stale/unverified cap · {count(page.restrictedScope.excludedIssuerTrials)} missing/unsupported listed-issuer evidence. The last two groups are <strong>unresolved, not proven outside the cap range</strong>.</p>}
      <div className={styles.toolsStartChoices}>
        <button type="button" className={styles.toolsStartChoice} aria-expanded={activeFilter==="phase"}
          aria-controls="tools-first-phase" onClick={()=>setActiveFilter(open=>open==="phase"?null:"phase")}>
          <ToolsOptionNumber level={3} index={0} total={2}/>
          <span>Phase ({page?.restrictedScope?count(page.restrictedScope.screenedTrials):"—"})<small>{selectedStages.length?selectedStages.length+" selected":"Select clinical stages"}</small></span>
          <span aria-hidden="true">{activeFilter==="phase"?"▴":"▾"}</span>
        </button>
        <button type="button" className={styles.toolsStartChoice} aria-expanded={activeFilter==="designation"}
          aria-controls="tools-first-designation" onClick={()=>setActiveFilter(open=>open==="designation"?null:"designation")}>
          <ToolsOptionNumber level={3} index={1} total={2}/>
          <span>Special Designation ({page?.designationScopeSummary?count(page.designationScopeSummary.documentedCategoryLinks):"—"})<small>{page?.designationScopeSummary?count(page.designationScopeSummary.documentedUniqueTrials)+" documented trials · partial":page&&page.regulatorySourcesAvailable===false?"FDA source unavailable":"Documented category links · partial"}{selectedDesignations.length?" · "+selectedDesignations.length+" selected":" · Select FDA categories"}</small></span>
          <span aria-hidden="true">{activeFilter==="designation"?"▴":"▾"}</span>
        </button>
      </div>
      {activeFilter==="phase"&&<div id="tools-first-phase" className={styles.toolsStartPanel}>
        <div className={styles.toolsStepHeader}>
          <h3>Step 3A · Choose a clinical phase</h3>
          <button type="button" className={styles.toolsClearSection} onClick={clearPhaseSection}
            disabled={selectedStages.length===0}>Clear This Section</button>
        </div>
        <p className={styles.muted}><strong>Step 3A Phase breakdown:</strong> {stats?count(stats.trials):"—"} NCT trials across 14 mutually exclusive recorded stages, all inside the $300M–$10B market-cap screen. The counts below do not change when FDA categories are checked.</p>
        {selectedStages.length>0&&<p role="status" className={styles.muted}>{selectedStages.length} stage choices selected · {count(selectedPhaseTrials)} NCT trials across those stages, before any FDA or text-search intersection.</p>}
        <div className={styles.stageDesignationPane}>
          <div className={styles.stageDesignationBody}>
            <div className={styles.stageDropdownActions}>
              <button type="button" onClick={()=>changeStages([...stages])}>Select all</button>
            </div>
            <div className={styles.stageDesignationList} role="group" aria-label="Clinical development stages">
              {stages.map((stage,stageIndex)=><label key={stage} className={styles.stageCheckboxRow}>
                <input type="checkbox" checked={selectedStages.includes(stage)}
                  onChange={()=>toggleStage(stage)}/>
                <ToolsOptionNumber level={2} index={stageIndex} total={stages.length}/>
                <span>{stage}</span>
                <strong title="NCT trials in this stage, within the $300M–$10B issuer-cap screen">{stats?count(stageCount(stats.stages[stage])):"—"}</strong>
              </label>)}
            </div>
            <p className={styles.muted}>All phases are measured independently within the $300M–$10B issuer-cap subset. No phase is preselected; selecting an FDA designation additionally filters the trial results.</p>
          </div>

        </div>
      </div>}
      {activeFilter==="designation"&&<div id="tools-first-designation" className={styles.toolsStartPanel}>
        <div className={styles.toolsStepHeader}>
          <h3>Step 3B · Choose an FDA special designation</h3>
          <button type="button" className={styles.toolsClearSection}
            onClick={()=>changeDesignations([])} disabled={selectedDesignations.length===0}>
            Clear This Section
          </button>
        </div>
        <p className={styles.muted}><strong>Step 3B designation totals:</strong> {page?.designationScopeSummary?count(page.designationScopeSummary.documentedCategoryLinks)+" documented FDA category links across "+count(page.designationScopeSummary.documentedUniqueTrials)+" distinct NCTs":"FDA evidence being checked"} in the same $300M–$10B restricted trial pool. Counts are partial, not a complete FDA census.</p>
        <PoolDesignationSelector guided selected={selectedDesignations} onChange={changeDesignations} poolTrialCount={stats?.trials??null}
          poolTotals={page?.designationTotals??null}
          contextCounts={page?.contextualDesignationCounts??null}
          scopeStages={selectedStages} scopeQuery={hasSelections?query:""} scopeLoading={loading} scopeError={error}/>
      </div>}
      {hasSelections&&<div className={styles.toolsStartSelected} role="status">
        <strong>{selectedStages.length} Phase selected · {selectedDesignations.length} Special Designation selected</strong>
      </div>}
    </div>
    {/* Step 3 selections reveal all twenty Step 4 assessments, then Step 5 immediately below. */}
    {hasSelections&&<>
      <ToolsAssessmentSection
        rows={page?.spreadsheetRows||[]}
        total={page?.total??0}
        offset={offset}
        loading={loading}
        error={error}
      />
<div className={styles.toolsFinalSpreadsheet} id="tools-final-trial-spreadsheet">
      <ToolsOpeningTrialGrid
        rows={hasSelections?page?.spreadsheetRows||[]:[]}
        total={hasSelections?page?.total??0:0}
        offset={hasSelections?offset:0}
        nextOffset={hasSelections?page?.nextOffset??null:null}
        inventoryMode={!hasSelections}
        selectedStages={selectedStages.length}
        selectedDesignations={selectedDesignations.length}
        noVerifiedNctLinks={!!page?.designationCoverage?.noVerifiedNctLinks}
        loading={hasSelections&&loading}
        error={hasSelections?error:""}
        sourceDate={sourceDate}
        sourceState={sourceState}
        regulatorySourcesAvailable={!!page?.regulatorySourcesAvailable}
        onPrevious={()=>setOffset(Math.max(0,offset-50))}
        onNext={()=>{if(page?.nextOffset!==null&&page?.nextOffset!==undefined)setOffset(page.nextOffset);}}
      />
    </div>
      <details id="tools-advanced-research" className={styles.toolsAdvanced}>
        <summary>Additional filters, detailed trial comparisons, rankings and CSV export</summary>
    <details className={styles.toolsAdvanced}>
      <summary>Quick filters and shortcuts</summary>
    <div className={styles.toolsQuickFilter}>
      <button type="button" onClick={selectPhase3Trials} aria-label="Select Phase 3 clinical stage to display screened trial matches">
        Select Phase 3 trials
      </button>
      <button type="button" onClick={findPhase3OrphanTrials} aria-label="Select Phase 3 and Orphan Drug Designation together">
        Find Phase 3 + Orphan Drug trials
      </button>
      <small>Both selectors operate within the same $300M–$10B issuer market-cap subset, across all recorded phases.</small>
    </div>

    </details>
    <form onSubmit={submitSearch} className={styles.search} style={{margin:"16px 0"}}>
      <input aria-label="Search trial NCT, ticker, company, drug or disease" type="search"
        value={queryInput} onChange={e=>setQueryInput(e.target.value)} maxLength={100}
        placeholder="Search selected results by NCT, ticker, drug or disease"/>
      <button type="submit">Search results</button>
      <button type="button" onClick={()=>{setQueryInput("");setQuery("");setOffset(0)}}>Clear search</button>
    </form>
    <p className={styles.muted}><strong>Filter logic:</strong> First filter all published NCTs by saved verified issuer market cap ($300M–$10B), with no preselected phase. Phase totals and FDA totals are separate breakdowns of that same restricted universe. Within each group selections are OR; across both groups selections are AND. FDA linkage remains incomplete.</p>
    {page?.restrictedScope&&<p className={styles.muted}>Full published POOL: {count(page.restrictedScope.originalPoolTrials)} NCTs · restricted research subset: {count(page.restrictedScope.screenedTrials)} NCTs · source state {value(sourceState)} · as of {value(sourceDate)}. Only the restricted subset feeds both selectors.</p>}
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
      </details>
    </>}
  </section>;
}
