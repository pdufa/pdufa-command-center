/** Missingness across the original 38 benefit-survey inputs, NEVER a trial result.
 * Only compute if a validated, canonical exact-NCT research identity is unique
 * for the registry NCT and matches the publicly traded ticker. Registry
 * posting alone is insufficient to infer 38 failed or missing study outcomes.
 */
import {BENEFIT_GROUPS,type BenefitFeed} from "./benefit-assessments";
import type {RegistryPostingRow} from "./phase3-registry-posting";
export type SurveyMissingness={
  total:number;verified:number;modeled:number;missing:number;missingPercent:number;
  /** This means recorded research-input availability, NOT underlying medical merit. */
  exactResearchMatch:true;
};
const surveyIds=[...new Set(BENEFIT_GROUPS.flatMap(group=>group.fields.map(field=>field.id)))];
export const SURVEY_INPUT_COUNT=surveyIds.length;
export function surveyMissingnessForPosting(
  row:RegistryPostingRow,feed:BenefitFeed|null
):SurveyMissingness|null{
  if(!feed||!/^NCT\d{8}$/.test(row.nctId)||!row.ticker.trim()||
    !SURVEY_INPUT_COUNT)return null;
  // Refuse ambiguous NCT identities; never join on ticker alone.
  const sameNct=feed.records.filter(record=>record.nctId===row.nctId);
  if(sameNct.length!==1)return null;
  const record=sameNct[0];
  if(record.ticker.trim().toUpperCase()!==row.ticker.trim().toUpperCase()||
     !record.drug.trim()||!record.indication.trim())return null;
  let verified=0,modeled=0;
  for(const key of surveyIds){
    const fact=record.facts[key];
    if(fact?.status==="VERIFIED")verified++;
    else if(fact?.status==="MODELED")modeled++;
  }
  const missing=SURVEY_INPUT_COUNT-verified-modeled;
  return {total:SURVEY_INPUT_COUNT,verified,modeled,missing,
    missingPercent:Math.round(missing*1000/SURVEY_INPUT_COUNT)/10,
    exactResearchMatch:true};
}
