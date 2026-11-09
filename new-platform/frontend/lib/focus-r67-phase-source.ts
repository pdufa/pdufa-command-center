/** MAIN R67. Dated original ClinicalTrials.gov phase/design intake from the
 * archived immutable R66 29-NCT source research. This is registry-reporting,
 * NOT independent phase verification, FDA status or a clinical method grade.
 */
import source from "../data/focus-r67-original-phase-source.json";
import {FOCUS_R60_ORIGINAL_TRIAL_REVIEW} from "./focus-r60-original-trial-research";
import {FOCUS_R65_REVIEW_GATES} from "./focus-r65-independent-review-gates";

const ORIGINAL_R66_SHA="be3f8f0f4351579a7eddea2ebb67654992f8dd8f5125cbd78bf56ed440f43257";
const DATE=/^20\d{2}(?:-\d{2}){1,2}$/;
const NCT=/^NCT\d{8}$/;
type SourceRow=[string,string,string,string,string,string,string,number,string,string,string];
type Source={schema:string;run:number;artifact:number;originalR66Sha256:string;rows:SourceRow[]};

export function buildR67PhaseSource(input:unknown=source){
  const original=FOCUS_R60_ORIGINAL_TRIAL_REVIEW;
  const review=FOCUS_R65_REVIEW_GATES;
  if(!original||!review||original.counts.uniqueNcts!==29||
     original.counts.applicationGroups!==23||
     review.uniqueTrials!==29||review.provisionalApplications!==23||
     review.signedPhaseReviews!==0||review.signedScientificReviews!==0||
     review.releasedMethodGrades!==0||
     review.independentlyValidatedFdaForecasts!==0||
     review.officialFutureFdaOutcome!=="ABSTAIN"||
     review.predictionAccuracy!==null||
     !input||typeof input!=="object"||Array.isArray(input))return null;
  const value=input as Source;
  if(Object.keys(value).sort().join("|")!==
       ["artifact","originalR66Sha256","rows","run","schema"].join("|")||
     value.schema!=="MAIN_R67_COMPACT_ORIGINAL_R66_PHASE_SOURCE_ONLY"||
     value.run!==42720903307||value.artifact!==13720041195||
     value.originalR66Sha256!==ORIGINAL_R66_SHA||
     !Array.isArray(value.rows)||value.rows.length!==29)return null;
  const originalByNct=new Map(original.trials.map(t=>[t.nct,t]));
  const docketByNct=new Map(review.records.map(t=>[t.nct,t]));
  const seen=new Set<string>();
  const phases={phase3:0,combined:0};
  const statuses={completed:0,active:0,recruiting:0};
  let randomized=0;
  const records=[];
  for(const r of value.rows){
    if(!Array.isArray(r)||r.length!==11||
       !r.every((x,i)=>i===7?Number.isSafeInteger(x)&&x>0&&x<=100000:
         typeof x==="string"&&x.length<=120)||
       !NCT.test(r[0])||seen.has(r[0])||
       !originalByNct.has(r[0])||!docketByNct.has(r[0]))return null;
    const [nct,phase,status,updated,verified,allocation,masking,
      enrollment,enrollmentType,primaryDate,primaryType]=r;
    if(!(phase==="PHASE3"||phase==="PHASE2,PHASE3")||
       !["COMPLETED","ACTIVE_NOT_RECRUITING","RECRUITING"].includes(status)||
       !DATE.test(updated)||updated>"2026-11-09"||!DATE.test(verified)||verified.length!==7||
       verified>updated.slice(0,7)||
       !DATE.test(primaryDate)||!["RANDOMIZED","NA"].includes(allocation)||
       !["NONE","DOUBLE","TRIPLE","QUADRUPLE"].includes(masking)||
       !["ACTUAL","ESTIMATED"].includes(enrollmentType)||
       !["ACTUAL","ESTIMATED"].includes(primaryType))return null;
    const originalTrial=originalByNct.get(nct)!;
    const docketTrial=docketByNct.get(nct)!;
    if(originalTrial.cycles.length===0||
       originalTrial.officialApprovalOrCrlForecast!=="ABSTAIN"||
       originalTrial.independentlyValidatedScientificReview!==false||
       docketTrial.clinicalAssessmentLevel!=="UNASSESSED_SOURCE_ONLY"||
       docketTrial.reviewedPhaseVerified!==false||
       docketTrial.qualifiedSignedGrades!==0||
       docketTrial.methodTasks.length!==8||
       originalTrial.cycles.join("|")!==docketTrial.applicationCycles.join("|"))return null;
    seen.add(nct);
    if(phase==="PHASE3")phases.phase3++;else phases.combined++;
    if(status==="COMPLETED")statuses.completed++;
    if(status==="ACTIVE_NOT_RECRUITING")statuses.active++;
    if(status==="RECRUITING")statuses.recruiting++;
    if(allocation==="RANDOMIZED")randomized++;
    const flags=[
      "Registry-reported phase requires independent verification",
      "Registration/recruitment status is not an FDA application outcome",
      "Original signed, prospectively locked protocol/SAP chronology remains unverified",
      ...(phase==="PHASE2,PHASE3"?["Combined Phase 2/3 designation requires study-design review"]:[]),
      ...(allocation==="NA"?["Allocation N/A: study design cannot be described as randomized"]:[]),
      ...(status!=="COMPLETED"?["Registry study remains in progress; do not infer a failed trial"]:[])
    ];
    records.push({
      nct,ticker:docketTrial.ticker,applicationCycles:[...docketTrial.applicationCycles],
      originalRegistryUrl:"https://clinicaltrials.gov/study/"+nct,
      currentOriginalSourceSha256:originalTrial.originalRegistrySha256,
      sourcePhase:phase==="PHASE3"?"Phase 3":"Combined Phase 2/3",
      sourceStatus:status.replaceAll("_"," "),
      sourceUpdatedDate:updated,registryVerifiedMonth:verified,
      allocation,masking,enrollment,enrollmentType,
      primaryCompletionDate:primaryDate,primaryCompletionType:primaryType,
      reviewFlags:flags,
      researchInstallationStage:4,
      independentlyVerifiedTrialPhase:false,
      independentPhaseReviewEventId:null,
      independentlyCompletedScientificLevel:null,
      scientificMethodScores:0,
      verifiedFdaApplicationStatus:null,
      predictedFDAOutcome:"ABSTAIN" as const,
      predictionConfidence:null
    });
  }
  if(seen.size!==29||originalByNct.size!==29||docketByNct.size!==29||
     [...originalByNct.keys()].some(nct=>!seen.has(nct))||
     phases.phase3!==28||phases.combined!==1||
     statuses.completed!==19||statuses.active!==8||statuses.recruiting!==2||
     randomized!==28||
     records.find(r=>r.nct==="NCT04871282")?.sourcePhase!=="Combined Phase 2/3"||
     records.find(r=>r.nct==="NCT06331299")?.allocation!=="NA")return null;
  return {
    schema:"MAIN_R67_VIEW_ONLY_OF_ORIGINAL_R66_PHASE_SOURCE",
    run:value.run,artifact:value.artifact,sha256:value.originalR66Sha256,
    archiveUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+
      value.run+"/artifacts/"+value.artifact,
    ncts:29,applications:23,
    sourceReportedPhase3Only:28,sourceReportedCombinedPhase23:1,
    sourceReportedCompleted:19,sourceReportedActiveNotRecruiting:8,
    sourceReportedRecruiting:2,
    records,
    verifiedPhaseReviews:0,signedScienceReviews:0,
    independentlyValidatedFDAForecasts:0,
    futureFDAOutcome:"ABSTAIN" as const,
    measuredForecastAccuracy:null,
    hasIndependentRegulatoryReview:false,
    sourceLabelsAreNotClinicalAdjudication:true,
    productionOrClinicalWrites:false,
  };
}
export const FOCUS_R67_PHASE_SOURCE=buildR67PhaseSource();
