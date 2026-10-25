/** Read-only exact-NCT eligibility audit of the CURRENT published workspace.
 *
 * Counts list membership only. Never infers trials from ticker/company/drug,
 * never imports evidence, calculates science grades or changes GEM/FS/FA/W/T.
 */
export type CohortName = "GEM JR" | "GEM" | "WT";
export type PublishedCandidate = {
  id: string;
  programId?: string;
  nctId?: string;
  ticker?: string;
};
export type PublishedWorkspace = {
  asOf: string;
  mode: string;
  pipeline: PublishedCandidate[];
  members: {
    GEM_JR: { rows: PublishedCandidate[] };
    GEM: { rows: PublishedCandidate[] };
  };
  sourceHealth?: {
    state?: string;
    pipelineSourceParity?: { exactPrograms?: number };
    streamlitPipelineParity?: { exactPrograms?: number };
  };
};
export type PublishedWt = {
  watch: string[];
  trade: string[];
};
export type StageCoverage = {
  list: CohortName;
  publishedRows: number;
  uniquePrograms: number;
  exactNctPrograms: number;
  unlinkedPrograms: number;
  conflictingIdentityPrograms: number;
  rowsWithoutPermanentId: number;
  sourceMissingPrograms: number;
  sampleExactNct: { programId: string; nctId: string }[];
  sampleUnlinkedPrograms: { programId: string; sourceType: string }[];
};
export type PublishedCoverage = {
  asOf: string;
  sourceMode: string;
  sourceHealthState: string;
  status: "SOURCE_NOT_FRESHLY_VERIFIED" | "PUBLISHED_SNAPSHOT_AUDIT";
  pipelineRows: number;
  stages: StageCoverage[];
  archivedScientificRecordsVerified: null;
  scientificFindingsVerified: null;
  importsPerformed: false;
  approvalProbability: null;
  qualificationPresetsChanged: false;
  reason: string;
};

const NCT = /^NCT[0-9]{8}$/;
const TRIAL = /^TRIAL\|(NCT[0-9]{8})$/;
const PROGRAM = /^PDUFA-[0-9]{6,}$/;
const WTS = /^PDUFA-[0-9]{6,}$/;
const SAMPLE_CAP = 12;
const MAX_ROWS = 50000;
const MAX_SOURCE_AGE_MS = 48 * 60 * 60 * 1000;
const MAX_FUTURE_SKEW_MS = 24 * 60 * 60 * 1000;
const SOURCE_DATE = /^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2}))?$/;

/** Published source uses a Pacific calendar date; allow that or an explicit
 * timezone-bearing timestamp. Neither format proves a completed live scan.
 */
