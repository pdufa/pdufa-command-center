"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import {
  parsePhase3CensusCsv, PHASE3_CENSUS_CSV_PATH,
} from "../../lib/phase3-census-rows";
import {
  parsePhase3CensusSourceDirectory, PHASE3_CENSUS_SOURCES_PATH,
} from "../../lib/phase3-census-sources";
import {
  selectPostPhase3PopulationTrials, PATIENT_POPULATION_DETAIL_SECTIONS,
  PATIENT_POPULATION_MARKET_CAP_MIN, PATIENT_POPULATION_MARKET_CAP_MAX,
  type PostPhase3PopulationTrial,
} from "../../lib/post-phase3-population";
import type { RegistryResearchRecord } from "../../lib/phase3-live-registry";
import styles from "./PatientPopulationTab.module.css";
import {
  EMPTY_PATIENT_POPULATION_FILTERS,
  filterPatientPopulationRows,
  type Availability, type PatientPopulationFilters,
  type NumberColumnFilter, type SourceTextFilter, type PopulationSourceFields,
} from "../../lib/patient-population-filters";

const PAGE_SIZE = 25;
type RegistryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; record: RegistryResearchRecord };

function safeResearchRecord(value: unknown, expectedNct: string): RegistryResearchRecord {
  if (!value || typeof value !== "object") throw new Error("Registry response invalid");
  const record = value as Partial<RegistryResearchRecord>;
  if (record.nctId !== expectedNct
      || record.recordUrl !== "https://clinicaltrials.gov/study/" + expectedNct
      || !Array.isArray(record.conditions) || !Array.isArray(record.interventions)
      || typeof record.sourceUpdated !== "string" && record.sourceUpdated !== null
      || typeof record.registryOverallStatus !== "string"
      || record.verifiedUsFdaPdufa !== false
      || record.verifiedCommercialDevelopment !== false) {
    throw new Error("Exact study source was not verified");
  }
  return record as RegistryResearchRecord;
}

const researchValue = (value: string | number | null) =>
  typeof value === "number" ? value.toLocaleString("en-US") : value || "Not researched";
type NumberKey = "diseasePopulation" | "eligibleUsPatients" | "eligibleGlobalPatients" | "evidence";
type SourceKey = "drug" | "indication";
const AVAILABILITY: { value:Availability; label:string }[] = [
  { value:"all", label:"All records" },
  { value:"available", label:"With research" },
  { value:"missing", label:"Not researched" },
];
function registryDrugs(record?: RegistryResearchRecord) {
  if (!record) return null;
  const values = record.interventions.filter(x =>
    ["DRUG","BIOLOGICAL","GENETIC","COMBINATION_PRODUCT"].includes(x.type)
    && !/^(?:placebo|vehicle|sham|control)(?:\b|\s)/i.test(x.name));
  return values.length ? [...new Set(values.map(x=>x.name))].slice(0,3).join("; ") : null;
}
function registryConditions(record?: RegistryResearchRecord) {
  return record?.conditions.length ? record.conditions.slice(0,3).join("; ") : null;
}

