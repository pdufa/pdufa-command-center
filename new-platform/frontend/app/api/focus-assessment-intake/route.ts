import {NextResponse} from "next/server";
import {FOCUS_SPECIALTY_ASSESSMENT_QUEUE,FOCUS_SPECIALTY_SUMMARY} from "../../../lib/focus-specialty-assessment";

export const dynamic="force-dynamic";
export function GET(){
  return NextResponse.json({
    schemaVersion:1,
    kind:"FOCUS_SCIENTIFIC_RESEARCH_INTAKE_NOT_COMPLETED_ASSESSMENTS",
    summary:FOCUS_SPECIALTY_SUMMARY,
    methodology:{
      phaseFirst:true,
      primaryKey:"nct",
      applicationCycleScoped:true,
      sourceProvenance:"Dated FOCUS roster and independently unverified public research pointers",
      specialistReviewComplete:false,
      predictionReleasePermitted:false,
      note:"No numerical FDA probabilities or validated certainty. Research text does not establish FDA acceptance."
    },
    trials:FOCUS_SPECIALTY_ASSESSMENT_QUEUE
  },{headers:{"Cache-Control":"no-store"}});
}
