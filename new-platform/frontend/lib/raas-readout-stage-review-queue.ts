/** Research intake for trials NOT yet assigned to either RAAS spreadsheet.
 * Only the dated, exact-NCT issuer-readout census can supply this queue.
 * Registry completion/results posting alone never assigns PRE or POST, and
 * this is NOT a rating, a 762-NCT score feed, or an 11k+ POOL scan.
 */
import type {ReadoutClassification,ReadoutRow} from "./phase3-public-readout";

export type RaasReadoutStageReviewItem={
 nctId:string;ticker:string;company:string;registryStatus:string;
 registrySourceUrl:string;researchCensusDate:string;
 lastIssuerReadoutSourceSnapshot:string;
 stage:"UNVERIFIED";topRaasScore:null;bottomRaasScore:null;
 reviewStatus:"NEEDS_ISSUER_READOUT_IDENTITY_EVIDENCE";
 exactNctToIssuerProgramConfirmed:false;
 latestDatedIssuerReadoutOrNegativeCheckVerified:false;
 sourceDate:string|null;issuerEvidenceUrl:string|null;
 requiredProof:string;nextAction:string;
};
const FIELDS=[
 "nctId","ticker","company","registryStatus","registrySourceUrl",
 "researchCensusDate","lastIssuerReadoutSourceSnapshot","stage",
 "exactNctToIssuerProgramConfirmed","latestDatedIssuerReadoutOrNegativeCheckVerified",
 "sourceDate","issuerEvidenceUrl","requiredProof","nextAction",
 "topRaasScore","bottomRaasScore"
] as const;
const BASE="https://clinicaltrials.gov/study/";
const csvSafe=(raw:unknown)=>{
 const s=raw==null?"":String(raw);
 // Spreadsheet formula injection: names and status are external data.
 const safe=/^[=+@\-\t\r]/.test(s)?"'"+s:s;
 return /[",\r\n]/.test(safe)?'"'+safe.replace(/"/g,'""')+'"':safe;
};
const csvLine=(values:unknown[])=>values.map(csvSafe).join(",");
const validDay=(x:unknown):x is string=>typeof x==="string"&&
 /^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+"T00:00:00Z"))&&
 new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;

export function buildRaasReadoutStageReviewQueue(data:ReadoutClassification){
 if(!data||data.total!==741||!validDay(data.censusDate)||
  !validDay(data.sourceAsOf)||data.censusDate>data.sourceAsOf||
  !Array.isArray(data.pre)||!Array.isArray(data.post)||
  !Array.isArray(data.unverified)||
  data.pre.length+data.post.length+data.unverified.length!==data.total)
  throw Error("RAAS_TOP_BOTTOM_STAGE_REVIEW_CENSUS_REQUIRED");
 const seen=new Set<string>();
 function verifyRow(row:ReadoutRow,expected:"PRE_AS_OF_CHECK"|"POST_PUBLIC_READOUT"|null){
  if(!row||!/^NCT\d{8}$/.test(row.nctId)||seen.has(row.nctId)||
   !/^[A-Z0-9.-]{1,15}$/.test(row.ticker)||
   typeof row.company!=="string"||!row.company.trim()||
   row.sourceUrl!==BASE+row.nctId||
   typeof row.status!=="string"||row.status.length>60||
   (expected===null?row.evidence!==null:
    !row.evidence||row.evidence.kind!==expected||
    row.evidence.nctId!==row.nctId||row.evidence.ticker!==row.ticker||
    !validDay(row.evidence.evidenceDate)||
    row.evidence.evidenceDate>data.sourceAsOf||
    !row.evidence.evidenceUrl.startsWith("https://")))
   throw Error("RAAS_TOP_BOTTOM_STAGE_REVIEW_UNVERIFIED_SOURCE_IDENTITY");
  seen.add(row.nctId);
 }
 for(const row of data.pre)verifyRow(row,"PRE_AS_OF_CHECK");
 for(const row of data.post)verifyRow(row,"POST_PUBLIC_READOUT");
 const rows:RaasReadoutStageReviewItem[]=[];
 for(const row of data.unverified){
  verifyRow(row,null);
  rows.push({
   nctId:row.nctId,ticker:row.ticker,company:row.company,
   registryStatus:row.status,registrySourceUrl:row.sourceUrl,
   researchCensusDate:data.censusDate,
   lastIssuerReadoutSourceSnapshot:data.sourceAsOf,
   stage:"UNVERIFIED",topRaasScore:null,bottomRaasScore:null,
   reviewStatus:"NEEDS_ISSUER_READOUT_IDENTITY_EVIDENCE",
   exactNctToIssuerProgramConfirmed:false,
   latestDatedIssuerReadoutOrNegativeCheckVerified:false,
   sourceDate:null,issuerEvidenceUrl:null,
   requiredProof:"Exact NCT+issuer+treatment+indication matched to dated issuer public readout or independently documented negative issuer-source check",
   nextAction:"Research company IR, SEC filings and source-dated Phase 3 disclosures; verify exact NCT/therapy and retain timestamped URL. Do not infer a stage from ClinicalTrials.gov results posting or trial status."
  });
 }
 if(seen.size!==data.total||rows.length!==data.unverified.length)
  throw Error("RAAS_TOP_BOTTOM_STAGE_REVIEW_ROSTER_INCOMPLETE");
 rows.sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
 const csv=[FIELDS.join(","),...rows.map(x=>csvLine([
  x.nctId,x.ticker,x.company,x.registryStatus,x.registrySourceUrl,
  x.researchCensusDate,x.lastIssuerReadoutSourceSnapshot,x.stage,
  x.exactNctToIssuerProgramConfirmed,x.latestDatedIssuerReadoutOrNegativeCheckVerified,
  x.sourceDate,x.issuerEvidenceUrl,x.requiredProof,x.nextAction,
  x.topRaasScore,x.bottomRaasScore
 ]))].join("\r\n")+"\r\n";
 return {
  csv,
  summary:{
   totalSourceCensusNcts:data.total,
   sourceClassifiedTopNcts:data.pre.length,
   sourceClassifiedBottomNcts:data.post.length,
   awaitingStageVerification:rows.length,
   raasRatingsAssignedByQueue:0,
   sourceCensusDate:data.censusDate,
   issuerReadoutEvidenceAsOf:data.sourceAsOf
  },
  rows
 };
}
