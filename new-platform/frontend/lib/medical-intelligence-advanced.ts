/**
 * Independent FDA failure-first analysis workbench (advanced levels 1–12).
 * This is an evidence-index and research workflow, NOT a validated prediction model.
 * Every level is defined for every application, adapts to phase/indication and
 * disclosure availability, and exposes gaps without treating missing data as safety.
 * RAAS/surveys are neither read nor imported.
 */
import {APPLICATION_CYCLES,type ApplicationCycle} from "./medical-intelligence-applications";
import focus from "../data/p3PostDataActive.json";
import {REVIEWED_FINDINGS,type ReviewedFinding} from "./medical-intelligence-reviewed-findings";
import {deskIssuesForCycle,type ReviewIssue} from "./medical-intelligence-failure-desk";
import {adjudicationForCycle,type AdjudicationClaim} from "./medical-intelligence-clinical-adjudication";
import {getFullSpecialistCase} from "./medical-intelligence-specialist-all";

export type AdvancedLevelId =
  | "CRL_HISTORY" | "MULTIDISCIPLINARY_REVIEW" | "STATISTICAL_FORENSICS"
  | "MANUFACTURING_CMC" | "REGULATORY_PRECEDENT" | "CLINICAL_BENEFIT_RISK"
  | "TRIAL_INTEGRITY" | "SCIENTIFIC_CONTRADICTIONS"
  | "FDA_COMMUNICATIONS" | "REGULATORY_PATHWAY"
  | "REVIEW_DELAY" | "BACKTEST_CALIBRATION";

export type AdvancedLevelDefinition={
  id:AdvancedLevelId;number:number;title:string;failureQuestion:string;
  requiredEvidence:readonly string[];
};
export const ADVANCED_LEVELS:readonly AdvancedLevelDefinition[]=[
  {id:"CRL_HISTORY",number:1,title:"Historical FDA CRL intelligence",
    failureQuestion:"Which earlier FDA-identified deficiencies could remain relevant to the exact current review cycle?",
    requiredEvidence:["FDA original action letter and cited deficiencies","Evidence of corrective action and FDA response","Date and exact application-cycle linkage"]},
  {id:"MULTIDISCIPLINARY_REVIEW",number:2,title:"FDA-style multidisciplinary reviewer analysis",
    failureQuestion:"Would statistical, clinical, safety, pharmacology and quality reviewers reach conflicting risk conclusions?",
    requiredEvidence:["Discipline-specific FDA review documents when public","Medical/pharmacology/toxicology and biostatistics assessments","Integrated reviewer disagreements and disposition"]},
  {id:"STATISTICAL_FORENSICS",number:3,title:"Advanced statistical forensic analysis",
    failureQuestion:"Do prespecified estimands, multiplicity, missing data and sensitivity analyses support the proposed claim?",
    requiredEvidence:["Dated protocol, SAP and amendments","Exact denominators, endpoints, confidence intervals and p-values","Prespecified and post-hoc analyses clearly separated"]},
  {id:"MANUFACTURING_CMC",number:4,title:"Manufacturing and CMC risk investigation",
    failureQuestion:"Could process validation, facility inspection, comparability or supply deficiencies block approval?",
    requiredEvidence:["Facility and manufacturer identification","CMC validation/comparability evidence","Inspection observations, responses and FDA clearance status"]},
  {id:"REGULATORY_PRECEDENT",number:5,title:"Regulatory precedent matching",
    failureQuestion:"Does a truly comparable FDA application, indication, pathway and evidence package support the claimed precedent?",
    requiredEvidence:["Original FDA decision/action package","Matched indication, modality, endpoint and population","Documented similarities, differences and time-specific policy"]},
  {id:"CLINICAL_BENEFIT_RISK",number:6,title:"Clinical benefit-risk evaluation",
    failureQuestion:"Are patient-important benefits meaningful relative to serious harms, comparators and durability?",
    requiredEvidence:["Integrated clinical efficacy across relevant trials","Serious adverse events, exposures and treatment discontinuations","Disease-specific benefit, subgroup and durability analysis"]},
  {id:"TRIAL_INTEGRITY",number:7,title:"Trial design and data integrity analysis",
    failureQuestion:"Could design bias, protocol deviation, unblinding, missingness or inspection issues invalidate conclusions?",
    requiredEvidence:["Original protocol and randomization/blinding plan","Full deviations, missing-data mechanisms and quality checks","Site/BIMO findings and any documented resolution"]},
  {id:"SCIENTIFIC_CONTRADICTIONS",number:8,title:"Scientific contradiction detection",
    failureQuestion:"Which material endpoint, study, source or FDA-versus-sponsor disagreements remain unresolved?",
    requiredEvidence:["Opposing results for the same estimand/population","Source-level analysis provenance and chronology","Reconciliation or justified unresolved contradiction"]},
  {id:"FDA_COMMUNICATIONS",number:9,title:"FDA communications and regulatory feedback analysis",
    failureQuestion:"Do formal FDA communications identify current objections, required studies or outstanding responses?",
    requiredEvidence:["Original FDA correspondence where disclosed","Meeting minutes and exact speaker attribution","Current-cycle response and unresolved feedback"]},
  {id:"REGULATORY_PATHWAY",number:10,title:"Drug-specific regulatory pathway analysis",
    failureQuestion:"Is the exact NDA/BLA/supplement, indication and expedited pathway eligible for the requested action?",
    requiredEvidence:["Application identity and source-reported filing stage","Original FDA designation and pathway confirmation","Indication, biologic/small molecule and supplement distinctions"]},
  {id:"REVIEW_DELAY",number:11,title:"PDUFA delay and review-extension forecasting",
    failureQuestion:"Has FDA announced a clock change, or is there current-cycle evidence of a material review-timing blocker?",
    requiredEvidence:["Current-cycle FDA goal and filing/acceptance letter","Major-amendment, inspection or advisory-calendar evidence","Formal current-cycle extension notice, if any"]},
  {id:"BACKTEST_CALIBRATION",number:12,title:"Historical prediction backtesting and calibration",
    failureQuestion:"Do dated, locked, out-of-sample predictions discriminate correctly and remain calibrated over time?",
    requiredEvidence:["As-of historical feature snapshots without future leakage","Independent dated FDA approval/CRL and extension outcomes","Temporal holdout, Brier scores, sample sizes and calibration by outcome"]}
] as const;

