"use client";

import { useId, useMemo, useState } from "react";
import { PIPELINE_STAGES } from "../lib/pipeline-data";
import { activeTrialFilters, criterionChecked, EMPTY_TRIAL_FILTERS, matchesTrialFilters,
  QUALIFICATION_CRITERIA, withCriterion, type TrialFilterRecord, type TrialFilterValues } from "../lib/trial-filters";

const DATE_WINDOWS = [["30", "Last 30 days"], ["90", "Last 90 days"], ["365", "Last 12 months"], ["OLDER", "Over 12 months ago"], ["UNKNOWN", "Unknown / unverified"]];
const FLAGS = [["FLAGGED", "Flag reported"], ["CLEAR", "Explicitly cleared"], ["UNKNOWN", "Unknown / unverified"]];

function Choice({ label, value, options, onChange }: { label: string; value: string; options: string[][]; onChange: (value: string) => void }) {
  return <label className="trial-filter-field">{label}<select value={value} onChange={event => onChange(event.target.value)}>
    <option value="">All / no restriction</option>{options.map(([key, title]) => <option key={key} value={key}>{title || key}</option>)}
  </select></label>;
}

function SuggestedChoice({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  const id = useId();
  const choices = options.filter(option => !value || option.toLowerCase().includes(value.toLowerCase())).slice(0, 100);
  return <label className="trial-filter-field">{label}<input list={id} value={value} placeholder="All · type to find" onChange={event => onChange(event.target.value)} />
    <datalist id={id}>{choices.map(option => <option key={option} value={option} />)}</datalist></label>;
}

export default function TrialQualificationFilters({ rows, countRows, value, onChange, asOf, ready = true }: {
  rows: TrialFilterRecord[]; countRows: TrialFilterRecord[]; value: TrialFilterValues;
  onChange: (value: TrialFilterValues) => void; asOf?: string; ready?: boolean;
}) {
  const [moreOpen, setMoreOpen] = useState(false);
  const choices = useMemo(() => {
    const companies = new Map<string, string>(), drugs = new Set<string>(), indications = new Set<string>();
    for (const row of rows) {
      if (row.ticker) companies.set(row.ticker, row.ticker + (row.company ? " — " + row.company : ""));
      if (row.drug) drugs.add(row.drug);
      if (row.indication) indications.add(row.indication);
    }
    return { companies: [...companies.entries()].sort(([a], [b]) => a.localeCompare(b)), drugs: [...drugs].sort(), indications: [...indications].sort() };
  }, [rows]);
  const counts = useMemo(() => QUALIFICATION_CRITERIA.map(criterion => countRows.filter(row =>
    matchesTrialFilters(row, withCriterion(value, criterion.key, true), asOf)).length), [countRows, value, asOf]);
  function set<K extends keyof TrialFilterValues>(key: K, next: TrialFilterValues[K]) { onChange({ ...value, [key]: next }); }
  return <fieldset className="filter-count-group trial-qualification-filters" disabled={!ready}>
    <legend>TRIAL FILTERS</legend>
    <div className="filter-group-total"><span>All selected conditions must match</span><strong>{activeTrialFilters(value)} selected</strong></div>
    {!ready && <p role="status" className="subtle">Trial evidence is refreshing. These filters will become available when the updated source data loads.</p>}
    <div className="filter-checks trial-qualification-checks">{QUALIFICATION_CRITERIA.map((criterion, index) => <label
      key={criterion.key} title={criterion.help} className={criterionChecked(value, criterion.key) ? "filter-option filter-option-selected" : "filter-option"}>
      <input type="checkbox" checked={criterionChecked(value, criterion.key)} onChange={event => onChange(withCriterion(value, criterion.key, event.target.checked))} />
      <span className="filter-label-text">{criterion.label}</span><b className="filter-count" title="Matches with your other selections">{counts[index].toLocaleString("en-US")}</b>
    </label>)}</div>
    <p className="trial-filter-note">Unknown evidence does not pass a checked criterion. Financing uses saved closing evidence; source freshness is a separate filter.</p>
    <details className="trial-more-filters" onToggle={event => setMoreOpen(event.currentTarget.open)}>
      <summary>More trial filters</summary>
      {moreOpen && <div className="trial-filter-dropdowns">
        <h4>Trial identity, phase &amp; status</h4>
        <Choice label="Company / ticker" value={value.company} options={choices.companies} onChange={next => set("company", next)} />
        <SuggestedChoice label="Drug / study" value={value.drug} options={choices.drugs} onChange={next => set("drug", next)} />
        <SuggestedChoice label="Indication" value={value.indication} options={choices.indications} onChange={next => set("indication", next)} />
        <label className="trial-filter-field">NCT trial ID<input value={value.nctId} placeholder="All · optional NCT ID" onChange={event => set("nctId", event.target.value)} /></label>
        <Choice label="Registered phase" value={value.registeredPhase} options={PIPELINE_STAGES.filter(phase => !["Phase 3 Results", "NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision", "Post-Decision"].includes(phase)).map(phase => [phase, phase])} onChange={next => set("registeredPhase", next)} />
        <Choice label="Trial recruitment status" value={value.trialStatus} options={[
          ["NOT_YET_RECRUITING", "Not yet recruiting"], ["RECRUITING", "Recruiting"], ["ENROLLING_BY_INVITATION", "Enrolling by invitation"],
          ["ACTIVE_NOT_RECRUITING", "Active, not recruiting"], ["COMPLETED", "Completed"], ["SUSPENDED", "Suspended"],
          ["TERMINATED", "Terminated"], ["WITHDRAWN", "Withdrawn"], ["UNKNOWN", "Unknown / not recorded"],
        ]} onChange={next => set("trialStatus", next)} />
        <h4>Clinical results</h4>
        <Choice label="Primary endpoint outcome" value={value.primaryOutcome} options={[["SUCCESS", "Success verified"], ["FAILED", "Failure verified"], ["REVIEW", "Awaiting review"], ["UNKNOWN", "Unknown / unverified"]]} onChange={next => set("primaryOutcome", next)} />
        <Choice label="Results release date" value={value.resultsWindow} options={DATE_WINDOWS} onChange={next => set("resultsWindow", next)} />
        <Choice label="Safety concerns" value={value.safety} options={FLAGS} onChange={next => set("safety", next)} />
        <h4>Post-readout financing</h4>
        <label className="trial-first-financing"><input type="checkbox" checked={value.firstFinancingClosed} onChange={event => set("firstFinancingClosed", event.target.checked)} />First post-readout financing closed</label>
        <Choice label="Independent financing transactions" value={value.independentFinancings} options={[["VERIFIED", "Two separate transactions verified"], ["REVIEW", "Evidence needs review"], ["UNKNOWN", "Unknown / unverified"]]} onChange={next => set("independentFinancings", next)} />
        <Choice label="First verified close date" value={value.firstCloseWindow} options={DATE_WINDOWS} onChange={next => set("firstCloseWindow", next)} />
        <Choice label="Second verified close date" value={value.secondCloseWindow} options={DATE_WINDOWS} onChange={next => set("secondCloseWindow", next)} />
        <h4>Regulatory progress</h4>
        <Choice label="Regulatory milestone reached" value={value.regulatoryMilestone} options={["NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision", "Post-Decision"].map(stage => [stage, stage])} onChange={next => set("regulatoryMilestone", next)} />
        <Choice label="FDA decision / outcome" value={value.outcome} options={[["APPROVED", "Approved"], ["CRL", "Complete response letter"], ["REJECTED", "Rejected"], ["WITHDRAWN", "Withdrawn"], ["REFUSED", "Refused"], ["UNKNOWN", "No recorded decision"]]} onChange={next => set("outcome", next)} />
        <p className="trial-filter-note">Use DATE TRIAL COUNTS for PDUFA timing, including no date and past / recheck.</p>
        <h4>Financial screening</h4>
        <p className="trial-filter-note">The optional market-cap checkbox above applies across all groups.</p>
        <Choice label="Cash runway" value={value.runway} options={[["UNDER12", "Under 12 months"], ["12", "At least 12 months"], ["18", "At least 18 months"], ["24", "At least 24 months"], ["UNKNOWN", "Unknown / unverified"]]} onChange={next => set("runway", next)} />
        <Choice label="Dilution / financing overhang" value={value.dilution} options={FLAGS} onChange={next => set("dilution", next)} />
        <h4>Evidence &amp; list membership</h4>
        <Choice label="Evidence quality" value={value.evidence} options={[["VERIFIED", "Verified milestone evidence"], ["SOURCE_RECORDED", "Registry / source recorded"], ["REVIEW", "Awaiting review"], ["MISSING", "Missing evidence"], ["CONFLICTING", "Conflicting evidence"], ["STALE", "Source review older than 7 days"]]} onChange={next => set("evidence", next)} />
        <Choice label="List membership" value={value.membership} options={[["PIPELINE", "PIPELINE"], ["GEM_JR", "GEM JR"], ["GEM", "GEM"], ["HISTORICAL", "Historical / removed"]]} onChange={next => set("membership", next)} />
      </div>}
    </details>
    {activeTrialFilters(value) > 0 && <button type="button" className="secondary trial-filter-reset" onClick={() => onChange({ ...EMPTY_TRIAL_FILTERS })}>Clear trial filters</button>}
  </fieldset>;
}
