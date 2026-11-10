/** MAIN R84: provisional FDA application-cycle chronology, not an FDA forecast.
 * Material is issuer/source-reported as of the fixed research snapshot below;
 * no live FDA acceptance, action-date, science or safety adjudication occurs here.
 */
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {FOCUS_R81_SOURCE_READINESS} from "./focus-r81-all-focus-source-readiness";

type R81=NonNullable<typeof FOCUS_R81_SOURCE_READINESS>;
type Cycle=typeof APPLICATION_CYCLES[number];
const VALID_STAGES = new Set([
  "NOT_RECONCILED","PLANNED","PRIOR_CRL_RESUBMISSION_PLANNED",
  "SUBMITTED_PENDING_ACCEPTANCE","UNDER_REVIEW","SUPPLEMENT_UNDER_REVIEW","APPROVED_ALREADY"
]);
const DATE=/^\d{4}-\d{2}-\d{2}$/u;
function dateOk(value:string):boolean {
  if(!DATE.test(value))return false;
  const d=new Date(value+"T00:00:00Z");
  return !Number.isNaN(d.getTime())&&d.toISOString().slice(0,10)===value;
}
export const R84_CYCLE_SNAPSHOT_AS_OF="2026-11-07";
export const R84_STATUS_BANNER=
  "Dated issuer/source-reported application leads; no live FDA status verification, approval probability or calibrated forecast.";

export function buildR84ApplicationVerificationQueue(
 source:R81|null=FOCUS_R81_SOURCE_READINESS,
 cycles:readonly Cycle[]=APPLICATION_CYCLES
) {
 if(!source || source.exactTrials!==29 || source.provisionalCycles!==23 ||
    source.rows.length!==29 || source.applicationGroups.length!==23 ||
    source.validFutureFDAApplicationForecasts!==0 ||
    source.independentScientificSignoffs!==0 ||
    source.originalSignedProspectiveSAPsVerified!==0 ||
    source.FDAOutcome!=="ABSTAIN" || source.accuracyCalibrated!==false ||
    cycles.length!==23) return null;

 const canonicalGroups = new Map(source.applicationGroups.map(x=>[x.cycleId,x]));
 if(canonicalGroups.size!==23)return null;
 const seen=new Set<string>();
 const rows=[];
 for(const c of cycles) {
  const group=canonicalGroups.get(c.id);
  if(!group || seen.has(c.id) || !VALID_STAGES.has(c.stage) ||
     !/^[a-z0-9]+(?:-[a-z0-9]+)+$/u.test(c.id)||
     c.ticker!==group.ticker || !c.drug.trim()||!c.indication.trim()||
     !c.criticalQuestion.trim()|| !["NDA","BLA","sNDA","sBLA"].includes(c.applicationType)||
     !dateOk(c.sourceDate) || !/^https:\/\//u.test(c.sourceUrl)||
     (c.reportedGoal!==null && (!dateOk(c.reportedGoal)||c.reportedGoal<c.sourceDate))||
     (c.stage==="APPROVED_ALREADY" && c.reportedGoal!==null)||
     c.ncts.length!==group.trialCount ||
     new Set(c.ncts).size!==c.ncts.length||
     !c.ncts.every(nct=>group.ncts.includes(nct)) ||
     group.ncts.some(nct=>!c.ncts.includes(nct))||
     group.validatedFDAApplicationForecasts!==0||
     group.independentlySignedScientificReviews!==0||
     group.clinicalGrade!==null||group.FDAOutcome!=="ABSTAIN")return null;

  seen.add(c.id);
  const linked=group.ncts.map(nct=>source.rows.find(t=>t.nct===nct));
  if(linked.some(t=>!t||t.validatedFDAApplicationPrediction!==false||
       t.officialFDAOutcome!=="ABSTAIN"))return null;
  const missingPrimary=linked.filter(t=>!t!.currentRegistryPrimaryTable).length;
  const missingSafety=linked.filter(t=>!t!.currentRegistrySafetyArms).length;
  const missingMethodPages=linked.filter(t=>!t!.retainedMethodPageLeads).length;
  const observedClaim=c.stage==="APPROVED_ALREADY";
  rows.push({
   cycleId:c.id,ticker:c.ticker,drug:c.drug,indication:c.indication,
   applicationType:c.applicationType,
   linkedNcts:[...group.ncts],
   sourceDate:c.sourceDate,sourceUrl:c.sourceUrl,
   sponsorReportedStatus:c.stage,
   sponsorReportedGoal:c.reportedGoal,
   goalProvenance:c.reportedGoal?
    "SOURCE_REPORTED_NOT_FDA_INDEPENDENTLY_VERIFIED":
    "NO_PDUFA_GOAL_IN_RETAINED_CYCLE_SNAPSHOT",
   observedHistoricalStatusClaim:observedClaim,
   prospectiveDecisionCandidate:!observedClaim,
   reviewPriority:observedClaim?"OBSERVED_STATUS_VERIFY":
     c.reportedGoal?"DATED_GOAL_SOURCE_RECHECK":"NO_GOAL_RECONCILE",
   missingRegistryPrimaryTables:missingPrimary,
   missingRegistrySafetyArms:missingSafety,
   missingMethodPageLeads:missingMethodPages,
   criticalQuestion:c.criticalQuestion,
   scienceSignoff:"NOT_COMPLETED" as const,
   fdaOutcomePrediction:"ABSTAIN" as const,
   fdaTimingPrediction:"UNKNOWN" as const
  });
 }
 if(seen.size!==23 || [...canonicalGroups.keys()].some(id=>!seen.has(id)))return null;

 rows.sort((a,b)=>{
   const aa=a.observedHistoricalStatusClaim?2:(a.sponsorReportedGoal?0:1);
   const bb=b.observedHistoricalStatusClaim?2:(b.sponsorReportedGoal?0:1);
   if(aa!==bb)return aa-bb;
   if(aa===0 && a.sponsorReportedGoal!==b.sponsorReportedGoal)
     return a.sponsorReportedGoal!.localeCompare(b.sponsorReportedGoal!);
   return a.ticker.localeCompare(b.ticker)||a.cycleId.localeCompare(b.cycleId);
 });
 const uniqueNcts=new Set(rows.flatMap(r=>r.linkedNcts));
 if(uniqueNcts.size!==29 || source.rows.some(r=>!uniqueNcts.has(r.nct)))return null;
 return {
  schema:"MAIN_R84_REPORTED_APPLICATION_CYCLE_VERIFY_ONLY" as const,
  snapshotAsOf:R84_CYCLE_SNAPSHOT_AS_OF,
  banner:R84_STATUS_BANNER,
  exactTrials:29 as const,provisionalCycles:23 as const,
  reportedTargetCount:rows.filter(r=>r.sponsorReportedGoal!==null).length,
  noReportedTargetCount:rows.filter(r=>r.sponsorReportedGoal===null).length,
  observedStatusClaims:rows.filter(r=>r.observedHistoricalStatusClaim).length,
  independentFDAApplicationStatusConfirmations:0 as const,
  independentlyValidatedForecasts:0 as const,
  readOnly:true as const,
  rows
 };
}
export const R84_APPLICATION_VERIFICATION=buildR84ApplicationVerificationQueue();
