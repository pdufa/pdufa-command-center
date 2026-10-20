/**
 * Read-only display model for the SCANS "NEW FROM SCAN" section.
 * Never infer that a changed trial is new, or that a Phase 3 result
 * record represents a newly GEM JR-qualified program.
 */
type JsonObject = Record<string, unknown>;
const obj = (x: unknown): JsonObject | null =>
  x !== null && typeof x === "object" && !Array.isArray(x) ? x as JsonObject : null;
const string = (x: unknown): string | null =>
  typeof x === "string" && x.trim() ? x.trim() : null;
const count = (x: unknown): number | null =>
  typeof x === "number" && Number.isSafeInteger(x) && x >= 0 ? x : null;
const dateMs = (x: unknown): number | null => {
  const text = string(x);
  if (!text) return null;
  const time = Date.parse(text);
  return Number.isFinite(time) ? time : null;
};
const sameCollection = (start: unknown, stamp: unknown): boolean => {
  const a = dateMs(start), b = dateMs(stamp);
  // A collector may finish after report creation and may cross UTC midnight.
  return a !== null && b !== null && b >= a && b - a <= 6 * 60 * 60 * 1000;
};
export function pacificDay(timestamp: string): string | null {
  const date = dateMs(timestamp);
  if (date === null) return null;
  const fields = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(date));
  const parts = Object.fromEntries(fields.map(({type,value}) => [type,value]));
  return parts.year && parts.month && parts.day
    ? parts.year + "-" + parts.month + "-" + parts.day : null;
}

export type NewFromScanRow = {
  kind: "NEW_PROGRAM" | "NEW_PHASE3_RESULT" | "NEW_STAGE_MEMBER";
  stage: "PIPELINE" | "GEM JR" | "GEM";
  ticker: string | null;
  drug: string | null;
  trialId: string | null;
  label: string;
  exactRun: boolean;
};
export type NewFromScanSummary = {
  runId: number | null;
  startedAt: string | null;
  scanPacificDate: string | null;
  reportUpdatedAt: string | null;
  pipelineNewPrograms: number | null;
  gemJrNewResultRecords: number | null;
  gemJrNewMembersOnDate: number | null;
  gemNewMembersOnDate: number | null;
  pipelineChangedTrials: number | null;
  rows: NewFromScanRow[];
  warnings: string[];
  membershipBasis: "SAME_DATE_LEDGER" | "UNVERIFIED";
};

function ledgerRows(
  ledger: JsonObject | null, stage: "GEM_JR" | "GEM", day: string | null
): NewFromScanRow[] | null {
  const group = obj(obj(ledger?.stages)?.[stage]);
  if (!day || string(group?.last_complete_snapshot) !== day) return null;
  const entries = obj(group?.entries);
  if (!entries) return null;
  const rows: NewFromScanRow[] = [];
  for (const value of Object.values(entries)) {
    const item = obj(value);
    if (!item || item.status !== "ACTIVE") continue;
    // A re-entry must be treated as one new membership, not a duplicate.
    const periods = Array.isArray(item.periods) ? item.periods : [];
    const newPeriod = periods.some(period => {
      const p = obj(period);
      return p?.found === day && (p?.left === null || p?.left === undefined);
    });
    if (!newPeriod) continue;
    rows.push({
      kind: "NEW_STAGE_MEMBER", stage: stage === "GEM" ? "GEM" : "GEM JR",
      ticker: string(item.ticker), drug: string(item.drug), trialId: string(item.nct_id),
      label: "NEW ON SCAN DATE — saved candidate", exactRun: false,
    });
  }
  return rows.sort((a,b) => (a.ticker || "").localeCompare(b.ticker || "") ||
    (a.trialId || "").localeCompare(b.trialId || ""));
}

