/** Generic Phase 3 pre-readout analytical questions for mixed indications.
 * Never reuse IZAR-2/PsA-specific questions as if they apply to all diseases.
 * DOCUMENTED source checks are observations, not outcome predictions.
 */
import batch from "../data/phase3PreDataBatch20261105.json";
export type PreDataProtocol={primaryEndpoint:string;primaryTimeframe:string;allocation:string;masking:string;interventionModel:string;comparator:string;enrollment:string;enrollmentType:string;firstPosted:string;sourceUpdated:string;checkedAt:string;resultsFirstPosted:string};
export type PreDataTrial={nctId:string;ticker:string;company:string;indication:string;interventions:string;registryStatus:string;registryPhase:string;marketCapUsd:number;marketCapCheckedAt:string;registrySourceUrl:string;registryAsOf:string;readoutStatus:string;protocol:PreDataProtocol|null;priorPhase2Lead:{phase2Nct:string;pValue:string;sourceUrl:string;sourceDate:string}|null};
export const phase3PredataSnapshot=batch as {schemaVersion:number;asOf:string;note:string;counts:{registryActiveCapScreen:number;knownIssuerReadoutsExcluded:number;preReadoutResearchCandidates:number;withStoredProtocol:number;withoutStoredProtocol:number;withPriorPhase2EvidenceLead:number;withProgramSpecificThirtyPredictions:number};excludedKnownIssuerReadouts:{nctId:string;ticker:string}[];trials:PreDataTrial[]};
const index=new Map(phase3PredataSnapshot.trials.map(t=>[t.nctId,t] as const));
export const getPreDataTrial=(nctId:string):PreDataTrial|undefined=>index.get(nctId);
export type SourceObservation={description:string;documentationScore:100;sourceUrl:string};
export type UniversalQuestion={heading:string;question:string;missingEvidence:string};
export const UNIVERSAL_PHASE3_QUESTIONS:readonly UniversalQuestion[]=[
 {heading:"Primary endpoint success forecast",question:"Is the primary efficacy endpoint likely to be met?",missingEvidence:"Matched prior-stage efficacy results, effect sizes, comparator response, and prespecified analysis assumptions."},
 {heading:"Prior statistical significance",question:"Is prior efficacy statistically convincing for the same drug and indication?",missingEvidence:"Verified prior trial NCT, statistical effect and p-value, endpoint alignment, and program crosswalk."},
 {heading:"Safety and tolerability forecast",question:"Is a clinically acceptable safety profile likely?",missingEvidence:"Relevant Phase 2/earlier Phase 3 adverse-event data, exposure and discontinuations."},
 {heading:"Biological target validation",question:"Is the mechanism of action supported in this disease?",missingEvidence:"Mechanistic publications and indication-specific human target validation."},
 {heading:"Phase 3 dose justification",question:"Is the regimen supported by dose-finding evidence?",missingEvidence:"Earlier dose-response, pharmacokinetics, exposure-response, and final regimen rationale."},
 {heading:"Patient population generalizability",question:"Does the Phase 3 population match the population with prior efficacy evidence?",missingEvidence:"Inclusion/exclusion criteria and matched earlier-study population and prior treatment mix."},
 {heading:"Registered primary endpoint",question:"Is the primary outcome registered in the saved protocol?",missingEvidence:"Protocol primary outcome field from an accessible ClinicalTrials.gov snapshot."},
 {heading:"Primary endpoint assessment time",question:"Is the primary endpoint timeframe recorded?",missingEvidence:"Protocol primary-timeframe field and clinical justification of timing."},
 {heading:"Allocation and randomization",question:"Does the registry specify randomized or nonrandomized allocation?",missingEvidence:"Current or dated registry allocation field."},
 {heading:"Masking and blinding",question:"Does the registry specify the masking design?",missingEvidence:"Current or dated registry masking field."},
 {heading:"Comparator documentation",question:"Is the protocol comparator explicitly documented?",missingEvidence:"Registered arm-level comparator or protocol control-group description."},
 {heading:"Enrollment documentation",question:"Does the registered protocol state enrollment?",missingEvidence:"Dated registry enrollment count and actual-versus-estimated status."},
 {heading:"Statistical power adequacy",question:"Is the planned study sufficiently powered for the primary endpoint?",missingEvidence:"Statistical analysis plan, sample-size assumptions, effect size, alpha and power."},
 {heading:"Missing data robustness",question:"Can missing data and intercurrent events be handled robustly?",missingEvidence:"Prespecified estimand, missing-data handling and sensitivity analyses."},
 {heading:"Multiplicity control",question:"Are testing and multiplicity adjustments adequately specified?",missingEvidence:"Statistical testing hierarchy, endpoints and alpha allocation."},
 {heading:"Prior clinical effect size",question:"Does earlier human evidence show a material treatment effect?",missingEvidence:"Program-matched effect sizes and controls from earlier completed trials."},
 {heading:"Secondary clinical endpoints",question:"Are supporting secondary clinical endpoints likely to be positive?",missingEvidence:"Exact indication-specific secondary endpoints and earlier comparable outcomes."},
 {heading:"Patient-reported outcomes",question:"Are patient-reported benefits likely to be meaningful?",missingEvidence:"Validated PRO instruments and earlier treatment effect estimates."},
 {heading:"Key prespecified subgroups",question:"Will major subgroups have consistent benefit?",missingEvidence:"Prespecified subgroup definitions, prior subgroup signals and interaction estimates."},
 {heading:"Clinical importance",question:"Is the anticipated treatment benefit clinically meaningful?",missingEvidence:"Minimum clinically important difference, expected effect size and existing standard of care."},
 {heading:"Long-term durability",question:"Will benefit persist through later follow-up?",missingEvidence:"Longer-term earlier-study outcomes, exposure duration, and continuation results."},
 {heading:"Common infection tolerability",question:"Are common treatment-related infections likely manageable?",missingEvidence:"Drug-specific infection event rates and mechanism-related risks."},
 {heading:"Rare and serious adverse events",question:"Is the risk of serious or uncommon adverse events acceptable?",missingEvidence:"Pooled exposure, serious-event history and longer follow-up."},
 {heading:"Retention and discontinuation",question:"Will retention and discontinuation allow interpretable efficacy results?",missingEvidence:"Actual dropout experience, treatment burden and missing-data projections."},
 {heading:"Registry operational status",question:"What is the study's documented current recruitment status?",missingEvidence:"Source-dated registry recruitment status."},
 {heading:"Site and population representativeness",question:"Is the trial population and site mix representative of intended treatment users?",missingEvidence:"Site/geography census, demographic enrollment and representativeness review."},
 {heading:"Placebo named in interventions",question:"Does the registry intervention list explicitly mention placebo?",missingEvidence:"Dated intervention list and arm assignment; absence of the word placebo is not evidence of no control."},
 {heading:"Regulatory alignment",question:"Is the Phase 3 design aligned with regulators' expectations?",missingEvidence:"FDA/EMA meeting feedback, indication-specific guidance and program correspondence."},
 {heading:"Confirmed unreleased primary readout",question:"Has a public Phase 3 primary readout been ruled out?",missingEvidence:"Dated issuer-press-release check for the exact NCT and current registry results status; active status alone is insufficient."},
 {heading:"Application/PDUFA readiness",question:"Is the program positioned for a favorable regulatory decision after Phase 3?",missingEvidence:"Verified efficacy and safety, exact drug-indication application crosswalk, submission acceptance, and FDA review history."}
] as const;
if(UNIVERSAL_PHASE3_QUESTIONS.length!==30)throw Error("UNIVERSAL_QUESTION_COUNT_INVALID");
const summary=(value:string,max=340)=>value.length>max?value.slice(0,max-1)+"…":value;
export function sourceObservation(nctId:string,number:number):SourceObservation|null{
 const t=getPreDataTrial(nctId);if(!t)return null;
 const p=t.protocol;
 const doc=(description:string):SourceObservation=>({description:summary(description),documentationScore:100,sourceUrl:t.registrySourceUrl});
 switch(number){
  case 7:return p?.primaryEndpoint?.trim()?doc("Registry primary outcome: "+p.primaryEndpoint):null;
  case 8:return p?.primaryTimeframe?.trim()?doc("Registry primary outcome timeframe: "+p.primaryTimeframe):null;
  case 9:return p?.allocation?.trim()?doc("Registry allocation: "+p.allocation):null;
  case 10:return p?.masking?.trim()?doc("Registry masking: "+p.masking):null;
  case 11:return p?.comparator?.trim()?doc("Saved protocol comparator field: "+p.comparator):null;
  case 12:return p?.enrollment?.trim()?doc("Registry enrollment: "+p.enrollment+" ("+p.enrollmentType.toLowerCase()+")"):null;
  case 25:return t.registryStatus?doc("Registry status on "+t.registryAsOf+": "+t.registryStatus.replaceAll("_"," ")):null;
  case 27:return /\bplacebo\b/i.test(t.interventions)?doc("Placebo is named in the registered intervention list; trial arms and formal comparison remain to be checked."):null;
  default:return null;
 }
}
export function missingQuestionEvidence(nctId:string,number:number):string{
 const q=UNIVERSAL_PHASE3_QUESTIONS[number-1];if(!q)return "Question not defined";
 const t=getPreDataTrial(nctId);
 if(number===2&&t?.priorPhase2Lead)return q.missingEvidence+" A saved potential Phase 2 lead exists: "+t.priorPhase2Lead.phase2Nct+" (reported p="+t.priorPhase2Lead.pValue+"); drug/indication matching is not independently established.";
 if(number===29&&t?.readoutStatus==="HISTORICAL_PRE_CHECK_ONLY")return "Issuer research marked unreleased in an October 2026 historical check, but this does not verify the status today. "+q.missingEvidence;
 if(!t)return "No matching record in the dated 2026-11-05 pre-readout candidate snapshot. "+q.missingEvidence;
 return q.missingEvidence;
}
export function phase3PreDataSourceFactCount(nctId:string):number{
 return UNIVERSAL_PHASE3_QUESTIONS.filter((_,i)=>sourceObservation(nctId,i+1)!==null).length;
}
