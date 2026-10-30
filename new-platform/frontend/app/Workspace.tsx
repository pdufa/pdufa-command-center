"use client";

import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import dynamic from "next/dynamic";
import MasterChart from "./MasterChart";
import WorkflowStageIcon from "./WorkflowStageIcon";
import AlpacaStockChart from "./AlpacaStockChart";
import ProgramMarketEnrichment from "./ProgramMarketEnrichment";
import TradingDashboard, { type TradingTicker } from "./TradingDashboard";
import HopReadinessPanel from "./HopReadinessPanel";
import EntrySignal from "./EntrySignal";
import WtTradingSections, {areWtSuggestedIndicatorsChecked,suggestedWtIndicators,nextWtPresetFlags,wtEffectivePresetKeys,type WtPresetFlags} from "./WtTradingSections";
import {WT_GROUPS} from "../lib/wt-entry-stay-exit";
import PublishedScansPanel from "./PublishedScansPanel";
import HistoricalFdaReadiness from "./HistoricalFdaReadiness";
import GoalDashboard, { type GoalSection } from "./GoalDashboard";
import { goalRestrictionSummaries } from "../lib/goal-restrictions";
import DailyResultsPanel from "./DailyResultsPanel";
import BackupStatusPanel from "./BackupStatusPanel";
import PipelineData from "./PipelineData";
import MainPhase3ResearchPanel from "./MainPhase3ResearchPanel";
import PeakResearchPanel from "./PeakResearchPanel";
import DetailButton from "./DetailButton";
import SharedEnrichment from "./SharedEnrichment";
import RestrictionImpact from "./RestrictionImpact";
import TrialQualificationFilters from "./TrialQualificationFilters";
import SpecialDesignationCounts from "./SpecialDesignationCounts";
import { useTrialDesignations } from "./TrialDesignations";
import { filterBySelectedDesignations, SPECIAL_DESIGNATION_CATEGORIES, type DesignationKey } from "../lib/trial-designations";
import TrialFields from "./TrialFields";
import CandidateAssessments, { AssessmentProvider, AssessmentCells, AssessmentHeaders, AssessmentSort, AssessmentStatus, ScoreProgressButton, useAssessments } from "./CandidateAssessments";
import { sortByAssessment } from "../lib/candidate-assessments";
import GemQualificationChecklist, {newlyObservedProgramIds,checkboxGroupsForStage,availableGemRestrictionOptions,type GemScanResult,type GemJrLivePreview,type GemJrUiDraft} from "./GemQualificationChecklist";
import { catalogStages, catalogStagePriority, catalogDefinition, selectedRestrictionList, insertRestrictionIntoList, removeRestrictionFromList, RESTRICTION_PURPOSE_GROUPS, restrictionPurposeGroup, defaultCatalogEntries, restoreCatalogEntries, type CatalogEntry } from "../lib/restriction-catalog";
import { validatePipelinePage, type PipelinePage } from "../lib/workspace-pages";
import {pickGemResearchRows} from "../lib/gem-screen-rows";
import { filterPipelineRows, pipelineAvailability, PIPELINE_STAGES as STAGES, trialId } from "../lib/pipeline-data";
import { activeTrialFilters, EMPTY_TRIAL_FILTERS, trialFilterSummary, type TrialFilterFacts, type TrialFilterValues } from "../lib/trial-filters";

const DiseaseRestriction = dynamic(() => import("./DiseaseRestriction"), { loading: () => <p role="status">Loading populated disease catalog…</p> });
const CompanyDiseaseLinks = dynamic(() => import("./CompanyDiseaseLinks"), { loading: () => <p role="status">Loading company–disease relationships…</p> });

type Stage = "PIPELINE" | "GEM_JR" | "GEM";
function catalogGemKey(id:string){return id==="runway"?"cash":id==="gem_jr_source"?"gem_jr_source":id.startsWith("gem_")?id.slice(4):id.startsWith("alert_")?id.slice(6):"";}
function gemAllowedKeys(stage:"GEM_JR"|"GEM"){
  const groups=checkboxGroupsForStage(stage);
  const allowed=new Set([...groups.clinical,...groups.trading].map(([key])=>key));
  if(stage==="GEM")allowed.add("gem_jr_source");
  else for(const item of availableGemRestrictionOptions())allowed.add(item.key);
  return allowed;
}
function selectedGemKeys(entries:CatalogEntry[],stage:"GEM_JR"|"GEM"){
  const allowed=gemAllowedKeys(stage);
  return [...new Set(entries.filter(entry=>entry.enabled&&!!catalogStagePriority(entry,stage)&&catalogStages(entry).includes(stage))
    .map(entry=>catalogGemKey(entry.id)).filter(key=>allowed.has(key)))];
}
type Factor = { label: string; weight: number; earned: number | null; evidence: string };
type ResearchTechnical = {
  benchmarks?: { phase3: boolean; secondFinancing: boolean; bothConfirmed: boolean; warning: string; readoutDate: string; firstClose: string; secondClose: string };
  tradeCall?: string; tradeReason?: string;
  marketDate?: string; marketSource?: string; eodFresh?: boolean;
  chartBars?: {date:string;close:number;volume:number}[];
  close?: number | null; sma20?: number | null; sma50?: number | null;
  rsi14?: number | null; rvol?: number | null; avgDollarVolume20?: number | null;
  closingSupport20?: number | null; macd?: { macd: number | null; signal: number | null; bullish: boolean } | null;
  base?: { status: string; support: number | null; resistance: number | null; touches: number | null; widthPct: number | null; contractionRatio: number | null; volumeRatio: number | null; breakoutRvol: number | null };
  indicatorEntry?: number | null; indicatorEntryCoverage?: number; indicatorEntryObservedPoints?: number; indicatorExitRisk?: number | null; indicatorExitCoverage?: number; indicatorExitObservedPoints?: number; indicatorEntryFactors?: Factor[]; indicatorExitFactors?: Factor[]; indicatorDisclaimer?: string; indicatorModel?: string;
  dataGaps?: string; entry?: number | null; entryCoverage?: number; entryStatus?: string;
  exitRisk?: number | null; exitCoverage?: number; exitStatus?: string;
  entryFactors?: Factor[]; exitFactors?: Factor[];
  runwayMonths?: number | null; runwayGate?: string; runwayReason?: string; runwaySource?: string; runwayAsOf?: string;
  riskAlerts?: string[]; researchOnly?: boolean;
};

export type Candidate = {
  id: string; programId?: string; eventKey?: string; ticker: string; company?: string;
  drug?: string; indication?: string; nctId?: string; pdufaDate?: string;
  priorityReview?: {status: string; source?: string; designationDate?: string};
  phase3Date?: string; phase3Status?: string; phase3Source?: string;
  stage?: string; outcome?: string; marketCap?: number | null; capInRange?: boolean;
  capChecked?: string; capSource?: string; financingStatus?: string; financingDate?: string;
  financingSource?: string; financingEvidence?: string; fdaSource?: string;
  lastChecked?: string; approvalProbability?: string; checkStatus?: string;
  pValues?: string; evidenceSummary?: string; signal?: string;
  membershipStatus?: string; firstFound?: string; lastSeen?: string; candidateLinked?: boolean;
  listAddedOn?: string; listRemovedOn?: string;
  technical?: ResearchTechnical;
  trialFilters?: TrialFilterFacts;
};
type StageHistory = { id: string; programId?: string; ticker: string; drug: string; enteredOn: string; leftOn: string; reason: string; status: string; cycle: number };
type StageData = { asOf?: string; rows: Candidate[]; history?: StageHistory[] };
type Snapshot = {
  mode: string; asOf: string; disclaimer: string;
  marketCapRange: { min: number; max: number };
  pipeline: Candidate[]; members: { GEM_JR: StageData; GEM: StageData };
  trialFilterSchema?: number;
  workspaceVersion?: string;
  sourceHealth?: { state: string; issues: string[]; clinicalRows: number; regulatoryRows: number; pipelineSourceParity?: {exactPrograms:number;clinicalAndResults:number;regulatoryPrograms:number;comparison:string}; publishedScan?: { state?: string; finishedAt?: string; complete?: boolean; sources?: Record<string,{status?:string;finished_at?:string}> } | null };
};
// Display source-reported timestamps in the operating (Pacific) time zone.
// Invalid or missing evidence is never replaced with the current clock.
function pacificSourceTime(value?: string | null): string {
  if (!value || !Number.isFinite(Date.parse(value))) return "Unavailable";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", year: "numeric", month: "short",
    day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short",
  }).format(new Date(value));
}
// IndexedDB stores only validated, successfully fetched published snapshots.
// A failed fetch never overwrites the last-known-good local copy.
const SNAPSHOT_CACHE_DB = "pdufa-workspace-cache-v1";
function validWorkspaceSnapshot(value: unknown): value is Snapshot {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<Snapshot>;
  return typeof v.asOf === "string" && v.mode !== "STALE_PREVIOUS_FETCH" &&
    v.sourceHealth?.state !== "STALE" && Array.isArray(v.pipeline) &&
    !!v.members && Array.isArray(v.members.GEM_JR?.rows) && Array.isArray(v.members.GEM?.rows);
}
type WorkspaceDelta = {
  version: string; baseVersion?: string; reset: boolean; unchanged: boolean;
  changes?: Record<"PIPELINE" | "GEM_JR" | "GEM", {
    upsert: Candidate[]; remove: string[]; count: number; order: string[];
  }>;
  metadata?: Partial<Snapshot>;
  membersMetadata?: { GEM_JR: Partial<StageData>; GEM: Partial<StageData> };
};
function applyWorkspaceDelta(base: Snapshot, delta: WorkspaceDelta): Snapshot {
  if (!base.workspaceVersion || delta.reset || delta.unchanged ||
      delta.baseVersion !== base.workspaceVersion || !delta.changes ||
      !delta.metadata || !delta.membersMetadata) {
    throw new Error("Delta base version or metadata invalid");
  }
  const update = (rows: Candidate[], stage: "PIPELINE" | "GEM_JR" | "GEM") => {
    const patch = delta.changes![stage];
    if (!patch || !Array.isArray(patch.upsert) || !Array.isArray(patch.remove) ||
        !Number.isSafeInteger(patch.count) || !Array.isArray(patch.order)) throw new Error("Malformed stage delta");
    const index = new Map<string, Candidate>();
    for (const row of rows) {
      if (!row.id || index.has(row.id)) throw new Error("Invalid baseline record IDs");
      index.set(row.id, row);
    }
    for (const id of patch.remove) {
      if (!index.delete(id)) throw new Error("Delta removal not found");
    }
    for (const row of patch.upsert) {
      if (!row.id) throw new Error("Delta record missing ID");
      index.set(row.id, row);
    }
    if (index.size !== patch.count) throw new Error("Delta record count mismatch");
    if (patch.order.length !== patch.count || new Set(patch.order).size !== patch.count ||
        patch.order.some(id => !index.has(id))) throw new Error("Delta ordering mismatch");
    return patch.order.map(id => index.get(id)!);
  };
  const next: Snapshot = {
    ...base, ...delta.metadata,
    workspaceVersion: delta.version,
    pipeline: update(base.pipeline, "PIPELINE"),
    members: {
      GEM_JR: { ...base.members.GEM_JR, ...delta.membersMetadata.GEM_JR,
        rows: update(base.members.GEM_JR.rows, "GEM_JR") },
      GEM: { ...base.members.GEM, ...delta.membersMetadata.GEM,
        rows: update(base.members.GEM.rows, "GEM") },
    },
  };
  if (!validWorkspaceSnapshot(next)) throw new Error("Delta snapshot validation failed");
  return next;
}
function openWorkspaceCache(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(SNAPSHOT_CACHE_DB, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains("snapshots")) request.result.createObjectStore("snapshots");
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function readWorkspaceCache(): Promise<Snapshot | null> {
  const db = await openWorkspaceCache();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction("snapshots", "readonly").objectStore("snapshots").get("lastVerified");
      request.onsuccess = () => {
        if (validWorkspaceSnapshot(request.result)) { resolve(request.result); return; }
        // Recover from the previous verified copy if the newest slot is missing or invalid.
        const fallback = db.transaction("snapshots", "readonly").objectStore("snapshots").get("previousVerified");
        fallback.onsuccess = () => resolve(validWorkspaceSnapshot(fallback.result) ? fallback.result : null);
        fallback.onerror = () => reject(fallback.error);
      };
      request.onerror = () => reject(request.error);
    });
  } finally { db.close(); }
}
async function writeWorkspaceCache(snapshot: Snapshot): Promise<void> {
  if (!validWorkspaceSnapshot(snapshot)) throw new Error("Invalid published snapshot");
  const db = await openWorkspaceCache();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction("snapshots", "readwrite");
      const store = transaction.objectStore("snapshots");
      const previous = store.get("lastVerified");
      previous.onsuccess = () => {
        if (validWorkspaceSnapshot(previous.result)) store.put(previous.result, "previousVerified");
        store.put(snapshot, "lastVerified");
      };
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally { db.close(); }
}
type PublishedCounts = { pipeline: number; gemJr: number; gem: number; sourceState?: string; asOf?: string };
type Nav = "PIPELINE" | "GEM_JR" | "GEM" | "MASTER" | "WT" | "TRADING";
type TopNav = "GOAL" | "SCANS" | "RESULTS" | "BACKUP" | "PDUFA" | "PREDICTION" | "CALENDAR" | "RESTRICTIONS";
type Tags = { watch: string[]; trade: string[] };
type PipelineSelection = { stages: string[]; dates: string[]; query: string; onlyBand: boolean; trial: TrialFilterValues; asOf?: string };
const TAG_KEY = "pdufa_new_program_watch_trade_v1";
const LEGACY_TAG_KEY = "pdufa_new_watch_trade_v1";
const WT_TRIAL_INDICATORS_KEY = "pdufa_wt_trial_indicators_v1";
type WtTrialStage = "entry"|"stay"|"exit";
type WtTrialIndicatorPreference = {
  stage: WtTrialStage|"";
  keys: Record<WtTrialStage,string[]>;
  /** Manually chosen options, before FS/FA overlays are applied. */
  manualKeys: Record<WtTrialStage,string[]>;
  /** Separate button states for each stage, never inferred from checked options. */
  presets: Record<WtTrialStage,WtPresetFlags>;
  configured: WtTrialStage[];
};
function isWtStage(value:unknown):value is WtTrialStage {
  return value==="entry"||value==="stay"||value==="exit";
}
function emptyWtPreference():WtTrialIndicatorPreference {
  return {
    stage:"",keys:{entry:[],stay:[],exit:[]},
    manualKeys:{entry:[],stay:[],exit:[]},
    presets:{entry:{fs:false,fa:false},stay:{fs:false,fa:false},exit:{fs:false,fa:false}},
    configured:[]
  };
}
function normalizeWtPreference(value:unknown):WtTrialIndicatorPreference {
  if(!value||typeof value!=="object"||Array.isArray(value))return emptyWtPreference();
  const source=value as Record<string,unknown>;
  const storedKeys=source.keys&&typeof source.keys==="object"&&!Array.isArray(source.keys)
    ?source.keys as Record<string,unknown>:{};
  const sourceManual=source.manualKeys&&typeof source.manualKeys==="object"&&!Array.isArray(source.manualKeys)
    ?source.manualKeys as Record<string,unknown>:null;
  const sourcePresets=source.presets&&typeof source.presets==="object"&&!Array.isArray(source.presets)
    ?source.presets as Record<string,unknown>:{};
  const manualKeys={entry:[] as string[],stay:[] as string[],exit:[] as string[]};
  const presets={
    entry:{fs:false,fa:false},stay:{fs:false,fa:false},exit:{fs:false,fa:false}
  };
  const keys={entry:[] as string[],stay:[] as string[],exit:[] as string[]};
  for(const stage of ["entry","stay","exit"] as const){
    const allowed=new Set(WT_GROUPS.find(group=>group.id===stage)?.items.map(item=>item.key)||[]);
    // Old saved choices had no preset flags: treat those checkmarks as manual.
    const raw=sourceManual?sourceManual[stage]:storedKeys[stage];
    manualKeys[stage]=Array.isArray(raw)?[...new Set(raw.filter((key):key is string=>
      typeof key==="string"&&allowed.has(key)))]:[];
    const rawFlags=sourceManual?sourcePresets[stage]:null;
    if(rawFlags&&typeof rawFlags==="object"&&!Array.isArray(rawFlags)){
      const flags=rawFlags as Record<string,unknown>;
      presets[stage]={fs:flags.fs===true,fa:flags.fa===true};
    }
    keys[stage]=wtEffectivePresetKeys(manualKeys[stage],stage,presets[stage]);
  }
  return {
    stage:isWtStage(source.stage)?source.stage:"",
    keys,manualKeys,presets,
    configured:Array.isArray(source.configured)?
      [...new Set(source.configured.filter(isWtStage))]:[]
  };
}
function readWtPreferences(raw:string|null):Record<string,WtTrialIndicatorPreference> {
  if(!raw)return {};
  try {
    const parsed:unknown=JSON.parse(raw);
    if(!parsed||typeof parsed!=="object"||Array.isArray(parsed))return {};
    const entries=Object.entries(parsed).filter(([id])=>/^PDUFA-\d{6,}$/.test(id)).slice(0,2000);
    return Object.fromEntries(entries.map(([id,value])=>[id,normalizeWtPreference(value)]));
  }catch{return {};}
}

const BANDS = ["0–30 DAYS", "31–60 DAYS", "61–90 DAYS", "+90 DAYS", "NO PDUFA YET", "PAST / RECHECK"];

function dateTodayPT() {
  const x = new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const parts = Object.fromEntries(x.filter(part => part.type !== "literal").map(part => [part.type, part.value]));
  return parts.year + "-" + parts.month + "-" + parts.day;
}
function daysAway(raw?: string) {
  if (!raw || !/^\d{4}-\d{2}-\d{2}$/.test(raw.slice(0, 10))) return null;
  const d = Date.parse(raw.slice(0, 10) + "T00:00:00Z");
  const today = Date.parse(dateTodayPT() + "T00:00:00Z");
  const n = Math.round((d - today) / 86400000);
  return Number.isFinite(n) ? n : null;
}
function dateBand(c: Candidate) {
  const n = daysAway(c.pdufaDate);
  if (n === null) return "NO PDUFA YET";
  return n < 0 ? "PAST / RECHECK" : n <= 30 ? "0–30 DAYS" : n <= 60 ? "31–60 DAYS" : n <= 90 ? "61–90 DAYS" : "+90 DAYS";
}
function money(value?: number | null) {
  return value == null ? "NOT VERIFIED" : "$" + (value >= 1e9 ? (value / 1e9).toFixed(2) + "B" : (value / 1e6).toFixed(0) + "M");
}
function stated(value?: string | null, fallback = "NOT VERIFIED") {
  return value && value.trim() ? value.trim() : fallback;
}
function evidence(url?: string) { return url && /^https:\/\/[^\s]+$/.test(url) ? url : undefined; }
function trialSheetUrl(record: Candidate) {
  const nct = trialId(record);
  return nct ? "/trial/" + encodeURIComponent(nct) : "";
}
function uniqueRows(rows: Candidate[]) {
  const seen = new Set<string>();
  return rows.filter(row => { if (!row.id || seen.has(row.id)) return false; seen.add(row.id); return true; });
}
function scoreNum(number?: number | null, digits = 2, suffix = "") {
  return typeof number === "number" && Number.isFinite(number) ? number.toFixed(digits) + suffix : "NOT VERIFIED";
}

