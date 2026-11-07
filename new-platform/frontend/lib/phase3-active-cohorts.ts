/**
 * Source-reconciled active Phase 3 TOP/BOTTOM sheets.
 * Scope: the dated 762 exact-NCT research census, NOT the verified PDUFA
 * application pipeline. Only study status ACTIVE can appear in these sheets.
 *
 * Historical source ledgers stay immutable; five known independently sourced
 * issuer readouts override stale PRE labels in this read-only derived view.
 */
import ledger from "../public/phase3-unified-classifications-2026-11-05.json";
import endpoint from "../data/phase3EndpointAdjudications20261105.json";
import issuer from "../data/phase3CompanyWebsiteEvidence20261105.json";
import {trialLifecycle} from "./pdufa-selected-restrictions";

export const ACTIVE_PHASE3_COHORT_AS_OF="2026-11-06";
export const PROMOTED_ISSUER_NCTS=[
 "NCT05535946", // ABVX: ABTECT Maintenance
 "NCT05031780", // AGIO: RISE; hemoglobin met, pain co-primary not met
 "NCT05144256", // AGIO: ACTIVATE-Kids-T
 "NCT05175105", // AGIO: ACTIVATE-Kids
 "NCT06747468", // AMLX: avexitide
] as const;
/** Source-confirmed readouts missed by dated original PRE labels.
 * Endpoint status is an observed issuer/peer-reviewed claim, not a prospective
 * clinical prediction or an FDA approval decision.
 */
