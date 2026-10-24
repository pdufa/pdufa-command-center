/** Validate exact-program read-only market observations on the server.
 * Never trust arbitrary backend JSON or forward provider secrets/errors.
 */
const obj = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const optionalNumber = (v: unknown) => v == null || finite(v);

export function verifiedMarketEnrichment(value: unknown, programId: string): Record<string, unknown> {
  if (!obj(value) || value.programId !== programId || typeof value.exactKey !== "string"
      || !value.exactKey.trim() || value.exactKey.length > 512
      || typeof value.ticker !== "string" || !/^[A-Z][A-Z0-9.-]{0,12}$/.test(value.ticker)
      || typeof value.status !== "string" || !value.status || value.status.length > 80
      || value.researchOnly !== true || value.orderExecutionEnabled !== false
      || value.qualificationChanges !== false || value.restrictionChanges !== false
      || value.fsFaChanges !== false
      || !optionalNumber(value.latestDailyClose) || !optionalNumber(value.latestIexVolume)
      || !obj(value.marketEvidenceReview) || !obj(value.marketSignals)) {
    throw new Error("Market evidence boundary or identity invalid");
  }
  const review = value.marketEvidenceReview, signals = value.marketSignals;
  if (review.programId !== programId || review.exactKey !== value.exactKey
      || review.recommendation !== null || review.assessmentScoreChange !== false
      || review.qualificationChange !== false || review.fsFaChange !== false
      || !["RESEARCH_ONLY", "INSUFFICIENT_EVIDENCE"].includes(String(review.status))
      || !Array.isArray(review.observations) || review.observations.length > 2
      || review.observations.some(x => !obj(x) || typeof x.metric !== "string"
        || !finite(x.value) || typeof x.unit !== "string")
      || (review.status === "INSUFFICIENT_EVIDENCE" && review.observations.length !== 0)
      || (review.status === "RESEARCH_ONLY" && (review.observations.length !== 2 || value.status !== "OK"))
      || !["OK", "INSUFFICIENT_DATA"].includes(String(signals.status))
      || !Number.isSafeInteger(signals.validBars) || (signals.validBars as number) < 0
      || !optionalNumber(signals.return20Pct)
      || !optionalNumber(signals.averageVolume20) || !optionalNumber(signals.volumeRatio20)
      || (signals.status === "OK" && ((signals.validBars as number) < 20 || value.status !== "OK"))
      || (value.status === "OK" && (!finite(value.latestDailyClose) || value.latestDailyClose <= 0
        || !finite(value.latestIexVolume) || value.latestIexVolume < 0))) {
    throw new Error("Market observations incomplete or inconsistent");
  }
  return value;
}
