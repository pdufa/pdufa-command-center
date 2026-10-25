/** Exact-NCT scientific archive contract. No candidate rankings or scoring.
 * A checksum is verified by the backend before it returns this read-only
 * dossier. The browser independently rejects conflicting identity/provenance.
 */
export const ARCHIVE_DOMAINS = [
  "disease_biology", "mechanism_of_action", "preclinical_evidence",
  "clinical_design", "clinical_results", "competitive_landscape",
  "regulatory_analysis", "advanced_inference",
] as const;
export type ArchiveDomain = typeof ARCHIVE_DOMAINS[number];
export const ARCHIVE_DOMAIN_NAMES: Record<ArchiveDomain, string> = {
  disease_biology: "Disease biology",
  mechanism_of_action: "Mechanism of action",
  preclinical_evidence: "Preclinical evidence",
  clinical_design: "Clinical design",
  clinical_results: "Clinical results",
  competitive_landscape: "Competitive landscape",
  regulatory_analysis: "Regulatory analysis",
  advanced_inference: "Advanced inference",
};

export const ARCHIVE_NCT_PATTERN = /^NCT[0-9]{8}$/;
const CLAIM_LOCATORS = {
  allocation: "protocolSection.designModule.designInfo.allocation",
  intervention_model: "protocolSection.designModule.designInfo.interventionModel",
  masking: "protocolSection.designModule.designInfo.maskingInfo.masking",
  enrollment: "protocolSection.designModule.enrollmentInfo.count",
  primary_outcomes: "protocolSection.outcomesModule.primaryOutcomes",
} as const;
export type ArchiveClaimField = keyof typeof CLAIM_LOCATORS;
export type ArchiveSourceClaim = {
  field: ArchiveClaimField;
  reported_value: unknown;
  source_url: string;
  source_locator: string;
  verification_status: "source_record_only";
  scientifically_verified: false;
};
export type ArchivedDomain = {
  status: "source_record_only" | "not_assessed";
  score: null;
  claims: ArchiveSourceClaim[];
};
export type ArchivedScienceDossier = {
  model_version: "trial-science-dossier-v1";
  exact_program_id: string;
  nct_id: string;
  source_url: string;
  source_sha256: string;
  source_fetched_at?: string;
  assessment_status: "incomplete";
  domains: Record<ArchiveDomain, ArchivedDomain>;
  overall_score: null;
  fda_approval_probability: null;
  read_only: true;
  note: string;
};

const object = (x: unknown): x is Record<string, unknown> =>
  x !== null && typeof x === "object" && !Array.isArray(x);

function safeJsonValue(value: unknown): boolean {
  try {
    const json = JSON.stringify(value);
    return typeof json === "string" && json.length <= 60000;
  } catch {
    return false;
  }
}

/** Show only registry metadata for exactly the selected NCT, never scored data. */
export function isExactArchivedDossier(value: unknown, requestedNct: string): value is ArchivedScienceDossier {
  if (!ARCHIVE_NCT_PATTERN.test(requestedNct) || !object(value) || !object(value.domains)) return false;
  if (value.model_version !== "trial-science-dossier-v1"
      || value.exact_program_id !== "TRIAL|" + requestedNct
      || value.nct_id !== requestedNct
      || value.source_url !== "https://clinicaltrials.gov/study/" + requestedNct
      || typeof value.source_sha256 !== "string"
      || !/^[0-9a-f]{64}$/.test(value.source_sha256)
      || value.assessment_status !== "incomplete"
      || value.overall_score !== null
      || value.fda_approval_probability !== null
      || value.read_only !== true
      || typeof value.note !== "string"
      || value.note.length > 1000) return false;
  if (value.source_fetched_at !== undefined
      && (typeof value.source_fetched_at !== "string"
          || value.source_fetched_at.length > 64
          || !/^(20[0-9]{2}-[0-9]{2}-[0-9]{2})T/.test(value.source_fetched_at)
          || !/(Z|[+-][0-9]{2}:[0-9]{2})$/.test(value.source_fetched_at))) return false;
  if (Object.keys(value.domains).length !== ARCHIVE_DOMAINS.length) return false;
  for (const key of ARCHIVE_DOMAINS) {
    const domain = value.domains[key];
    if (!object(domain) || domain.score !== null || !Array.isArray(domain.claims)
        || domain.claims.length > 5) return false;
    const design = key === "clinical_design";
    const wantedStatus = design && domain.claims.length > 0 ? "source_record_only" : "not_assessed";
    if (domain.status !== wantedStatus || (!design && domain.claims.length !== 0)) return false;
    const observedFields = new Set<string>();
    for (const claim of domain.claims) {
      if (!object(claim) || typeof claim.field !== "string"
          || !Object.prototype.hasOwnProperty.call(CLAIM_LOCATORS, claim.field)
          || observedFields.has(claim.field)
          || claim.source_url !== value.source_url
          || claim.source_locator !== CLAIM_LOCATORS[claim.field as ArchiveClaimField]
          || claim.verification_status !== "source_record_only"
          || claim.scientifically_verified !== false
          || !safeJsonValue(claim.reported_value)) return false;
      observedFields.add(claim.field);
    }
  }
  return true;
}

export function formatArchivedField(field: ArchiveClaimField): string {
  return ({
    allocation: "Allocation",
    intervention_model: "Intervention model",
    masking: "Masking",
    enrollment: "Enrollment",
    primary_outcomes: "Registered primary outcomes",
  } as const)[field];
}

/** Bounded plain text, not HTML. Long outcomes stay inspectable at the source. */
export function summarizeArchivedValue(value: unknown): string {
  if (typeof value === "string") return value.slice(0, 420);
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    const json = JSON.stringify(value);
    return (json ?? "Unavailable").slice(0, 600) + ((json?.length ?? 0) > 600 ? " …" : "");
  } catch {
    return "Unavailable";
  }
}