export const NEW_VERIFIED_READOUTS=[
 {nctId:"NCT06087276",ticker:"PRAX",evidenceDate:"2025-10-16",
  evidenceUrl:"https://investors.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_MET",drug:"ulixacaltamide (PRAX-944)",
  evidence:"Exact-NCT Essential3 program: Study 1 mADL11 primary mean improvement 4.3 points (p<0.0001); Study 2 randomized-withdrawal maintenance primary met (p=0.0369). Company-issued observations are not an independent FDA assessment."},
 {nctId:"NCT05208047",ticker:"COGT",evidenceDate:"2026-05-30",
  evidenceUrl:"https://cogentbiosciences.gcs-web.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_MET",drug:"bezuclastinib + sunitinib",
  evidence:"Exact-NCT PEAK GIST Phase 3 primary PFS reported met, median 16.5 vs 9.2 months, HR 0.50 (95% CI 0.39-0.65), p<0.0001. Cross-referenced ASCO 2026 abstract explicitly identifies NCT05208047. Priority Review and Nov 30 2026 PDUFA date are separate application-level milestones."},
 {nctId:"NCT06634420",ticker:"NTLA",evidenceDate:"2026-04-27",
  evidenceUrl:"https://ir.intelliatx.com/news-releases/news-release-details/intellia-therapeutics-reports-positive-phase-3-results",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_MET",drug:"lonvoguran ziclumeran (NTLA-2002)",
  evidence:"Exact-NCT HAELO Phase 3 monthly HAE attack rate primary met, 0.26 vs 2.10 on placebo, p<0.0001 (issuer). Independently published June 2026 NEJM trial report confirms NCT06634420. Rolling BLA initiation is not FDA approval."},
 {nctId:"NCT05125809",ticker:"RARE",evidenceDate:"2025-12-29",
  evidenceUrl:"https://ir.ultragenyx.com/news-releases/news-release-details/ultragenyx-announces-phase-3-orbit-and-cosmic-results-setrusumab",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_NOT_MET",drug:"setrusumab (UX143)",
  evidence:"Phase 2/3 ORBIT exact NCT05125809 Phase 3 fracture-rate primary endpoint failed to reach statistical significance versus placebo. Bone mineral density secondary improved; not a primary success. Distinguish prior Phase 2 from post-data Phase 3."},
 {nctId:"NCT05768854",ticker:"RARE",evidenceDate:"2025-12-29",
  evidenceUrl:"https://ir.ultragenyx.com/news-releases/news-release-details/ultragenyx-announces-phase-3-orbit-and-cosmic-results-setrusumab",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_NOT_MET",drug:"setrusumab (UX143)",
  evidence:"Phase 3 COSMIC exact NCT05768854 annualized clinical fracture rate primary endpoint did not reach statistical significance versus bisphosphonates. Bone mineral density secondary improved; not a primary success."},
 {nctId:"NCT06556368",ticker:"KOD",evidenceDate:"2026-09-28",
  evidenceUrl:"https://ir.kodiak.com/news-releases/news-release-details/zenkuda-and-tabirafusp-ted-meet-primary-endpoints-pivotal",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_MET",drug:"tarcocimab tedromer (Zenkuda); tabirafusp alfa tedromer (KSI-501)",
  evidence:"Exact-NCT DAYBREAK wet AMD Phase 3: both Zenkuda (p=0.0007) and tabirafusp (p=0.0036) primary vision endpoints reported met for noninferiority versus aflibercept at one year. Noninferiority is not superiority; no BLA approval inferred."},
] as const;
/** Previously verified dated readouts: prospective scores MUST NOT use these post-readout facts. */
export const IONIS_VERIFIED_READOUTS=[
 {nctId:"NCT04768972",evidenceDate:"2026-09-22",evidenceUrl:"https://ir.ionis.com/news-releases/news-release-details/ionis-announces-positive-topline-results-phase-3-fusion-study",
  evidenceType:"ISSUER_READOUT",outcome:"PRIMARY_ENDPOINT_MET",drug:"ulefnersen (ION363)",
  evidence:"FUSION FUS-ALS Phase 3 primary joint-rank functional/survival endpoint reported met, p=0.0005; not an FDA application or approval."},
 {nctId:"NCT04849741",evidenceDate:"2026-09-03",evidenceUrl:"https://www.fda.gov/news-events/press-announcements/fda-approves-first-drug-treat-alexander-disease",
  evidenceType:"FDA_APPROVAL_SUPPORTING_TRIAL",outcome:"NO_BINARY_PASS_FAIL",drug:"zilganersen (ZANVASTRO)",
  evidence:"FDA approved zilganersen for Alexander disease Sept 3, 2026 and explicitly identifies NCT04849741 as supporting study; approval does not supply an independent binary primary-endpoint adjudication."},
 {nctId:"NCT05392114",evidenceDate:"2026-02-23",evidenceUrl:"https://pubmed.ncbi.nlm.nih.gov/41767175/",
  evidenceType:"PEER_REVIEWED_OPEN_LABEL_RESULTS",outcome:"NO_BINARY_PASS_FAIL",drug:"donidalorsen",
  evidence:"Exact-NCT one-year OASISplus open-label extension report: 83 participants in OLE subgroup; safety primary descriptive, attack-rate reductions are uncontrolled."}
] as const;
export type ActivePhase3Cohort="PRE_DATA"|"POST_DATA";
type BaseRow=(typeof ledger.rows)[number];
export type ActivePhase3Trial=BaseRow&{
 cohort:ActivePhase3Cohort;
 evidenceBasis:"ISSUER_READOUT"|"REGISTRY_RESULTS_POSTED"|"FDA_APPROVAL_SUPPORTING_TRIAL"|"PEER_REVIEWED_RESULTS"|"PUBLIC_READOUT_NOT_VERIFIED";
 originalClassificationCode:string;
 correctionApplied:boolean;
};
const endpoints=new Map(endpoint.records.map(r=>[r.nctId,r]));
const issuers=new Map(issuer.records.map(r=>[r.nctId,r]));
const assert=(ok:unknown,why:string):void=>{if(!ok)throw Error("ACTIVE_PHASE3_COHORT_INTEGRITY_"+why);};
const iso=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))
 &&new Date(s).toISOString().slice(0,10)===s;
const matchedIssuer=(id:string):{
 evidenceDate:string;evidenceUrl:string;drug:string;endpointInterpretation:string;
}|null=>{
 const a=endpoints.get(id),b=issuers.get(id);
 if(!a||!b)return null;
 if(!b.companyUrl?.startsWith("https://")||!iso(b.sourceDate)||
  b.sourceDate>ACTIVE_PHASE3_COHORT_AS_OF||a.evidenceUrl!==b.companyUrl||
  !["PRIMARY_ENDPOINT_MET","PRIMARY_ENDPOINT_NOT_MET"].includes(a.endpointOutcome))
  return null;
 return {evidenceDate:b.sourceDate,evidenceUrl:b.companyUrl,
  drug:b.drug||"",endpointInterpretation:b.endpointInterpretation||a.endpointOutcome};
};

