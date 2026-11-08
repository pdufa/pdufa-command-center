/**
 * Phase-consistent Deep Clinical Subspecialty Intelligence contract.
 * The same ten disease-specialist clinical reasoning axes apply at every phase,
 * with phase-appropriate depth and evidence gates. No axis is "passed" because
 * later-stage evidence does not exist yet. No clinical credentials are implied.
 */
import {
  CLINICAL_SPECIALTY_AXES,
  CLINICAL_SPECIALTY_PROFILES,
  type ClinicalSpecialtyProfile,
} from "./medical-intelligence-specialty";
import type {TrialPhase,TestGrade} from "./medical-intelligence-assessment-rankings";
import {PHASE_RISK_WATCHLIST,type PhaseRiskPrompt} from "./medical-intelligence-phase-snapshot";

export type SpecialtyPhaseAxis = {
  axis:number;
  name:string;
  universalQuestion:string;
  phaseQuestion:string;
  conditionSpecificChallenge:string;
  evidenceStandard:string;
  expectation:"CURRENT_PHASE"|"FORWARD_LOOKING";
  status:"NOT_CLINICALLY_ADJUDICATED";
};
export type SpecialtyAxisReview = {
  nct:string;
  profileId:string;
  phase:TrialPhase;
  axis:number;
  status:"REVIEWED"|"NOT_APPLICABLE";
  grade?:TestGrade;
  finding:string;
  counterEvidence:string;
  unresolvedRisk:string;
  verifiedSourceUrls:readonly string[];
  reviewedOn:string;
};
export type SpecialtyPhaseScore={
  phase:TrialPhase;
  provisionalScore:number|null;
  finalizedScore:number|null;
  reviewedRequiredAxes:number;
  requiredAxes:number;
  unratedRequiredAxes:number;
  status:"NOT_REVIEWED"|"PARTIAL"|"COMPLETE"|"PHASE_UNKNOWN";
};
export type SpecialtyPhasePlan = {
  nct:string;
  phase:TrialPhase;
  profile:ClinicalSpecialtyProfile;
  axes:SpecialtyPhaseAxis[];
  riskQuestions:readonly PhaseRiskPrompt[];
  score:SpecialtyPhaseScore;
  clinicalSignoff:false;
  outcomeProbability:null;
};

