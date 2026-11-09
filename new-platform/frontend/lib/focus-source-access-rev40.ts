/** Revision 40 exact public source *retrieval* receipt; NOT independent science.
 * Pinned to immutable GitHub Actions run/artifact and SHA-256 of its JSON.
 * No unapproved model probabilities, clinical credentials or grading.
 */
import focus from "../data/p3PostDataActive.json";
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";

export const FOCUS_SOURCE_R40={
  schema:"MAIN_FOCUS_PUBLIC_SOURCE_RECAPTURE_R40" as const,
  capturedAtUtc:"2026-11-09T16:24:54+00:00",
  exactGithubRun:42654460905,
  runUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/42654460905",
  artifactId:13691348436,
  artifactUrl:"https://github.com/pdufa/pdufa-command-center/actions/runs/42654460905/artifacts/13691348436",
  jsonReceiptSha256:"0601058cd65f62380c3f3242b408f95ca13408f21d2845e589e9e4f5faf7d32c",
  artifactExpiryUtc:"2027-02-07T16:24:36Z",
  trials:29,
  trialRegistryFetched:29,
  trialResultsModulePresent:12,
  trialResultsModuleNotPresent:17,
  provisionalApplicationGroups:23,
  groupsWithAtLeastOnePublicSourceRetrieved:23,
  canonicalApplicationUrls:21,
  additionalOfficialSecFallbackUrls:1,
  totalUniqueUrlsAttempted:22,
  totalUniqueUrlsFetched:21,
  blockedCanonicalSource:{
    cycleId:"achv-cytisinicline",
    originalIssuerHttpStatus:301,
    fallback:"https://www.sec.gov/Archives/edgar/data/949858/000119312526344624/achv-20260630.htm",
    fallbackFetched:true
  },
  singlePhase3RegistryRecords:28,
  combinedPhase2Phase3RegistryRecords:1,
  combinedPhaseRecordNct:"NCT04871282",
  resultsPostedNcts:[
    "NCT05507203","NCT05507216","NCT04576949","NCT05206370",
    "NCT05811247","NCT05813275","NCT03697109","NCT04308590",
    "NCT05767346","NCT04544293","NCT06331299","NCT04716231"
  ],
  sourceVersionsIndependentlyAuthenticated:0,
  qualifiedClinicalReviews:0,
  scientificGradesWritten:0,
  independentlyValidatedApplicationForecasts:0,
  verifiedHistoricalBacktests:0,
  measuredAccuracy:null,
  predictionProbability:null,
  officialFdaModelOutcome:"ABSTAIN" as const,
  lastSourceCaptureOnly:true,
  sourceBodiesSavedToRepo:false,
  permanentOriginalSourceVault:false
} as const;
export type FocusSourceAccess="PUBLIC_LINK_FETCHED_NOT_CLINICALLY_VERIFIED"|"ISSUER_LINK_REDIRECTED_OFFICIAL_SEC_FALLBACK_FETCHED";
export function sourceStatusForCycle(id:string):FocusSourceAccess{
  if(focus.records.length!==29||APPLICATION_CYCLES.length!==23||
    !APPLICATION_CYCLES.some(x=>x.id===id))
    throw Error("R40_APPLICATION_ID_OR_ROSTER_MISMATCH");
  return id==="achv-cytisinicline"
    ?"ISSUER_LINK_REDIRECTED_OFFICIAL_SEC_FALLBACK_FETCHED"
    :"PUBLIC_LINK_FETCHED_NOT_CLINICALLY_VERIFIED";
}
export function verifyR40ResearchReadiness(){
  const r=FOCUS_SOURCE_R40;
  if(focus.asOf!=="2026-11-08"||
     r.trials!==focus.records.length||
     r.provisionalApplicationGroups!==APPLICATION_CYCLES.length||
     r.resultsPostedNcts.length!==12||
     new Set(r.resultsPostedNcts).size!==12||
     r.resultsPostedNcts.some(nct=>!focus.records.some(row=>row.nct===nct))||
     r.groupsWithAtLeastOnePublicSourceRetrieved!==23||
     r.totalUniqueUrlsFetched!==21||
     r.totalUniqueUrlsAttempted!==22||
     r.qualifiedClinicalReviews!==0||
     r.independentlyValidatedApplicationForecasts!==0||
     r.officialFdaModelOutcome!=="ABSTAIN"){
    throw Error("R40_SOURCE_RECEIPT_NOT_SUPPORTED_BY_CANONICAL_ROSTER");
  }
  return r;
}