function reconcile():{
 asOf:string;sourceAsOf:string;totalPool:number;activeTotal:number;
 counts:{PRE_DATA:number;POST_DATA:number;HISTORICAL:number;VERIFY:number};
 promotedNcts:string[];
 pre:ActivePhase3Trial[];post:ActivePhase3Trial[];
 snapshot:typeof ledger;
}{
 assert(ledger.total===762&&ledger.rows.length===762,"762_LENGTH");
 const unique=new Set(ledger.rows.map(r=>r.nctId));
 assert(unique.size===762,"NCT_DUPLICATE");
 const promotions=new Set<string>([...PROMOTED_ISSUER_NCTS,...IONIS_VERIFIED_READOUTS.map(r=>r.nctId),
  ...NEW_VERIFIED_READOUTS.map(r=>r.nctId)]);
 assert(promotions.size===14,"PROMOTION_DUPLICATE");
 const ionisCorrections=new Map<string,(typeof IONIS_VERIFIED_READOUTS)[number]>(IONIS_VERIFIED_READOUTS.map(r=>[r.nctId,r]));
 const newCorrections=new Map<string,(typeof NEW_VERIFIED_READOUTS)[number]>(NEW_VERIFIED_READOUTS.map(r=>[r.nctId,r]));
 assert(NEW_VERIFIED_READOUTS.length===6&&NEW_VERIFIED_READOUTS.every(r=>
  iso(r.evidenceDate)&&r.evidenceDate<=ACTIVE_PHASE3_COHORT_AS_OF&&
  r.evidenceUrl.startsWith("https://")&&
  ledger.rows.some(x=>x.nctId===r.nctId&&x.ticker===r.ticker&&
   x.classificationCode==="P3_PRE_DATA_CANDIDATE"&&trialLifecycle(x.registryStatus)==="ACTIVE")),
  "NEW_READOUT_SOURCE");
 assert(IONIS_VERIFIED_READOUTS.every(r=>iso(r.evidenceDate)&&r.evidenceDate<=ACTIVE_PHASE3_COHORT_AS_OF&&
  r.evidenceUrl.startsWith("https://")&&ledger.rows.some(x=>x.nctId===r.nctId&&x.ticker==="IONS")),"IONIS_READOUT_SOURCE");
 const patched:BaseRow[]=ledger.rows.map(r=>{
  if(!promotions.has(r.nctId))return r;
  assert(trialLifecycle(r.registryStatus)==="ACTIVE"&&
   r.classificationCode==="P3_PRE_DATA_CANDIDATE","PROMOTION_STAGE_"+r.nctId);
  const newReadout=ionisCorrections.get(r.nctId)||newCorrections.get(r.nctId);
  if(newReadout){
   return {...r,classificationCode:"P3_POST_DATA_ISSUER",
    classification:"P3 POST-DATA · verified public readout",
    classificationEvidence:newReadout.evidence,
    classificationVerified:true,readoutEvidenceType:newReadout.evidenceType,
    readoutSourceDate:newReadout.evidenceDate,readoutEvidenceUrl:newReadout.evidenceUrl,
    readoutOutcome:newReadout.outcome,drug:newReadout.drug,
    ...(r.nctId==="NCT04849741"?{fdaApplicationStatus:"FDA_APPROVED_HISTORICAL"}:{}),
    ...(r.nctId==="NCT05208047"?{fdaApplicationStatus:"FDA_NDA_ACCEPTED_PRIORITY_REVIEW",
     fdaReviewType:"PRIORITY_REVIEW",pdufaGoalDate:"2026-11-30"}:{})};
  }
  const matched=matchedIssuer(r.nctId);
  assert(matched,"PROMOTION_SOURCE_"+r.nctId);
  const e=endpoints.get(r.nctId)!;
  const b=issuers.get(r.nctId)!;
  assert(b.ticker===r.ticker,"PROMOTION_TICKER_"+r.nctId);
  const mixed=r.nctId==="NCT05031780";
  return {...r,
   classificationCode:"P3_POST_DATA_ISSUER",
   classification:"P3 POST-DATA · issuer readout documented",
   classificationEvidence:"Original issuer Phase 3 readout reconciled against exact-NCT endpoint adjudication; "+(b.endpointInterpretation||e.endpointOutcome),
   classificationVerified:true,
   readoutEvidenceType:"ISSUER_READOUT",
   readoutSourceDate:matched!.evidenceDate,
   readoutEvidenceUrl:matched!.evidenceUrl,
   readoutOutcome:mixed?"MIXED_COPRIMARY_RESULTS":e.endpointOutcome,
   drug:r.drug||matched!.drug};
 });
 const counts=Object.fromEntries(ledger.classifications.map(c=>[c.code,0])) as typeof ledger.counts;
 patched.forEach(r=>{assert(Object.prototype.hasOwnProperty.call(counts,r.classificationCode),"UNRECOGNIZED_CLASS");const key=r.classificationCode as keyof typeof counts;counts[key]++;});
 const withCounts={...ledger,asOf:ACTIVE_PHASE3_COHORT_AS_OF,counts,
  note:ledger.note+" Read-only reconciliation: fourteen dated issuer, FDA and peer-reviewed source-matched readouts promoted from PRE to POST; historical source preserved.",
  rows:patched};
 const pre:ActivePhase3Trial[]=[],post:ActivePhase3Trial[]=[];
 let historical=0,verify=0;
 for(const row of patched){
  const lifecycle=trialLifecycle(row.registryStatus);
  if(lifecycle==="HISTORICAL"){historical++;continue;}
  if(lifecycle==="VERIFY"){verify++;continue;}
  const prev=ledger.rows.find(r=>r.nctId===row.nctId)!;
  if(row.classificationCode==="P3_PRE_DATA_CANDIDATE"){
   pre.push({...row,cohort:"PRE_DATA",evidenceBasis:"PUBLIC_READOUT_NOT_VERIFIED",
    originalClassificationCode:prev.classificationCode,correctionApplied:false});
  }else if(row.classificationCode==="P3_POST_DATA_ISSUER"||row.classificationCode==="P3_POST_DATA_REGISTRY"){
   post.push({...row,cohort:"POST_DATA",evidenceBasis:row.readoutEvidenceType==="FDA_APPROVAL_SUPPORTING_TRIAL"?"FDA_APPROVAL_SUPPORTING_TRIAL":
    row.readoutEvidenceType==="PEER_REVIEWED_OPEN_LABEL_RESULTS"?"PEER_REVIEWED_RESULTS":
    row.classificationCode==="P3_POST_DATA_ISSUER"?"ISSUER_READOUT":"REGISTRY_RESULTS_POSTED",
    originalClassificationCode:prev.classificationCode,correctionApplied:promotions.has(row.nctId)});
  }else throw Error("ACTIVE_PHASE3_UNCLASSIFIED_"+row.nctId);
 }
 const byTicker=(a:ActivePhase3Trial,b:ActivePhase3Trial)=>a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId);
 pre.sort(byTicker);post.sort(byTicker);
 assert(pre.length===229&&post.length===29&&historical===501&&verify===3,"RECONCILED_COUNTS");
 assert(new Set([...pre,...post].map(r=>r.nctId)).size===258,"COHORT_DUPLICATE");
 assert(post.filter(r=>r.correctionApplied).length===14,"PROMOTIONS_NOT_EXACTLY_FOURTEEN");
 assert(patched.length===762,"PRESERVE_ARCHIVE");
 return {asOf:ACTIVE_PHASE3_COHORT_AS_OF,sourceAsOf:ledger.asOf,totalPool:762,activeTotal:258,
  counts:{PRE_DATA:pre.length,POST_DATA:post.length,HISTORICAL:historical,VERIFY:verify},
  promotedNcts:[...promotions],pre,post,snapshot:withCounts};
}
/** Cached immutable derived snapshot: does not change source JSON or historical RAAS. */
export const activePhase3Cohorts=reconcile();
