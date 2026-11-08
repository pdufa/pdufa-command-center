/**
 * Application-level specialist evidence triage. All results are source pointers,
 * never completed clinical judgments, medical signoff, or predictions.
 *
 * A referenced trial can support more than one distinct FDA supplement; source
 * duplication is not independent confirmation or cross-product equivalence.
 */
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {findingsForNct,type ReviewedFinding} from "./medical-intelligence-reviewed-findings";
import {getSpecialtyTasks,getSpecialtyProfile,type SpecialistResearchTask} from "./medical-intelligence-specialty";
import {deskIssuesForCycle} from "./medical-intelligence-failure-desk";

export type EvidenceTriageState="RELEVANT_SOURCE_FOUND_REVIEW_PENDING"|"NO_CURATED_SOURCE_YET";
export type ClinicalAxisEvidence={
  axis:number;
  axisName:string;
  status:EvidenceTriageState;
  researchTask:SpecialistResearchTask;
  supportingSourceFindings:ReviewedFinding[];
  sourceCount:number;
  notes:string[];
};
export type SpecialtyEvidenceAudit={
  cycleId:string;drug:string;specialty:string;linkedNcts:readonly string[];
  axes:ClinicalAxisEvidence[];
  sourceBackedAxes:number;uncoveredAxes:number;
  uniqueSourceFindings:number;
  targetedRegulatoryIssues:number;
  clinicalEvaluationStatus:"INCOMPLETE_NOT_PHYSICIAN_REVIEWED";
};

const CLINICAL_SOURCE_DOMAINS:Readonly<Record<number,readonly string[]>>={
  1:["disease","design"],
  2:["mechanism","disease","pkpd"],
  3:["competition","design","prior"],
  4:["endpoint","statistics","design"],
  5:["subgroups","design","disease"],
  6:["endpoint","statistics"],
  7:["safety","integrity"],
  8:["statistics","integrity","design"],
  9:["statistics","safety","prior","integrity","cmc"],
  10:["prior","cmc","inspections","safety","timing","label","integrity","regulatory"]
};
export function buildSpecialtyEvidenceAudit(cycleId:string):SpecialtyEvidenceAudit|null{
  const cycle=APPLICATION_CYCLES.find(c=>c.id===cycleId);
  const profile=getSpecialtyProfile(cycleId);
  if(!cycle||!profile)return null;
  const sourceFindings=[...new Map(cycle.ncts.flatMap(findingsForNct).map(f=>[f.id,f])).values()];
  const questions=getSpecialtyTasks(cycleId);
  const regulatoryIssues=deskIssuesForCycle(cycleId);
  const axes=questions.map((question,i)=>{
    const allowed=CLINICAL_SOURCE_DOMAINS[question.axis]||[];
    const matching=sourceFindings.filter(f=>allowed.includes(f.domain));
    const notes:string[]=[];
    if(matching.some(f=>f.evidence==="SPONSOR_RELEASE"||f.evidence==="SEC_COMPANY_DISCLOSURE"))
      notes.push("Sponsor-disclosed results are not equivalent to independent FDA acceptance.");
    if(matching.some(f=>f.type==="PREVIOUS_CRL"||f.type==="EXTENSION_CONFIRMED"))
      notes.push("Historical FDA actions do not establish the next review-cycle outcome.");
    if(question.axis===9||question.axis===10){
      if(regulatoryIssues.length)notes.push(regulatoryIssues.length+" separately curated targeted FDA/review issue(s) exist; investigate their original evidence.");
    }
    if(!matching.length)notes.push("No relevant curated source in this axis. This is a research-coverage gap, not a passing clinical result.");
    return {
      axis:question.axis,
      axisName:[
        "Clinical phenotype and differential diagnosis",
        "Mechanism and disease-specific plausibility",
        "Clinical treatment algorithm",
        "Outcome validity and patient importance",
        "Subgroup selection and heterogeneity",
        "Magnitude and duration of benefit",
        "Serious harms and practical manageability",
        "Alternative explanations and real-world fit",
        "Independent specialty challenge",
        "FDA benefit-risk translation"
      ][i],
      researchTask:question,
      status:matching.length?"RELEVANT_SOURCE_FOUND_REVIEW_PENDING":"NO_CURATED_SOURCE_YET",
      supportingSourceFindings:matching,
      sourceCount:matching.length,
      notes
    } satisfies ClinicalAxisEvidence;
  });
  return {
    cycleId,drug:cycle.drug,specialty:profile.specialty,linkedNcts:cycle.ncts,
    axes,sourceBackedAxes:axes.filter(x=>x.sourceCount>0).length,
    uncoveredAxes:axes.filter(x=>x.sourceCount===0).length,
    uniqueSourceFindings:sourceFindings.length,
    targetedRegulatoryIssues:regulatoryIssues.length,
    clinicalEvaluationStatus:"INCOMPLETE_NOT_PHYSICIAN_REVIEWED"
  };
}
export function allSpecialtyEvidenceAudits():SpecialtyEvidenceAudit[]{
 return APPLICATION_CYCLES.map(c=>buildSpecialtyEvidenceAudit(c.id)).filter((a):a is SpecialtyEvidenceAudit=>Boolean(a));
}