/** Each row corresponds to the SAME ten universal specialty axes, in identical order. */
const PHASE_LENS:Record<TrialPhase,readonly string[]>={
  EARLY_PHASE1:[
    "Check source-verified initial diagnosis, enrolled disease phenotype and sentinel cohort context",
    "Assess first-human target engagement and disease-model relevance, where measured",
    "Define existing care options and what an experimental intervention might replace",
    "Identify clinically meaningful outcomes for later tests; do not demand pivotal efficacy",
    "Identify patient subtypes vulnerable to dosing and first-in-human uncertainty",
    "Assess early signals without claiming a clinically established duration of benefit",
    "Examine dose-limiting toxicity, sentinel safety monitoring and escalation rules",
    "Challenge whether biomarkers or uncontrolled changes have alternative explanations",
    "Formulate the strongest specialty-specific safety or biological counterhypothesis",
    "Identify potential development-pathway uncertainties without assuming an NDA/BLA filing",
  ],
  PHASE1:[
    "Verify clinical phenotype and inclusion/exclusion risk in treated cohorts",
    "Assess observed PK/PD and target engagement against disease-specific biological predictions",
    "Consider standard care interactions, rescue therapies and ethical comparator pathways",
    "Check whether patient-important outcome instruments are valid for future proof of benefit",
    "Inspect dose-related risks, phenotype subgroups and populations not yet studied",
    "Rate early response or exposure-response only when measured; no Phase 3 efficacy requirement",
    "Review DLTs, SAEs, discontinuations, organ toxicity and monitoring burden",
    "Challenge uncontrolled efficacy claims, dose-escalation selection and biomarker surrogacy",
    "Test the strongest specialist alternative to the sponsor's dose and safety interpretation",
    "Identify end-of-Phase-1 evidence gaps and Phase 2 readiness, not FDA approval readiness",
  ],
  PHASE2:[
    "Check disease phenotype, representative enrollment and relevant misdiagnoses",
    "Compare biological target engagement to observed clinical endpoints at selected doses",
    "Assess planned place in therapy, comparator relevance and feasible Phase 3 treatment setting",
    "Evaluate preliminary endpoints for clinical validity and patient-important benefit",
    "Examine responder heterogeneity, dose selection and possible subgroup overinterpretation",
    "Scrutinize preliminary effect sizes, uncertainty, durability and dose-response",
    "Review serious events, exposure-adjusted safety and duration of treatment",
    "Challenge missingness, multiplicity, randomization or control-group alternatives",
    "Develop a skeptical specialty critique of claimed efficacy and proposed pivotal design",
    "Judge Phase 3 readiness and FDA alignment signals, not an assumed filing decision",
  ],
  PHASE3:[
    "Verify exact indication and clinical phenotype in pivotal populations",
    "Confirm mechanism-to-outcome consistency and clinically relevant response",
    "Compare proposed standard-of-care position and active comparator relevance",
    "Inspect prespecified primary outcomes, patient importance and endpoint validity",
    "Evaluate representativeness, subgroup interactions and site variation",
    "Test prespecified effect magnitude, multiplicity, confidence intervals and durability when reported",
    "Integrate SAEs, withdrawals, exposure, mortality and major risk tradeoffs",
    "Challenge post-hoc changes, missing data, selective reporting and alternative estimands",
    "Construct an independent specialty rebuttal of pivotal efficacy and safety claims",
    "Translate confirmed evidence gaps to regulatory readiness, label and CMC questions as appropriate",
  ],
  PHASE4:[
    "Verify real-world disease phenotype, diagnostic practice and treated population",
    "Evaluate whether biological effects remain consistent under routine treatment conditions",
    "Assess place in therapy against evolving treatments, guidelines and adherence patterns",
    "Check real-world patient-important outcomes and effectiveness",
    "Assess generalizability, demographic and rare/underrepresented subpopulations",
    "Investigate benefit durability, comparative effectiveness and loss of response",
    "Investigate rare, long-latency, cumulative or drug-interaction harms",
    "Challenge confounding, exposure bias, nonadherence and real-world selection effects",
    "Generate skeptical specialist interpretations of postapproval safety/benefit claims",
    "Assess postmarketing obligations, confirmatory studies, labeling updates and risk controls",
  ],
  UNKNOWN:[
    "Verify registered phase and disease diagnosis before clinical claims",
    "Collect candidate mechanism without claiming trial phase readiness",
    "Identify existing clinical practice context while phase is unverified",
    "Identify potential patient-important outcomes without inferring measured efficacy",
    "Identify relevant phenotype and safety subgroup questions",
    "Withhold phase-dependent magnitude/durability conclusions until stage confirmed",
    "Identify potential safety surveillance sources without asserting observed harms",
    "Separate unverified claims from source-reconciled clinical findings",
    "Request a verified stage before issuing a specialty conclusion",
    "Do not infer filing, FDA outcomes or development readiness until phase confirmed",
  ],
};
const FORWARD:Partial<Record<TrialPhase,readonly number[]>>={
  EARLY_PHASE1:[4,6,10],
  PHASE1:[6,10],
  PHASE2:[10],
  UNKNOWN:[1,2,3,4,5,6,7,8,9,10],
};

function validDay(v:string):boolean{
  if(!/^\d{4}-\d{2}-\d{2}$/.test(v))return false;
  const d=new Date(v+"T00:00:00Z");
  return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===v;
}
const evidenceByAxis=(p:ClinicalSpecialtyProfile):readonly string[]=>[
  p.clinicalContext,
  p.mechanism,
  p.clinicalContext+"; current treatment standards and comparative indications",
  p.meaningfulOutcomes,
  p.subgroups,
  "Dated exact-NCT protocol, relevant dose/efficacy results and effect sizes when available",
  p.seriousRisks+"; adverse event denominators and dose/exposure context",
  "Original trial methodology, controls, competing explanations and contradictory data",
  p.coreChallenge+"; source-linked opposition and contradictory results",
  "Phase-specific regulatory correspondence, applicable FDA guidance and exact indication context",
];

