/**
 * Validate two separately registered trial records before GEM JR evaluates
 * the optional two-study evidence criterion. Entered IDs are research targets,
 * not independent confirmation of pivotal success.
 */
export function normalizeTrialId(value: string): string {
  return value.trim().toUpperCase();
}

export function twoTrialInputError(trials: readonly [string, string]): string | null {
  const [first, second] = trials.map(normalizeTrialId);
  if (!first || !second) return "Enter both Trial 1 and Trial 2 NCT IDs.";
  if (!/^NCT\d{8}$/.test(first) || !/^NCT\d{8}$/.test(second)) {
    return "Both trials need valid ClinicalTrials.gov IDs (NCT followed by eight digits).";
  }
  if (first === second) return "Trial 1 and Trial 2 must be different registered studies.";
  return null;
}
