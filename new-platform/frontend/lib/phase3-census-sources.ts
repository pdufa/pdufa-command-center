/** Saved, exact-identity research pointers. A URL is not verified program evidence. */
import { PHASE3_CENSUS_EXPECTED_ROWS, type Phase3CensusRows, type Phase3CensusTrial } from "./phase3-census-rows";

export const PHASE3_CENSUS_SOURCES_PATH = "/phase3-census-sources-2026-10-26.json";
export const FDA_RESEARCH_LINKS = [
  { label: "Drugs@FDA research entry point (CDER)", url: "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm" },
  { label: "FDA biologics research entry point (CBER)", url: "https://www.fda.gov/vaccines-blood-biologics/biologics-products-establishments" },
] as const;
export type CensusResearchLink = { label: string; url: string };
export type Phase3CompanySources = {
  ticker: string;
  company: string;
  cik: string;
  leadSponsorNames: string[];
  nctIds: string[];
  marketCapUsd: number;
  marketCapCheckedAt: string;
  marketCapSourceUrl: string;
  secFilingsUrl: string;
  secSubmissionsUrl: string;
  configuredIssuerHomepages: string[];
};
export type Phase3CensusSourceDirectory = {
  schemaVersion: 1;
  scope: "RESEARCH_POINTERS_ONLY";
  censusAsOf: string;
  trialCount: 741;
  companyCount: 130;
  inputs: { path: string; sha256: string }[];
  companies: Phase3CompanySources[];
};

const INPUT_PATHS = ["data/phase3_all_years_300m_10b_trials.csv", "data/company_registry.csv",
  "data/snapshots/phase_pipeline_market_caps_2026-10-26.csv", "config/snapshots/issuer_sources_2026-10-26.json"];
const CENSUS_SHA256 = "a426ac6c01726a2c3a9916698e50f3cc87b0e6230260068231c88f1b4a30a143";
const COMPANY_KEYS = ["ticker","company","cik","leadSponsorNames","nctIds","marketCapUsd",
  "marketCapCheckedAt","marketCapSourceUrl","secFilingsUrl","secSubmissionsUrl","configuredIssuerHomepages"];
function fail(): never { throw new Error("Census research sources blocked: exact saved identities or source scope differ."); }
const record = (x: unknown): x is Record<string, unknown> => x !== null && typeof x === "object" && !Array.isArray(x);
const exactKeys = (x: Record<string, unknown>, keys: string[]) => Object.keys(x).length === keys.length && keys.every(k => Object.hasOwn(x,k));
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(v => typeof v === "string" && v.length > 0)
    && new Set(value).size === value.length;
}
function homepage(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password && !url.port
      && value === `https://${url.hostname}/` && /^[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}$/.test(url.hostname);
  } catch { return false; }
}

/** Checks saved-source consistency, not the truth/freshness of external websites. */
export function parsePhase3CensusSourceDirectory(value: unknown, inventory: Phase3CensusRows): Phase3CensusSourceDirectory {
  if (!record(value) || !exactKeys(value,["schemaVersion","scope","censusAsOf","trialCount","companyCount","inputs","companies"])
      || value.schemaVersion !== 1 || value.scope !== "RESEARCH_POINTERS_ONLY"
      || value.censusAsOf !== "2026-10-26T12:21:15.972309+00:00"
      || value.trialCount !== PHASE3_CENSUS_EXPECTED_ROWS || value.companyCount !== 130
      || !Array.isArray(value.inputs) || value.inputs.length !== INPUT_PATHS.length
      || !Array.isArray(value.companies) || value.companies.length !== 130
      || inventory.rows.length !== 741 || inventory.uniqueCompanies !== 130
      || inventory.qualifiedPipelineTotal !== null || inventory.pdufaQualifiedCount !== null) fail();
  for (const [i, input] of value.inputs.entries()) {
    if (!record(input) || !exactKeys(input,["path","sha256"]) || input.path !== INPUT_PATHS[i]
        || typeof input.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(input.sha256)
        || (i === 0 && input.sha256 !== CENSUS_SHA256)) fail();
  }
  const trials = new Map(inventory.rows.map(row => [row.nctId, row]));
  if (trials.size !== 741) fail();
  const seen = new Set<string>(), tickers = new Set<string>();
  for (const company of value.companies) {
    if (!record(company) || !exactKeys(company,COMPANY_KEYS)
        || typeof company.ticker !== "string" || !/^[A-Z]{1,7}(?:[.-][A-Z]{1,3})?$/.test(company.ticker)
        || tickers.has(company.ticker) || typeof company.company !== "string" || !company.company.trim()
        || /[\u0000-\u001f<>]/u.test(company.company)
        || typeof company.cik !== "string" || !/^\d{10}$/.test(company.cik) || Number(company.cik) <= 0
        || !strings(company.nctIds) || !company.nctIds.length || !strings(company.leadSponsorNames)
        || !company.leadSponsorNames.length || !strings(company.configuredIssuerHomepages)
        || !company.configuredIssuerHomepages.every(homepage)
        || typeof company.marketCapUsd !== "number" || !Number.isFinite(company.marketCapUsd)
        || company.marketCapUsd < 300_000_000 || company.marketCapUsd > 10_000_000_000
        || typeof company.marketCapCheckedAt !== "string" || !/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(company.marketCapCheckedAt)
        || !Number.isFinite(Date.parse(company.marketCapCheckedAt))
        || Date.parse(company.marketCapCheckedAt) > Date.parse(value.censusAsOf as string)
        || company.marketCapSourceUrl !== `https://api.nasdaq.com/api/quote/${company.ticker}/summary?assetclass=stocks`
        || company.secFilingsUrl !== `https://www.sec.gov/edgar/browse/?CIK=${company.cik}&owner=exclude`
        || company.secSubmissionsUrl !== `https://data.sec.gov/submissions/CIK${company.cik}.json`) fail();
    const names = new Set<string>();
    for (const id of company.nctIds) {
      const trial = trials.get(id);
      if (!trial || seen.has(id) || trial.ticker !== company.ticker || !company.leadSponsorNames.includes(trial.company)
          || trial.pipelineQualification !== null || trial.fdaPdufaVerification !== false
          || trial.sourceUrl !== `https://clinicaltrials.gov/study/${id}`) fail();
      seen.add(id);
      names.add(trial.company);
    }
    if (names.size !== company.leadSponsorNames.length) fail();
    tickers.add(company.ticker);
  }
  if (seen.size !== 741 || tickers.size !== 130) fail();
  return value as Phase3CensusSourceDirectory;
}

/** Only exact saved NCT/ticker pairs receive a company filing pointer. */
export function sourcesForPhase3Trial(trial: Phase3CensusTrial, directory: Phase3CensusSourceDirectory): Phase3CompanySources {
  const company = directory.companies.find(c => c.ticker === trial.ticker && c.nctIds.includes(trial.nctId));
  if (!company || !company.leadSponsorNames.includes(trial.company)
      || trial.pipelineQualification !== null || trial.fdaPdufaVerification !== false) fail();
  return company;
}

export function companyResearchLinks(company: Phase3CompanySources): CensusResearchLink[] {
  return [{label: `SEC company filings · CIK ${company.cik} (saved mapping)`,url: company.secFilingsUrl},
    ...company.configuredIssuerHomepages.map(url => ({label:"Configured issuer website (unverified pointer)",url}))];
}
