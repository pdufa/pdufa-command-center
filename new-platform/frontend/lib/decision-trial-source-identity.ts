/** Exact identity check for a document explicitly represented as primary-trial evidence.
 * Never infer trial identity from a URL, ticker, title, or adjacent study.
 * A passing result is identity consistency, NOT document authenticity.
 */
export function validatePrimaryTrialSourceIdentity(
  expected: {trialId:string; protocolId:string},
  source: {trialId:unknown; protocolId:unknown},
): void {
  const nct = /^NCT[0-9]{8}$/;
  const protocol = /^[A-Z0-9]+(?:-[A-Z0-9]+)+$/;
  if (!nct.test(expected.trialId) || !protocol.test(expected.protocolId)
      || typeof source.trialId !== "string" || !nct.test(source.trialId)
      || typeof source.protocolId !== "string" || !protocol.test(source.protocolId)
      || source.trialId !== expected.trialId || source.protocolId !== expected.protocolId) {
    throw new Error("Primary trial source identity mismatch or missing identifier");
  }
}