export default function PatientPopulationTab() {
  const [data, setData] = useState<PostPhase3PopulationTrial[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<PatientPopulationFilters>(EMPTY_PATIENT_POPULATION_FILTERS);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [registry, setRegistry] = useState<Record<string, RegistryState>>({});

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [censusResponse, sourceResponse] = await Promise.all([
          fetch(PHASE3_CENSUS_CSV_PATH, { cache:"no-store" }),
          fetch(PHASE3_CENSUS_SOURCES_PATH, { cache:"no-store" }),
        ]);
        if (!censusResponse.ok || !sourceResponse.ok) throw new Error("Saved dated trial census unavailable");
        const [csv, sources] = await Promise.all([censusResponse.text(), sourceResponse.json()]);
        const census = parsePhase3CensusCsv(csv);
        const directory = parsePhase3CensusSourceDirectory(sources, census);
        const qualifying = selectPostPhase3PopulationTrials(census, directory);
        if (active) setData(qualifying);
      } catch {
        if (active) setError("Unable to verify the exact sponsor, completed Phase 3 and $300M–$10B census. No unverified trials have been displayed.");
      }
    })();
    return () => { active = false; };
  }, []);

  const resolvedSources = useMemo<Record<string,PopulationSourceFields>>(() => {
    const result: Record<string,PopulationSourceFields> = {};
    for (const [nct,source] of Object.entries(registry)) {
      if(source.status === "ready") result[nct] = {
        drug:registryDrugs(source.record),indication:registryConditions(source.record),
      };
    }
    return result;
  }, [registry]);
  const matches = useMemo(() =>
    filterPatientPopulationRows(data || [],{...filters,all:query},resolvedSources),
    [data,filters,query,resolvedSources]);

  function modifyFilter(field: SourceKey,patch:Partial<SourceTextFilter>) {
    setFilters(prev => ({...prev,[field]:{...prev[field],...patch}}));
    setPage(0);setSelected(null);
  }
  function modifyNumber(field:NumberKey,patch:Partial<NumberColumnFilter>) {
    setFilters(prev => ({...prev,[field]:{...prev[field],...patch}}));
    setPage(0);setSelected(null);
  }
  function modifyDate(patch:Partial<PatientPopulationFilters["lastUpdated"]>) {
    setFilters(prev => ({...prev,lastUpdated:{...prev.lastUpdated,...patch}}));
    setPage(0);setSelected(null);
  }
  function resetFilters() {
    setFilters(EMPTY_PATIENT_POPULATION_FILTERS);
    setQuery("");setPage(0);setSelected(null);
  }
  function availabilitySelect(
    value:Availability,onChange:(value:Availability)=>void,label:string
  ) {
    return <select aria-label={label} value={value}
      onChange={e=>onChange(e.target.value as Availability)} className={styles.columnSelect}>
      {AVAILABILITY.map(o=><option value={o.value} key={o.value}>{o.label}</option>)}
    </select>;
  }
  function textColumn(field:SourceKey,title:string) {
    return <div className={styles.columnFilter}>
      <input type="search" aria-label={"Filter "+title} placeholder={"Find "+title.toLowerCase()}
        value={filters[field].search}
        onChange={e=>modifyFilter(field,{search:e.target.value})} />
      {availabilitySelect(filters[field].status,value=>modifyFilter(field,{status:value}),title+" research status")}
    </div>;
  }
  function numberColumn(field:NumberKey,title:string) {
    const filter=filters[field];
    const percentage=field==="evidence";
    return <div className={styles.columnFilter}>
      {availabilitySelect(filter.status,value=>modifyNumber(field,{status:value}),title+" research status")}
      <div className={styles.rangeInputs}>
        <input type="number" min={0} max={percentage?100:undefined}
          aria-label={"Minimum "+title} placeholder={percentage?"Min %":"Min"}
          value={filter.minimum} onChange={e=>modifyNumber(field,{minimum:e.target.value})} />
        <input type="number" min={0} max={percentage?100:undefined}
          aria-label={"Maximum "+title} placeholder={percentage?"Max %":"Max"}
          value={filter.maximum} onChange={e=>modifyNumber(field,{maximum:e.target.value})} />
      </div>
    </div>;
  }

  const pageCount = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = matches.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

  async function loadRegistry(nctId: string) {
    if (registry[nctId]?.status === "loading") return;
    setRegistry(prev => ({ ...prev, [nctId]: { status:"loading" } }));
    try {
      const response = await fetch("/api/phase3-registry?exact_nct=" + encodeURIComponent(nctId), { cache:"no-store" });
      if (!response.ok) throw new Error(response.status === 401
        ? "Sign in to the website to inspect the exact registry record."
        : "ClinicalTrials.gov lookup unavailable; no drug or indication has been verified.");
      const record = safeResearchRecord(await response.json(), nctId);
      setRegistry(prev => ({ ...prev, [nctId]: { status:"ready", record } }));
    } catch (error) {
      setRegistry(prev => ({ ...prev, [nctId]: {
        status:"error",
        message:error instanceof Error ? error.message : "Exact NCT source unavailable.",
      } }));
    }
  }

  return <section className={styles.root} aria-label="#1 Patient Population">
    <header className={styles.header}>
      <div>
        <p className={styles.eyebrow}>POST–PHASE 3 PIPELINE · ASSESSMENT #1</p>
        <h1>#1 — Patient Population</h1>
        <p>Publicly traded companies only · historical market capitalization <strong>$300M–$10B</strong> · registry-completed Phase 3 trials.</p>
      </div>
      <a className={styles.sourceLink}
        href="https://github.com/pdufa/pdufa-command-center/blob/main/data/phase3_all_years_300m_10b_status.json"
        target="_blank" rel="noopener noreferrer">Census methodology ↗</a>
    </header>

    <div className={styles.notice}>
      <strong>Scope and verification:</strong> the table is based on the October 26, 2026 historical issuer and market-cap snapshot.
      It does not include every published Phase 3 readout when the registry is not yet marked completed, or independently prove
      continuing listing, development rights, a positive Phase 3 outcome, FDA submission, or current market-cap eligibility.
      Such candidates require a separate verified reconciliation before entering this tab.
    </div>

    <div className={styles.metrics}>
      <div><span>Registry-completed Phase 3 trial IDs</span><strong>{data ? data.length.toLocaleString("en-US") : "—"}</strong></div>
      <div><span>Historical listed issuers in range</span><strong>{data ? new Set(data.map(x => x.trial.ticker)).size : "—"}</strong></div>
      <div><span>Verified patient population estimates</span><strong>Not yet assessed</strong></div>
      <div><span>Reference snapshot</span><strong>Oct 26, 2026</strong></div>
    </div>

    <div className={styles.panel}>
      <h2>Population research directory</h2>
      <p className={styles.muted}>Every row is an exact NCT trial record, not a distinct marketed drug. Multiple trials may support one drug and indication. Patient counts will only appear after documented epidemiology and label review.</p>
      <label className={styles.search}>Search ticker, company, NCT or loaded registry details
        <input type="search" value={query} onChange={e => { setQuery(e.target.value); setPage(0); setSelected(null); }}
          placeholder="Example: ABVX or NCT05507203" />
      </label>
      <div className={styles.filterToolbar}>
        <span>Use independent column filters beneath the headings. Drug and indication can be filtered once their exact NCT sources have been loaded.</span>
        <button type="button" className={styles.resetButton} onClick={resetFilters}>Clear all filters</button>
      </div>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      {!data && !error && <p role="status">Validating complete dated census and market-cap source links…</p>}
      {data && <p className={styles.muted} role="status">{matches.length} matching completed trial records ·
        showing {matches.length ? currentPage * PAGE_SIZE + 1 : 0}–{Math.min((currentPage + 1) * PAGE_SIZE, matches.length)}.
      </p>}
      {data && !matches.length && <p role="status" className={styles.emptyResults}>
        No trial records match these filters. Clear filters or choose Not researched to inspect missing data.
      </p>}
      {data && <div className={styles.scroll}>
        <table className={styles.table}>
          <thead><tr>
            <th scope="col">Ticker / study
              <div className={styles.columnFilter}>
                <input type="search" aria-label="Filter ticker, study or company"
                  placeholder="Ticker / NCT / company" value={filters.ticker}
                  onChange={e=>{setFilters(v=>({...v,ticker:e.target.value}));setPage(0);setSelected(null)}} />
              </div>
            </th>
            <th scope="col">Drug{textColumn("drug","Drug")}</th>
            <th scope="col">Indication{textColumn("indication","Indication")}</th>
            <th scope="col">Total disease population{numberColumn("diseasePopulation","Total disease population")}</th>
            <th scope="col">Eligible U.S. patients{numberColumn("eligibleUsPatients","Eligible U.S. patients")}</th>
            <th scope="col">Eligible global patients{numberColumn("eligibleGlobalPatients","Eligible global patients")}</th>
            <th scope="col">Evidence completeness{numberColumn("evidence","Evidence completeness")}</th>
            <th scope="col">Last updated
              <div className={styles.columnFilter}>
                {availabilitySelect(filters.lastUpdated.status,
                  status=>modifyDate({status}),"Last updated verification status")}
                <div className={styles.rangeInputs}>
                  <input type="date" aria-label="Last updated from" value={filters.lastUpdated.from}
                    onChange={e=>modifyDate({from:e.target.value})} />
                  <input type="date" aria-label="Last updated through" value={filters.lastUpdated.to}
                    onChange={e=>modifyDate({to:e.target.value})} />
                </div>
              </div>
            </th>
            <th scope="col">Details</th>
          </tr></thead>
          <tbody>{visible.map(row => {
            const nct = row.trial.nctId;
            const state = registry[nct];
            const record = state?.status === "ready" ? state.record : undefined;
            return <Fragment key={nct}>
              <tr>
                <th scope="row"><strong>{row.trial.ticker}</strong><small>{nct}</small><small>{row.trial.company}</small></th>
                <td>{record ? (registryDrugs(record) || "No verified intervention") : "Needs source review"}{record && <small>Registry-reported; not matched to product</small>}</td>
                <td>{record ? (registryConditions(record) || "No reported condition") : "Needs source review"}{record && <small>Registry-reported; not proposed FDA label</small>}</td>
                <td>{researchValue(row.diseasePopulation)}</td>
                <td>{researchValue(row.eligibleUsPatients)}</td>
                <td>{researchValue(row.eligibleGlobalPatients)}</td>
                <td>{row.populationEvidenceCompleteness === null ? "Not assessed" : row.populationEvidenceCompleteness + "%"}</td>
                <td>{researchValue(row.populationLastVerified)}</td>
                <td><button type="button" className={styles.smallButton}
                  aria-expanded={selected === nct} aria-controls={"population-detail-" + nct}
                  onClick={() => setSelected(selected === nct ? null : nct)}>
                  {selected === nct ? "Close ▴" : "View ▾"}
                </button></td>
              </tr>
              {selected === nct && <tr id={"population-detail-" + nct} className={styles.expanded}>
                <td colSpan={9}>
                  <div className={styles.detailsHead}>
                    <div><h3>{row.trial.ticker} · {nct}</h3><p>{row.trial.company} · registry status COMPLETED at census date</p></div>
                    <button type="button" onClick={() => void loadRegistry(nct)} disabled={state?.status === "loading"}>
                      {state?.status === "loading" ? "Checking source…" : "Review exact NCT source"}
                    </button>
                  </div>
                  <p className={styles.muted}><strong>Market-cap gate:</strong> {row.companySources.marketCapUsd.toLocaleString("en-US", {style:"currency",currency:"USD",maximumFractionDigits:0})}
                    {" "}({row.companySources.marketCapCheckedAt.slice(0,10)} snapshot, not a live quote).
                    {" "}<a href={row.companySources.marketCapSourceUrl} target="_blank" rel="noopener noreferrer">Market-cap source ↗</a>
                    {" · "}<a href={row.trial.sourceUrl} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov ↗</a>
                  </p>
                  {state?.status === "error" && <p role="alert" className={styles.error}>{state.message}</p>}
                  {record && <p className={styles.muted}><strong>Registry update:</strong> {record.sourceUpdated || "Not supplied"}
                    {" · "}Recorded status: {record.registryOverallStatus}
                    {!record.phase3CurrentlyReported && " · Current registry Phase 3 phase is not verified; manual reconciliation required."}
                    {" · "}Drug/indication mapping remains pending independent issuer and FDA source verification.
                  </p>}
                  <h4>12 detailed population assessments — collapsed by default</h4>
                  <div className={styles.accordion}>
                    {PATIENT_POPULATION_DETAIL_SECTIONS.map((section,index) => <details key={section.title}>
                      <summary><span>{String(index + 1).padStart(2,"0")}. {section.title}</span><span>Not assessed ▾</span></summary>
                      <div className={styles.detailContent}>
                        <p>{section.detail}</p>
                        {index === 3 && record && <p><strong>Registry-reported conditions:</strong> {record.conditions.join("; ") || "Not supplied"}.
                          {" "}<strong>Interventions:</strong> {record.interventions.map(i => i.type + ": " + i.name).join("; ") || "Not supplied"}.</p>}
                        <p><strong>Required:</strong> source URL, publication date, patient denominator, inclusion/exclusion method, low/base/high values as applicable, and independent verification.</p>
                        <p><strong>Result:</strong> NEEDS REVIEW — no eligible population estimate is authorized by the saved census alone.</p>
                      </div>
                    </details>)}
                  </div>
                </td>
              </tr>}
            </Fragment>;
          })}</tbody>
        </table>
      </div>}
      {data && <div className={styles.paging}>
        <button type="button" disabled={currentPage === 0} onClick={() => {setPage(currentPage - 1);setSelected(null)}}>Previous</button>
        <span>Page {currentPage + 1} of {pageCount}</span>
        <button type="button" disabled={currentPage + 1 >= pageCount} onClick={() => {setPage(currentPage + 1);setSelected(null)}}>Next</button>
      </div>}
    </div>
    <p className={styles.footer}>Read-only research tab. No estimates, approvals, trade signals or eligibility upgrades are inferred. The company market-cap filter remains $300M–$10B. No other pipeline stages or screens are altered.</p>
  </section>;
}
