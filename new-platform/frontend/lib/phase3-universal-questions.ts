/** Generic Phase 3 pre-readout analytical questions for mixed indications.
 * Never reuse IZAR-2/PsA-specific questions as if they apply to all diseases.
 * DOCUMENTED source checks are observations, not outcome predictions.
 */
import batch from "../data/phase3PreDataBatch20261105.json";
import officialResearchRaw from "../data/phase3PreDataOfficialResearch.json";
type OfficialPrior={nctId:string;registeredResults?:{primary?:{title:string;analyses?:{pValue?:string|number|null;pValueModifier?:string}[]}[];seriousEventCount?:number}|null};
type OfficialRecord={nctId:string;sourceState:string;registry?:{primaryOutcomes?:{measure:string;timeFrame:string}[];secondaryOutcomes?:{measure:string;timeFrame:string}[];allocation?:string;masking?:string;enrollment?:number;status?:string;interventions?:{name:string;type:string}[];arms?:{label:string;type:string}[];hasResults?:boolean;resultsFirstPosted?:string};priorPhase2?:{matches:OfficialPrior[]}};
const officialResearch=officialResearchRaw as unknown as {records:OfficialRecord[]};
const officialByNct=new Map(officialResearch.records.map(r=>[r.nctId,r] as const));
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
 const research=officialByNct.get(nctId), registry=research?.registry;
 const prior=research?.priorPhase2?.matches||[];
 const sourcedPrimary=prior.flatMap(r=>(r.registeredResults?.primary||[]).flatMap(p=>
  (p.analyses||[]).filter(a=>a.pValue!==null&&a.pValue!==undefined&&a.pValue!=="")
   .map(a=>({nctId:r.nctId,pValue:String(a.pValue),modifier:a.pValueModifier||"",endpoint:p.title}))));
 const doc=(description:string,sourceUrl=t.registrySourceUrl):SourceObservation=>
  ({description:summary(description),documentationScore:100,sourceUrl});
 switch(number){
  case 2:return sourcedPrimary.length>0?doc(
   "Earlier same-drug same-condition Phase 2 registry primary p-values (direction and comparator need independent review): "+
   sourcedPrimary.slice(0,5).map(a=>a.nctId+" "+a.modifier+"p="+a.pValue+" ("+a.endpoint.slice(0,50)+")").join("; "),
   "https://clinicaltrials.gov/study/"+sourcedPrimary[0].nctId):null;
  case 3:{
   const priorSafety=prior.find(r=>r.registeredResults&&r.registeredResults.seriousEventCount!==undefined);
   return priorSafety?doc("An earlier matched Phase 2 registry record reports "+
    priorSafety.registeredResults?.seriousEventCount+
    " named serious-adverse-event categories; this is NOT a patient-level rate or safety verdict.",
    "https://clinicaltrials.gov/study/"+priorSafety.nctId):null;
  }
  case 7:return p?.primaryEndpoint?.trim()?doc("Registry primary outcome: "+p.primaryEndpoint):
   registry?.primaryOutcomes?.[0]?.measure?doc("Official registry primary outcome: "+registry.primaryOutcomes[0].measure):null;
  case 8:return p?.primaryTimeframe?.trim()?doc("Registry primary outcome timeframe: "+p.primaryTimeframe):
   registry?.primaryOutcomes?.[0]?.timeFrame?doc("Official registry primary outcome timeframe: "+registry.primaryOutcomes[0].timeFrame):null;
  case 9:return p?.allocation?.trim()?doc("Registry allocation: "+p.allocation):
   registry?.allocation?doc("Official registry allocation: "+registry.allocation):null;
  case 10:return p?.masking?.trim()?doc("Registry masking: "+p.masking):
   registry?.masking?doc("Official registry masking: "+registry.masking):null;
  case 11:{
   const compare=(registry?.arms||[]).filter(a=>["PLACEBO_COMPARATOR","ACTIVE_COMPARATOR","SHAM_COMPARATOR","NO_INTERVENTION"].includes(a.type));
   return p?.comparator?.trim()?doc("Saved protocol comparator field: "+p.comparator):
    compare.length>0?doc("Official registry comparator arms: "+compare.map(a=>a.type+": "+a.label).join(" | ")):null;
  }
  case 12:return p?.enrollment?.trim()?doc("Registry enrollment: "+p.enrollment+" ("+p.enrollmentType.toLowerCase()+")"):
   registry?.enrollment!==undefined?doc("Official registry enrollment: "+registry.enrollment):null;
  case 16:{
   // The earlier-stage crosswalk is a conservative source lead, not an independently
   // adjudicated same-patient-population result or an efficacy grade.
   const measured=prior.flatMap(study=>(study.registeredResults?.primary||[])
    .filter(outcome=>!/adverse|safety|tolerability|treatment.emergent|serious events|clinical laboratory|vital signs|electrocardiogram|concomitant medication|physical examination abnormalities/i.test(outcome.title))
    .map(outcome=>({nctId:study.nctId,title:outcome.title,
     pValues:(outcome.analyses||[]).filter(a=>a.pValue!==null&&a.pValue!==undefined&&a.pValue!=="")
       .map(a=>(a.pValueModifier||"")+"p="+a.pValue)}));
   if(!measured.length)return null;
   const m=measured[0];
   return doc("Earlier candidate same-drug and same-condition Phase 2 registry has posted "+
    "an efficacy-oriented primary outcome: "+m.title+
    (m.pValues.length?"; statistical test(s): "+m.pValues.slice(0,3).join(", "):"")+
    ". Reported statistical tests are NOT effect-size estimates; actual treatment benefit, "+
    "clinical importance, prior-study population matching, comparator and dosing need "+
    "independent review. This is NOT a positive clinical verdict.",
    "https://clinicaltrials.gov/study/"+m.nctId);
  }
  case 21:{
   // Longer measured follow-up is relevant context but cannot establish sustained benefit.
   const measured=prior.flatMap(study=>(study.registeredResults?.primary||[])
    .filter(outcome=>!/adverse|safety|tolerability|treatment.emergent|serious events|clinical laboratory|vital signs|electrocardiogram|concomitant medication|physical examination abnormalities/i.test(outcome.title))
    .filter(outcome=>/week\s*(?:2[4-9]|[3-9]\d|\d{3})\b|month\s*(?:[6-9]|\d{2})\b|\b(?:6|9|12|18|24)\s+months?\b/i.test(outcome.title+" "+outcome.timeFrame))
    .map(outcome=>({nctId:study.nctId,title:outcome.title,timeFrame:outcome.timeFrame}));
   if(!measured.length)return null;
   const m=measured[0];
   return doc("An earlier candidate Phase 2 record has a publicly posted clinical "+
    "outcome with extended follow-up: "+m.title+"; assessment time: "+m.timeFrame+
    ". Recording a longer observation window does NOT prove that benefit was sustained, "+
    "does not establish a controlled durability effect or justify a numerical rating.",
    "https://clinicaltrials.gov/study/"+m.nctId);
  }
  case 17:return registry?.secondaryOutcomes?.length?doc(
   "Registered secondary outcomes (presence only, NOT predicted efficacy): "+
   registry.secondaryOutcomes.slice(0,3).map(x=>x.measure).join("; ")):null;
  case 19:{
   const subgroup=(registry?.secondaryOutcomes||[]).filter(x=>/subgroup|stratified|interaction|by age|by sex|by gender|by race/i.test(x.measure));
   return subgroup.length?doc("Registered subgroup-labelled outcomes (existence only; no claim of subgroup effect or multiplicity adequacy): "+
    subgroup.slice(0,3).map(x=>x.measure).join("; ")):null;
  }
  case 18:{
   const pro=registry?.secondaryOutcomes?.filter(x=>/quality.of.life|patient.report|functional|symptom|pain|fatigue/i.test(x.measure))||[];
   return pro.length?doc("Registered patient symptom/quality-of-life outcome(s), NOT observed benefits: "+
    pro.slice(0,3).map(x=>x.measure).join("; ")):null;
  }
  case 25:return registry?.status?doc("Official registry status checked in source backfill: "+registry.status):
   t.registryStatus?doc("Registry status on "+t.registryAsOf+": "+t.registryStatus.replaceAll("_"," ")):null;
  case 27:return /\bplacebo\b/i.test(t.interventions)||
   (registry?.interventions||[]).some(x=>/\bplacebo\b/i.test(x.name))?
   doc("Placebo is named among registered interventions. The existence of an arm does NOT prove adequate power or treatment superiority."):null;
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