type EligibilityTone = "review" | "hold" | "warning";
type CandidateDecision = { title: string; reason: string; tone: EligibilityTone };
function candidateDecision(record: Candidate | null, stage: "GEM_JR" | "GEM"): CandidateDecision {
  if (!record) return {title: "NO PROGRAM SELECTED", reason: "Select an exact program to review its source-verified entry benchmarks.", tone: "review"};
  const prefix = stage === "GEM_JR" ? "GEM JR research" : "GEM research";
  const tech = record.technical;
  if (record.candidateLinked === false) return {
    title: "PROGRAM LINK NOT VERIFIED",
    reason: prefix + ": the exact program linkage has not been confirmed. Entry eligibility is withheld.",
    tone: "hold"
  };
  if (!tech) return {
    title: "ELIGIBILITY UNVERIFIED",
    reason: prefix + ": current clinical, financing, and market research evidence is unavailable. No trade clearance.",
    tone: "hold"
  };
  const hardExit = tech.exitStatus?.startsWith("HARD EXIT WARNING") ||
    tech.entryStatus?.startsWith("NO NEW ENTRY") ||
    tech.tradeCall?.startsWith("EXIT RISK") ||
    (tech.riskAlerts || []).some(alert =>
      /FDA decision within 3 days|FDA event already resolved|New or unresolved dilution/i.test(alert));
  if (hardExit) return {
    title: "HARD EXIT / NO NEW ENTRY",
    reason: stated(tech.exitStatus || tech.tradeReason, "Recorded FDA, dilution, or market risk requires immediate review."),
    tone: "warning"
  };
  const benchmark = tech.benchmarks;
  if (benchmark?.phase3 !== true) {
    return {
      title: "PHASE 3 ELIGIBILITY NOT VERIFIED",
      reason: prefix + ": independently verified successful Phase 3 evidence is required. "
        + "Second financing is optional; this does not clear cash, dilution or other trading risks.",
      tone: "hold"
    };
  }
  if (tech.entryStatus?.startsWith("NOT ELIGIBLE")) return {
    title: "ENTRY NOT CLEARED",
    reason: stated(tech.entryStatus) + ". Verified benchmarks do not override clinical risk.",
    tone: "warning"
  };
  if (tech.entryStatus?.startsWith("UNAVAILABLE") || tech.tradeCall?.startsWith("WAIT — SOURCE RECHECK")) return {
    title: "SOURCES REQUIRE RECHECK",
    reason: prefix + ": Phase 3 is verified, but source freshness or other required inputs have not cleared review.",
    tone: "hold"
  };
  return {
    title: "PHASE 3 VERIFIED · ENTRY REVIEW",
    reason: prefix + ": successful Phase 3 verified. Second financing is OPTIONAL (" +
      (benchmark?.secondFinancing === true ? "verified" : "not verified") + "). " +
      "Cash runway, dilution, market evidence, exit overrides and manual review remain separate safeguards.",
    tone: "review"
  };
}
function EvidenceCoverage({label, coverage, compact=false}: {label:string;coverage?:number|null;compact?:boolean}) {
  // Do not silently translate missing observations to zero or imply that
  // evidence coverage measures likelihood of FDA approval or trade success.
  const amount = typeof coverage === "number" && Number.isFinite(coverage) && coverage >= 0 && coverage <= 100
    ? coverage : null;
  return <div className={compact ? "gem-evidence-meter gem-evidence-meter-small" : "gem-evidence-meter"}>
    <div className="gem-evidence-meter-label"><strong>{label}</strong><span>{amount === null ? "NOT REPORTED" : amount + "/100"}</span></div>
    <div className="gem-evidence-meter-track"
      role={amount === null ? undefined : "progressbar"}
      aria-label={label + " weighted evidence coverage"}
      aria-valuemin={amount === null ? undefined : 0}
      aria-valuemax={amount === null ? undefined : 100}
      aria-valuenow={amount === null ? undefined : amount}>
      <span style={{width: amount === null ? "0%" : amount + "%"}} />
    </div>
    {!compact && <small>{amount === null ? "No published coverage figure." :
      "Weighted evidence observed; not a probability of approval or a trading signal."}</small>}
  </div>;
}
function Goals({ record }: { record: Candidate | null }) {
  const tech = record?.technical;
  const pass = (value?: boolean) => value === true;
  const rows: [string,string,string,boolean][] = [
    ["Market capitalization", money(record?.marketCap), "$300M–$10B",pass(record?.capInRange)],
    ["Phase 3 verified positive", tech?.benchmarks?.phase3 ? "PASS — source checked" : stated(record?.phase3Status), "Exact successful primary endpoint + source", pass(tech?.benchmarks?.phase3)],
    ["Second financing (OPTIONAL)", tech?.benchmarks?.secondFinancing ? "VERIFIED — SEC reviewed" : "NOT VERIFIED — MONITOR RISK", "Not required for GEM/GEM JR research eligibility; assess cash and dilution separately", pass(tech?.benchmarks?.secondFinancing)],
    ["SEC cash-only runway", tech?.runwayMonths == null ? stated(tech?.runwayGate) : scoreNum(tech.runwayMonths,1," months"), "≥12 months; source current and reconciled", pass(tech?.runwayGate?.startsWith("PASS"))],
    ["EOD closing price", scoreNum(tech?.close,2," USD"), "Compare SMA20 and SMA50; not executable quote", false],
    ["SMA20 / SMA50", scoreNum(tech?.sma20)+" / "+scoreNum(tech?.sma50), "Close above SMA20 & SMA50", false],
    ["Relative volume", scoreNum(tech?.rvol,2,"×"), "≥1.5× provisional", (tech?.rvol??0)>=1.5],
    ["RSI(14)", scoreNum(tech?.rsi14,1), "45–65 provisional", tech?.rsi14 != null && tech.rsi14>=45 && tech.rsi14<=65],
    ["20D traded dollar volume", tech?.avgDollarVolume20 == null ? "NOT VERIFIED" : "$"+Math.round(tech.avgDollarVolume20).toLocaleString("en-US"), "≥$5M/day", (tech?.avgDollarVolume20??0)>=5000000],
    ["Closing support proxy", scoreNum(tech?.closingSupport20,2), "Verify 20 prior sessions; not a hard stop", false],
    ["Base formation", stated(tech?.base?.status), "2+ separate tests; width ≤18%; volume review", false],
    ["Entry strength / coverage", tech?.entry == null ? stated(tech?.entryStatus,"UNAVAILABLE") : tech.entry+"/100 · "+tech.entryCoverage+"/100 observed", "Only when ≥50/100 evidence coverage and all gates pass", false],
    ["Exit risk / coverage", tech?.exitRisk == null ? stated(tech?.exitStatus,"UNAVAILABLE") : tech.exitRisk+"/100 · "+tech.exitCoverage+"/100 observed", "PDUFA −3 and hard-exit warnings override scores", false],
  ];
  return <div className="goal-table">
    <div className="goal-grid goal-header"><span>Indicator</span><span>Observed / status</span><span>Goal / rule</span></div>
    {rows.map(([label, observed, goal, verified])=><div key={label} className="goal-grid">
      <span className="goal-row-heading">{label}</span>
      <span className={verified ? "verified" : "unknown-value"}><small className="goal-mini-label">Observed / status</small>{observed}</span>
      <span className="gold-goal"><small className="goal-mini-label">Goal / rule</small>{goal}</span>
    </div>)}
  </div>;
}
function TechnicalPanel({ record }: { record: Candidate }) {
  const x = record.technical;
  if (!x) return <p className="subtle">Saved market/SEC observations are unavailable for this exact program.</p>;
  return <div className="research-technical">
    <h3>Evidence-gated entry / exit monitor</h3>
    <p className="risk-line"><strong>{stated(x.tradeCall,"NO VERIFIED MARKET ASSESSMENT")}</strong> · {stated(x.tradeReason)}</p>
    <div className="research-score-cards">
      <div><strong>Entry /100</strong><span>{x.entry == null ? "UNSCORED" : x.entry}</span><small>Evidence coverage {x.entryCoverage??0}/100</small></div>
      <div><strong>Exit risk /100</strong><span>{x.exitRisk == null ? "UNSCORED" : x.exitRisk}</span><small>Evidence coverage {x.exitCoverage??0}/100</small></div>
      <div><strong>Market snapshot</strong><span>{x.eodFresh ? "RECENT EOD" : "STALE / REVIEW"}</span><small>{stated(x.marketDate,"No verified session")}</small></div>
    </div>
    <div className="research-facts-grid">
      <p><strong>Entry:</strong> {stated(x.entryStatus)}</p>
      <p><strong>Exit:</strong> {stated(x.exitStatus)}</p>
      <p><strong>Closing base:</strong> {stated(x.base?.status)} · support {scoreNum(x.base?.support,2)} / resistance {scoreNum(x.base?.resistance,2)}</p>
      <p><strong>MACD:</strong> {scoreNum(x.macd?.macd,3)} · Signal {scoreNum(x.macd?.signal,3)} (close-based; no intraday VWAP)</p>
      <p><strong>SEC cash runway:</strong> {stated(x.runwayGate)} · {stated(x.runwayReason)}</p>
    </div>
    {x.riskAlerts?.length ? <div className="risk-warnings"><strong>Source warnings</strong><div className="risk-alert-grid">{x.riskAlerts.map(alert=><p key={alert}>{alert}</p>)}</div></div> : null}
    <details><summary>All weighted scoring factors and missing evidence</summary>
      <div className="score-factor-groups">{([["Entry strength",x.entryFactors||[]],["Exit risk",x.exitFactors||[]]] as [string,Factor[]][]).map(([name,items])=>
        <div key={name}><h4>{name}</h4><div className="factor-item-grid">{items.map(item=><div className="score-factor" key={item.label}><strong>{item.label}</strong>
          <span>{item.earned==null ? "NOT AVAILABLE" : item.earned} / {item.weight}</span>
          <small>{item.evidence}</small></div>)}</div></div>)}</div>
    </details>
    <p className="subtle small">GEM membership and numerical scores do not authorize trading. No order, stop, ATR, spread or position is inferred. {stated(x.dataGaps,"Missing observations remain unscored.")}</p>
    {evidence(x.marketSource) && <a target="_blank" rel="noopener noreferrer" href={x.marketSource}>Saved market source ↗</a>}
    {evidence(x.runwaySource) && <a target="_blank" rel="noopener noreferrer" href={x.runwaySource}>SEC cash runway evidence ↗</a>}
  </div>;
}

type WTResearchReply = {
  programId: string; exactKey?: string;
  source: string; technical: ResearchTechnical | null; asOf?: string;
  scope?: string; missingSources?: string[];
};
function WTIndicatorDetails({programId, record, ticker}: {programId:string;record?:Candidate;ticker:string}) {
  const [reply,setReply] = useState<WTResearchReply|null>(null);
  const [error,setError] = useState("");
  useEffect(()=>{
    const ctrl=new AbortController();
    setReply(null);
    setError("");
    fetch("/api/wt-research/"+encodeURIComponent(programId),{
      cache:"no-store",signal:ctrl.signal
    }).then(async result=>{
      if(!result.ok)throw Error("WT indicator feed returned "+result.status);
      return await result.json() as WTResearchReply;
    }).then(x=>{if(!ctrl.signal.aborted){
      if(x.programId!==programId|| (record && x.exactKey!==record.id)) {
        setError("Program identity mismatch; scores withheld.");return;
      }
      setReply(x);
    }}).catch(e=>{if(!ctrl.signal.aborted)setError(String(e));});
    return ()=>ctrl.abort();
  },[programId,record?.id]);
  const x=reply?.technical;
  const observed=(v?:number|null)=>typeof v==="number"&&Number.isFinite(v)?v.toString()+"/100":"UNSCORED";
  return <section className="wt-score-details" aria-label={programId+" indicator entry and exit research"}>
    <div className="wt-indicator-title"><h3>WT INDICATOR ENTRY &amp; EXIT SCORES</h3>
      <span className="permanent-id">{programId}</span></div>
    <p className="subtle">Uses GEM JR / GEM’s original EOD indicator calculations and factor weights. Indicator strength is separate from verified Phase 3 eligibility and does not authorize a trade. Second financing is optional.</p>
    {error ? <p className="risk-line">Indicator lookup failed: {error}. Scores withheld.</p>
    : !reply ? <p className="subtle">Checking verified price, volume, trend, technical risks and source dates…</p>
    : !x ? <p className="risk-line">Current exact-program indicator evidence unavailable. Scores withheld.</p>
    : <>
      <div className="research-score-cards wt-observed-scores">
        <div><strong>Indicator entry /100</strong>
          <span>{observed(x.indicatorEntry)}</span>
          <small>Evidence coverage {x.indicatorEntryCoverage??0}/100 · {x.indicatorEntry==null? "Observed points "+(x.indicatorEntryObservedPoints??0)+" (partial, not a validated /100 score)":"GEM weighted score"}</small></div>
        <div><strong>Indicator exit risk /100</strong>
          <span>{observed(x.indicatorExitRisk)}</span>
          <small>Evidence coverage {x.indicatorExitCoverage??0}/100 · {x.indicatorExitRisk==null? "Observed points "+(x.indicatorExitObservedPoints??0)+" (partial, not a validated /100 score)":"GEM weighted score"}</small></div>
        <div><strong>Verified market snapshot</strong>
          <span>{x.eodFresh?stated(x.marketDate,"CHECK DATE"):"STALE / MISSING"}</span>
          <small>{x.eodFresh?"Recent, source-consistent EOD":"Unverified / old observations"}</small></div>
      </div>
      <p className="wt-indicator-eligibility"><strong>Clinical entry / source-risk gate:</strong> {stated(x.entryStatus,"NOT VERIFIED")}</p>
      <p><strong>Exit overrides:</strong> {stated(x.exitStatus,"NOT VERIFIED")}{x.riskAlerts?.length?" · "+x.riskAlerts.join("; "):""}</p>
      <details className="wt-factors"><summary>Expand indicator scoring factors, weights, actual evidence and gaps</summary>
        <div className="score-factor-groups">{([
          ["Entry indicators",x.indicatorEntryFactors||[]],
          ["Exit indicators",x.indicatorExitFactors||[]],
        ] as [string,Factor[]][]).map(([title,items])=><div key={title}>
          <h4>{title}</h4>
          {items.length ? <div className="factor-item-grid">{items.map(f=><div className="score-factor" key={f.label}>
            <strong>{f.label}</strong><span>{f.earned==null?"NOT VERIFIED":f.earned} / {f.weight}</span>
            <small>{f.evidence}</small></div>)}</div> : <p className="subtle">No verified EOD observations yet.</p>}
        </div>)}</div>
      </details>
      {record && <details className="wt-factors"><summary>Original GEM eligibility entry / exit monitor (same Program ID)</summary>
        <TechnicalPanel record={{...record,technical:x}} />
      </details>}
      <p className="subtle small">Source: {stated(reply.source)}. {stated(reply.scope)} {stated(x.indicatorDisclaimer)}
        Missing ATR, real stops, VWAP, spread, and reward/risk are not scored.
        {reply.missingSources?.length?" Missing upstream files: "+reply.missingSources.join(", "):""}
      </p>
      {evidence(x.marketSource)&&<a href={x.marketSource} target="_blank" rel="noopener noreferrer">Market data source ↗</a>}
    </>}
  </section>;
}

function PriorityIndicators({ record }: { record: Candidate }) {
  const t = record.technical;
  const pdufaDays = daysAway(record.pdufaDate);
  const observations: [string,string,string][] = [
    ["Support / resistance / base", t?.base ? scoreNum(t.base.support)+" / "+scoreNum(t.base.resistance)+" · "+t.base.status : "NOT VERIFIED", "≥2 separated support touches; verify 20-session base"],
    ["Volume and relative volume", scoreNum(t?.rvol,2,"×")+" · "+(t?.avgDollarVolume20 == null ? "liquidity unknown" : money(t.avgDollarVolume20)), "RVOL ≥1.5× breakout; average $ volume ≥$5M"],
    ["SMA20 and SMA50", scoreNum(t?.sma20)+" / "+scoreNum(t?.sma50), "Close above rising SMA20 and SMA50"],
    ["ATR(14)", "NOT AVAILABLE — no verified high/low bars", "Size volatility-based stop; no fixed ATR target"],
    ["Reward / risk", "NOT AVAILABLE — no validated stop and target", "Prefer ≥2:1 after costs; define hard stop before entry"],
    ["VWAP / anchored VWAP", "NOT AVAILABLE — intraday / anchor data missing", "Price above significant VWAP level"],
    ["Relative strength vs XBI", "NOT AVAILABLE — benchmark data missing", "Outperform XBI across matched periods"],
    ["Catalyst / PDUFA markers", record.pdufaDate ? record.pdufaDate+" · "+(pdufaDays??"—")+" days (reported)" : "NOT VERIFIED", "Verify date; pre-PDUFA exit at −3 days"],
    ["RSI(14)", scoreNum(t?.rsi14,1), "45–65 provisional; optional filter"],
    ["MACD", scoreNum(t?.macd?.macd,3)+" vs "+scoreNum(t?.macd?.signal,3), "Bullish crossover preferred; optional confirmation"],
  ];
  return <details className="priority-panel"><summary>Chart indicators — strict priority 1–10 and target levels</summary>
    <div className="priority-scroll"><table><thead><tr><th>Priority</th><th>Observed</th><th>Gold target</th></tr></thead><tbody>
      {observations.map(([name,value,goal],i)=><tr key={name}><td><strong>{i+1}. {name}</strong></td>
        <td>{value}</td><td><span className="gold-goal">{goal}</span></td></tr>)}
    </tbody></table></div>
    <p className="subtle small">The market feed contains close/volume observations only. Intraday ATR, spread, actual stops, anchored VWAP and XBI comparisons are not fabricated.</p>
  </details>;
}
function GemInlineSection({title,description,open,onToggle,children}:{
  title:string;description:string;open:boolean;onToggle:()=>void;children:ReactNode
}) {
  return <section className={"gem-inline-section"+(open?" gem-inline-section-open":"")}>
    <button type="button" className="gem-inline-section-trigger" onClick={onToggle} aria-expanded={open}>
      <span className="gem-inline-section-heading"><span aria-hidden="true">{open?"▾":"▸"}</span> {title}</span>
      <small>{description}</small>
    </button>
    {open && <div className="gem-inline-section-content">{children}</div>}
  </section>;
}

