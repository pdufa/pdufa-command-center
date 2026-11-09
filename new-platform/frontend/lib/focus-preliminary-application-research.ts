/** MAIN issue #979 — dated, source-linked Phase-3 preliminary application research.
 * These are VERSIONED, UNSIGNED RESEARCH LEANS, NOT released FDA predictions.
 * No historical accuracy, grade, model probability or CMC verification is claimed.
 */
import focus from "../data/p3PostDataActive.json";
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {getFullSpecialistCase} from "./medical-intelligence-specialist-all";

export const PRELIMINARY_AS_OF="2026-11-09" as const;
export const PRELIMINARY_METHOD="MAIN_FOCUS_29_23_APP_RESEARCH_V1" as const;
export type ResearchLean="APPROVAL_LEAN"|"CRL_LEAN"|"ABSTAIN"|"OBSERVED_APPROVAL";
export type ResearchEvidenceDirection="FAVORABLE_PIVOTAL_EFFICACY"|"MIXED_OR_UNRESOLVED"|"MATERIAL_REGULATORY_CONCERN"|"OBSERVED_REGULATORY_ACTION";
type Curated={support:number;risk:number;lean:ResearchLean;direction:ResearchEvidenceDirection};
/** Explicit editorial selection of *existing* source-linked observations, not a numeric rule. */
const CUTS:Record<string,Curated>={
 "abvx-uc":{support:2,risk:4,lean:"ABSTAIN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "achv-cytisinicline":{support:2,risk:6,lean:"ABSTAIN",direction:"MATERIAL_REGULATORY_CONCERN"},
 "apmd-ad109":{support:1,risk:5,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "axsm-axs12":{support:1,risk:5,lean:"ABSTAIN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "blte-stargardt":{support:1,risk:5,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "capr-deramiocel":{support:2,risk:1,lean:"CRL_LEAN",direction:"MATERIAL_REGULATORY_CONCERN"},
 "cldx-barzolvolimab":{support:1,risk:5,lean:"ABSTAIN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "cogt-gist":{support:2,risk:3,lean:"APPROVAL_LEAN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "cort-relacorilant":{support:3,risk:6,lean:"ABSTAIN",direction:"MATERIAL_REGULATORY_CONCERN"},
 "cytk-aficamten-ohcm":{support:1,risk:5,lean:"OBSERVED_APPROVAL",direction:"OBSERVED_REGULATORY_ACTION"},
 "cytk-aficamten-nhcm":{support:1,risk:4,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "imnm-desmoid":{support:1,risk:5,lean:"APPROVAL_LEAN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "mltx-sonelokimab":{support:2,risk:3,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "mlys-lorundrostat":{support:1,risk:4,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "phvs-ondemand":{support:1,risk:4,lean:"APPROVAL_LEAN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "phvs-prophylaxis":{support:1,risk:5,lean:"ABSTAIN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "prax-ulixacaltamide":{support:1,risk:4,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "srpt-casimersen":{support:2,risk:1,lean:"ABSTAIN",direction:"MATERIAL_REGULATORY_CONCERN"},
 "srpt-golodirsen":{support:3,risk:1,lean:"ABSTAIN",direction:"MATERIAL_REGULATORY_CONCERN"},
 "svra-molgramostim":{support:1,risk:2,lean:"APPROVAL_LEAN",direction:"FAVORABLE_PIVOTAL_EFFICACY"},
 "urgn-ugn103":{support:2,risk:4,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "vera-trutakna":{support:2,risk:5,lean:"ABSTAIN",direction:"MIXED_OR_UNRESOLVED"},
 "zbio-obexelimab":{support:2,risk:5,lean:"APPROVAL_LEAN",direction:"FAVORABLE_PIVOTAL_EFFICACY"}
};
const CURRENT_PRIMARY_SOURCE_CHECKED=new Set([
 "apmd-ad109","capr-deramiocel","cogt-gist","cytk-aficamten-ohcm",
 "imnm-desmoid","mltx-sonelokimab","prax-ulixacaltamide",
 "srpt-casimersen","srpt-golodirsen","svra-molgramostim"
]);
const CONFIRMED_APPROVAL_URL="https://www.fda.gov/drugs/drug-trials-snapshots/drug-trials-snapshots-myqorzo";
export const PRELIMINARY_SOURCE_CUTOFF="Only dated public evidence available on or before 2026-11-09, sourced from the existing Phase 3 dossiers" as const;
function cleanLink(url:string|null|undefined){
  return typeof url==="string"&&url.startsWith("https://")?url:null;
}
export function buildFocusApplicationPreliminaries(){
  if(focus.asOf!=="2026-11-08"||focus.records.length!==29||APPLICATION_CYCLES.length!==23||
     Object.keys(CUTS).length!==23)throw Error("FOCUS_CANONICAL_ROSTER_OR_CYCLE_COUNT_CHANGED");
  const ncts=focus.records.map(r=>r.nct);
  if(new Set(ncts).size!==29||
     APPLICATION_CYCLES.some(c=>!CUTS[c.id]||
       c.ncts.length===0||c.ncts.some(n=>!ncts.includes(n))||
       c.sourceDate>PRELIMINARY_AS_OF||
       (c.reportedGoal!==null&&c.reportedGoal<PRELIMINARY_AS_OF&&c.stage!=="APPROVED_ALREADY")))
       throw Error("INVALID_FOCUS_CYCLE_OR_SOURCE_CUTOFF");
  const linked=new Map(ncts.map(n=>[n,[] as string[]]));
  const applications=APPLICATION_CYCLES.map(c=>{
    const cut=CUTS[c.id];
    const caseFile=getFullSpecialistCase(c.id);
    if(!caseFile||caseFile.completedSpecialistSignoff!==false||caseFile.conclusion!=="PARTIAL_SOURCED_RESEARCH"||
       !Array.isArray(caseFile.dimensions)||caseFile.dimensions.length<7)
       throw Error("MISSING_UNREVIEWED_APPLICATION_DOSSIER");
    const support=caseFile.dimensions[cut.support],counter=caseFile.dimensions[cut.risk];
    if(!support||!counter||!support.observedClinicalEvidence||!counter.observedClinicalEvidence||
       !support.neededToResolve||!counter.neededToResolve)
       throw Error("MISSING_EXPLICIT_BENEFIT_RISK_EVIDENCE");
    if(c.stage==="APPROVED_ALREADY" !== (cut.lean==="OBSERVED_APPROVAL"))
       throw Error("OBSERVED_ACTION_IS_NOT_A_PREDICTION");
    if((cut.lean==="APPROVAL_LEAN"||cut.lean==="CRL_LEAN")&&
       !["UNDER_REVIEW","SUPPLEMENT_UNDER_REVIEW"].includes(c.stage))
       throw Error("UNFILED_APPLICATION_CANNOT_RECEIVE_EVIDENCE_OUTCOME_LEAN");
    for(const n of c.ncts)linked.get(n)!.push(c.id);
    const sponsor=c.sourceUrl;
    const observed=c.stage==="APPROVED_ALREADY";
    const sourceLinks=[
      {title:"Clinical evidence source",url:cleanLink(support.sourceUrl)||cleanLink(caseFile.source)||sponsor},
      {title:"Opposing evidence source",url:cleanLink(counter.sourceUrl)||cleanLink(caseFile.source)||sponsor},
      {title:"Application status source",url:sponsor},
      ...(observed?[{title:"FDA observed approval",url:CONFIRMED_APPROVAL_URL}]:[])
    ];
    return {
      id:c.id,ticker:c.ticker,drug:c.drug,indication:c.indication,
      ncts:[...c.ncts],applicationType:c.applicationType,
      sourceDate:c.sourceDate,
      originalStage:c.stage,reportedGoal:c.reportedGoal,
      goalEvidence:"SPONSOR_OR_ISSUER_REPORTED_NEEDS_LIVE_RECONFIRMATION",
      sourceRecheckedOn:CURRENT_PRIMARY_SOURCE_CHECKED.has(c.id)?PRELIMINARY_AS_OF:null,
      exactFdaDecisionCycleIndependentlyCertified:false,
      clinicalEvidence:{topic:support.topic,observation:support.observedClinicalEvidence,
        clinicalInterpretation:support.specialistInterpretation,
        stillNeeded:support.neededToResolve},
      opposingEvidence:{topic:counter.topic,observation:counter.observedClinicalEvidence,
        clinicalInterpretation:counter.specialistInterpretation,
        stillNeeded:counter.neededToResolve},
      regulatoryRisk:c.criticalQuestion,
      sourceLinks,
      preliminaryResearchLean:cut.lean,
      preliminaryEvidenceDirection:cut.direction,
      leanConfidence:"HIGH_UNQUANTIFIED_UNCERTAINTY",
      releasedRegulatoryPrediction:observed?"NOT_APPLICABLE_ALREADY_OBSERVED":"ABSTAIN",
      observedAction:observed?"FDA_APPROVED_2025_12_19":null,
      observedFormalReviewExtension:["capr-deramiocel","svra-molgramostim"].includes(c.id),
      reviewDelayOrExtensionPrediction:observed?"NOT_APPLICABLE_ALREADY_OBSERVED":"ABSTAIN",
      reviewTimingStatus:["capr-deramiocel","svra-molgramostim"].includes(c.id)?
        "PRIOR_FORMAL_EXTENSION_DOCUMENTED_NOT_FUTURE_FORECAST":"UNKNOWN_NO_VALIDATED_TIMING_FORECAST",
      uncertaintyReasons:[
        support.neededToResolve,counter.neededToResolve,c.criticalQuestion,
        "Independent original-source/phase/safety/CMC review and prospective calibration not completed."
      ],
      qualifiedReviewerSignoff:false,
      numericalFDAProbability:null,
      calibratedAccuracy:null,
      evidenceCutoff:PRELIMINARY_AS_OF,
      methodVersion:PRELIMINARY_METHOD
    };
  });
  if([...linked.values()].some(ids=>ids.length===0)||
     applications.filter(a=>a.preliminaryResearchLean==="OBSERVED_APPROVAL").length!==1)
     throw Error("FOCUS_NCT_APPLICATION_CROSSWALK_INCOMPLETE");
  const trials=focus.records.map(r=>({
    ticker:r.ticker,nct:r.nct,company:r.company,recordedReleaseDate:r.recordedReleaseDate,
    recordedFdaStatus:r.fdaStatus,
    regulatorySource:r.regulatoryUrl,
    registrySource:"https://clinicaltrials.gov/study/"+r.nct,
    applicationCycleIds:[...linked.get(r.nct)!],
    trialIndependentClinicalReview:false,
    FDAForecast:"ABSTAIN" as const
  }));
  const researchCalls=applications.reduce((a,c)=>{a[c.preliminaryResearchLean]=(a[c.preliminaryResearchLean]||0)+1;return a;},
     {} as Record<ResearchLean,number>);
  return {
    schema:PRELIMINARY_METHOD,asOf:PRELIMINARY_AS_OF,
    scope:"29 exact NCT trial rows mapped to 23 provisional FDA application cycles",
    status:"DATED_SOURCE_BASED_RESEARCH_ONLY_NO_VALIDATED_FORECAST",
    trials,applications,summary:{
      ncts:trials.length,applicationCycles:applications.length,
      sourceBasedPreliminaryResearchProfiles:applications.length,
      researchLeanApprovals:researchCalls.APPROVAL_LEAN??0,
      researchLeanCrls:researchCalls.CRL_LEAN??0,
      abstainResearchCalls:researchCalls.ABSTAIN??0,
      observedPastApprovals:researchCalls.OBSERVED_APPROVAL??0,
      qualifiedIndependentClinicalReviews:0,
      independentlyValidatedFDAForecasts:0,
      verifiedHistoricalBacktests:0,
      numericalPredictionsReleased:0
    },
    releaseStatus:"ALL_FUTURE_APPLICATION_APPROVAL_CRL_AND_REVIEW_DELAY_FORECASTS_ABSTAIN",
    sourceLimitations:PRELIMINARY_SOURCE_CUTOFF
  };
}
export const FOCUS_PRELIMINARY_R39=buildFocusApplicationPreliminaries();