export type SourceRecord={
  id:string;title:string;url:string;date:string;
  sourceClass:"FDA_PRIMARY"|"SEC_SPONSOR"|"SPONSOR"|"PEER_REVIEWED"|"CONFERENCE"|"OTHER";
  scope:"EXACT_NCT"|"RELATED_EXTERNAL_TRIAL"|"APPLICATION_CONTEXT";
  observation:string;limitations:string;
};
export type PhaseContext={
  nct:string;
  verifiedPhase:"EARLY_PHASE1"|"PHASE1"|"PHASE2"|"PHASE3"|"PHASE4"|"UNKNOWN";
  sourceUrl?:string;
  verifiedAt?:string;
};
export type AdvancedLevelAssessment=AdvancedLevelDefinition & {
  state:"SOURCE_LEADS_REQUIRE_ADJUDICATION"|"EVIDENCE_GAP"|"NOT_CURRENT_REVIEW";
  sources:SourceRecord[];
  missing:string[];
  explanation:string;
  relevantNcts:readonly string[];
};
export type OutcomePrediction={
  outcome:"APPROVAL"|"CRL"|"REVIEW_DELAY";
  status:"ABSTAIN"|"NOT_APPLICABLE_PREVIOUSLY_APPROVED";
  probability:null;
  reasoning:string;
  supportingEvidence:SourceRecord[];
  missingEvidence:string[];
};
export type CertaintyAssessment={
  status:"NOT_VALIDATED";rating:null;calibrationDatasetSize:0;
  explanation:string;
};
export type AdvancedAssessment={
  cycle:ApplicationCycle;
  phase:PhaseContext[];
  levels:AdvancedLevelAssessment[];
  predictions:OutcomePrediction[];
  certainty:CertaintyAssessment;
  sourceLeadLevelCount:number;
  completedIndependentReviews:0;
  snapshotDate:"2026-11-07";
  automaticEvidenceMonitoring:"NOT_ENABLED_IN_STATIC_SOURCE_SNAPSHOT";
};
function sourceClassOfFinding(f:ReviewedFinding):SourceRecord["sourceClass"]{
  return f.evidence==="FDA_PRIMARY"?"FDA_PRIMARY":
    f.evidence==="SEC_COMPANY_DISCLOSURE"?"SEC_SPONSOR":
    f.evidence==="SPONSOR_RELEASE"?"SPONSOR":"PEER_REVIEWED";
}
function claimSourceClass(type:AdjudicationClaim["type"]):SourceRecord["sourceClass"]{
  if(type.startsWith("FDA_"))return "FDA_PRIMARY";
  if(type==="SEC_SPONSOR_FILING")return "SEC_SPONSOR";
  if(type==="PEER_REVIEWED_TRIAL")return "PEER_REVIEWED";
  if(type==="CONFERENCE_ABSTRACT")return "CONFERENCE";
  return "SPONSOR";
}
function selectEvidence(cycle:ApplicationCycle, level:AdvancedLevelId):SourceRecord[]{
  const cases=adjudicationForCycle(cycle.id);
  const issues=deskIssuesForCycle(cycle.id);
  const linked=REVIEWED_FINDINGS.filter(f=>f.relatedNcts.some(n=>cycle.ncts.includes(n)));
  const sources:SourceRecord[]=[];
  const relevantFinding=(f:ReviewedFinding)=>{
    switch(level){
      case "CRL_HISTORY":return f.type==="PREVIOUS_CRL";
      case "MULTIDISCIPLINARY_REVIEW":return f.type==="REGULATORY_OBJECTION";
      case "STATISTICAL_FORENSICS":return /statistic|efficacy|endpoint|data/i.test(f.domain+" "+f.headline);
      case "MANUFACTURING_CMC":return /cmc|manufactur|inspection|quality|integrity/i.test(f.domain+" "+f.headline);
      case "REGULATORY_PRECEDENT":return f.type==="PREVIOUS_CRL"||f.type==="REVIEW_STATUS";
      case "CLINICAL_BENEFIT_RISK":return f.type==="EFFICACY_EVIDENCE"||f.type==="SCIENTIFIC_UNCERTAINTY";
      case "TRIAL_INTEGRITY":return f.type==="INSPECTION_OBSERVATION"||/trial design|missing data|protocol|integrity/i.test(f.domain+" "+f.headline);
      case "SCIENTIFIC_CONTRADICTIONS":return f.type==="REGULATORY_OBJECTION"||f.type==="SCIENTIFIC_UNCERTAINTY";
      case "FDA_COMMUNICATIONS":return f.type==="REGULATORY_OBJECTION"||f.type==="REVIEW_STATUS";
      case "REGULATORY_PATHWAY":return f.type==="REVIEW_STATUS";
      case "REVIEW_DELAY":return f.type==="EXTENSION_CONFIRMED";
      case "BACKTEST_CALIBRATION":return false;
    }
  };
  for(const f of linked.filter(relevantFinding)){
    sources.push({id:"finding:"+f.id,title:f.headline,url:f.sourceUrl,date:f.published,
      sourceClass:sourceClassOfFinding(f),scope:"APPLICATION_CONTEXT",
      observation:f.detail,limitations:f.remainingQuestion});
  }
  const relevantClaim=(c:AdjudicationClaim)=>{
    switch(level){
      case "CRL_HISTORY":return c.type==="FDA_ACTION_LETTER";
      case "MULTIDISCIPLINARY_REVIEW":return c.type==="FDA_REVIEWER"||c.type==="FDA_DOCUMENTED_APPLICANT_ANALYSIS";
      case "STATISTICAL_FORENSICS":return /statistic|p.value|confidence|estimand|sensitivity|model|primary|CI\b/i.test(c.section+" "+c.measure+" "+c.limits);
      case "MANUFACTURING_CMC":return /manufactur|facility|CMC|CGMP|inspection|validation/i.test(c.section+" "+c.measure+" "+c.result);
      case "REGULATORY_PRECEDENT":return c.type==="FDA_PUBLIC_APPROVAL"||c.type==="FDA_ACTION_LETTER";
      case "CLINICAL_BENEFIT_RISK":return c.role==="FAVORABLE"||c.role==="CHALLENGING";
      case "TRIAL_INTEGRITY":return /BIMO|missing data|unblinding|inspection|protocol|randomiz|deviation|amendment/i.test(c.section+" "+c.result+" "+c.limits);
      case "SCIENTIFIC_CONTRADICTIONS":return c.role!=="CONTEXT"&&/disagree|conflict|non.significant|different|alternative|versus|contradict|p=0\.0/i.test(c.result+" "+c.limits);
      case "FDA_COMMUNICATIONS":return c.type==="SPONSOR_REPORT_OF_FDA_COMMUNICATION"||c.type==="FDA_REVIEWER"||c.type==="FDA_ACTION_LETTER";
      case "REGULATORY_PATHWAY":return c.type==="FDA_PUBLIC_APPROVAL"||c.type==="SPONSOR_STATUS"||c.type==="FDA_ACTION_LETTER";
      case "REVIEW_DELAY":return /extension|clock|goal date|major amendment|review timing/i.test(c.section+" "+c.result);
      case "BACKTEST_CALIBRATION":return false;
    }
  };
  for(const dossier of cases)for(const c of dossier.sources.filter(relevantClaim)){
    sources.push({id:"claim:"+c.id,title:c.title,url:c.url,date:c.date,
      sourceClass:claimSourceClass(c.type),
      scope:c.scope==="RELATED_EXTERNAL_TRIAL"?"RELATED_EXTERNAL_TRIAL":cycle.ncts.includes(c.trial)?"EXACT_NCT":"APPLICATION_CONTEXT",
      observation:c.result,limitations:c.limits});
  }
  const relevantIssue=(issue:ReviewIssue)=>{
    switch(level){
      case "CRL_HISTORY":return issue.evidenceClass==="PREVIOUS_CRL";
      case "MULTIDISCIPLINARY_REVIEW":return issue.evidenceClass==="FDA_REVIEWER_OBJECTION";
      case "STATISTICAL_FORENSICS":return /statistic|analysis|endpoint|imputation|SAP|estimand/i.test(issue.title+" "+issue.observation);
      case "MANUFACTURING_CMC":return /manufactur|CMC|facility|inspection|CGMP/i.test(issue.title+" "+issue.observation);
      case "REGULATORY_PRECEDENT":return issue.evidenceClass==="PREVIOUS_CRL";
      case "CLINICAL_BENEFIT_RISK":return issue.evidenceClass==="TRIAL_SIGNAL";
      case "TRIAL_INTEGRITY":return /BIMO|inspection|integrity|protocol/i.test(issue.title+" "+issue.observation);
      case "SCIENTIFIC_CONTRADICTIONS":return issue.resolutionState==="OPEN_EVIDENCE_DISPUTE";
      case "FDA_COMMUNICATIONS":return issue.evidenceClass==="FDA_REVIEWER_OBJECTION"||issue.evidenceClass==="PREVIOUS_CRL";
      case "REGULATORY_PATHWAY":return issue.evidenceClass==="REVIEW_GAP";
      case "REVIEW_DELAY":return issue.evidenceClass==="PRIOR_EXTENSION";
      case "BACKTEST_CALIBRATION":return false;
    }
  };
  for(const issue of issues.filter(relevantIssue)){
    sources.push({id:"issue:"+issue.id,title:issue.title,url:issue.sourceUrl,date:issue.sourceDate,
      sourceClass:issue.sourceType==="FDA"?"FDA_PRIMARY":issue.sourceType==="SEC_SPONSOR"?"SEC_SPONSOR":"SPONSOR",
      scope:"APPLICATION_CONTEXT",observation:issue.observation,
      limitations:issue.decisiveFollowUp});
  }
  if(level==="REGULATORY_PATHWAY"&&cycle.stage!=="NOT_RECONCILED"){
    sources.push({id:"cycle:"+cycle.id,title:"Dated application identity and filing status",url:cycle.sourceUrl,
      date:cycle.sourceDate,
      sourceClass:"SPONSOR",scope:"APPLICATION_CONTEXT",
      observation:cycle.applicationType+"; "+cycle.stage+"; indication: "+cycle.indication,
      limitations:"Source-reconstructed application status; independently confirm the original FDA acceptance, pathway and review goal."});
  }
  const unique=new Map<string,SourceRecord>();
  for(const s of sources){
    if(/^https:\/\//.test(s.url)&&/^20\d\d-\d\d-\d\d$/.test(s.date)&&s.date<="2026-11-07")unique.set(s.id,s);
  }
  return [...unique.values()];
}
/**
 * Reuse the same 12-level architecture if a future qualifying FOCUS NCT has
 * not yet been mapped to an FDA application. This is NOT a guessed submission.
 */
export function listAdvancedCandidates():ApplicationCycle[]{
  const mapped=new Set(APPLICATION_CYCLES.flatMap(a=>a.ncts));
  const unmapped=focus.records.filter(r=>/^NCT\d{8}$/.test(r.nct)&&!mapped.has(r.nct))
    .map(r=>({
      id:"focus-unmapped-"+r.nct,ticker:r.ticker,drug:"NOT VERIFIED",
      indication:"NOT VERIFIED",ncts:[r.nct],applicationType:"UNCONFIRMED",
      stage:"NOT_RECONCILED" as const,reportedGoal:null,sourceDate:focus.asOf,
      sourceUrl:"https://clinicaltrials.gov/study/"+r.nct,
      criticalQuestion:"Verify the drug, indication, regulatory application identity, phase and original FDA documentation before making any filing or approval prediction."
    }));
  return [...APPLICATION_CYCLES,...unmapped];
}
export function buildAdvancedAssessment(cycleId:string,phases:readonly PhaseContext[]=[]):AdvancedAssessment|null{
  const cycle=listAdvancedCandidates().find(a=>a.id===cycleId);
  if(!cycle)return null;
  const known=phases.filter(p=>cycle.ncts.includes(p.nct)&&
    /^NCT\d{8}$/.test(p.nct)&&p.verifiedPhase!=="UNKNOWN");
  const phase=cycle.ncts.map(nct=>known.find(p=>p.nct===nct)||
    ({nct,verifiedPhase:"UNKNOWN" as const}));
  const levels=ADVANCED_LEVELS.map(def=>{
    const sources=selectEvidence(cycle,def.id);
    const isApproved=cycle.stage==="APPROVED_ALREADY";
    const notCurrentReview=isApproved&&(def.id==="REVIEW_DELAY"||def.id==="FDA_COMMUNICATIONS");
    const early=phase.length>0&&phase.every(p=>
      ["EARLY_PHASE1","PHASE1","PHASE2"].includes(p.verifiedPhase));
    const missing=[...def.requiredEvidence];
    if(phase.some(p=>p.verifiedPhase==="UNKNOWN"))
      missing.unshift("Verify registry phase from the exact NCT; do not require Phase 3 results from an early-phase trial.");
    if(early&&(def.id==="STATISTICAL_FORENSICS"||def.id==="CLINICAL_BENEFIT_RISK"))
      missing.push("Current phase is early; later-phase pivotal or integrated data are not yet due and must not be treated as a deficiency.");
    if(def.id==="MANUFACTURING_CMC"&&cycle.applicationType.toUpperCase().includes("BLA"))
      missing.push("Biologic-specific potency, process comparability, analytical methods, stability and viral/adventitious-agent controls where relevant.");
    if(def.id==="MANUFACTURING_CMC"&&cycle.applicationType.toUpperCase().includes("NDA"))
      missing.push("Drug-product process validation, impurity/degradation controls, stability and commercial manufacturing readiness.");
    if(def.id==="REGULATORY_PATHWAY"&&/SUPPLEMENT/.test(cycle.stage))
      missing.push("Identify the previously approved indication and exact supplement scope; do not relabel a supplement as an original NDA/BLA.");
    const specialist=getFullSpecialistCase(cycle.id);
    if(def.id==="CLINICAL_BENEFIT_RISK"&&specialist)
      missing.push(specialist.specialty+": "+specialist.medicalQuestion+" (no independent medical signoff)");
    if(cycle.stage==="NOT_RECONCILED"&&def.id==="REGULATORY_PATHWAY")
      missing.unshift("No source-reconciled FDA application identity or filing status exists for this FOCUS NCT.");
    if(def.id==="BACKTEST_CALIBRATION")
      missing.push("No approved historical out-of-sample calibration cohort is installed; numerical probabilities are disabled.");
    return {...def,sources,missing,relevantNcts:cycle.ncts,
      state:notCurrentReview?"NOT_CURRENT_REVIEW" as const:
        sources.length?"SOURCE_LEADS_REQUIRE_ADJUDICATION" as const:"EVIDENCE_GAP" as const,
      explanation:notCurrentReview?
        "Already-approved indication: historical evidence remains relevant but a new pending review cannot be invented.":
        sources.length?
        "Source pointers identified. Each still requires adversarial, source-by-source review and exact FDA-cycle reconciliation; this level is not complete.":
        "No qualifying original-source item in the dated curated snapshot. This is a research gap, not proof that the risk is absent."
    };
  });
  const used=(ids:AdvancedLevelId[])=>levels.filter(l=>ids.includes(l.id)).flatMap(l=>l.sources).slice(0,12);
  const predictive=cycle.stage!=="APPROVED_ALREADY";
  const mk=(outcome:OutcomePrediction["outcome"],ids:AdvancedLevelId[]):OutcomePrediction=>({
    outcome,
    status:predictive?"ABSTAIN":"NOT_APPLICABLE_PREVIOUSLY_APPROVED",
    probability:null,
    reasoning:predictive?
      "No calibrated, prospective approval/CRL/delay model or current-cycle multidisciplinary adjudication has passed validation.":
      "The associated indication was already FDA approved in an earlier cycle; this is not a pending first-approval prediction.",
    supportingEvidence:used(ids),
    missingEvidence:levels.filter(l=>ids.includes(l.id)).flatMap(l=>l.missing)
  });
  return {cycle,phase,levels,
    predictions:[
      mk("APPROVAL",["MULTIDISCIPLINARY_REVIEW","STATISTICAL_FORENSICS","CLINICAL_BENEFIT_RISK","REGULATORY_PATHWAY","BACKTEST_CALIBRATION"]),
      mk("CRL",["CRL_HISTORY","MANUFACTURING_CMC","TRIAL_INTEGRITY","FDA_COMMUNICATIONS","BACKTEST_CALIBRATION"]),
      mk("REVIEW_DELAY",["REVIEW_DELAY","FDA_COMMUNICATIONS","MANUFACTURING_CMC","BACKTEST_CALIBRATION"])
    ],
    certainty:{status:"NOT_VALIDATED",rating:null,calibrationDatasetSize:0,
      explanation:"Certainty is separate from source coverage and approval probability. It cannot be rated until out-of-sample historical reliability, missingness and regime changes have been measured."},
    sourceLeadLevelCount:levels.filter(l=>l.sources.length>0).length,
    completedIndependentReviews:0,snapshotDate:"2026-11-07",
    automaticEvidenceMonitoring:"NOT_ENABLED_IN_STATIC_SOURCE_SNAPSHOT"
  };
}