function SourceDetails({ record }: { record: Candidate }) {
  return (
    <div className="program-details">
      <DetailButton item={record} />
      <div className="trial-details">
        <div><strong>Permanent Program ID</strong><span className="permanent-id">{stated(record.programId,"REGISTRY UNAVAILABLE")}</span></div>
        <div><strong>Exact Pipeline source key</strong><span>{record.id}</span></div>
        {record.listAddedOn !== undefined && <div><strong>Date added to this list</strong><span>{stated(record.listAddedOn,"NOT RECORDED")}</span></div>}
        {record.listRemovedOn !== undefined && <div><strong>Date removed from this list</strong><span>{stated(record.listRemovedOn,"— Still listed")}</span></div>}
        <div><strong>Drug / indication</strong><span>{stated(record.drug)} / {stated(record.indication)}</span></div>
        <div><strong>ClinicalTrials.gov NCT</strong><span>{trialSheetUrl(record)
          ? <a href={trialSheetUrl(record)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">{trialId(record)} · OPEN FULL TRIAL SHEET ↗</a>
          : "NO EXACT TRIAL LINKED"}</span></div>
        <div><strong>Phase 3</strong><span>{stated(record.phase3Status)} · {stated(record.phase3Date, "date unavailable")}</span></div>
        <div><strong>Second financing</strong><span>{stated(record.financingStatus)} · {stated(record.financingDate, "date unavailable")}</span></div>
        <div><strong>PDUFA</strong><span>{stated(record.pdufaDate)}</span></div>
        <div><strong>Market cap</strong><span>{money(record.marketCap)} · {record.capInRange ? "Within $300M–$10B" : "Unknown / outside preferred band"}</span></div>
        <div><strong>Source verification</strong><span>{stated(record.checkStatus)} · {stated(record.lastChecked)}</span></div>
      </div>
      <div className="source-links">
        {evidence(record.phase3Source) && <a href={record.phase3Source} target="_blank" rel="noopener noreferrer">Phase 3 source ↗</a>}
        {evidence(record.financingSource) && <a href={record.financingSource} target="_blank" rel="noopener noreferrer">SEC financing ↗</a>}
        {evidence(record.fdaSource) && <a href={record.fdaSource} target="_blank" rel="noopener noreferrer">FDA evidence ↗</a>}
      </div>
      <p className="subtle small">Missing data is not a pass. Nested hierarchy: ticker → drug/program → source trial/evidence. Program membership is not trade authorization.</p>
    </div>
  );
}
export function Drilldown({ rows }: { rows: Candidate[] }) {
  const [open,setOpen]=useState(false);
  const [page,setPage]=useState(0);
  const [expandedPrograms,setExpandedPrograms]=useState<Record<string,boolean>>({});
  const records=useMemo(()=>uniqueRows(rows),[rows]);
  const pageSize=25;
  const pages=Math.max(1,Math.ceil(records.length/pageSize));
  const currentPage=Math.min(page,pages-1);
  const first=currentPage*pageSize;
  const grouped = useMemo(() => {
    const map = new Map<string, Candidate[]>();
    for(const item of records.slice(first,first+pageSize)){
      const programs=map.get(item.ticker);
      if(programs)programs.push(item);
      else map.set(item.ticker,[item]);
    }
    return [...map].sort(([a], [b]) => a.localeCompare(b));
  }, [records,first]);
  function changePage(next:number){setPage(next);setExpandedPrograms({});}
  return <details className="nested-expander" onToggle={event=>{
    if(event.target===event.currentTarget)setOpen(event.currentTarget.open);
  }}>
    <summary>Three-level clinical trials and evidence table · ticker → drug/program → trial</summary>
    {open && <div className="nested-records">
    <div className="sectionhead" aria-label="Clinical evidence table pages">
      <span role="status">Trials {records.length?first+1:0}–{Math.min(first+pageSize,records.length)} of {records.length.toLocaleString("en-US")} · Page {currentPage+1} of {pages}</span>
      <button type="button" className="secondary" disabled={currentPage===0} onClick={()=>changePage(currentPage-1)}>PREVIOUS TRIAL PAGE</button>
      <button type="button" className="secondary" disabled={currentPage===pages-1} onClick={()=>changePage(currentPage+1)}>NEXT TRIAL PAGE</button>
    </div>
    {grouped.map(([ticker, companies]) => (
      <details key={ticker} className="drill-company">
        <summary><strong>{ticker}</strong><span>{companies.length} exact program{companies.length === 1 ? "" : "s"} on this page</span></summary>
        <div className="drill-program-grid">{companies.map(item => (
          <details key={item.id} className="drill-program" onToggle={event=>{
            if(event.target!==event.currentTarget)return;
            const expanded=event.currentTarget.open;
            setExpandedPrograms(current=>current[item.id]===expanded?current:{...current,[item.id]:expanded});
          }}>
            <summary><strong>{stated(item.drug)}</strong><span><strong className="permanent-id">{stated(item.programId)}</strong> · {stated(item.indication, "program research")} · {stated(item.pdufaDate, "no date")}</span></summary>
            {expandedPrograms[item.id] && <div className="drill-evidence"><strong>Trial details and verification</strong>
              {trialSheetUrl(item) && <a href={trialSheetUrl(item)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">OPEN FULL TRIAL SHEET · {trialId(item)} ↗</a>}
              <SourceDetails record={item} />
            </div>}
          </details>
        ))}</div>
      </details>
    ))}
    {grouped.length === 0 && <p className="subtle">No exact-program records match these filters.</p>}
    </div>}
  </details>;
}

function WorkspaceContent({ onInspect }: { onInspect: (ticker: string, stage: Stage, programId?: string) => void }) {
  const { records: assessmentRecords } = useAssessments();
  const { index: designationIndex, loading: designationLoading, error: designationError, retry: retryDesignations } = useTrialDesignations();
  const [assessmentOrder, setAssessmentOrder] = useState({ GEM_JR: "source", GEM: "source" });
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [publishedCounts, setPublishedCounts] = useState<PublishedCounts | null>(null);
  // A bounded page becomes usable before the complete qualification dataset.
  // Search covers the entire published pipeline on the server.
  const [earlyPipelinePage, setEarlyPipelinePage] = useState<PipelinePage | null>(null);
  const [earlyPageLoading, setEarlyPageLoading] = useState(false);
  const [earlyPageQuery, setEarlyPageQuery] = useState("");
  const [earlyAppliedQuery, setEarlyAppliedQuery] = useState("");
  const [earlyPageError, setEarlyPageError] = useState("");
  const earlyRequestSequence = useRef(0);
  const earlyController = useRef<AbortController | null>(null);
  async function loadEarlyPage(offset: number, query: string, version?: string) {
    const requestSequence = ++earlyRequestSequence.current;
    earlyController.current?.abort();
    const controller = new AbortController();
    earlyController.current = controller;
    setEarlyPageLoading(true);
    setEarlyPageError("");
    try {
      const params = new URLSearchParams({offset: String(offset), limit: "50"});
      if (query.trim()) params.set("query", query.trim());
      if (version) params.set("version", version);
      const response = await fetch("/api/workspace/page?" + params.toString(), {
        cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(55000)]),
      });
      if (controller.signal.aborted || requestSequence !== earlyRequestSequence.current) return;
      if (response.status === 409) {
        setEarlyPipelinePage(null);
        throw new Error("Published candidates changed. Search again to load the latest page.");
      }
      if (!response.ok) throw new Error("Pipeline page unavailable. Search again to retry.");
      const page = validatePipelinePage(await response.json(), offset, 50, version);
      if (controller.signal.aborted || requestSequence !== earlyRequestSequence.current) return;
      setEarlyPipelinePage(page);
      setEarlyAppliedQuery(query.trim());
    } catch (error) {
      if (!controller.signal.aborted && requestSequence === earlyRequestSequence.current)
        setEarlyPageError(error instanceof Error ? error.message : "Pipeline page unavailable.");
    } finally {
      if (!controller.signal.aborted && requestSequence === earlyRequestSequence.current) setEarlyPageLoading(false);
    }
  }
  useEffect(() => {
    void loadEarlyPage(0, "");
    return () => { earlyRequestSequence.current++; earlyController.current?.abort(); };
  }, []);

  const [summaryError, setSummaryError] = useState("");
  const [gemScans,setGemScans]=useState<Partial<Record<"GEM_JR"|"GEM",GemScanResult>>>({});
  // Explicitly curated manual shortlist only. Published stage membership and
  // its top-card totals remain source-owned, not rewritten by browser clicks.
  const [manualStageLists,setManualStageLists]=useState<Record<"GEM_JR"|"GEM",Record<string,string>>>({GEM_JR:{},GEM:{}});
  const [manualStageListsLoaded,setManualStageListsLoaded]=useState(false);
  useEffect(()=>{
    try{
      const raw=window.localStorage.getItem("pdufa_manual_stage_list_v1");
      const parsed=raw?JSON.parse(raw):null;
      const clean=(stage:"GEM_JR"|"GEM")=>{
        const entries=parsed?.[stage];
        if(!entries||typeof entries!=="object"||Array.isArray(entries))return {} as Record<string,string>;
        return Object.fromEntries(
          Object.entries(entries)
          .filter(([id,date])=>id.length>0&&id.length<1024&&typeof date==="string"&&/^\d{4}-\d{2}-\d{2}T/.test(date))
          .slice(0,1000)
        ) as Record<string,string>;
      };
      setManualStageLists({GEM_JR:clean("GEM_JR"),GEM:clean("GEM")});
    }catch{setManualStageLists({GEM_JR:{},GEM:{}});}
    setManualStageListsLoaded(true);
  },[]);
  useEffect(()=>{
    if(!manualStageListsLoaded)return;
    try{window.localStorage.setItem("pdufa_manual_stage_list_v1",JSON.stringify(manualStageLists));}
    catch{/* Browser storage disabled: list remains in memory this session. */}
  },[manualStageLists,manualStageListsLoaded]);

  // Remember which exact program IDs have ALREADY appeared in a completed
  // filtered scan, separately for GEM JR and GEM. Scans never auto-add to
  // curated lists; repeated scans cannot falsely label a prior match as NEW.
  const [seenStagePrograms,setSeenStagePrograms]=useState<Record<"GEM_JR"|"GEM",Record<string,string>>>({GEM_JR:{},GEM:{}});
  const [seenStageHistoryLoaded,setSeenStageHistoryLoaded]=useState(false);
  const [latestNewStageIds,setLatestNewStageIds]=useState<Record<"GEM_JR"|"GEM",string[]>>({GEM_JR:[],GEM:[]});
  useEffect(()=>{
    try{
      const raw=window.localStorage.getItem("pdufa_seen_stage_programs_v1");
      const parsed=raw?JSON.parse(raw):null;
      const clean=(stage:"GEM_JR"|"GEM")=>{
        const entries=parsed?.[stage];
        if(!entries||typeof entries!=="object"||Array.isArray(entries))return {} as Record<string,string>;
        return Object.fromEntries(Object.entries(entries)
          .filter(([id,date])=>typeof id==="string"&&id.length>0&&id.length<1024
            &&typeof date==="string"&&/^\d{4}-\d{2}-\d{2}T/.test(date))
          .slice(0,30000)) as Record<string,string>;
      };
      setSeenStagePrograms({GEM_JR:clean("GEM_JR"),GEM:clean("GEM")});
    }catch{setSeenStagePrograms({GEM_JR:{},GEM:{}});}
    setSeenStageHistoryLoaded(true);
  },[]);
  useEffect(()=>{
    if(!seenStageHistoryLoaded)return;
    try{window.localStorage.setItem("pdufa_seen_stage_programs_v1",JSON.stringify(seenStagePrograms));}
    catch{/* Browser storage disabled: stage history remains in memory this session. */}
  },[seenStagePrograms,seenStageHistoryLoaded]);
  // GEM JR live screen is not saved stage membership (11), nor a finished SCAN.
  // Keep the exact candidate IDs and checklist draft while switching stage tabs.
  const [gemJrLivePreview,setGemJrLivePreview]=useState<GemJrLivePreview|null>(null);
  const [gemJrDraft,setGemJrDraft]=useState<GemJrUiDraft|null>(null);
  const [gemLivePreview,setGemLivePreview]=useState<GemJrLivePreview|null>(null);
  const [gemDraft,setGemDraft]=useState<GemJrUiDraft|null>(null);
  const [gemSavedOnly,setGemSavedOnly]=useState<Record<"GEM_JR"|"GEM",boolean>>({GEM_JR:false,GEM:false});
  // One persisted set of restriction definitions and stage assignments drives
  // the central catalog and both GEM qualification scan checklists.
  const [masterRestrictions,setMasterRestrictions]=useState<CatalogEntry[]>(defaultCatalogEntries);
  const [masterRestrictionsReady,setMasterRestrictionsReady]=useState(false);
  useEffect(()=>{
    try{const raw=window.localStorage.getItem("pdufa-restriction-catalog-v1");
      if(raw)setMasterRestrictions(restoreCatalogEntries(JSON.parse(raw)));}
    catch{/* Keep approved defaults if browser storage is unavailable. */}
    setMasterRestrictionsReady(true);
  },[]);
  useEffect(()=>{
    if(!masterRestrictionsReady)return;
    try{window.localStorage.setItem("pdufa-restriction-catalog-v1",JSON.stringify(masterRestrictions));}
    catch{/* Editing remains available in memory. */}
  },[masterRestrictions,masterRestrictionsReady]);
  type RestrictionPresetStage = "PIPELINE" | "GEM_JR" | "GEM";
  type RestrictionPreset = {name:string; entries:CatalogEntry[]};
  const [restrictionPresets,setRestrictionPresets]=useState<Record<RestrictionPresetStage,RestrictionPreset[]>>({PIPELINE:[],GEM_JR:[],GEM:[]});
  const [presetNames,setPresetNames]=useState<Record<RestrictionPresetStage,string>>({PIPELINE:"",GEM_JR:"",GEM:""});
  const [presetChoices,setPresetChoices]=useState<Record<RestrictionPresetStage,string>>({PIPELINE:"",GEM_JR:"",GEM:""});
  const [presetsReady,setPresetsReady]=useState(false);
  useEffect(()=>{
    try {
      const saved=window.localStorage.getItem("pdufa-restriction-presets-v1");
      if(saved){
        const parsed=JSON.parse(saved);
        setRestrictionPresets({PIPELINE:Array.isArray(parsed.PIPELINE)?parsed.PIPELINE:[],GEM_JR:Array.isArray(parsed.GEM_JR)?parsed.GEM_JR:[],GEM:Array.isArray(parsed.GEM)?parsed.GEM:[]});
      }
    }catch{/* Keep presets usable in memory. */}
    setPresetsReady(true);
  },[]);
  useEffect(()=>{
    if(!presetsReady)return;
    try{window.localStorage.setItem("pdufa-restriction-presets-v1",JSON.stringify(restrictionPresets));}catch{/* Browser storage unavailable. */}
  },[restrictionPresets,presetsReady]);
  function saveRestrictionPreset(stage:RestrictionPresetStage, overrideName?:string){
    const name=overrideName?.trim()||presetNames[stage].trim()||presetChoices[stage];
    if(!name)return;
    if(restrictionPresets[stage].some(p=>p.name===name)&&!window.confirm("Overwrite saved preset "+name+"?"))return;
    setRestrictionPresets(old=>({...old,[stage]:[...old[stage].filter(p=>p.name!==name),{name,entries:masterRestrictions.map(e=>({...e,additionalStages:[...(e.additionalStages||[])],stagePriorities:{...e.stagePriorities}}))}]}));
    setPresetChoices(old=>({...old,[stage]:name}));
    setPresetNames(old=>({...old,[stage]:""}));
  }
  function loadRestrictionPreset(stage:RestrictionPresetStage){
    const saved=restrictionPresets[stage].find(p=>p.name===presetChoices[stage]);
    if(!saved||!window.confirm("Load "+saved.name+" for "+stage.replace("_"," ")+"? Current unsaved changes to this list will be replaced."))return;
    const stored=new Map(saved.entries.map(e=>[e.id,e]));
    setMasterRestrictions(current=>current.map(entry=>{
      const old=stored.get(entry.id);
      if(!old)return entry;
      const otherStages=catalogStages(entry).filter(s=>s!==stage);
      const included=catalogStages(old).includes(stage);
      const stages=[...otherStages,...(included?[stage]:[])];
      const priorityByStage={...entry.stagePriorities,[stage]:included?catalogStagePriority(old,stage):""};
      return {...entry,stage:stages[0]||"",additionalStages:stages.slice(1),
        stagePriorities:priorityByStage,priority:stages.length?priorityByStage[stages[0]]||entry.priority:"",
        enabled:otherStages.length?entry.enabled:(included?old.enabled:false),
        value:otherStages.length?entry.value:old.value,maximum:otherStages.length?entry.maximum:old.maximum};
    }));
  }
  function bottomPresetSave(stage:RestrictionPresetStage){
    return <div style={{borderTop:"1px solid #a2b4a4",marginTop:16,paddingTop:14,display:"grid",gap:8}}>
      <button type="button" style={{padding:"12px 16px",fontWeight:800,width:"100%",background:"#e4f1e2",border:"1px solid #35543a",borderRadius:9,color:"#18321c"}}
        onClick={()=>{
          const proposed=window.prompt("Name this new "+stage.replace("_"," ")+" restriction preset:");
          if(proposed?.trim())saveRestrictionPreset(stage,proposed.trim());
        }}>SAVE THIS LIST AS A NEW PRESET</button>
      <small>Save as many named presets as you need. Find them in the Saved Restriction Presets dropdown above.</small>
    </div>;
  }
  function restrictionPresetControls(stage:RestrictionPresetStage){
    return <div style={{border:"1px solid #a2b4a4",borderRadius:10,padding:12,margin:"12px 0",display:"grid",gap:9}}>
      <strong>SAVED RESTRICTION PRESETS — {stage.replace("_"," ")}</strong>
      <small>Save this list's membership, priority, enabled status and numeric values. Stored in this browser; other lists' membership is preserved on load.</small>
      <select aria-label={stage+" saved restriction preset"} style={{width:"100%",maxWidth:440}} value={presetChoices[stage]} onChange={e=>setPresetChoices(old=>({...old,[stage]:e.target.value}))}>
        <option value="">Select a saved preset</option>
        {restrictionPresets[stage].map(p=><option key={p.name} value={p.name}>{p.name}</option>)}
      </select>
      <input aria-label={stage+" new preset name"} placeholder="New preset name (e.g. Pipeline 1)" style={{width:"100%",maxWidth:440}} value={presetNames[stage]} onChange={e=>setPresetNames(old=>({...old,[stage]:e.target.value}))}/>
      <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
        <button type="button" disabled={!presetNames[stage].trim()&&!presetChoices[stage]} onClick={()=>saveRestrictionPreset(stage)}>SAVE / SAVE AS</button>
        <button type="button" disabled={!presetChoices[stage]} onClick={()=>loadRestrictionPreset(stage)}>LOAD</button>
        <button type="button" disabled={!presetChoices[stage]} onClick={()=>{
          const name=presetChoices[stage];
          if(!window.confirm("Delete saved preset "+name+"?"))return;
          setRestrictionPresets(old=>({...old,[stage]:old[stage].filter(p=>p.name!==name)}));
          setPresetChoices(old=>({...old,[stage]:""}));
        }}>DELETE PRESET</button>
      </div>
    </div>;
  }
  const [restrictionDestination,setRestrictionDestination]=useState<Record<string,"PIPELINE"|"GEM_JR"|"GEM">>({});
  const [restrictionListView,setRestrictionListView]=useState<"PIPELINE"|"GEM_JR"|"GEM">("PIPELINE");
  const jrRuleKeys=useMemo(()=>selectedGemKeys(masterRestrictions,"GEM_JR"),[masterRestrictions]);
  const gemRuleKeys=useMemo(()=>selectedGemKeys(masterRestrictions,"GEM"),[masterRestrictions]);
  const masterAlertGoals=useMemo(()=>Object.fromEntries(masterRestrictions.filter(entry=>entry.id.startsWith("alert_")).map(entry=>[entry.id.slice(6),entry.value])),[masterRestrictions]);
  const masterThresholds=useMemo(()=>Object.fromEntries(masterRestrictions
    .filter(entry=>["runway","gem_marketcap","gem_window","gem_volume","gem_rsi","gem_liquidity"].includes(entry.id))
    .map(entry=>[catalogGemKey(entry.id),{value:entry.value,maximum:entry.maximum}])),[masterRestrictions]);
  // A changed master selection/target invalidates old completed scan results.
  // Live previews are recomputed by the existing GEM checklist against the new rules.
  const masterScanFingerprint=useMemo(()=>JSON.stringify(masterRestrictions
    .filter(entry=>entry.enabled&&catalogStages(entry).some(stage=>(stage==="GEM_JR"||stage==="GEM")&&!!catalogStagePriority(entry,stage)))
    .map(entry=>[entry.id,entry.stage,entry.additionalStages,entry.priority,entry.stagePriorities,entry.value,entry.maximum])),[masterRestrictions]);
  const lastMasterScanFingerprint=useRef<string|null>(null);
  useEffect(()=>{
    if(!masterRestrictionsReady)return;
    if(lastMasterScanFingerprint.current!==null&&lastMasterScanFingerprint.current!==masterScanFingerprint){
      setGemScans({});
      setGemSavedOnly({GEM_JR:false,GEM:false});
    }
    lastMasterScanFingerprint.current=masterScanFingerprint;
  },[masterScanFingerprint,masterRestrictionsReady]);
  function changeManagedGemRules(stage:"GEM_JR"|"GEM",next:string[]){
    const desired=new Set(next);
    const allowed=gemAllowedKeys(stage);
    setMasterRestrictions(current=>current.map(entry=>{
      const key=catalogGemKey(entry.id);
      if(!key || !allowed.has(key))return entry;
      const assigned=catalogStages(entry),has=assigned.includes(stage),wants=desired.has(key);
      if(has===wants && (!wants || entry.enabled&&!!catalogStagePriority(entry,stage)))return entry;
      const stages=wants?[...assigned.filter(s=>s!==stage),stage]:assigned.filter(s=>s!==stage);
      const primary=stages.includes(entry.stage as "PIPELINE"|"GEM_JR"|"GEM")?entry.stage:(stages[0]||"");
      return {...entry,stage:primary,additionalStages:stages.filter(s=>s!==primary),
        enabled:wants?true:stages.length>0&&entry.enabled,priority:wants?(entry.priority||"1"):stages.length?entry.priority:"",
        stagePriorities:{...entry.stagePriorities,[stage]:wants?(catalogStagePriority(entry,stage)||"1"):""}};
    }));
  }
  // Automatically fetch the published snapshot once on mount; manual refresh remains available.
  const [fetchVersion, setFetchVersion] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [cachedAsOf, setCachedAsOf] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);
  const workspaceEtag = useRef<string | null>(null);
  const verifiedSnapshotRef = useRef<Snapshot | null>(null);
  const hasVerifiedWorkspace = useRef(false);
  const cachedAsOfRef = useRef<string | null>(null);
  const freshSnapshotReceived = useRef(false);
  const [top, setTop] = useState<TopNav>("PDUFA");
  const [restrictionTab,setRestrictionTab]=useState<"PRESET"|"RESTRICTIONS">("RESTRICTIONS");
  const [restrictionFocus,setRestrictionFocus]=useState<"DISEASE"|"COMPANY">("DISEASE");
  const [nav, setNav] = useState<Nav>("PIPELINE");
  // Deep links from standalone trial sheets reopen the matching workspace tab.
  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("section");
    if (requested === "GOAL") { setTop("GOAL"); return; }
    if (requested === "SCANS") { setTop("SCANS"); return; }
    if (requested === "RESULTS") { setTop("RESULTS"); return; }
    if (requested === "BACKUP") { setTop("BACKUP"); return; }
    if (requested === "RESTRICTIONS" || requested === "PRESET") { setTop("RESTRICTIONS"); if(requested==="PRESET")setRestrictionTab("PRESET"); return; }
    if (requested && (["PIPELINE","GEM_JR","GEM","WT","TRADING"] as const).some(section => section === requested)) {
      setTop("PDUFA");
      setNav(requested as Nav);
    }
  }, []);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  // Each GEM table shows up to 10 rows around its independently selected
  // candidate. Previous / Next move exactly one source-ordered row at a time.
  // The complete list remains available to nested clinical trial drilldowns.
  const highlightedGemRow=useRef<HTMLTableRowElement|null>(null);
  const gemTableScrollViewport=useRef<HTMLDivElement|null>(null);
  const [gemTrialExpanded,setGemTrialExpanded]=useState<Record<"GEM_JR"|"GEM",boolean>>({GEM_JR:false,GEM:false});
  const [gemTrialSections,setGemTrialSections]=useState<Record<string,boolean>>({});
  // Mobile-only qualification criteria: initially collapsed for both stages.
  // On desktop CSS keeps the complete criteria visible, regardless of this state.
  const [gemCriteriaExpanded,setGemCriteriaExpanded]=useState<Record<"GEM_JR"|"GEM",boolean>>({GEM_JR:false,GEM:false});
  const [masterProgram, setMasterProgram] = useState("");
  const [stageFilters, setStageFilters] = useState<string[]>([]);
  const [dateFilters, setDateFilters] = useState<string[]>([]);
  const [designationFilters, setDesignationFilters] = useState<DesignationKey[]>([]);
  const [appliedDesignationFilters, setAppliedDesignationFilters] = useState<DesignationKey[]>([]);
  const [query, setQuery] = useState("");
  const [onlyBand, setOnlyBand] = useState(false);
  const [trialFilters, setTrialFilters] = useState<TrialFilterValues>({ ...EMPTY_TRIAL_FILTERS });
  const [displayFilters, setDisplayFilters] = useState<PipelineSelection | null>(null);
  const [displayVersion, setDisplayVersion] = useState(0);
  const pipelineDataRef = useRef<HTMLDivElement>(null);
  const [gemQuery, setGemQuery] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [tags, setTags] = useState<Tags>({ watch: [], trade: [] });
  const [tagsReady, setTagsReady] = useState(false);
  const [legacyTags, setLegacyTags] = useState<Tags>({watch:[],trade:[]});
  const [storedIdentities,setStoredIdentities] = useState<{programId:string;id:string;ticker:string;drug:string}[]>([]);
  const [wtStatus, setWtStatus] = useState("Loading saved W/T labels…");
  const [wtTrialPreferences,setWtTrialPreferences]=useState<Record<string,WtTrialIndicatorPreference>>({});
  const [wtTrialPreferencesReady,setWtTrialPreferencesReady]=useState(false);
  const wtVersion = useRef(0);
  const wtCurrent = useRef<Tags>({ watch: [], trade: [] });
  const wtQueue = useRef<Promise<void>>(Promise.resolve());
  // Each permanent Program ID independently remembers ENTRY / STAY / EXIT indicator preferences.
  // Settings are local to this browser; existing WT tags and GEM qualification remain untouched.
  useEffect(()=>{
    try{setWtTrialPreferences(readWtPreferences(window.localStorage.getItem(WT_TRIAL_INDICATORS_KEY)));}
    catch{setWtTrialPreferences({});}
    setWtTrialPreferencesReady(true);
  },[]);
  useEffect(()=>{
    if(!wtTrialPreferencesReady)return;
    try{window.localStorage.setItem(WT_TRIAL_INDICATORS_KEY,JSON.stringify(wtTrialPreferences));}
    catch{/* In private browsing, settings remain usable until the page closes. */}
  },[wtTrialPreferences,wtTrialPreferencesReady]);
  function changeWtTrialStage(programId:string,stage:WtTrialStage|""){
    setWtTrialPreferences(current=>{
      const prior=current[programId]||emptyWtPreference();
      // Stage selection reveals its checkbox list; it does not pre-check any
      // indicators or erase earlier choices made for other stages of this trial.
      return {...current,[programId]:{...prior,stage}};
    });
  }
  function changeWtTrialIndicators(programId:string,stage:WtTrialStage,keys:string[]){
    const allowed=new Set(WT_GROUPS.find(group=>group.id===stage)?.items.map(item=>item.key)||[]);
    const manual=[...new Set(keys.filter(key=>allowed.has(key)))];
    setWtTrialPreferences(current=>{
      const prior=current[programId]||emptyWtPreference();
      // A manual checkbox edit replaces the FS preset for this stage.
      // Preserve FA's independent state and settings for other programs/stages.
      return {...current,[programId]:{
        ...prior,
        keys:{...prior.keys,[stage]:manual},
        manualKeys:{...prior.manualKeys,[stage]:manual},
        presets:{...prior.presets,[stage]:{...prior.presets[stage],fs:false}},
        configured:prior.configured.includes(stage)?prior.configured:[...prior.configured,stage],
      }};
    });
  }
  function toggleWtTrialPreset(programId:string,stage:WtTrialStage,mode:"FS"|"FA"){
    setWtTrialPreferences(current=>{
      const prior=current[programId]||emptyWtPreference();
      // FS follows all five visible checkmarks, not a stale stored boolean.
      // Thus clicking an already-lit FS turns off exactly its five indicators,
      // including when they were checked manually. FA remains independent.
      const turnFsOff=mode==="FS"&&areWtSuggestedIndicatorsChecked(prior.keys[stage],stage);
      const manual=turnFsOff?prior.manualKeys[stage].filter(
        key=>!suggestedWtIndicators[stage].includes(key)
      ):prior.manualKeys[stage];
      const flags=mode==="FS"
        ?{...prior.presets[stage],fs:!turnFsOff}
        :nextWtPresetFlags(prior.presets[stage],"FA");
      return {...current,[programId]:{
        ...prior,
        presets:{...prior.presets,[stage]:flags},
        manualKeys:{...prior.manualKeys,[stage]:manual},
        keys:{...prior.keys,[stage]:wtEffectivePresetKeys(manual,stage,flags)},
        configured:prior.configured.includes(stage)?prior.configured:[...prior.configured,stage],
      }};
    });
  }

  useEffect(() => {
    const ctrl = new AbortController();
    async function loadCounts() {
      try {
        // Render free instances can be waking when the initial summary request
        // reaches the frontend. Retry one transient gateway failure only;
        // never create a repeating browser polling loop.
        let response = await fetch("/api/workspace/summary", {
          cache: "no-store",
          signal: AbortSignal.any([ctrl.signal, AbortSignal.timeout(95000)]),
        });
        if ([502, 503, 504].includes(response.status) && !ctrl.signal.aborted) {
          await new Promise<void>(resolve => setTimeout(resolve, 4000));
          if (ctrl.signal.aborted) return;
          response = await fetch("/api/workspace/summary", {
            cache: "no-store",
            signal: AbortSignal.any([ctrl.signal, AbortSignal.timeout(95000)]),
          });
        }
        if (!response.ok) {
          if (!ctrl.signal.aborted) setSummaryError("Candidate totals request failed (HTTP " + response.status + ").");
          return;
        }
        const result: PublishedCounts = await response.json();
        if (!ctrl.signal.aborted) {
          setPublishedCounts(result);
          setSummaryError("");
        }
      } catch (error) {
        if (!ctrl.signal.aborted) setSummaryError("Candidate totals request failed: " + (error instanceof Error ? error.message : "Network error"));
      }
    }
    void loadCounts();
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    if (fetchVersion < 0) return;
    const ctrl = new AbortController();
    // Restore local data immediately while a fresh authoritative copy loads.
    if (fetchVersion === 0) {
      void readWorkspaceCache().then(cached => {
        if (!ctrl.signal.aborted && cached && !freshSnapshotReceived.current) {
          cachedAsOfRef.current = cached.asOf;
          setSnapshot(current => current ?? cached);
          setCachedAsOf(cached.asOf);
        }
      }).catch(() => { /* IndexedDB may be unavailable in private mode. */ });
    }
    // One bounded request on initial page load or an explicit Refresh click.
    // Never loop on a failing backend; preserve the previous verified snapshot.
    async function loadPublishedSources() {
      setRefreshing(true);
      setFetchError("Connecting to published PIPELINE, GEM JR and GEM data…");
      try {
        // Incremental refresh is safe only against a snapshot verified in this session.
        // Cached IndexedDB snapshots remain display-only until a full verification.
        const baseline = verifiedSnapshotRef.current;
        if (hasVerifiedWorkspace.current && baseline?.workspaceVersion) {
          try {
            const deltaResponse = await fetch("/api/workspace/delta?since=" + encodeURIComponent(baseline.workspaceVersion), {
              cache: "no-store",
              signal: AbortSignal.any([ctrl.signal, AbortSignal.timeout(30000)]),
            });
            if (deltaResponse.ok) {
              const delta = await deltaResponse.json() as WorkspaceDelta;
              if (ctrl.signal.aborted) return;
              if (delta.version && delta.unchanged && !delta.reset &&
                  delta.version === baseline.workspaceVersion) {
                setLastCheckedAt(new Date().toISOString());
                setFetchError("");
                return;
              }
              if (!delta.reset && !delta.unchanged) {
                const patched = applyWorkspaceDelta(baseline, delta);
                if (ctrl.signal.aborted) return;
                verifiedSnapshotRef.current = patched;
                workspaceEtag.current = null;
                setSnapshot(patched);
                void writeWorkspaceCache(patched).catch(() => {});
                setLastCheckedAt(new Date().toISOString());
                setFetchError("");
                return;
              }
            }
          } catch {
            if (ctrl.signal.aborted) return;
            // Unknown version, transient delta failure or invalid patch:
            // fall back to the complete verified workspace response below.
          }
        }
        // The bounded first-page request and full workspace verification are
        // independent. Never block the full load on a slow/failed page request,
        // particularly on mobile networks.
        const response = await fetch("/api/workspace", {
          cache: "no-store",
          headers: hasVerifiedWorkspace.current && workspaceEtag.current ? { "If-None-Match": workspaceEtag.current } : {},
          signal: AbortSignal.any([ctrl.signal, AbortSignal.timeout(95000)]),
        });
        if (response.status === 304) {
          if (!hasVerifiedWorkspace.current) throw new Error("Server returned unchanged without a verified in-memory snapshot");
          setLastCheckedAt(new Date().toISOString());
                setFetchError("");
          return;
        }
        if (!response.ok) {
          const details = await response.json().catch(() => ({})) as {error?:string};
          throw new Error("Published source unavailable: HTTP " + response.status +
            (details.error ? " — " + details.error : "."));
        }
        const data = await response.json() as Snapshot;
        if (ctrl.signal.aborted) return;
        if (!validWorkspaceSnapshot(data)) throw new Error("Published snapshot failed validation or backend returned stale source data");
        verifiedSnapshotRef.current = data;
        workspaceEtag.current = response.headers.get("etag");
        hasVerifiedWorkspace.current = true;
        freshSnapshotReceived.current = true;
        cachedAsOfRef.current = null;
        setSnapshot(data);
        setCachedAsOf(null);
        void writeWorkspaceCache(data).catch(() => { /* Keep fresh in-memory data if storage is unavailable. */ });
        setLastCheckedAt(new Date().toISOString());
                setFetchError("");
      } catch (error) {
        if (ctrl.signal.aborted) return;
        const message = error instanceof Error ? error.message : String(error);
        setFetchError(
          (cachedAsOfRef.current ? "Showing locally cached snapshot (as of " + cachedAsOfRef.current + "); NOT VERIFIED CURRENT. " : "") +
          (message.includes("timeout") || message.includes("Timeout")
            ? "Candidate loading timed out after 95 seconds. Automatic retries are disabled; tap RETRY LOADING CANDIDATES to try once more."
            : "Candidate loading failed: " + message + " Automatic retries are disabled.")
        );
      } finally {
        if (!ctrl.signal.aborted) setRefreshing(false);
      }
    }
    void loadPublishedSources();
    return () => ctrl.abort();
  }, [fetchVersion]);
  useEffect(() => {
    let local: Tags = {watch:[],trade:[]};
    try {
      const saved = JSON.parse(localStorage.getItem(TAG_KEY)||"{}");
      const valid=(v: unknown)=>typeof v==="string" && /^PDUFA-[0-9]{6,}$/.test(v);
      if(Array.isArray(saved.watch)&&Array.isArray(saved.trade)){
        const trade = [...new Set<string>(saved.trade.filter(valid))];
        local={watch:[...new Set<string>(saved.watch.filter(valid))].filter(v=>!trade.includes(v)),trade};
      }
      const legacy=JSON.parse(localStorage.getItem(LEGACY_TAG_KEY)||"{}");
      if(Array.isArray(legacy.watch)&&Array.isArray(legacy.trade)){
        setLegacyTags({watch:legacy.watch.filter((v:unknown)=>typeof v==="string"),trade:legacy.trade.filter((v:unknown)=>typeof v==="string")});
      }
    } catch { /* local storage may be disabled */ }
    wtCurrent.current=local;setTags(local);
    let cancelled=false;
    async function restore(){
      try {
        const response=await fetch("/api/program-watch-trade",{cache:"no-store"});
        if(!response.ok) throw Error("Program WT storage unavailable");
        const remote=await response.json();
        if(!Array.isArray(remote.watch)||!Array.isArray(remote.trade)||!Number.isSafeInteger(remote.version)) throw Error("Invalid WT data");
        if(cancelled)return;
        wtVersion.current=remote.version;
        const canonical: Tags={watch:remote.watch,trade:remote.trade};
        wtCurrent.current=canonical;setTags(canonical);
        setStoredIdentities(Array.isArray(remote.identities)?remote.identities:[]);
        setLegacyTags(prev=>({
          watch:[...new Set([...(remote.legacy?.watch||[]),...prev.watch])],
          trade:[...new Set([...(remote.legacy?.trade||[]),...prev.trade])]
        }));
        setWtStatus("Permanent program selections saved in Neon PostgreSQL; old ticker-only tags retained separately");
      } catch {
        if(!cancelled)setWtStatus("WT database unavailable — local program selections not synchronized");
      } finally {
        if(!cancelled)setTagsReady(true);
      }
    }
    void restore();
    return()=>{cancelled=true};
  },[]);
  useEffect(() => {
    if (!tagsReady) return;
    try { localStorage.setItem(TAG_KEY, JSON.stringify(tags)); } catch { /* keep current memory */ }
  }, [tags, tagsReady]);
  function mark(programId: string,kind: "watch"|"trade"|"clear"){
    if(!tagsReady||!/^PDUFA-[0-9]{6,}$/.test(programId)){
      setWtStatus("Unable to select this program: permanent Neon ID not available");
      return;
    }
    const prev=wtCurrent.current;
    const updated: Tags={
      watch:kind==="watch"?[...new Set([...prev.watch.filter(v=>v!==programId),programId])].sort():prev.watch.filter(v=>v!==programId),
      trade:kind==="trade"?[...new Set([...prev.trade.filter(v=>v!==programId),programId])].sort():prev.trade.filter(v=>v!==programId)
    };
    wtCurrent.current=updated;setTags(updated);setWtStatus("Saving permanent Program IDs to Neon…");
    wtQueue.current=wtQueue.current.catch(()=>{}).then(async()=>{
      const response=await fetch("/api/program-watch-trade",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({...updated,version:wtVersion.current})
      });
      if(!response.ok){setWtStatus(response.status===409?"Program selection conflict — reload this page": "Program selection save failed — local changes unsynchronized");return;}
      const remote=await response.json();
      wtVersion.current=remote.version;
      setWtStatus("Permanent Program IDs saved in Neon PostgreSQL");
    }).catch(()=>setWtStatus("Program selection save failed — local changes unsynchronized"));
  }

  const pipeline = snapshot?.pipeline || [];
  const restrictionRows = useMemo(() => {
    const technical = new Map<string, Candidate>();
    for (const member of [...(snapshot?.members.GEM_JR.rows || []), ...(snapshot?.members.GEM.rows || [])]) technical.set(member.id, member);
    return pipeline.map(row => { const member = technical.get(row.id);
      return member?.ticker === row.ticker && member.technical ? { ...row, technical: member.technical } : row; });
  }, [snapshot?.pipeline, snapshot?.members]);
  const availability = useMemo(() => pipelineAvailability(pipeline, { query, onlyBand, trial: trialFilters, asOf: snapshot?.asOf }, dateBand, STAGES, BANDS), [pipeline, onlyBand, query, trialFilters, snapshot?.asOf]);
  const possible = availability.rows;
  const qualificationBase = useMemo(() => filterPipelineRows(pipeline, { query, onlyBand, stages: stageFilters, dates: dateFilters }, dateBand), [pipeline, query, onlyBand, stageFilters, dateFilters]);
  const designationQualified = useMemo(() => filterBySelectedDesignations(possible, designationFilters, designationIndex), [possible, designationFilters, designationIndex]);
  const counted = useMemo(() => filterPipelineRows(designationQualified, { stages: stageFilters, dates: dateFilters }, dateBand), [designationQualified, stageFilters, dateFilters]);
  const displayed = useMemo(() => displayFilters ? filterBySelectedDesignations(
    filterPipelineRows(pipeline, displayFilters, dateBand), appliedDesignationFilters, designationIndex
  ) : [], [pipeline, displayFilters, appliedDesignationFilters, designationIndex]);
  const selectionKey = (selection: PipelineSelection) => JSON.stringify([
    [...selection.stages].sort(), [...selection.dates].sort(), selection.query, selection.onlyBand, selection.trial,
  ]);
  const draftKey = JSON.stringify([selectionKey({ stages: stageFilters, dates: dateFilters, query, onlyBand, trial: trialFilters }), [...designationFilters].sort()]);
  const appliedKey = displayFilters ? JSON.stringify([selectionKey(displayFilters), [...appliedDesignationFilters].sort()]) : "";
  const selectionsChanged = displayFilters !== null && draftKey !== appliedKey;

  useEffect(() => {
    if (displayVersion) pipelineDataRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [displayVersion]);

  function displayTrials() {
    if (designationFilters.length && !designationIndex) return;
    setDisplayFilters({ stages: [...stageFilters], dates: [...dateFilters], query, onlyBand, trial: { ...trialFilters }, asOf: snapshot?.asOf });
    setAppliedDesignationFilters([...designationFilters]);
    setDisplayVersion(value => value + 1);
  }
  function clearPipelineSelections() {
    setStageFilters([]);
    setDateFilters([]);
    setDesignationFilters([]);
    setAppliedDesignationFilters([]);
    setQuery("");
    setOnlyBand(false);
    setTrialFilters({ ...EMPTY_TRIAL_FILTERS });
    setDisplayFilters(null);
    setDisplayVersion(0);
  }
  const byProgram = useMemo(() => {
    const m=new Map<string,Candidate>();
    // Avoid allocating and copying the entire pipeline into a temporary array.
    for (const source of [snapshot?.members.GEM.rows, snapshot?.members.GEM_JR.rows, pipeline]) {
      for (const r of source || []) {
        if(r.programId&&!m.has(r.programId))m.set(r.programId,r);
      }
    }
    return m;
  },[snapshot,pipeline]);
  const byTicker = useMemo(() => {
    // Use a per-ticker identity set instead of scanning/copying the whole
    // ticker list for each of 11k+ published records on mobile.
    const m = new Map<string, Candidate[]>();
    const seen = new Map<string, Set<string>>();
    for (const source of [pipeline, snapshot?.members.GEM_JR.rows, snapshot?.members.GEM.rows]) {
      for (const r of source || []) {
        if (!r.ticker) continue;
        let keys = seen.get(r.ticker);
        if (!keys) { keys = new Set<string>(); seen.set(r.ticker, keys); }
        if (keys.has(r.id)) continue;
        keys.add(r.id);
        const items = m.get(r.ticker);
        if (items) items.push(r);
        else m.set(r.ticker, [r]);
      }
    }
    return m;
  }, [snapshot, pipeline]);

  // TRADING dropdown uses the same Neon-backed exact W/T programs as WT.
  // Multiple programs for one ticker remain separate choices.
  const tradingTickers = useMemo<TradingTicker[]>(() => {
    const saved = new Map(storedIdentities.map(x => [x.programId, x]));
    const toTicker = (programId:string,kind:"watch"|"trade"):TradingTicker => {
      const record = byProgram.get(programId);
      const identity = saved.get(programId);
      return {
        programId,kind,ticker:record?.ticker||identity?.ticker||"",
        drug:record?.drug||identity?.drug,
        pdufaDate:record?.pdufaDate,
        financingStatus:record?.financingStatus,
        phase3Status:record?.phase3Status,
        outcome:record?.outcome,
        runwayMonths:record?.technical?.runwayMonths,
        avgDollarVolume20:record?.technical?.avgDollarVolume20,
        riskAlerts:record?.technical?.riskAlerts
      };
    };
    return [
      ...tags.watch.map(id=>toTicker(id,"watch")),
      ...tags.trade.map(id=>toTicker(id,"trade"))
    ];
  },[tags.watch,tags.trade,byProgram,storedIdentities]);

  function toggleFilter(current: string[], item: string, setter: (value: string[])=>void) {
    setter(current.includes(item) ? current.filter(v => v !== item) : [...current, item]);
  }
  const stageCounts = availability.stageCounts;
  const dateCounts = availability.dateCounts;

  // Keep the top workflow totals in lockstep with each GEM candidate table,
  // including its live checkbox preview, completed scan and saved-only mode.
  // A new published snapshot invalidates old previews/scans.
  function gemCandidateRows(stage: "GEM_JR" | "GEM") {
    const scan = gemScans[stage];
    const activeScan = scan && scan.asOf === snapshot?.asOf && scan.sourceTotal === pipeline.length ? scan : null;
    const preview = stage === "GEM_JR" ? gemJrLivePreview : gemLivePreview;
    const activePreview = preview && preview.asOf === snapshot?.asOf && preview.sourceTotal === pipeline.length ? preview : null;
    return pickGemResearchRows({
      pipeline,
      savedStage: snapshot?.members[stage].rows || [],
      livePreview: activePreview,
      completedScan: activeScan,
      savedOnly: gemSavedOnly[stage],
    }).filter(record => record.ticker.toLowerCase().includes(gemQuery.toLowerCase()) ||
      (record.drug || "").toLowerCase().includes(gemQuery.toLowerCase()));
  }

  // One source of truth for the top stage bar and the individual page totals.
  // These are displayed-page records, not independent or hardcoded estimates:
  // Pipeline: the Pipeline header's current available count.
  // GEM JR/GEM: the exact filtered list shown in that page's table.
  // WT: the sum of Watchlist and Trading research cards on its page.
  const gemPageRows = { GEM_JR: gemCandidateRows("GEM_JR"), GEM: gemCandidateRows("GEM") };
  // Unscreened GEM research tables intentionally show the pipeline as a discovery
  // pool. Never label that pool size as a qualified GEM or GEM JR count.
  function verifiedStageCount(stage: "GEM_JR" | "GEM"): number | null {
    // Header cards count persistent stage membership, never the broad research
    // screening pool. An unqualified preview may contain every pipeline program.
    if (!snapshot) return null;
    return snapshot.members[stage].rows.length;
  }
  function stageCountDetail(_stage: "GEM_JR" | "GEM"): string {
    return "Saved members";
  }
  const pageTotals: Record<"PIPELINE" | "GEM_JR" | "GEM" | "WT",number> = {
    PIPELINE: designationQualified.length,
    GEM_JR: gemPageRows.GEM_JR.length,
    GEM: gemPageRows.GEM.length,
    WT: tags.watch.length + tags.trade.length,
  };
  const gemJrWorkflowCount = verifiedStageCount("GEM_JR");
  const gemWorkflowCount = verifiedStageCount("GEM");
  const gemJrCountDetail = stageCountDetail("GEM_JR");
  const gemCountDetail = stageCountDetail("GEM");

  // Preserve the exact numbers shown in these pages for linked trial sheets.
  // Snapshot date guards against displaying counts from an unrelated publication.
  useEffect(() => {
    if (!snapshot || !tagsReady) return;
    try {
      localStorage.setItem("pdufa_stage_totals_v1", JSON.stringify({
        asOf:snapshot.asOf,
        counts:{PIPELINE:pageTotals.PIPELINE,GEM_JR:verifiedStageCount("GEM_JR"),GEM:verifiedStageCount("GEM"),WT:pageTotals.WT},
        details:{GEM_JR:stageCountDetail("GEM_JR"),GEM:stageCountDetail("GEM")},
      }));
    } catch { /* local storage may be unavailable */ }
  },[snapshot?.asOf, tagsReady, pageTotals.PIPELINE, pageTotals.WT,
    gemJrWorkflowCount, gemWorkflowCount, gemJrCountDetail, gemCountDetail]);

  function wtButton(record: Candidate,kind:"watch"|"trade"){
    const id=record.programId||"";
    const current=tags[kind].includes(id);
    return <button type="button" className={current?"wt-active":"wt-btn"}
      disabled={!tagsReady||!/^PDUFA-[0-9]{6,}$/.test(id)} aria-pressed={current}
      onClick={()=>mark(id,current?"clear":kind)}
      title={id?(kind==="watch"?"Watch ":"Trading research ")+id:"Permanent ID unavailable"}>
      {kind==="watch"?"W":"T"}{current?" ✓":""}
    </button>;
  }
  function selectCandidate(record: Candidate, stage: Stage) { onInspect(record.ticker,stage,record.programId); }
  useEffect(()=>{
    if (nav!=="GEM" && nav!=="GEM_JR") return;
    if (!selected[nav]) return;
    const row=highlightedGemRow.current;
    const viewport=gemTableScrollViewport.current;
    if (!row || !viewport) return;
    // Scroll only the table viewport, not the full page or its wide
    // horizontal table position. Keep PREVIOUS / NEXT on screen.
    const bounds=viewport.getBoundingClientRect();
    const position=row.getBoundingClientRect();
    const stickyHeader=viewport.querySelector("thead")?.getBoundingClientRect().height || 38;
    if (position.top<bounds.top+stickyHeader+6) {
      viewport.scrollBy({top:position.top-bounds.top-stickyHeader-8,behavior:"smooth"});
    } else if (position.bottom>bounds.bottom-6) {
      viewport.scrollBy({top:position.bottom-bounds.bottom+8,behavior:"smooth"});
    }
  },[nav,selected.GEM,selected.GEM_JR,gemQuery]);

  function gemBlock(stage: "GEM_JR" | "GEM") {
    const group = snapshot?.members[stage];
    const scanned=gemScans[stage];
    // Live research candidates and saved stage membership are different data.
    const juniorScan=gemScans.GEM_JR;
    const currentJuniorScan=juniorScan && juniorScan.asOf===snapshot?.asOf && juniorScan.sourceTotal===pipeline.length ? juniorScan : null;
    const currentJuniorPreview=gemJrLivePreview && gemJrLivePreview.asOf===snapshot?.asOf && gemJrLivePreview.sourceTotal===pipeline.length?gemJrLivePreview:null;
    const currentJuniorDraft=gemJrDraft && gemJrDraft.asOf===snapshot?.asOf && gemJrDraft.sourceTotal===pipeline.length?gemJrDraft:null;
    const currentGemDraft=gemDraft && gemDraft.asOf===snapshot?.asOf && gemDraft.sourceTotal===pipeline.length?gemDraft:null;
    const currentGemPreview=gemLivePreview && gemLivePreview.asOf===snapshot?.asOf && gemLivePreview.sourceTotal===pipeline.length?gemLivePreview:null;
    const stageDraft=stage==="GEM_JR"?currentJuniorDraft:currentGemDraft;
    const stagePreview=stage==="GEM_JR"?currentJuniorPreview:currentGemPreview;
    const savedOnly=gemSavedOnly[stage];
    const savedMemberIds=new Set((group?.rows||[]).map(row=>row.id));
    // A screen is an unsaved research view, never a change to saved membership.
    // Re-run after published source refresh; never reuse results from another snapshot.
    const activeScan=scanned && scanned.asOf===snapshot?.asOf && scanned.sourceTotal===pipeline.length ? scanned : null;
    const researchResult=activeScan || stagePreview;
    const screenStatuses=!savedOnly&&researchResult?new Map<string,"PASS"|"NEEDS VERIFICATION">([
      ...researchResult.passes.map(r=>[r.id,"PASS"] as const),
      ...researchResult.needsReview.map(r=>[r.id,"NEEDS VERIFICATION"] as const)
    ]):null;
    // The candidate table and the live checkbox count must use one pool.
    // Only an explicit VIEW SAVED MEMBERS action displays saved membership.
    const rows=sortByAssessment(gemPageRows[stage],assessmentRecords,stage,assessmentOrder[stage]);
    const focusedIndex = Math.max(0,rows.findIndex(r=>r.id===selected[stage]));
    const chosen = rows[focusedIndex] || null;
    // Track the exact current stage-membership cycle (including re-entry).
    // No clinical readout, FDA date or scan-last-seen date is substituted.
    const historyById = new Map<string,StageHistory[]>();
    for(const period of group?.history||[]){
      historyById.set(period.id,[...(historyById.get(period.id)||[]),period]);
    }
    const listDates = (record:Candidate) => {
      if(!savedMemberIds.has(record.id))return {added:"",removed:""};
      const active = (historyById.get(record.id)||[]).filter(period=>!period.leftOn && period.status==="ACTIVE")
        .sort((a,b)=>b.cycle-a.cycle)[0];
      return {added:active?.enteredOn || record.firstFound || "",removed:""};
    };
    const visibleCount = Math.min(rows.length,10);
    const firstVisible = Math.max(0,Math.min(focusedIndex-4,rows.length-visibleCount));
    const visibleRows = rows.slice(firstVisible,firstVisible+visibleCount);
    // A newly opened row starts with only its chart expanded. Collapsing it
    // or moving to another row discards previously opened detail subsections.
    const resetOpenSections = (record:Candidate,section?:string) => {
      setGemTrialSections(current=>{
        const reset=Object.fromEntries(Object.entries(current).filter(([key])=>!key.startsWith(stage+"|")));
        if(section && section!=="chart") reset[stage+"|"+record.id+"|"+section]=true;
        return reset;
      });
    };
    const moveRow = (delta:-1|1) => {
      const next = rows[focusedIndex+delta];
      if(next){
        resetOpenSections(next);
        setSelected(current=>({...current,[stage]:next.id}));
        setGemTrialExpanded(current=>({...current,[stage]:true}));
      }
    };
    const selectTrial = (record:Candidate,section?:string) => {
      const same = chosen?.id===record.id && (selected[stage]===record.id || !selected[stage] && focusedIndex===0);
      const opening = Boolean(section) || !same || !gemTrialExpanded[stage];
      resetOpenSections(record,opening?section:undefined);
      setSelected(current=>({...current,[stage]:record.id}));
      setGemTrialExpanded(current=>({...current,[stage]:opening}));
    };
    // The first (Alpaca stock chart) section opens automatically for every
    // selected program, while a user's explicit collapse remains respected.
    const isSectionOpen=(section:string)=>{
      if(!chosen) return false;
      const key=stage+"|"+chosen.id+"|"+section;
      return section==="chart" ? gemTrialSections[key] !== false : gemTrialSections[key] === true;
    };
    const toggleSection=(section:string)=>{
      if(!chosen) return;
      const key=stage+"|"+chosen.id+"|"+section;
      setGemTrialSections(current=>({...current,[key]: !(section==="chart" ? current[key] !== false : current[key] === true)}));
    };
    const qualificationChecklist = (<GemQualificationChecklist key={stage} stage={stage} pipeline={pipeline} asOf={snapshot?.asOf||""} stageTotal={group?.rows?.length || 0} completedScan={activeScan}
        stageSavedRows={group?.rows||[]} manualStageList={manualStageLists[stage]}
        newThisScanIds={latestNewStageIds[stage]} scanHistoryReady={seenStageHistoryLoaded && manualStageListsLoaded}
        onAddToStageList={row=>{
          // Match exact program ID to currently loaded Pipeline, not ticker.
          if(!pipeline.some(candidate=>candidate.id===row.id))return;
          setManualStageLists(current=>current[stage][row.id]?current:{
            ...current,[stage]:{...current[stage],[row.id]:new Date().toISOString()}
          });
        }}
        onRemoveFromStageList={id=>setManualStageLists(current=>{
          if(!current[stage][id])return current;
          const next={...current[stage]};delete next[id];
          return {...current,[stage]:next};
        })}
        gemJrScan={currentJuniorScan} gemJrSavedRows={snapshot?.members.GEM_JR.rows||[]} gemJrLivePreview={currentJuniorPreview} gemJrDraft={currentJuniorDraft} gemDraft={currentGemDraft}
        managedSelected={stage==="GEM_JR"?jrRuleKeys:gemRuleKeys} managedGoals={masterAlertGoals} managedThresholds={masterThresholds} hideChecklistItems
        onManagedSelectedChange={keys=>changeManagedGemRules(stage,keys)} onOpenMasterRestrictions={()=>{setTop("RESTRICTIONS");setMobileNavOpen(false);}}
        onGemJrLivePreviewChange={setGemJrLivePreview} onGemJrDraftChange={setGemJrDraft} onGemLivePreviewChange={setGemLivePreview} onGemDraftChange={setGemDraft}
        onReset={()=>{
          setGemSavedOnly(current=>current[stage]?{...current,[stage]:false}:current);
          if(stage==="GEM_JR")setGemLivePreview(null);
          setGemScans(current=>{
          // Changing GEM JR criteria invalidates both its old scan and any GEM
          // result derived from that old upstream candidate pool.
          if(stage==="GEM_JR")return current.GEM_JR||current.GEM?{}:current;
          if(!current.GEM)return current;
          const next={...current};delete next.GEM;return next;
          });
        }}
        onScan={result=>{
          // Publish only first-time matching exact trial/program IDs as NEW.
          // Repeated runs remain visible through PREVIOUSLY SEEN, and users
          // manually choose whether to ADD any candidate to MY LIST.
          const publishedOrCurated=new Set([
            ...(group?.rows||[]).map(row=>row.id),
            ...Object.keys(manualStageLists[stage])
          ]);
          const firstSeen=newlyObservedProgramIds(
            result,new Set(Object.keys(seenStagePrograms[stage])),publishedOrCurated
          );
          setLatestNewStageIds(current=>({...current,[stage]:firstSeen}));
          if(result.selected.length){
            const today=result.evaluatedAt;
            const qualifying=new Set([...result.passes,...result.needsReview].map(row=>row.id).filter(Boolean));
            setSeenStagePrograms(current=>{
              const stageHistory=current[stage];
              const unseen=[...qualifying].filter(id=>!stageHistory[id]);
              if(unseen.length===0)return current;
              const additions=Object.fromEntries(unseen.map(id=>[id,today]));
              return {...current,[stage]:{...stageHistory,...additions}};
            });
          }
          setGemSavedOnly(current=>({...current,[stage]:false}));
          setGemScans(current=>stage==="GEM_JR"?{GEM_JR:result}:{...current,GEM:result});
          setGemQuery("");
          setGemTrialExpanded(current=>({...current,[stage]:false}));
          setGemTrialSections(current=>Object.fromEntries(Object.entries(current).filter(([key])=>!key.startsWith(stage+"|"))));
        }} />);
    if (top==="RESTRICTIONS") return <details className="panel" style={{margin:"12px 0",padding:12}}><summary style={{fontWeight:700,cursor:"pointer"}}>{stage==="GEM"?"GEM":"GEM JR"} SCAN — FS / FA</summary><p className="subtle">The restrictions are defined once in the master list above. FS and FA below select those same rows; no second editable checklist is shown.</p>{qualificationChecklist}</details>;
    return <section className={"gem-section " + (stage==="GEM" ? "gem-purple" : "gem-blue")} key={stage}>
      <div className="gem-heading">
        <div><h2>{stage==="GEM"?"GEM":"GEM JR"} · Candidate research</h2>
          <p>{stage==="GEM"?"Successful Phase 3 qualifies for review; second financing optional, dilution safeguards retained":"Early evidence watchlist; not GEM-qualified by ticker alone"}</p></div>
        <span className="gem-count">{pageTotals[stage].toLocaleString("en-US")} {savedOnly?"SAVED stage members":activeScan?"SCAN results":stagePreview?"LIVE checkbox screen candidates":"unrestricted research candidates"} · {(group?.rows.length||0).toLocaleString("en-US")} saved stage members · {stated(activeScan?.asOf||group?.asOf, "snapshot undated")}</span>
      </div>
      <AssessmentStatus stage={stage} />
      <AssessmentSort value={assessmentOrder[stage]} onChange={value=>setAssessmentOrder(current=>({...current,[stage]:value}))} />

      {activeScan && <div className="panel" role="status" aria-live="polite" style={{marginBottom:12,padding:14,border:"1px solid #76947d",borderRadius:7,background:"#f3fcf5"}}>
        <strong>{activeScan.sourceKind==="GEM_JR"?"GEM JR SCAN INPUT":activeScan.sourceKind==="GEM_JR_LIVE"?"GEM JR LIVE CHECKBOX INPUT":activeScan.sourceKind==="GEM_JR_UNSCREENED"?"GEM JR RESEARCH UNIVERSE INPUT":"PIPELINE"} SCREEN RESULTS — {stage==="GEM"?"GEM":"GEM JR"} · RUN #{activeScan.runNumber}</strong>
        <p><strong>{(activeScan.passes.length+activeScan.needsReview.length).toLocaleString("en-US")} TOTAL COMBINED CANDIDATES</strong> · intersection of all checked requirements (AND), no duplicate counting. Of {activeScan.baseline.toLocaleString("en-US")} {activeScan.sourceKind==="GEM_JR"?"GEM JR scan candidates":activeScan.sourceKind==="GEM_JR_LIVE"?"GEM JR checkbox screen candidates":activeScan.sourceKind==="GEM_JR_UNSCREENED"?"unscreened GEM JR research universe":"PIPELINE records"} assessed: {activeScan.passes.length.toLocaleString("en-US")} verified matches · {activeScan.needsReview.length.toLocaleString("en-US")} need evidence verification · {activeScan.fails.length.toLocaleString("en-US")} excluded.</p>
        <p className="subtle">Checked requirements: {activeScan.audits.map(a=>a.label).join("; ")||"None — unrestricted"}. Only programs satisfying every selected check or needing verification are included in the table, never a sum of independent criterion totals. Nothing is automatically added to GEM membership. Source {stated(activeScan.asOf)}; run finished {new Date(activeScan.evaluatedAt).toLocaleString()}.</p>
        <button type="button" className="secondary" onClick={()=>setGemScans(current=>{const next={...current};delete next[stage];return next})}>CLEAR SCAN — RETURN TO LIVE SCREEN</button>
      </div>}
      {chosen && <div className="gem-decision-band" aria-label={stage==="GEM"?"GEM candidate eligibility and evidence coverage":"GEM JR candidate eligibility and evidence coverage"}>
        <div className="gem-decision-summary">
          <span className="gem-decision-program">{chosen.ticker} · {stated(chosen.programId, "PROGRAM ID UNVERIFIED")} · {stage==="GEM"?"GEM":"GEM JR"}</span>
          <strong className={"gem-eligibility gem-eligibility-"+candidateDecision(chosen,stage).tone}>
            {candidateDecision(chosen,stage).title}
          </strong>
          <p>{candidateDecision(chosen,stage).reason}</p>
          <small>Entry decision: {stated(chosen.technical?.entryStatus)} · Exit override: {stated(chosen.technical?.exitStatus)}</small>
        </div>
        <div className="gem-decision-evidence">
          <EvidenceCoverage label="ENTRY EVIDENCE" coverage={chosen.technical?.entryCoverage} />
          <EvidenceCoverage label="EXIT EVIDENCE" coverage={chosen.technical?.exitCoverage} />
        </div>
      </div>}
      <div className="gem-body">
        <aside className="gem-criteria gem-criteria-responsive" data-open={gemCriteriaExpanded[stage]?"true":"false"}>
          <h3 className="gem-criteria-desktop-heading">Qualification criteria</h3>
          <button type="button" className="gem-criteria-mobile-trigger"
            aria-expanded={gemCriteriaExpanded[stage]} aria-controls={"gem-criteria-content-"+stage}
            onClick={()=>setGemCriteriaExpanded(current=>({...current,[stage]:!current[stage]}))}>
            <span>Qualification criteria</span>
            <span className="gem-criteria-trigger-state" aria-hidden="true">{gemCriteriaExpanded[stage]?"− Hide ▲":"+ Show ▼"}</span>
          </button>
          <div className="gem-criteria-collapsible-content" id={"gem-criteria-content-"+stage}>
            <p className="subtle">Source observations beside target levels for the selected program.</p>
            <Goals record={chosen} />
          </div>
        </aside>
        <div className="gem-table-panel">
          <div className="sectionhead gem-table-heading">
            <h3>{savedOnly?"SAVED STAGE MEMBERS · explicit saved-list view":activeScan?"COMPLETED SCAN RESULTS · research only · not saved stage membership":"LIVE RESEARCH SCREEN · not saved stage membership"}</h3>
            <div className="gem-table-controls" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" table rows"}>
               <button type="button" className="secondary" aria-pressed={savedOnly}
                 onClick={()=>setGemSavedOnly(current=>({...current,[stage]:!current[stage]}))}>
                 {savedOnly?"BACK TO LIVE SCREEN":"VIEW SAVED MEMBERS ("+(group?.rows.length||0).toLocaleString("en-US")+")"}
               </button>
              <span className="gem-table-visible" role="status" aria-live="polite">
                Selected row {rows.length?focusedIndex+1:0} of {rows.length} · {chosen?.ticker||"No candidate"}
              </span>
              <button type="button" className="secondary" disabled={focusedIndex<=0||!rows.length}
                onClick={()=>moveRow(-1)} aria-label="Select previous candidate row">↑ PREVIOUS ROW</button>
              <button type="button" className="secondary" disabled={focusedIndex>=rows.length-1||!rows.length}
                onClick={()=>moveRow(1)} aria-label="Select next candidate row">↓ NEXT ROW</button>
            </div>
          </div>
          <div className="table-scroll gem-row-scroller" ref={gemTableScrollViewport} aria-label={(stage==="GEM"?"GEM":"GEM JR")+" candidates scrollable table"}>
            <table className="gem-source-parity-table">
              <thead><tr>
                {["Score trial","#","Program ID","W","T","Ticker","Date Added","Date Removed","Eligibility","Company","Indication","Phase","P3 Readout","PDUFA","Financing Status","Cash Runway","Market Cap","PoA","Short Int.","Entry Score","Entry Evidence","Exit Risk","Exit Evidence","Status","Trend (source)","Details"].map(h=><th key={h}>{h}</th>)}<AssessmentHeaders stage={stage} />
              </tr></thead>
              <tbody>{visibleRows.map((r,i)=><Fragment key={r.id}><tr
                ref={chosen?.id===r.id && selected[stage] ? highlightedGemRow : undefined}
                className={chosen?.id===r.id?"selected-record gem-focused-row":"gem-selectable-row"}
                aria-selected={chosen?.id===r.id} tabIndex={0}
                onClick={event=>{
                  if ((event.target as HTMLElement).closest("a,button,input,select,textarea,label")) return;
                  selectTrial(r);
                }}
                onKeyDown={event=>{
                  if (event.target!==event.currentTarget) return;
                  if(event.key==="Enter"||event.key===" "){
                    event.preventDefault();
                    selectTrial(r);
                  }
                }}
                aria-expanded={chosen?.id===r.id && gemTrialExpanded[stage]}
                aria-label={"Trial "+r.ticker+" · click to expand or collapse stock details"}>
                <td><ScoreProgressButton label="Score Trial" stage={stage} rowId={r.id} onScore={() => selectTrial(r,"assessments")} /></td>
                <td className="numeric">{firstVisible+i+1}</td>
                <td><strong className="permanent-id">{stated(r.programId)}</strong></td>
                <td>{wtButton(r,"watch")}</td>
                <td>{wtButton(r,"trade")}</td>
                <td><button type="button" className="ticker-select" aria-expanded={chosen?.id===r.id && gemTrialExpanded[stage]} onClick={()=>selectTrial(r)}>{r.ticker} {chosen?.id===r.id && gemTrialExpanded[stage]?"▾":"▸"}</button></td>
                <td title="Saved stage membership date (not screening date)">{savedMemberIds.has(r.id)?stated(listDates(r).added,"NOT RECORDED"):"NOT STAGE MEMBER"}</td>
                <td title="No removal date while the exact program remains active in this list">—</td>
                <td>{screenStatuses?<span className="gem-table-eligibility" style={{background:screenStatuses.get(r.id)==="PASS"?"#d7f7e4":"#fff0d8",color:"#232323",padding:"5px 7px",borderRadius:5}}>{!stageDraft?.selected.length?"UNRESTRICTED / NOT QUALIFIED":screenStatuses.get(r.id)==="PASS"?"PASSED CHECKED RULES":"NEEDS VERIFICATION"}</span>:<span className={"gem-table-eligibility gem-eligibility-"+candidateDecision(r,stage).tone}
                  title={candidateDecision(r,stage).reason}>{candidateDecision(r,stage).title}</span>}</td>
                <td>{stated(r.company,"—")}</td>
                <td title={stated(r.drug)}>{trialSheetUrl(r)
                  ? <a href={trialSheetUrl(r)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">{stated(r.indication,"—")} ↗<small>{trialId(r)} · Full trial sheet</small></a>
                  : stated(r.indication,"—")}</td>
                <td>{stated(r.stage,"P3")}</td>
                <td>{stated(r.phase3Date,"—")}</td>
                <td title={stated(r.fdaSource,"FDA date unverified")}>{stated(r.pdufaDate,"—")}</td>
                <td>{stated(r.financingStatus,"—")}</td>
                <td title={stated(r.technical?.runwayReason)}>{r.technical?.runwayMonths == null?"—":r.technical.runwayMonths.toFixed(1)+" mo"}</td>
                <td>{money(r.marketCap)}</td>
                <td>{stated(r.approvalProbability,"—")}</td>
                <td>—</td>
                <td title={stated(r.technical?.entryStatus)}>{r.technical?.entry??"—"}</td>
                <td><EvidenceCoverage label="Entry" coverage={r.technical?.entryCoverage} compact /></td>
                <td title={stated(r.technical?.exitStatus)}>{r.technical?.exitRisk??"—"}</td>
                <td><EvidenceCoverage label="Exit" coverage={r.technical?.exitCoverage} compact /></td>
                <td>{r.candidateLinked===false?"UNLINKED":stated(r.membershipStatus||r.phase3Status,"—")}</td>
                <td><button type="button" className="secondary" onClick={()=>selectTrial(r,"chart")}>Alpaca chart ↓</button></td>
                <td>
                  <DetailButton item={r} />
                  {trialSheetUrl(r) && <a href={trialSheetUrl(r)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">Full trial sheet ↗</a>}
                  <button type="button" className="record-select" onClick={()=>selectTrial(r,"overview")}>Research details ↓<small>{stated(r.drug)} · {r.id}</small></button>
                </td>
                <AssessmentCells row={r} stage={stage} onOpen={()=>selectTrial(r,"assessments")} />
              </tr>
              {chosen?.id===r.id && gemTrialExpanded[stage] && <tr className="gem-inline-detail-row">
                <td colSpan={34}>
                  <div className="gem-inline-detail-panel" aria-label={r.ticker+" expandable clinical trial and stock details"}>
                    <div className="gem-inline-detail-header">
                      <div><strong>TRIAL · {stated(r.drug,r.ticker)} · {r.ticker}</strong>
                        <small>{stated(r.programId)} · {stated(r.nctId,"NO EXACT NCT")} · {stated(r.indication)}</small>
                        <small>{savedMemberIds.has(r.id)?"Saved stage member · Added: "+stated(listDates(r).added,"NOT RECORDED"):"Research screen candidate · NOT a saved stage member"}</small>
                        <span>Selected gold row · expand any detail category below</span></div>
                      <button type="button" className="secondary" onClick={()=>setGemTrialExpanded(current=>({...current,[stage]:false}))}>
                        COLLAPSE TRIAL ↑
                      </button>
                    </div>
                    <div className="gem-inline-sections">
                      <GemInlineSection title="Stock price / Alpaca chart" description="Saved close and volume evidence for this exact permanent program"
                        open={isSectionOpen("chart")} onToggle={()=>toggleSection("chart")}>
                        {r.programId ? <><ProgramMarketEnrichment key={r.programId+"-market"} programId={r.programId} exactKey={r.id} stage={stage}/><EntrySignal programId={r.programId} ticker={r.ticker}/><AlpacaStockChart key={r.programId} programId={r.programId} ticker={r.ticker} /></>
                          : <p className="subtle">Alpaca chart awaits a verified permanent Program ID.</p>}
                      </GemInlineSection>
                      <GemInlineSection title="Stock / program details" description="Company, drug, trial identity, SEC financing, FDA evidence"
                        open={isSectionOpen("overview")} onToggle={()=>toggleSection("overview")}>
                        <SourceDetails record={{...r,listAddedOn:listDates(r).added,listRemovedOn:listDates(r).removed}}/>
                        <div className="gem-inline-detail-actions">
                          <button type="button" onClick={()=>{setMasterProgram(r.id);setNav("MASTER");window.scrollTo({top:0,behavior:"smooth"});}}>Gold Master Chart ↗</button>
                          <button type="button" onClick={()=>selectCandidate(r,stage)}>Open autosaved checklist ↗</button>
                        </div>
                      </GemInlineSection>
                      <GemInlineSection title="Clinical trial full record" description="Exact NCT registry fields, results and reported p-values"
                        open={isSectionOpen("trial")} onToggle={()=>toggleSection("trial")}>
                        {trialSheetUrl(r) ? <TrialFields key={r.id} row={r} onClose={()=>toggleSection("trial")}/>
                          : <p className="subtle">No exact NCT clinical-trial record linked to this program. Missing registry evidence is not inferred.</p>}
                      </GemInlineSection>
                      <GemInlineSection title="Candidate assessment scores and all data" description="Seven clinical and seven opportunity assessments, individual points, rules, sources and history"
                        open={isSectionOpen("assessments")} onToggle={()=>toggleSection("assessments")}>
                        <CandidateAssessments key={r.id+"-assessments"} row={r} initialStage={stage}/>
                      </GemInlineSection>
                      <GemInlineSection title="Entry and exit scores" description="Weighted evidence, completeness and risk overrides"
                        open={isSectionOpen("scores")} onToggle={()=>toggleSection("scores")}>
                        <TechnicalPanel record={r}/>
                      </GemInlineSection>
                      <GemInlineSection title="Indicators / targets" description="Market indicators, goal comparison and source gaps"
                        open={isSectionOpen("indicators")} onToggle={()=>toggleSection("indicators")}>
                        <PriorityIndicators record={r}/>
                      </GemInlineSection>
                    </div>
                  </div>
                </td>
              </tr>}
              </Fragment>)}</tbody></table>
            {!rows.length && <p className="subtle">{activeScan?"No passed or needs-verification pipeline records for these selections. Try SUGGESTED or reduce the restrictions; failed records are counted above.":"No matching saved GEM candidates."}</p>}
          </div>

        </div>
      </div>
      <details className="nested-expander">
        <summary>Historical stage transitions — recorded entries, departures and re-entries ({group?.history?.length||0})</summary>
        <div className="table-scroll"><table><thead><tr><th>Program ID</th><th>Ticker</th><th>Drug</th><th>Date Added</th><th>Date Removed</th><th>Cycle</th><th>Reason / status</th></tr></thead>
          <tbody>{(group?.history||[]).map((t,i)=><tr key={t.id+"|"+t.cycle+"|"+i}><td className="permanent-id">{stated(t.programId)}</td><td>{t.ticker}</td><td>{t.drug}</td><td>{stated(t.enteredOn,"Not recorded")}</td>
            <td>{stated(t.leftOn,"Currently listed")}</td><td>{t.cycle}</td><td>{stated(t.reason,t.status)}</td></tr>)}</tbody></table></div>
        <p className="subtle small">Date Added and Date Removed record source-verified GEM-stage list membership (including separate re-entry cycles), not trial registration, Phase 3, FDA, or financing dates. A blank removal date means this listing cycle is still active.</p>
      </details>
      <Drilldown rows={rows} />
    </section>;
  }

  // The original PIPELINE filter state and handlers stay unchanged.
  // The user has not yet asked to connect them to the separate live-impact
  // restrictions catalog; relocation is display-only.
  const stageAndDateFilter = (group: {title:string;description:string;total:string;items:{label:string;count:number}[];selected:string[];setter:typeof setStageFilters}) => (
    <fieldset className="filter-count-group">
      <legend>{group.title}</legend>
      <div className="filter-group-total"><span>{group.description} · {group.total}</span><strong>{possible.length.toLocaleString("en-US")}</strong></div>
      <div className="filter-checks">{[...group.items].sort((a,b)=>a.label.localeCompare(b.label)).map(item=><label className={group.selected.includes(item.label)?"filter-option filter-option-selected":"filter-option"} key={item.label}>
        <input type="checkbox" checked={group.selected.includes(item.label)} onChange={()=>toggleFilter(group.selected,item.label,group.setter)} />
        <span className="filter-label-text">{item.label}</span><b className="filter-count">{item.count.toLocaleString("en-US")}</b>
      </label>)}</div>
      <button type="button" className="secondary pipeline-group-select-toggle" onClick={()=>group.setter(group.items.every(item=>group.selected.includes(item.label))?[]:group.items.map(item=>item.label))}>{group.items.every(item=>group.selected.includes(item.label))?"NONE":"ALL"}</button>
    </fieldset>
  );
  const pipelineMovedFilters = (
    <section style={{margin:0,padding:0,width:"100%",maxWidth:"100%",minWidth:0,display:"contents"}}>
      <details className="panel" style={{margin:"12px 0",padding:12,width:"100%",minWidth:0,boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>STAGE COUNTS — PHASES ▾ ({stageFilters.length} selected)</summary>
        {stageAndDateFilter({title:"STAGE COUNTS",description:"Available by current stage",total:"PHASE TOTAL",items:stageCounts,selected:stageFilters,setter:setStageFilters})}
      </details>
      <details className="panel" style={{margin:"12px 0",padding:12,width:"100%",minWidth:0,boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>DATE TRIAL COUNTS — PDUFA ▾ ({dateFilters.length} selected)</summary>
        {stageAndDateFilter({title:"DATE TRIAL COUNTS",description:"Available by PDUFA countdown",total:"DATE TOTAL",items:dateCounts,selected:dateFilters,setter:setDateFilters})}
      </details>
      <details className="panel" style={{margin:"12px 0",padding:12,width:"100%",minWidth:0,boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>TRIAL QUALIFICATION FILTERS ▾ ({activeTrialFilters(trialFilters)} selected)</summary>
        <TrialQualificationFilters rows={pipeline} countRows={qualificationBase} value={trialFilters} onChange={setTrialFilters} asOf={snapshot?.asOf||""} ready={snapshot?.trialFilterSchema===1} />
      </details>
      <details className="panel" style={{margin:"12px 0",padding:12,width:"100%",minWidth:0,boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>FDA SPECIAL DESIGNATIONS — ORIGINAL COUNTS ▾ ({designationFilters.length} selected)</summary>
        <SpecialDesignationCounts rows={possible} asOf={snapshot?.asOf||""} selected={designationFilters} onChange={setDesignationFilters} index={designationIndex} loading={designationLoading} error={designationError} onRetry={retryDesignations}/>
      </details>
      <div className="panel" style={{padding:12,width:"100%",minWidth:0,boxSizing:"border-box"}}>
        <label>Search Program ID, ticker, drug, indication, NCT <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Optional search"/></label>
        <label className="cap-filter"><input type="checkbox" checked={onlyBand} onChange={e=>setOnlyBand(e.target.checked)}/>Market cap $300M–$10B only (optional)</label>
        <div className="pipeline-actions pipeline-display-actions">
          <button type="button" disabled={designationFilters.length>0&&!designationIndex} onClick={()=>{displayTrials();setTop("PDUFA");setNav("PIPELINE");setMobileNavOpen(false);}}>DISPLAY TRIALS · {counted.length.toLocaleString("en-US")} matching</button>
          <button type="button" className="secondary" onClick={clearPipelineSelections}>CLEAR SELECTIONS</button>
        </div>
        {selectionsChanged&&<p className="filter-pending" role="status">Selections changed — press DISPLAY TRIALS to update the list.</p>}
      </div>
    </section>
  );

  return <div className="migration-workspace">
    <div className="worktop">
      <button type="button" className={top==="GOAL"?"nav-selected":""} aria-current={top==="GOAL"?"page":undefined} onClick={()=>{setTop("GOAL");setMobileNavOpen(false);}}>GOAL</button>
      <button type="button" className={top==="SCANS"?"nav-selected":""} aria-current={top==="SCANS"?"page":undefined} onClick={()=>{setTop("SCANS");setMobileNavOpen(false);}}>SCANS</button>
      <button type="button" className={top==="RESULTS"?"nav-selected":""} aria-current={top==="RESULTS"?"page":undefined} onClick={()=>{setTop("RESULTS");setMobileNavOpen(false);}}>RESULTS</button>
      <a href="/predictions" style={{display:"inline-flex",alignItems:"center",padding:"8px 12px",textDecoration:"none",border:"1px solid currentColor",borderRadius:6}}>PREDICTIONS</a>
      <a href="/installation-audit" className="nav-selected" style={{display:"inline-flex",alignItems:"center",padding:"8px 12px",textDecoration:"none",border:"1px solid currentColor",borderRadius:6}}>SYSTEM STATUS</a>
      <button type="button" className={top==="BACKUP"?"nav-selected":""} aria-current={top==="BACKUP"?"page":undefined} onClick={()=>{setTop("BACKUP");setMobileNavOpen(false);}}>BACKUP</button>
      <button type="button" className={top==="PDUFA"?"nav-selected":""} onClick={()=>setTop("PDUFA")}>PDUFA</button>
      <button type="button" className={top==="PREDICTION"?"nav-selected":""} aria-current={top==="PREDICTION"?"page":undefined} onClick={()=>{setTop("PREDICTION");setMobileNavOpen(false);}}>PREDICTION</button>
      <button type="button" className={top==="CALENDAR"?"nav-selected":""} onClick={()=>setTop("CALENDAR")}>PDUFA Calendar</button>
      
      <button type="button" className={top==="RESTRICTIONS"?"nav-selected":""} aria-current={top==="RESTRICTIONS"?"page":undefined} onClick={()=>{setTop("RESTRICTIONS");setMobileNavOpen(false);}}>RESTRICTIONS</button>
      <button type="button" className="secondary" disabled={refreshing} onClick={()=>setFetchVersion(v=>v+1)}>{refreshing ? (cachedAsOf ? "Verifying latest data…" : "Loading published candidates…") : "Load published candidates"}</button>
      <span className="workspace-stage">{cachedAsOf ? "CACHED SNAPSHOT · " + cachedAsOf + " · NOT VERIFIED CURRENT" : snapshot ? "Published " + snapshot.asOf : refreshing ? "Loading published candidates…" : "Candidate totals ready · Full lists on demand"} · No live orders</span>
    </div>
    {top==="PREDICTION" && <section className="panel" aria-label="PREDICTION — HOP">
      <h2>PREDICTION</h2>
      <p>Historical Outcome Prediction (HOP) · Published GEM JR, GEM and W/T lists</p>
      <p role="status"><strong>Research only:</strong> Historical matching and validated approval probabilities are not available yet. Existing PoA values are not HOP predictions.</p>
      <HopReadinessPanel />
      {!snapshot ? <p>Load published candidates to see the source-linked trial inventory. No estimates will be generated.</p> : <>
        <p className="subtle">Published snapshot: {snapshot.asOf} · Membership and W/T labels reflect their respective saved sources.</p>
        {([
          ["GEM JR", snapshot.members.GEM_JR.rows],
          ["GEM", snapshot.members.GEM.rows],
          ["WT", [...snapshot.members.GEM_JR.rows, ...snapshot.members.GEM.rows].filter(row => tags.watch.includes(row.programId || row.id) || tags.trade.includes(row.programId || row.id))]
        ] as [string, Candidate[]][]).map(([group, rows]) => <details key={group} className="priority-panel" open={group==="GEM JR"}>
          <summary>{group} · {rows.length} published candidates {group==="WT"?"(saved W/T labels)":""}</summary>
          <div className="table-scroll"><table><thead><tr><th>Ticker</th><th>Program ID</th><th>Drug</th><th>Indication</th><th>PDUFA</th><th>Historical comparators</th><th>HOP prediction</th></tr></thead>
          <tbody>{rows.slice(0,100).map((row,index)=><tr key={row.programId || row.id || index}><td>{row.ticker}</td><td>{row.programId || row.id}</td><td>{row.drug || "Not available"}</td><td>{row.indication || "Not available"}</td><td>{row.pdufaDate || "Not verified"}</td><td>Not assessed</td><td>Not validated</td></tr>)}</tbody></table></div>
          {rows.length>100 && <p>Showing first 100 of {rows.length} records; historical matching is not yet active.</p>}
        </details>)}
      </>}
      <p>Source data is read-only. Pipeline, GEM JR, GEM, WT and FS/FA presets remain unchanged.</p>
    </section>}
    {top==="RESTRICTIONS" && <div aria-label="Restriction sub-tabs" style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,margin:"12px 0"}}>
      <button type="button" aria-current={restrictionTab==="RESTRICTIONS"?"page":undefined} className={restrictionTab==="RESTRICTIONS"?"nav-selected":""} onClick={()=>{setRestrictionTab("RESTRICTIONS");setMobileNavOpen(false);}}>RESTRICTIONS</button>
      <button type="button" aria-current={restrictionTab==="PRESET"?"page":undefined} className={restrictionTab==="PRESET"?"nav-selected":""} onClick={()=>{setRestrictionTab("PRESET");setMobileNavOpen(false);}}>PRESET</button>
    </div>}
    {top==="RESTRICTIONS" && restrictionTab==="RESTRICTIONS" && <div aria-label="Disease and company tools" style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,margin:"8px 0 14px"}}><button type="button" className={restrictionFocus==="DISEASE"?"nav-selected":""} aria-pressed={restrictionFocus==="DISEASE"} onClick={()=>setRestrictionFocus("DISEASE")}>DISEASE · 5,168</button><button type="button" className={restrictionFocus==="COMPANY"?"nav-selected":""} aria-pressed={restrictionFocus==="COMPANY"} onClick={()=>setRestrictionFocus("COMPANY")}>COMPANY ↔ DISEASE</button></div>}
    {top!=="GOAL" && top!=="RESTRICTIONS" && top!=="SCANS" && top!=="PREDICTION" && <div className="nav-wrapper">
      <div className="mobile-nav-toggle">
        <strong>Section: {top==="RESULTS"?"RESULTS":top==="CALENDAR"?"PDUFA Calendar":nav==="GEM_JR"?"GEM JR":nav==="MASTER"?"GOLD MASTER CHART":nav}</strong>
        <button type="button" aria-expanded={mobileNavOpen} aria-controls="pdufa-section-navigation"
          onClick={()=>setMobileNavOpen(current=>!current)}>
          {mobileNavOpen ? "Close menu ×" : "☰ Browse sections"}
        </button>
      </div>
      <nav id="pdufa-section-navigation" className="worknav" aria-label="PDUFA sections" data-open={mobileNavOpen?"true":"false"}>
        {([["PIPELINE","PIPELINE"],["GEM_JR","GEM JR"],["GEM","GEM"],["MASTER","GOLD MASTER CHART"],["WT","WT"],["TRADING","TRADING"]] as [Nav,string][]).map(([key,label])=>
          <button type="button" key={key} className={top==="PDUFA"&&nav===key?"nav-selected":""} aria-current={top==="PDUFA"&&nav===key?"page":undefined}
            onClick={()=>{setTop("PDUFA");setNav(key);setMobileNavOpen(false);}}>{label}</button>)}
      </nav>
    </div>}
    {top!=="GOAL" && <div className="workflow-counts" role="group" aria-label="Pipeline to WT current totals">
      {([
        {id:"PIPELINE" as Nav, label:"PIPELINE", count:snapshot ? pageTotals.PIPELINE : publishedCounts?.pipeline ?? null, detail:"Total candidates"},
        {id:"GEM_JR" as Nav, label:"GEM JR", count:snapshot ? verifiedStageCount("GEM_JR") : publishedCounts?.gemJr ?? null, detail:stageCountDetail("GEM_JR")},
        {id:"GEM" as Nav, label:"GEM", count:snapshot ? verifiedStageCount("GEM") : publishedCounts?.gem ?? null, detail:stageCountDetail("GEM")},
        {id:"WT" as Nav, label:"WT", count:tagsReady ? pageTotals.WT : null, detail:"Tracked watch / trade"},
      ]).map(item=><button type="button" key={item.id}
        className={"workflow-count workflow-count--"+item.id.toLowerCase()+(top==="PDUFA"&&nav===item.id?" workflow-count-selected":"")}
        aria-current={top==="PDUFA"&&nav===item.id?"page":undefined}
        aria-label={item.label+": "+(item.count===null?"loading":item.count.toLocaleString("en-US"))+" · Open "+item.label}
        onClick={()=>{setTop("PDUFA");setNav(item.id);setMobileNavOpen(false);}}>
        <span className="workflow-count-icon"><WorkflowStageIcon stage={item.id as "PIPELINE"|"GEM_JR"|"GEM"|"WT"}/></span>
        <span className="workflow-count-copy">
          <span className="workflow-count-label">{item.label}</span>
          <strong className="workflow-count-number" aria-live="polite">{item.count===null?"—":item.count.toLocaleString("en-US")}</strong>
          <span className="workflow-count-detail">{item.detail}</span>
        </span>
      </button>)}
    </div>}
    {top!=="GOAL" && <div className="workspace-update-row" role="status" aria-label="Data freshness and scan status">
        <section className="workspace-update-card">
          <span className="workspace-update-label">LAST UPDATED · SOURCE DATA</span>
          <strong className="workspace-update-value">{pacificSourceTime(snapshot?.asOf)}</strong>
          <span className="workspace-update-detail">{!snapshot ? "Loading published data" : cachedAsOf ? "Previously published · local cache" : fetchError && !refreshing ? "Previously published · refresh unverified" : snapshot.mode !== "LIVE_READ_ONLY_GITHUB_SOURCE" ? "Previously published · source fallback" : snapshot.sourceHealth?.publishedScan?.complete === true && snapshot.sourceHealth.publishedScan.finishedAt ? "Completed scan · published results" : "Previously published · scan not confirmed complete"}</span>
        </section>
        <section className="workspace-update-card">
          <span className="workspace-update-label">LAST SCAN FINISHED</span>
          <strong className="workspace-update-value">{pacificSourceTime(snapshot?.sourceHealth?.publishedScan?.finishedAt)}</strong>
          <span className="workspace-update-detail">{snapshot?.sourceHealth?.publishedScan?.complete === true ? "Confirmed complete in published report" : "Not confirmed complete"}</span>
        </section>
        <section className="workspace-update-card">
          <span className="workspace-update-label">DASHBOARD CHECKED</span>
          <strong className="workspace-update-value">{pacificSourceTime(lastCheckedAt)}</strong>
          <span className="workspace-update-detail">Data was checked, not a new scan. See SCANS for live progress.</span>
        </section>
      </div>}
    {summaryError && !publishedCounts && top!=="GOAL" && <p className="workspace-banner" role="alert">{summaryError} Candidate lists are preserved; retry loading candidates to try again.</p>}
    {snapshot?.sourceHealth && top!=="GOAL" && <div className="source-health workspace-source-health-full" role="status"><strong>Source health: {snapshot.sourceHealth.state}</strong><span>{snapshot.sourceHealth.regulatoryRows} regulatory programs · {snapshot.sourceHealth.clinicalRows} published clinical trials</span>{snapshot.sourceHealth.issues.length>0 && <ul>{snapshot.sourceHealth.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>}</div>}
    {top==="PDUFA" && nav==="PIPELINE" && <PeakResearchPanel />}
    {top==="PDUFA" && nav==="PIPELINE" && <MainPhase3ResearchPanel />}
    {(top==="RESTRICTIONS" || top==="PDUFA" && (nav==="PIPELINE" || nav==="GEM_JR" || nav==="GEM")) && <SharedEnrichment key={top+nav} stage={nav==="GEM_JR" || nav==="GEM" ? nav : "PIPELINE"}/>}
    {!snapshot && top!=="GOAL" && <div className="panel" role="status" aria-live="polite">
      <p>{fetchError || "Loading the complete workspace. You can browse the pipeline quick view below."}</p>
      <p className="subtle">Saved trial identities and WT selections are not erased by a source connection problem.</p>
      <div className="panel" aria-label="Pipeline quick view">
        <strong>Pipeline quick view{earlyPipelinePage ? " · " + earlyPipelinePage.total.toLocaleString() + " candidates" : ""}</strong>
        <p className="subtle">Browse published candidates while the complete workspace loads. Qualification filters become available when loading finishes.</p>
        <form onSubmit={event => {event.preventDefault();void loadEarlyPage(0, earlyPageQuery);}}>
          <label htmlFor="early-pipeline-search">Search all published pipeline candidates</label>
          <input id="early-pipeline-search" type="search" value={earlyPageQuery}
            maxLength={100} onChange={event => setEarlyPageQuery(event.target.value)}
            placeholder="Ticker or program" />
          <button type="submit" className="secondary" disabled={earlyPageLoading}>
            {earlyPageLoading ? "LOADING…" : "SEARCH PIPELINE"}
          </button>
        </form>
        {earlyPipelinePage && <>
          <p className="subtle">Showing {earlyPipelinePage.rows.length ? earlyPipelinePage.offset + 1 : 0}–{earlyPipelinePage.offset + earlyPipelinePage.rows.length} of {earlyPipelinePage.total.toLocaleString()} {earlyAppliedQuery ? "matching candidates · Search: " + earlyAppliedQuery : "total candidates"}.</p>
          <div className="priority-scroll"><table><thead><tr><th>Ticker</th><th>Program</th></tr></thead><tbody>
            {earlyPipelinePage.rows.map(candidate => <tr key={candidate.id}>
              <td>{candidate.ticker || "—"}</td><td>{candidate.drug || candidate.id}</td>
            </tr>)}
          </tbody></table></div>
          <div className="pipeline-row">
            <button type="button" className="secondary" disabled={earlyPageLoading || earlyPipelinePage.offset === 0}
              onClick={() => void loadEarlyPage(Math.max(0, earlyPipelinePage.offset - 50), earlyAppliedQuery, earlyPipelinePage.version)}>PREVIOUS 50</button>
            <button type="button" className="secondary" disabled={earlyPageLoading || earlyPipelinePage.nextOffset === null}
              onClick={() => { if (earlyPipelinePage.nextOffset !== null) void loadEarlyPage(earlyPipelinePage.nextOffset, earlyAppliedQuery, earlyPipelinePage.version); }}>NEXT 50 CANDIDATES</button>
          </div>
        </>}
        {earlyPageError && <p role="alert">{earlyPageError}</p>}
      </div>

      <button type="button" className="secondary" onClick={() => {
        if (!refreshing) { setFetchError("Loading candidates once…"); setFetchVersion(value => value + 1); }
      }} disabled={refreshing}>{refreshing ? "LOADING CANDIDATES…" : "LOAD CANDIDATES ONCE"}</button>
    </div>}
    {snapshot && top==="PDUFA" && nav==="MASTER" && <MasterChart records={pipeline} gemJr={snapshot.members.GEM_JR.rows} gem={snapshot.members.GEM.rows} history={[...(snapshot.members.GEM_JR.history||[]),...(snapshot.members.GEM.history||[])]} watch={tags.watch} trade={tags.trade} sourceHealth={snapshot.sourceHealth} asOf={snapshot.asOf} selectedId={masterProgram} onSelect={setMasterProgram} onInspect={record => {
      const stage: Stage = snapshot.members.GEM.rows.some(r=>r.id===record.id) ? "GEM" : snapshot.members.GEM_JR.rows.some(r=>r.id===record.id) ? "GEM_JR" : "PIPELINE";
      onInspect(record.ticker,stage,record.programId);
    }} />}
    {snapshot && top==="PDUFA" && nav==="PIPELINE" && <section className="pipeline-page">
      <div className="sectionhead"><div><h2>PIPELINE — Clinical and regulatory stages</h2>
        <p className="subtle">Stage, PDUFA-date, market-cap and trial restrictions are now all managed under RESTRICTIONS. Press DISPLAY TRIALS here to show your selected records below.</p>
        <a href="https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/" target="_blank" rel="noopener noreferrer" className="streamlit-fallback">OPEN FULL STREAMLIT PIPELINE ↗</a></div>
        <span className="counter">{pageTotals.PIPELINE.toLocaleString("en-US")} {onlyBand?"screened candidates":"source-recorded trials / programs"}</span></div>
      <p className="subtle pipeline-reconciliation">
        <strong>Streamlit-equivalent Pipeline source total:</strong> {(snapshot.sourceHealth?.pipelineSourceParity?.exactPrograms??pipeline.length).toLocaleString("en-US")}
        {" · Registered trials and results: "+(snapshot.sourceHealth?.pipelineSourceParity?.clinicalAndResults??snapshot.sourceHealth?.clinicalRows??0).toLocaleString("en-US")}
        {" · Regulatory records: "+(snapshot.sourceHealth?.pipelineSourceParity?.regulatoryPrograms??snapshot.sourceHealth?.regulatoryRows??0).toLocaleString("en-US")}
        {onlyBand?" · Optional $300M–$10B screen enabled":" · Full universe (no cap restriction)"}
        {query?" · Text search active":""}
        {" · As of "+snapshot.asOf}
      </p>
      <section className="panel pipeline-restrictions-shortcut" aria-labelledby="pipeline-moved-title">
        <h3 id="pipeline-moved-title">PIPELINE RESTRICTIONS MOVED</h3>
        <p>All stage, PDUFA date, trial, financing, evidence and market-cap filter controls now appear beneath the existing rules on the <strong>RESTRICTIONS</strong> page. Your current selections have not been reset or combined with the separate restriction catalog.</p>
        <p className="subtle" role="status">{stageFilters.length} stage selections · {dateFilters.length} date selections · {activeTrialFilters(trialFilters)} trial filters · {designationFilters.length} designation selections{onlyBand?" · $300M–$10B optional cap enabled":""}{query?" · Search active":""}.</p>
        <div className="pipeline-row">
          <button type="button" onClick={()=>{setTop("RESTRICTIONS");setMobileNavOpen(false);}}>OPEN RESTRICTIONS — EDIT FILTERS</button>
          <button type="button" className="secondary" disabled={designationFilters.length > 0 && !designationIndex} onClick={displayTrials}>DISPLAY TRIALS · {counted.length.toLocaleString("en-US")} matching</button>
        </div>
        {selectionsChanged && <p className="filter-pending" role="status">Your saved display has not been refreshed for the current selections. Press DISPLAY TRIALS to update it.</p>}
      </section>
      <div ref={pipelineDataRef} className="pipeline-results-anchor">
        {displayFilters ? <PipelineData key={appliedKey + "|" + displayVersion + "|" + snapshot.asOf} rows={displayed}
          filterSummary={"Stages: " + (displayFilters.stages.join(", ") || "All") + " · PDUFA dates: " + (displayFilters.dates.join(", ") || "All")
            + (displayFilters.query ? " · Search: " + displayFilters.query : "") + (displayFilters.onlyBand ? " · Market cap: $300M–$10B" : "")
            + (activeTrialFilters(displayFilters.trial) ? " · " + trialFilterSummary(displayFilters.trial) : "")
            + (appliedDesignationFilters.length ? " · FDA designation: " + appliedDesignationFilters.join(", ") : "")} /> :
          <section className="panel pipeline-data"><h3>PIPELINE DATA</h3><p className="subtle">Edit criteria under RESTRICTIONS, then press DISPLAY TRIALS to show the matching trials and programs here.</p></section>}
      </div>
    </section>}
    {top==="RESTRICTIONS" && restrictionTab==="RESTRICTIONS" && restrictionFocus==="DISEASE" && <DiseaseRestriction />}
    {top==="RESTRICTIONS" && restrictionTab==="RESTRICTIONS" && restrictionFocus==="COMPANY" && (snapshot ? <CompanyDiseaseLinks rows={[...snapshot.pipeline,...snapshot.members.GEM_JR.rows,...snapshot.members.GEM.rows]} pipelineRows={snapshot.pipeline} gemJrRows={snapshot.members.GEM_JR.rows} gemRows={snapshot.members.GEM.rows} /> : <section className="panel"><h3>COMPANY ↔ DISEASE</h3><p>Loading published scanner records…</p></section>)}
    {snapshot && top==="RESTRICTIONS" && <section aria-label="Original Pipeline filters" style={{width:"100%",minWidth:0,display:"flex",flexDirection:"column",gap:12,marginBottom:16}}>
      <div style={{fontWeight:800}}>ORIGINAL PIPELINE FILTERS</div>
      {pipelineMovedFilters}
    </section>}
    
    {snapshot && top==="RESTRICTIONS" && restrictionTab==="RESTRICTIONS" && <section aria-label="Restrictions page sections" style={{width:"100%",minWidth:0,display:"flex",flexDirection:"column",gap:16}}>
      <div className="panel" style={{padding:12,display:"grid",gap:8}}>
        <strong>SAVED RESTRICTION LISTS</strong>
        <label>View list <select value={restrictionListView} onChange={e=>setRestrictionListView(e.target.value as "PIPELINE"|"GEM_JR"|"GEM")}>
          <option value="PIPELINE">Pipeline</option><option value="GEM_JR">GEM JR</option><option value="GEM">GEM</option>
        </select></label>
        <div>{masterRestrictions.filter(e=>catalogStages(e).includes(restrictionListView)).length} saved restrictions</div>
        {masterRestrictions.filter(e=>catalogStages(e).includes(restrictionListView)).map(e=><div key={e.id} style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:8,flexWrap:"wrap"}}>
          <span>{catalogDefinition(e).title} · {e.enabled?"Enabled":"Disabled"}</span>
          <button type="button" onClick={()=>setMasterRestrictions(old=>removeRestrictionFromList(old,e.id,restrictionListView))}>REMOVE</button>
        </div>)}
      </div>
      <div style={{fontWeight:800}}>RESTRICTION CLASSES — ALL 11 LISTED BELOW</div>
      {RESTRICTION_PURPOSE_GROUPS.map(group=>{
        const entries=masterRestrictions.filter(entry=>restrictionPurposeGroup(entry)===group.id).sort((a,b)=>catalogDefinition(a).title.localeCompare(catalogDefinition(b).title));
        return <details className="panel" key={group.id} style={{margin:"12px 0",padding:12}}>
          <summary style={{fontWeight:700,cursor:"pointer"}}>{group.title} ({entries.length})</summary>
          <p className="subtle">{group.note}</p>
          <div style={{display:"grid",gap:8}}>{entries.map(entry=><div key={entry.id} style={{borderBottom:"1px solid var(--border, #ccc)",padding:"8px 0"}}>
            <strong>{catalogDefinition(entry).title}</strong>
            <div className="subtle">{catalogDefinition(entry).help}</div>
            <div className="subtle">Lists: {catalogStages(entry).join(", ")||"None"} · {entry.enabled?"Active":"Inactive"}</div>
            <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:8,marginTop:10}}>
              <label>Choose restriction list <select aria-label={"Destination list for "+catalogDefinition(entry).title} value={restrictionDestination[entry.id]||"PIPELINE"} onChange={e=>setRestrictionDestination(old=>({...old,[entry.id]:e.target.value as "PIPELINE"|"GEM_JR"|"GEM"}))}>
                <option value="PIPELINE">Pipeline</option><option value="GEM_JR">GEM JR</option><option value="GEM">GEM</option>
              </select></label>
              {(()=>{
                const stage=restrictionDestination[entry.id]||"PIPELINE";
                const assigned=catalogStages(entry).includes(stage);
                return <button type="button" onClick={()=>setMasterRestrictions(old=>assigned?removeRestrictionFromList(old,entry.id,stage):insertRestrictionIntoList(old,entry.id,stage,selectedRestrictionList(old,stage).length))}>{assigned?"REMOVE FROM LIST":"SAVE TO LIST"}</button>;
              })()}
              <small>Saved in: {catalogStages(entry).map(stage=>stage.replace("_"," ")).join(", ")||"None"}</small>
            </div>
            <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:12,marginTop:8}}>
              <label style={{display:"flex",alignItems:"center",gap:6}}><input type="checkbox" checked={entry.enabled} onChange={event=>setMasterRestrictions(previous=>previous.map(item=>item.id===entry.id?{...item,enabled:event.target.checked}:item))}/> Enabled</label>
              {(catalogDefinition(entry).numeric || entry.value!=="" || entry.maximum!=="") && <>
                <label style={{display:"flex",flexDirection:"column",gap:4}}>Minimum / value
                  <input aria-label={catalogDefinition(entry).title+" minimum value"} type="number" step="any" style={{width:130,maxWidth:"100%"}} value={entry.value} onChange={event=>setMasterRestrictions(previous=>previous.map(item=>item.id===entry.id?{...item,value:event.target.value}:item))}/>
                </label>
                {(entry.maximum!=="" || catalogDefinition(entry).maximum!==undefined) && <label style={{display:"flex",flexDirection:"column",gap:4}}>Maximum
                  <input aria-label={catalogDefinition(entry).title+" maximum value"} type="number" step="any" style={{width:130,maxWidth:"100%"}} value={entry.maximum} onChange={event=>setMasterRestrictions(previous=>previous.map(item=>item.id===entry.id?{...item,maximum:event.target.value}:item))}/>
                </label>}
              </>}
              {catalogDefinition(entry).unit && <span className="subtle">{catalogDefinition(entry).unit}</span>}
            </div>
          </div>)}</div>
        </details>;
      })}
    </section>}
    {top==="RESTRICTIONS" && restrictionTab==="PRESET" && <section aria-label="Saved restriction presets" style={{display:"grid",gap:12,width:"100%",minWidth:0}}>
      <h2>PRESET — Saved restriction configurations</h2>
      <p className="subtle">Choose Pipeline, GEM JR or GEM presets below. Load, rename by saving under a new name, overwrite or delete. Edit restriction values on the RESTRICTIONS tab, then save your changes as a preset at the bottom of that list.</p>
      {(["PIPELINE","GEM_JR","GEM"] as RestrictionPresetStage[]).map(stage=><div key={stage} className="panel" style={{padding:16}}>
        <h3>{stage.replace("_"," ")} PRESETS · {restrictionPresets[stage].length} saved</h3>
        {restrictionPresetControls(stage)}
      </div>)}
    </section>}
    {snapshot && top==="RESTRICTIONS" && restrictionTab==="RESTRICTIONS" && <section aria-label="Three independent restriction lists" style={{display:"flex",flexDirection:"column",gap:12,width:"100%",minWidth:0}}>
      <details className="panel" style={{margin:"4px 0",padding:16,width:"100%",boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>PIPELINE RESTRICTIONS</summary><RestrictionImpact rows={restrictionRows} asOf={snapshot.asOf} managedEntries={masterRestrictions} onManagedEntriesChange={setMasterRestrictions} cached={!!cachedAsOf || snapshot.sourceHealth?.state === "STALE"} onRefresh={() => { if (!refreshing) setFetchVersion(value => value + 1); }} />
        {bottomPresetSave("PIPELINE")}
      </details>
      <details className="panel" style={{margin:"4px 0",padding:16,width:"100%",boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>GEM JR RESTRICTIONS</summary>{gemBlock("GEM_JR")}{bottomPresetSave("GEM_JR")}</details>
      <details className="panel" style={{margin:"4px 0",padding:16,width:"100%",boxSizing:"border-box"}}><summary style={{fontWeight:700,cursor:"pointer"}}>GEM RESTRICTIONS</summary>{gemBlock("GEM")}{bottomPresetSave("GEM")}</details>
    </section>}
    {snapshot && top==="PDUFA" && (nav==="GEM_JR" || nav==="GEM") && <div className="gems-page">
      <div className="sectionhead"><div><h2>{nav==="GEM_JR"?"GEM JR":"GEM"} — Candidate research</h2><p className="subtle">The same permanent Program ID follows an exact candidate from Pipeline through GEM JR, GEM and WT. An observed junior does not automatically qualify as GEM.</p></div>
      <label>Find candidate<input value={gemQuery} onChange={e=>setGemQuery(e.target.value)} placeholder="Ticker or drug" /></label></div>
      <div className="gems-two-blocks">{gemBlock(nav==="GEM_JR"?"GEM_JR":"GEM")}</div>
    </div>}
    {snapshot && top==="PDUFA" && nav==="WT" && <div className="wt-page">
      <div className="sectionhead wt-page-header"><h2>WT — Permanent Program ID Watchlist &amp; Trading Research</h2><span className="counter">{tagsReady ? pageTotals.WT.toLocaleString("en-US") : "—"} total W/T programs</span></div>
      <p className="subtle">WT displays the identical GEM JR/GEM entry-strength and exit-risk scores for each permanent Program ID, including evidence coverage and safety overrides. Different drugs and trials remain independent. Research only — no broker orders.</p>
      <p aria-live="polite" className="saveState">{wtStatus}</p>
      <p className="subtle wt-trial-indicator-explanation">Choose ENTRY, STAY, or EXIT beside each trial ticker. The corresponding indicator checklist opens immediately below that trial. Tick the options you want to display; every new stage starts with no indicators selected. Settings are independent for each permanent Program ID and saved in this browser.</p>
      <div className="wt-screenwide-stages">
      {(["watch","trade"] as const).map(kind=><section className="panel wt-screenwide-stage" key={kind}>
        <div className="sectionhead"><h3>{kind==="watch"?"WATCHLIST — EXACT PROGRAMS":"TRADING RESEARCH — EXACT PROGRAMS / NO ORDERS"}</h3><span className="counter">{tags[kind].length} tracked programs</span></div>
        {tags[kind].length===0 && <p className="subtle">No exact programs selected yet. Use W/T buttons beside Program IDs in PIPELINE or GEM.</p>}
        <div className="wt-screenwide-list">
        {tags[kind].map(programId=>{
          const selectedRecord=byProgram.get(programId);
          const saved=storedIdentities.find(x=>x.programId===programId);
          const ticker=selectedRecord?.ticker||saved?.ticker||"";
          const preference=wtTrialPreferences[programId]||emptyWtPreference();
          const selectedStage=preference.stage;
          const chartIndicatorKeys=selectedStage?preference.keys[selectedStage]:[];
          return <article className="wt-screenwide-stock" key={programId}>
            <div className="wt-identity wt-screenwide-identity">
              <strong className="permanent-id">{programId}</strong>
              <div className="wt-ticker-stage">
                <h3>{ticker||"SOURCE NOT CURRENT"}</h3>
                {ticker&&<label className="wt-stage-selector">
                  <span>CHART INDICATORS</span>
                  <select aria-label={"Chart indicator stage for "+ticker+" "+programId}
                    disabled={!wtTrialPreferencesReady} value={selectedStage}
                    onChange={event=>{
                      const value=event.target.value;
                      changeWtTrialStage(programId,isWtStage(value)?value:"");
                    }}>
                    <option value="">NONE — price only</option>
                    <option value="entry">ENTRY — Buy setup</option>
                    <option value="stay">STAY — Hold monitoring</option>
                    <option value="exit">EXIT — Risk protection</option>
                  </select>
                </label>}
                {selectedStage&&<small className="wt-stage-selection-count">
                  {chartIndicatorKeys.length} selected · {selectedStage.toUpperCase()}
                </small>}
              </div>
              <p className="subtle">{stated(selectedRecord?.drug||saved?.drug)} · {stated(selectedRecord?.id||saved?.id,"historical exact program")}</p>
              {!selectedRecord && <p className="subtle">Program remains stored in Neon even when no longer in the latest published source. Historical identity has not been removed.</p>}
              <button type="button" onClick={()=>mark(programId,kind==="watch"?"trade":"watch")}>{kind==="watch"?"MOVE PROGRAM TO TRADING RESEARCH":"RETURN PROGRAM TO WATCHLIST"}</button>
              <button type="button" className="secondary" onClick={()=>mark(programId,"clear")}>REMOVE PROGRAM TAG</button>
              {selectedRecord && <button type="button" className="secondary" onClick={()=>{setMasterProgram(selectedRecord.id);setNav("MASTER");}}>Open program Master Chart</button>}
              {ticker && <button type="button" className="secondary" onClick={()=>onInspect(ticker,"PIPELINE",programId)}>Open exact program checklist</button>}
            </div>
            {ticker&&selectedStage&&<div className="wt-trial-indicator-panel">
              <WtTradingSections key={programId+"|"+selectedStage}
                programId={programId} ticker={ticker}
                record={selectedRecord} tech={selectedRecord?.technical}
                activeGroup={selectedStage} compact
                checkedKeys={chartIndicatorKeys}
                presetFlags={preference.presets[selectedStage]}
                onPresetToggle={mode=>toggleWtTrialPreset(programId,selectedStage,mode)}
                onCheckedKeysChange={keys=>changeWtTrialIndicators(programId,selectedStage,keys)}/>
            </div>}
            {ticker ? <>
              <div className="wt-screenwide-entry" id={"wt-entry-info-"+programId}>
                <EntrySignal ticker={ticker} programId={programId}/>
              </div>
              <div className="wt-screenwide-chart" id={"wt-chart-"+programId}>
                <AlpacaStockChart ticker={ticker} programId={programId} wtIndicatorKeys={chartIndicatorKeys} />
              </div>
              <div className="wt-screenwide-data" id={"wt-score-info-"+programId}>
                <WTIndicatorDetails programId={programId} record={selectedRecord} ticker={ticker} />
              </div>
            </> : <p className="subtle">Ticker unavailable in stored identity; price chart withheld.</p>}
          </article>;
        })}
        </div>
      </section>)}
      </div>
      {(legacyTags.watch.length>0||legacyTags.trade.length>0) && <section className="panel legacy-tags">
        <h3>Legacy ticker-only selections — preserved for review</h3>
        <p className="subtle">Older WT tags did not identify a particular drug or trial. They remain unchanged; choose an exact permanent Program ID below to add it to the new WT lists. Nothing is assigned automatically.</p>
        {(["watch","trade"] as const).map(kind=>legacyTags[kind].length>0 &&
          <div key={kind}><h4>{kind==="watch"?"Previous WATCH tickers":"Previous TRADING tickers"}</h4>
            {legacyTags[kind].map(ticker=><div key={kind+"|"+ticker} className="legacy-ticker-row">
              <strong>{ticker}</strong>
              {(byTicker.get(ticker)||[]).map(r=><button type="button" key={r.id} disabled={!r.programId||!tagsReady}
                onClick={()=>mark(r.programId||"",kind)}>{stated(r.programId)} · {stated(r.drug,r.id)}</button>)}
              {!byTicker.get(ticker)?.length && <span>Original ticker retained; no current exact-program match in published sources</span>}
            </div>)}
          </div>)}
      </section>}
    </div>}
    {top==="GOAL" && <GoalDashboard
      records={snapshot?.pipeline ?? null}
      pipelineCount={snapshot ? snapshot.pipeline.length : publishedCounts?.pipeline ?? null}
      gemJrCount={snapshot ? snapshot.members.GEM_JR.rows.length : publishedCounts?.gemJr ?? null}
      gemCount={snapshot ? snapshot.members.GEM.rows.length : publishedCounts?.gem ?? null}
      restrictions={masterRestrictionsReady ? goalRestrictionSummaries(masterRestrictions) : null}
      impactRows={snapshot ? restrictionRows : null}
      impactEntries={masterRestrictionsReady ? masterRestrictions : null}
      sourceAsOf={snapshot?.asOf}
      sourceState={snapshot?.sourceHealth?.state}
      scanFinishedAt={snapshot?.sourceHealth?.publishedScan?.finishedAt}
      scanComplete={snapshot?.sourceHealth?.publishedScan?.complete === true}
      cached={Boolean(cachedAsOf || fetchError || snapshot?.mode !== "LIVE_READ_ONLY_GITHUB_SOURCE")}
      onOpen={(section:GoalSection)=>{
        if(section==="PIPELINE" || section==="GEM_JR" || section==="GEM"){
          setTop("PDUFA");setNav(section);
        } else {
          setTop(section);
        }
        setMobileNavOpen(false);
      }}
    />}
    {top==="RESULTS" && <DailyResultsPanel />}
    {top==="BACKUP" && <BackupStatusPanel />}
    {top==="PDUFA" && nav==="TRADING" && <TradingDashboard tickers={tradingTickers} tagsReady={tagsReady} />}
    {top==="SCANS" && <HistoricalFdaReadiness />}
    {top==="SCANS" && <PublishedScansPanel />}
    {snapshot && top==="CALENDAR" && <section className="panel"><h2>PDUFA Calendar — Saved event snapshot</h2>
      <p className="subtle">Reported dates only, not FDA-confirmed future events unless the source explicitly verifies them.</p>
      <div className="table-scroll"><table><thead><tr><th>PDUFA</th><th>Program ID</th><th>Ticker</th><th>Drug</th><th>Program</th><th>Days away</th><th>FDA/source</th></tr></thead>
        <tbody>{pipeline.filter(r=>daysAway(r.pdufaDate)!==null && (daysAway(r.pdufaDate)||0)>=0).sort((a,b)=>(daysAway(a.pdufaDate)||0)-(daysAway(b.pdufaDate)||0)).map(r=><tr key={r.id}><td>{r.pdufaDate}</td><td className="permanent-id">{stated(r.programId)}</td><td>{r.ticker}</td><td>{r.drug}</td><td>{r.id}</td><td>{daysAway(r.pdufaDate)}</td><td>{stated(r.checkStatus)}</td></tr>)}</tbody>
      </table></div></section>}
  </div>;
}

export default function Workspace(props: { onInspect: (ticker: string, stage: Stage, programId?: string) => void }) {
  return <AssessmentProvider><WorkspaceContent {...props} /></AssessmentProvider>;
}
