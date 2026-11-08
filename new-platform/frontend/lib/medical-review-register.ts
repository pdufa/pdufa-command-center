/** Exact-NCT, read-only CSV of the 800 current reviewer method positions.
 * Never substitute source classification, a missing grade, or a stale phase for an independent score.
 * This is a local reviewer work register, not a grade-import or FDA forecast path.
 */
import type {AssessmentReview,CatalogMatrix,ReviewMatrix} from "./medical-review-matrix";

type Details=Record<number,AssessmentReview>;
const HEADERS=[
  "nct","verified_phase","phase_event_id","assessment_index","assessment_id","layer",
  "assessment_label","method_index","method","method_description","priority_tier",
  "priority_rank","phase_applicability","required_sources","review_status","clinical_grade_0_to_5",
  "review_event_id","revision","reviewed_at","reviewer_id","rationale",
  "captured_source_urls","captured_source_findings","evidence_gap_count","evidence_gaps"
];
const STATUSES=new Set(["SCORED","NOT_APPLICABLE","RETRACTED","STALE_PHASE","UNREVIEWED","VERIFY_PHASE"]);
function csvCell(value:unknown):string{
  let s=value===null||value===undefined?"":String(value);
  // Defend when CSV is opened in Excel/Sheets; even untrusted narrative and method titles are data.
  if (/^[\s\uFEFF]*[=+\-@]/.test(s))s="'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
}
function line(values:unknown[]):string{return values.map(csvCell).join(",");}

export function buildClinicalReviewRegisterCsv(catalog:CatalogMatrix,review:ReviewMatrix,details:Details):string{
  if(!/^NCT\d{8}$/.test(review.nct)||catalog.nct!==review.nct||review.totalPositions!==800||
     catalog.assessments.length!==40||review.assessments.length!==40||
     (review.verifiedPhase===null)!==(review.phaseEventId===null))
    throw Error("REVIEW_REGISTER_INVALID_SNAPSHOT");
  const rows=[line(HEADERS)];
  let graded=0,excluded=0;
  for(let a=1;a<=40;a++){
    const ca=catalog.assessments[a-1],summary=review.assessments[a-1],detail=details[a];
    if(ca?.assessmentIndex!==a||summary?.assessmentIndex!==a||
       !detail||detail.assessmentIndex!==a||!Array.isArray(detail.methods)||
       detail.methods.length!==20||ca.methods.length!==20||
       detail.reviewedMethods!==summary.reviewedMethods||
       detail.excludedMethods!==summary.excludedMethods||
       detail.pendingMethods!==summary.pendingMethods||
       detail.status!==summary.status)
      throw Error("REVIEW_REGISTER_REQUIRES_ALL_800_VERIFIED_METHOD_ROWS");
    let groupGraded=0,groupExcluded=0;
    for(let m=1;m<=20;m++){
      const cm=ca.methods[m-1],r=detail.methods[m-1];
      if(cm?.methodIndex!==m||r?.methodIndex!==m||!STATUSES.has(r.status))
        throw Error("REVIEW_REGISTER_METHOD_IDENTITY_MISMATCH");
      const scored=r.status==="SCORED",notApplicable=r.status==="NOT_APPLICABLE";
      if(scored?(!Number.isInteger(r.grade)||r.grade===null||r.grade<0||r.grade>5||
                 !r.reviewEventId||!r.reviewerId||!r.sourceEvidence.length||!review.phaseEventId):
         r.grade!==null)
        throw Error("REVIEW_REGISTER_UNVERIFIED_GRADE");
      if(!review.phaseEventId&&r.status!=="VERIFY_PHASE")
        throw Error("REVIEW_REGISTER_PHASE_NOT_VERIFIED");
      if(scored)groupGraded++;
      if(notApplicable)groupExcluded++;
      rows.push(line([
        review.nct,review.verifiedPhase,review.phaseEventId,a,ca.assessmentId,ca.layerId,
        ca.label,m,cm.method,cm.methodDescription,cm.priorityTier,cm.priorityRank,
        cm.phaseApplicability,cm.requiredSources,r.status,scored?r.grade:null,
        r.reviewEventId,r.revision,r.reviewedAt,r.reviewerId,r.rationale,
        JSON.stringify(r.sourceEvidence.map(x=>x.sourceUrl)),
        JSON.stringify(r.sourceEvidence),r.evidenceGaps.length,
        JSON.stringify(r.evidenceGaps.map(g=>({code:g.gap_code,note:g.evidence_note,date:g.recorded_at})))
      ]));
    }
    if(groupGraded!==summary.reviewedMethods||groupExcluded!==summary.excludedMethods)
      throw Error("REVIEW_REGISTER_GROUP_TOTALS_MISMATCH");
    graded+=groupGraded;excluded+=groupExcluded;
  }
  if(rows.length!==801||graded!==review.counts.SCORED||excluded!==review.counts.NOT_APPLICABLE)
    throw Error("REVIEW_REGISTER_TOTALS_MISMATCH");
  return rows.join("\r\n")+"\r\n";
}