function publishedAsOfMs(value: string): number {
  if (!SOURCE_DATE.test(value)) throw new Error("Published source date is malformed");
  const milliseconds = Date.parse(value);
  const year = Number(value.slice(0, 4));
  const month = Number(value.slice(5, 7));
  const day = Number(value.slice(8, 10));
  if (!Number.isFinite(milliseconds)
      || new Date(Date.UTC(year, month - 1, day)).toISOString().slice(0, 10)
        !== value.slice(0, 10)) {
    throw new Error("Published source date is invalid");
  }
  return milliseconds;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function validCandidate(row: unknown): row is PublishedCandidate {
  return isObject(row) && typeof row.id === "string"
    && (row.programId === undefined || typeof row.programId === "string")
    && (row.nctId === undefined || typeof row.nctId === "string");
}

function exactNct(row: PublishedCandidate): string | null {
  const match = TRIAL.exec(row.id);
  if (!match) return null;
  if (row.nctId !== undefined && row.nctId !== "" && row.nctId !== match[1]) return null;
  return match[1];
}

function sourceType(row: PublishedCandidate): string {
  if (TRIAL.test(row.id)) return "TRIAL_SOURCE_CONFLICT";
  const prefix = row.id.split("|", 1)[0];
  return prefix === "APPLICATION" || prefix === "RESULT" ? prefix : "OTHER_OR_UNVERIFIED";
}

function buildIndex(rows: PublishedCandidate[]): Map<string, PublishedCandidate[]> {
  const index = new Map<string, PublishedCandidate[]>();
  for (const row of rows) {
    if (!row.programId || !PROGRAM.test(row.programId)) continue;
    const existing = index.get(row.programId);
    if (existing) {
      if (!existing.some(prev => prev.id === row.id && prev.nctId === row.nctId)) existing.push(row);
    } else index.set(row.programId, [row]);
  }
  return index;
}

function auditedRows(
  name: CohortName,
  rows: PublishedCandidate[],
  missingExternal: number,
): StageCoverage {
  const index = buildIndex(rows);
  let exact = 0;
  let unlinked = 0;
  let conflicts = 0;
  const sampleExactNct: StageCoverage["sampleExactNct"] = [];
  const sampleUnlinkedPrograms: StageCoverage["sampleUnlinkedPrograms"] = [];
  const sorted = [...index.entries()].sort(([a], [b]) => a.localeCompare(b));
  for (const [programId, candidates] of sorted) {
    const identities = new Set(candidates.map(row => row.id));
    const invalid = identities.size !== 1 || candidates.some(row =>
      (row.nctId && !NCT.test(row.nctId))
      || (TRIAL.test(row.id) && row.nctId && exactNct(row) === null));
    if (invalid) { conflicts++; continue; }
    const nct = exactNct(candidates[0]);
    if (nct) {
      exact++;
      if (sampleExactNct.length < SAMPLE_CAP) sampleExactNct.push({ programId, nctId: nct });
    } else {
      unlinked++;
      if (sampleUnlinkedPrograms.length < SAMPLE_CAP) {
        sampleUnlinkedPrograms.push({ programId, sourceType: sourceType(candidates[0]) });
      }
    }
  }
  return {
    list: name,
    publishedRows: rows.length,
    uniquePrograms: index.size + missingExternal,
    exactNctPrograms: exact,
    unlinkedPrograms: unlinked,
    conflictingIdentityPrograms: conflicts,
    rowsWithoutPermanentId: rows.filter(row => !row.programId || !PROGRAM.test(row.programId)).length,
    sourceMissingPrograms: missingExternal,
    sampleExactNct,
    sampleUnlinkedPrograms,
  };
}

export function computePublishedScienceCoverage(
  workspace: unknown,
  wtTags: unknown,
): PublishedCoverage {
  if (!isObject(workspace) || typeof workspace.asOf !== "string"
    || !workspace.asOf.trim() || typeof workspace.mode !== "string"
    || !Array.isArray(workspace.pipeline) || workspace.pipeline.length > MAX_ROWS
    || !isObject(workspace.members) || !isObject(workspace.members.GEM_JR)
    || !isObject(workspace.members.GEM)
    || !Array.isArray(workspace.members.GEM_JR.rows)
    || !Array.isArray(workspace.members.GEM.rows)
    || workspace.members.GEM_JR.rows.length > MAX_ROWS
    || workspace.members.GEM.rows.length > MAX_ROWS) {
    throw new Error("Unverified or oversized published workspace snapshot.");
  }
  if (!isObject(wtTags) || !Array.isArray(wtTags.watch) || !Array.isArray(wtTags.trade)
      || wtTags.watch.length > 500 || wtTags.trade.length > 500
      || [...wtTags.watch, ...wtTags.trade].some(x => typeof x !== "string" || !WTS.test(x))) {
    throw new Error("WT permanent Program ID registry unavailable or invalid.");
  }
  const pipeline = workspace.pipeline as unknown[];
  const jr = workspace.members.GEM_JR.rows as unknown[];
  const gem = workspace.members.GEM.rows as unknown[];
  if (![...pipeline, ...jr, ...gem].every(validCandidate)) {
    throw new Error("Published exact program identity failed validation.");
  }
  const sourceHealth = isObject(workspace.sourceHealth) ? workspace.sourceHealth : {};
  const parity = isObject(sourceHealth.pipelineSourceParity) ? sourceHealth.pipelineSourceParity
    : isObject(sourceHealth.streamlitPipelineParity) ? sourceHealth.streamlitPipelineParity : null;
  if (!parity || parity.exactPrograms !== pipeline.length) {
    throw new Error("Published pipeline and source parity totals disagree.");
  }
  const all = [...(gem as PublishedCandidate[]), ...(jr as PublishedCandidate[]),
               ...(pipeline as PublishedCandidate[])];
  const programIndex = buildIndex(all);
  const watched = [...new Set([...wtTags.watch, ...wtTags.trade])].sort();
  const selected: PublishedCandidate[] = [];
  let missing = 0;
  for (const id of watched) {
    const records = programIndex.get(id);
    if (records) selected.push(...records);
    else missing++;
  }
  const state = typeof sourceHealth.state === "string" ? sourceHealth.state : "UNKNOWN";
  const ageMs = Date.now() - publishedAsOfMs(workspace.asOf);
  const publishedSourceIsCurrent = state === "COMPLETE_PUBLISHED"
    && workspace.mode === "LIVE_READ_ONLY_GITHUB_SOURCE"
    && ageMs >= -MAX_FUTURE_SKEW_MS && ageMs <= MAX_SOURCE_AGE_MS
    && (!Array.isArray(sourceHealth.issues) || sourceHealth.issues.length === 0);
  return {
    asOf: workspace.asOf,
    sourceMode: workspace.mode,
    sourceHealthState: state,
    status: publishedSourceIsCurrent
      ? "PUBLISHED_SNAPSHOT_AUDIT" : "SOURCE_NOT_FRESHLY_VERIFIED",
    pipelineRows: pipeline.length,
    stages: [
      auditedRows("GEM JR", jr as PublishedCandidate[], 0),
      auditedRows("GEM", gem as PublishedCandidate[], 0),
      auditedRows("WT", selected, missing),
    ],
    archivedScientificRecordsVerified: null,
    scientificFindingsVerified: null,
    importsPerformed: false,
    approvalProbability: null,
    qualificationPresetsChanged: false,
    reason: "A list member is eligible for trial identity review only if its published source key is exactly TRIAL|NCT########. The published snapshot does not establish a matching science archive, external evidence verification, approval probability, or a completed 20-level analysis. Missing WT programs are never inferred from ticker/company.",
  };
}