export function newFromScanSummary(
  clinicalInput: unknown,
  gemInput: unknown,
  pipelineInput: unknown,
  membershipInput: unknown,
): NewFromScanSummary {
  const clinical = obj(clinicalInput);
  const gem = obj(gemInput);
  const pipeline = obj(pipelineInput);
  const membership = obj(membershipInput);
  const runId = count(clinical?.latest_run_id);
  const startedAt = string(clinical?.latest_run_started_at_utc);
  const day = startedAt ? pacificDay(startedAt) : null;
  const clinicalScans = Array.isArray(clinical?.scans) ? clinical.scans : [];
  const stages = new Map<string, JsonObject>();
  for (const value of clinicalScans) {
    const scan = obj(value);
    const id = string(scan?.scan);
    if (id && !stages.has(id)) stages.set(id, scan!);
  }
  const pipelineReport = stages.get("2");
  const enrichmentReport = stages.get("3");
  const jrReport = stages.get("4");
  const pipelineNewPrograms: NewFromScanRow[] = [];
  const warnings: string[] = [];
  const sourceFinished = dateMs(pipeline?.finished_at);
  const reportFinished = dateMs(enrichmentReport?.collected_at_utc);
  const finishedTogether = sourceFinished !== null && reportFinished !== null &&
    Math.abs(sourceFinished - reportFinished) <= 2 * 60 * 1000;
  // Match the stage 3 artifact timestamp to its exact published source
  // snapshot. A later scan's pipeline_state must never leak into old results.
  const samePipelineRun = Boolean(
    pipeline && sameCollection(startedAt, pipeline.started_at) &&
    sameCollection(startedAt, pipeline.finished_at) && finishedTogether &&
    pipeline.status === "COMPLETE");
  const newMasterPrograms = samePipelineRun && Array.isArray(pipeline?.new_master_programs)
    ? pipeline.new_master_programs : null;
  if (newMasterPrograms !== null) {
    const seen = new Set<string>();
    for (const raw of newMasterPrograms) {
      const item = obj(raw);
      if (!item) continue;
      const ticker = string(item.ticker), trialId = string(item.nct_id);
      if (!ticker || !trialId || !/^NCT\d{8}$/.test(trialId)) continue;
      const key = ticker + "|" + trialId;
      if (seen.has(key)) continue;
      seen.add(key);
      pipelineNewPrograms.push({
        kind:"NEW_PROGRAM", stage:"PIPELINE", ticker,
        drug:string(item.drug), trialId,
        label:"NEW FROM SCAN — newly identified master program",exactRun:true,
      });
    }
  } else {
    warnings.push("PIPELINE program additions cannot be matched to this report's scan execution.");
  }
  const rawJrNew = count(jrReport?.new_records);
  // GEM research run must match the same parent workflow before its
  // candidate ledger can be paired with the clinical result counts.
  const sameGemRun = runId !== null && count(gem?.run_id) === runId &&
    sameCollection(startedAt, gem?.generated_at_utc);
  const juniorMembers = sameGemRun ? ledgerRows(membership, "GEM_JR", day) : null;
  const gemMembers = sameGemRun ? ledgerRows(membership, "GEM", day) : null;
  if (juniorMembers === null || gemMembers === null) {
    warnings.push("Saved GEM JR/GEM membership additions are not independently verified for this scan date.");
  }
  if (rawJrNew !== null && rawJrNew > 0) {
    warnings.push("GEM JR source reports a new Phase 3 result count, but does not publish the new record's ticker/NCT identity.");
  }
  if (gem && !sameGemRun) warnings.push("GEM report does not match the latest clinical scan run; candidate additions are withheld.");
  const rows: NewFromScanRow[] = [
    ...pipelineNewPrograms,
    ...(rawJrNew !== null && rawJrNew > 0 ? [{
      kind:"NEW_PHASE3_RESULT" as const, stage:"GEM JR" as const, ticker:null,
      drug:null, trialId:null,
      label:rawJrNew.toLocaleString("en-US")+" NEW FROM SCAN — posted Phase 3 result record(s), identity not published",
      exactRun:true,
    }] : []),
    ...(juniorMembers || []),
    ...(gemMembers || []),
  ];
  return {
    runId, startedAt, scanPacificDate:day,
    reportUpdatedAt:string(clinical?.updated_at_utc),
    pipelineNewPrograms:newMasterPrograms === null ? null : pipelineNewPrograms.length,
    gemJrNewResultRecords:rawJrNew,
    gemJrNewMembersOnDate:juniorMembers?.length ?? null,
    gemNewMembersOnDate:gemMembers?.length ?? null,
    pipelineChangedTrials:count(pipelineReport?.changed_trials_this_execution),
    membershipBasis: juniorMembers !== null && gemMembers !== null ? "SAME_DATE_LEDGER" : "UNVERIFIED",
    rows, warnings,
  };
}
