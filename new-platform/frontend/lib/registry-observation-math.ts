/** Descriptive event rates from publicly reported ClinicalTrials.gov group counts.
 * NEVER a treatment-attributed risk, relative risk, or comparative safety grade.
 */
export function observedSeriousEventRate(affected:number,atRisk:number):number|null{
  if(!Number.isSafeInteger(affected)||!Number.isSafeInteger(atRisk)||
     affected<0||atRisk<=0||affected>atRisk)return null;
  return Math.round(affected/atRisk*1000)/10;
}
