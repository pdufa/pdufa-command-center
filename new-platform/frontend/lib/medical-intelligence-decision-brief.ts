import {APPLICATION_CYCLES,type ApplicationCycle} from "./medical-intelligence-applications";
import {REVIEWED_FINDINGS,type ReviewedFinding} from "./medical-intelligence-reviewed-findings";

export type DecisionBrief={
  cycle:ApplicationCycle;
  outcome:"INDETERMINATE"|"ALREADY_APPROVED";
  timing:"INDETERMINATE"|"NOT_APPLICABLE";
  approvalEvidence:ReviewedFinding[];
  documentedFdaObjections:ReviewedFinding[];
  pastCrls:ReviewedFinding[];
  scientificUncertainties:ReviewedFinding[];
  priorExtensions:ReviewedFinding[];
  otherEvidence:ReviewedFinding[];
  primaryReviewQuestion:string;
  evidenceLimitations:string[];
  researchState:"INITIAL_SOURCE_MAPPING_ONLY";
  confidence:"NOT_CALIBRATED";
};
/** This is an evidence-organizing brief, deliberately NOT an approval probability or automated FDA forecast. */
export function buildDecisionBrief(cycleId:string):DecisionBrief|null{
  const cycle=APPLICATION_CYCLES.find(c=>c.id===cycleId);
  if(!cycle)return null;
  const collected=REVIEWED_FINDINGS.filter(f=>f.relatedNcts.some(n=>cycle.ncts.includes(n)));
  const evidence=[...new Map(collected.map(f=>[f.id,f])).values()];
  const type=(name:ReviewedFinding["type"])=>evidence.filter(f=>f.type===name);
  const approvalEvidence=type("EFFICACY_EVIDENCE");
  const documentedFdaObjections=type("REGULATORY_OBJECTION");
  const pastCrls=type("PREVIOUS_CRL");
  const scientificUncertainties=type("SCIENTIFIC_UNCERTAINTY");
  const priorExtensions=type("EXTENSION_CONFIRMED");
  const excludedIds=new Set([...approvalEvidence,...documentedFdaObjections,...pastCrls,...scientificUncertainties,...priorExtensions].map(f=>f.id));
  const otherEvidence=evidence.filter(f=>!excludedIds.has(f.id));
  const hasCmc=evidence.some(f=>f.domain==="cmc");
  const hasInspection=evidence.some(f=>f.domain==="inspections"||f.domain==="integrity");
  const limitations=[
    "Full confidential FDA multidisciplinary review and sponsor submission are not accessible in this preview.",
    "A curated source finding does not establish exhaustive review of all relevant trials, endpoints, regulators or competitors.",
    !hasCmc ? "No candidate-specific CMC evaluation has been independently completed; absent public information is not a clean inspection.":
      "Existing public CMC facts are partial; FDA's current-cycle resolution and commercial process adequacy remain to be verified.",
    !hasInspection ? "No comprehensive site/facility inspection review is completed; no finding cannot be inferred from missing disclosures.":
      "Public inspection findings, where present, do not establish whether FDA has closed them.",
    cycle.reportedGoal ? "The recorded review goal is sourced to a public disclosure, not separately certified against confidential FDA correspondence." :
      "No confirmed review goal is associated with this application cycle in the dated source material."
  ];
  return {
    cycle,
    outcome:cycle.stage==="APPROVED_ALREADY"?"ALREADY_APPROVED":"INDETERMINATE",
    timing:cycle.stage==="APPROVED_ALREADY"?"NOT_APPLICABLE":"INDETERMINATE",
    approvalEvidence,documentedFdaObjections,pastCrls,scientificUncertainties,priorExtensions,otherEvidence,
    primaryReviewQuestion:cycle.criticalQuestion,evidenceLimitations:limitations,
    researchState:"INITIAL_SOURCE_MAPPING_ONLY",confidence:"NOT_CALIBRATED"
  };
}
