/**
 * Read-only clinical scan reporting. Active categories: PIPELINE and posted
 * Phase 3 results. Former tier membership data is archival and not collected,
 * interpreted, or returned as a new/current candidate.
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
  kind: "NEW_PROGRAM" | "NEW_PHASE3_RESULT";
  stage: "PIPELINE" | "PHASE3_RESULTS";
  ticker: string | null;
  drug: string | null;
  trialId: string | null;
  label: string;
  exactRun: boolean;
  sourceUrl?: string;
};

export type NewFromScanSummary = {
  runId: number | null;
  startedAt: string | null;
  scanPacificDate: string | null;
  reportUpdatedAt: string | null;
  pipelineNewPrograms: number | null;
  phase3NewResultRecords: number | null;
  pipelineChangedTrials: number | null;
  rows: NewFromScanRow[];
  warnings: string[];
};

export function newFromScanSummary(
  clinicalInput: unknown,
  pipelineInput: unknown,
): NewFromScanSummary {
  const clinical = obj(clinicalInput);
  const pipeline = obj(pipelineInput);
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
  const matchedStage = (id: string): JsonObject | null => {
    const stage = stages.get(id);
    return stage && runId !== null && count(stage.run_id) === runId &&
      stage.artifact_integrity === "PASS" && stage.status === "PARTIAL" &&
      stage.collector_status === "COMPLETE" ? stage : null;
  };

  const pipelineReport = matchedStage("2");
  const enrichmentReport = matchedStage("3");
  // Scan 4 is a clinical posted-results collector, not a stage membership scan.
  const resultsReport = matchedStage("4");
  const warnings: string[] = [];
  const pipelineNewPrograms: NewFromScanRow[] = [];

  const sourceFinished = dateMs(pipeline?.finished_at);
  const reportFinished = dateMs(enrichmentReport?.collected_at_utc);
  const finishedTogether = sourceFinished !== null && reportFinished !== null &&
    Math.abs(sourceFinished - reportFinished) <= 2 * 60 * 1000;
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
        label:"NEW FROM SCAN — newly identified master program", exactRun:true,
      });
    }
  } else {
    warnings.push("PIPELINE program additions cannot be matched to this report's scan execution.");
  }

  const rawResultCount = count(resultsReport?.new_records);
  const rawDetails = Array.isArray(resultsReport?.new_record_details)
    ? resultsReport.new_record_details : [];
  const resultDetails: NewFromScanRow[] = [];
  const seenResults = new Set<string>();
  if (rawResultCount !== null) for (const raw of rawDetails.slice(0, Math.min(100, rawResultCount))) {
    const detail = obj(raw);
    const ticker = string(detail?.ticker), nct = string(detail?.nct_id);
    const sourceUrl = string(detail?.source_url);
    if (!ticker || !/^[A-Z][A-Z0-9.-]{0,12}$/.test(ticker) ||
        !nct || !/^NCT\d{8}$/.test(nct) ||
        sourceUrl !== "https://clinicaltrials.gov/study/" + nct ||
        seenResults.has(ticker + "|" + nct)) continue;
    seenResults.add(ticker + "|" + nct);
    resultDetails.push({
      kind:"NEW_PHASE3_RESULT", stage:"PHASE3_RESULTS", ticker, drug:string(detail?.drug),
      trialId:nct, sourceUrl,
      label:"NEW FROM SCAN — registry results posted " +
        (string(detail?.results_posted_at) || "date unreported"), exactRun:true,
    });
  }
  const unidentified = rawResultCount === null ? 0 : Math.max(0, rawResultCount - resultDetails.length);
  if (unidentified > 0) {
    warnings.push("Phase 3 results collector reported " + unidentified.toLocaleString("en-US") +
      " new result record(s) without published ticker/NCT identities.");
  }
  if (stages.get("4") && !resultsReport) {
    warnings.push("Posted Phase 3 results belong to a different or unverified run; current-run count withheld.");
  }
  const rows: NewFromScanRow[] = [
    ...pipelineNewPrograms,
    ...resultDetails,
    ...(unidentified > 0 ? [{
      kind:"NEW_PHASE3_RESULT" as const, stage:"PHASE3_RESULTS" as const,
      ticker:null, drug:null, trialId:null,
      label:unidentified.toLocaleString("en-US") +
        " NEW FROM SCAN — posted Phase 3 result record(s), identity not published",
      exactRun:true,
    }] : []),
  ];
  return {
    runId, startedAt, scanPacificDate:day,
    reportUpdatedAt:string(clinical?.updated_at_utc),
    pipelineNewPrograms:newMasterPrograms === null ? null : pipelineNewPrograms.length,
    phase3NewResultRecords:rawResultCount,
    pipelineChangedTrials:count(pipelineReport?.changed_trials_this_execution),
    rows, warnings,
  };
}