export function buildAllPhaseSubspecialtyReview(
  nct:string,phase:TrialPhase,profileId:string,
  reviews:readonly SpecialtyAxisReview[]=[],
):SpecialtyPhasePlan|null{
  if(!/^NCT\d{8}$/.test(nct))throw Error("Exact NCT identifier required");
  if(!Object.hasOwn(PHASE_LENS,phase))throw Error("Unrecognized clinical phase");
  const p=CLINICAL_SPECIALTY_PROFILES.find(x=>x.id===profileId);
  if(!p)return null; // Never guess an indication's correct clinical subspecialty.
  const phrases=PHASE_LENS[phase];
  if(phrases.length!==CLINICAL_SPECIALTY_AXES.length||CLINICAL_SPECIALTY_AXES.length!==10)
    throw Error("Ten consistent specialty axes required across all phases");
  const evidence=evidenceByAxis(p);
  const future=new Set(FORWARD[phase]??[]);
  const axes:SpecialtyPhaseAxis[]=CLINICAL_SPECIALTY_AXES.map((a,i)=>({
    axis:a.id,name:a.name,universalQuestion:a.clinicalQuestion,
    phaseQuestion:phrases[i],conditionSpecificChallenge:p.coreChallenge,
    evidenceStandard:evidence[i],
    expectation:future.has(a.id)?"FORWARD_LOOKING":"CURRENT_PHASE",
    status:"NOT_CLINICALLY_ADJUDICATED"
  }));
  const seen=new Set<number>();
  for(const r of reviews){
    if(r.nct!==nct||r.profileId!==profileId||r.phase!==phase||
       !Number.isInteger(r.axis)||r.axis<1||r.axis>10||seen.has(r.axis))
      throw Error("Specialty review identity, phase, clinical axis or uniqueness mismatch");
    seen.add(r.axis);
    if(!validDay(r.reviewedOn)||!r.finding.trim()||!r.counterEvidence.trim()||
       !r.unresolvedRisk.trim())
      throw Error("Specialist-style assessment requires dated analysis, countercase and unresolved risk");
    if(r.status==="REVIEWED"){
      if(phase==="UNKNOWN"||typeof r.grade!=="number"||
         !Number.isInteger(r.grade)||r.grade<0||r.grade>5)
        throw Error("Verified phase and evidence-backed 0-5 grade required");
      if(!r.verifiedSourceUrls.length||!r.verifiedSourceUrls.every(url=>/^https:\/\/[^/]+/.test(url)))
        throw Error("A graded clinical axis needs original source citations");
      if(future.has(r.axis))
        throw Error("Forward-looking axes cannot earn a score for not-yet-due results");
    }else if(r.status==="NOT_APPLICABLE"){
      if(r.grade!==undefined)throw Error("Not applicable axes cannot be scored");
    }else throw Error("Unknown specialist-axis disposition");
  }
  const required=axes.filter(x=>x.expectation==="CURRENT_PHASE");
  const scored=reviews.filter(x=>x.status==="REVIEWED" && !future.has(x.axis));
  const excluded=reviews.filter(x=>x.status==="NOT_APPLICABLE" && !future.has(x.axis));
  const denominator=required.length-excluded.length;
  const reviewed=scored.length;
  const average=reviewed?Math.round(scored.reduce((sum,r)=>sum+Number(r.grade),0)/reviewed*200)/10:null;
  const complete=denominator>0&&reviewed===denominator;
  const status:SpecialtyPhaseScore["status"]=phase==="UNKNOWN"?"PHASE_UNKNOWN":
    complete?"COMPLETE":reviewed?"PARTIAL":"NOT_REVIEWED";
  return {
    nct,phase,profile:p,axes,riskQuestions:PHASE_RISK_WATCHLIST[phase],
    score:{phase,provisionalScore:average,finalizedScore:complete?average:null,
      reviewedRequiredAxes:reviewed,requiredAxes:denominator,
      unratedRequiredAxes:denominator-reviewed,status},
    clinicalSignoff:false,outcomeProbability:null
  };
}
