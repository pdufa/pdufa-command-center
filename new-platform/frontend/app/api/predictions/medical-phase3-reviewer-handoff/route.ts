import {NextRequest,NextResponse} from "next/server";
import {authConfigured,COOKIE_NAME,hasSession} from "../../../../lib/auth";
import pilot from "../../../../data/acacia-pilot-prediction-workup-20261108.json";
import {evaluatePilotScientificSignals} from "../../../../lib/acacia-quantitative-science";
import {evaluateClinicalRubricReadiness} from "../../../../lib/phase3-clinical-quality-rubric";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"};
/** A versioned, reviewer-ready *research evidence dossier*, not a signed review.
 * Same dashboard session guard as the read-only medical matrix. No POST route.
 */
export async function GET(req:NextRequest){
  if(!authConfigured()||!hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return NextResponse.json({error:"Authentication required"},{status:401,headers});
  const params=req.nextUrl.searchParams;
  if(params.getAll("nct").length!==1||params.get("nct")!=="NCT06081894"||
    [...params.keys()].some(k=>k!=="nct")){
    return NextResponse.json({error:"Exact Phase III pilot trial required"},{status:422,headers});
  }
  const evidence=evaluatePilotScientificSignals(pilot);
  const rubrics=evaluateClinicalRubricReadiness(evidence,pilot);
  if(!evidence||!rubrics||rubrics.methods.some(m=>
    m.numericGrade!==null||m.officialGrade!==null||m.reviewerSignature!==null)){
    return NextResponse.json({error:"Evidence quality review dossier withheld"},{status:503,headers});
  }
  return NextResponse.json({
    schema:"MAIN_PHASE3_REVIEWER_HANDOFF_V1",
    exactNct:"NCT06081894",
    protocolCode:"CY 6033",
    evidenceSnapshotAsOf:pilot.asOf,
    sourceReport:evidence,
    clinicalQualityRubric:rubrics,
    requestedAction:"INDEPENDENT_EVIDENCE_REVIEW_NOT_SCORE_PUBLICATION",
    missingDataAreNotZeroGrades:true,
    prospectiveApprovalProbability:null,
    officialMethodGradeEventsWritten:0,
    finalFdaPrediction:"ABSTAIN",
    authorizedForClinicalWrite:false,
  },{headers});
}
