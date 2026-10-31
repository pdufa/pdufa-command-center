/** Read-only per-column filters for assessment #1. Never widen the source universe. */
import type { PostPhase3PopulationTrial } from "./post-phase3-population";

export type Availability = "all" | "available" | "missing";
export type NumberColumnFilter = {
  status: Availability;
  minimum: string;
  maximum: string;
};
export type DateColumnFilter = {
  status: Availability;
  from: string;
  to: string;
};
export type SourceTextFilter = {
  search: string;
  status: Availability;
};
export type PatientPopulationFilters = {
  all: string;
  ticker: string;
  drug: SourceTextFilter;
  indication: SourceTextFilter;
  diseasePopulation: NumberColumnFilter;
  eligibleUsPatients: NumberColumnFilter;
  eligibleGlobalPatients: NumberColumnFilter;
  adoption12MonthPct: NumberColumnFilter;
  evidence: NumberColumnFilter;
  lastUpdated: DateColumnFilter;
};

export type PopulationSourceFields = {
  drug: string | null;
  indication: string | null;
};

export const EMPTY_PATIENT_POPULATION_FILTERS: PatientPopulationFilters = {
  all: "",
  ticker: "",
  drug: {search:"",status:"all"},
  indication: {search:"",status:"all"},
  diseasePopulation: {status:"all",minimum:"",maximum:""},
  eligibleUsPatients: {status:"all",minimum:"",maximum:""},
  eligibleGlobalPatients: {status:"all",minimum:"",maximum:""},
  adoption12MonthPct: {status:"all",minimum:"",maximum:""},
  evidence: {status:"all",minimum:"",maximum:""},
  lastUpdated: {status:"all",from:"",to:""},
};

function lower(text:string) {return text.trim().toLocaleLowerCase();}
function contains(value:string|null|undefined, needle:string) {
  return !lower(needle) || !!value?.toLocaleLowerCase().includes(lower(needle));
}
function availabilityMatch(hasValue:boolean,status:Availability) {
  return status === "all" || (status === "available" ? hasValue : !hasValue);
}
function numericMatch(value:number|null,filter:NumberColumnFilter) {
  const valid = value !== null && Number.isFinite(value) && value >= 0;
  if(!availabilityMatch(valid,filter.status)) return false;
  const min=filter.minimum.trim(), max=filter.maximum.trim();
  if(!min && !max) return true;
  // An unknown value never passes numerical comparison. Invalid input fails closed.
  if(!valid) return false;
  if(min && (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(min) || value! < Number(min))) return false;
  if(max && (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(max) || value! > Number(max))) return false;
  return true;
}
function dateMatch(value:string|null,filter:DateColumnFilter) {
  const valid = !!value && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(value));
  if(!availabilityMatch(valid,filter.status)) return false;
  if(!filter.from && !filter.to) return true;
  if(!valid) return false;
  return (!filter.from || value! >= filter.from) && (!filter.to || value! <= filter.to);
}
function textMatch(value:string|null|undefined,filter:SourceTextFilter) {
  const known=typeof value === "string" && value.trim().length>0;
  return availabilityMatch(known,filter.status) && contains(value,filter.search);
}

/**
 * Applies all user-selected column filters to only the prequalified census rows.
 * Source-derived drug and indication fields must be resolved for the exact NCT.
 * Missing source data is never turned into a made-up patient count or indication.
 */
export function filterPatientPopulationRows(
  rows: readonly PostPhase3PopulationTrial[],
  filters: PatientPopulationFilters,
  sources: Readonly<Record<string,PopulationSourceFields>>,
): PostPhase3PopulationTrial[] {
  return rows.filter(row => {
    const source=sources[row.trial.nctId];
    return contains([row.trial.ticker,row.trial.nctId,row.trial.company].join(" "),filters.ticker)
      && textMatch(source?.drug,filters.drug)
      && textMatch(source?.indication,filters.indication)
      && numericMatch(row.diseasePopulation,filters.diseasePopulation)
      && numericMatch(row.eligibleUsPatients,filters.eligibleUsPatients)
      && numericMatch(row.eligibleGlobalPatients,filters.eligibleGlobalPatients)
      && numericMatch(row.projectedAdoption12MonthPct,filters.adoption12MonthPct)
      && numericMatch(row.populationEvidenceCompleteness,filters.evidence)
      && dateMatch(row.populationLastVerified,filters.lastUpdated)
      && contains([
        row.trial.ticker,row.trial.nctId,row.trial.company,
        source?.drug||"",source?.indication||""
      ].join(" "),filters.all);
  });
}
