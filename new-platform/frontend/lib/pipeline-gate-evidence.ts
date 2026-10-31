/** One shared, fail-closed evidence-stage checklist for each exact-NCT research row.
 * It audits what information is *recorded*; it does not qualify a drug,
 * interpret clinical outcomes, infer a verified FDA milestone or place a trade.
 */
import type { PipelineResearchRow } from "./pipeline-research-view";
export type ResearchGateStatus="HISTORICAL_POINTER"|"SOURCE_REVIEW_REQUIRED"|"MISSING_EVIDENCE"|"IDENTITY_CONFLICT";
export type ResearchGate={
 id:"registry"|"pool"|"listing"|"readout"|"therapy"|"rights"|"pdufa";
 title:string;
 status:ResearchGateStatus;
 explanation:string;
 sourceUrl:string|null;
};
const url=(v:unknown)=>typeof v==="string"&&/^https:\/\/[^\s]+$/.test(v)?v:null;
/** Must remain a documentation-only queue; no value here means FDA-qualified. */
export function pipelineEvidenceGates(row:PipelineResearchRow,today:string):ResearchGate[]{
 const exact=row.poolStatus==="EXACT_MATCH";
 const release=row.timeline?.phase3DataRelease;
 const target=row.timeline?.pdufaTarget;
 const historical=typeof row.capAsOf==="string"?row.capAsOf.slice(0,10):"date unavailable";
 const releaseKnown=!!release?.date&&!!url(release?.sourceUrl)&&release.date<=today;
 const targetKnown=!!target?.date&&!!url(target?.sourceUrl);
 return [
  {id:"pool",title:"Exact NCT and issuer reconciliation",
   status:exact?"HISTORICAL_POINTER":"IDENTITY_CONFLICT",
   explanation:exact?"Historical POOL has a matching NCT and ticker; this does not verify product rights or current listing.":
    "Exact NCT plus ticker ownership has not been reconciled in the source POOL.",
   sourceUrl:url(row.sourceUrl)},
  {id:"registry",title:"Phase 3 registry milestone",
   status:"HISTORICAL_POINTER",
   explanation:row.censusStatus==="COMPLETED"?
    "The dated registry snapshot says COMPLETED. Completion is NOT proof of a public pivotal readout, efficacy or FDA acceptance.":
    "Historical registry status: "+row.censusStatus+". Check current registry and any independent pivotal readout.",
   sourceUrl:url(row.sourceUrl)},
  {id:"listing",title:"Current U.S. listing and $300M–$10B market cap",
   status:"MISSING_EVIDENCE",
   explanation:"The market-cap figure is a historical pointer dated "+historical+
    ", not independently verified current listing and source-dated market cap.",
   sourceUrl:null},
  {id:"readout",title:"Public pivotal Phase 3 results and date",
   status:releaseKnown?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
   explanation:releaseKnown?"A dated public release is recorded; independently confirm pivotal design, drug, disease and final readout against primary study documents.":
    "No eligible exact-program public pivotal Phase 3 result release is independently established here.",
   sourceUrl:releaseKnown?url(release?.sourceUrl):null},
  {id:"therapy",title:"Exact proposed therapy, indication and treatment line",
   status:row.drug&&row.indication&&exact?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
   explanation:row.drug&&row.indication&&exact?"Drug and indication names are recorded in POOL, but NCT linkage, line, population and commercial program still need independent verification.":
    "Exact drug, disease/indication and treatment-line linkage is missing or not reconciled.",
   sourceUrl:exact?url(row.sourceUrl):null},
  {id:"rights",title:"Public-company commercial rights and indication",
   status:"MISSING_EVIDENCE",
   explanation:"Sourced sponsor/developer commercial rights, territorial rights, license agreements and an independently verified public listing are required.",
   sourceUrl:null},
  {id:"pdufa",title:"FDA action-date evidence and research cutoff",
   status:targetKnown?"SOURCE_REVIEW_REQUIRED":"MISSING_EVIDENCE",
   explanation:targetKnown?"An FDA target date is recorded; independently verify exact product/indication, extensions and the PDUFA minus-three-day window.":
    "No source-verified exact-program FDA PDUFA action target is established in this review.",
   sourceUrl:targetKnown?url(target?.sourceUrl):null},
 ];
}
export function pipelineGateCounts(row:PipelineResearchRow,today:string){
 const gates=pipelineEvidenceGates(row,today);
 return {total:gates.length,missing:gates.filter(g=>g.status==="MISSING_EVIDENCE").length,
  review:gates.filter(g=>g.status==="SOURCE_REVIEW_REQUIRED").length,
  historical:gates.filter(g=>g.status==="HISTORICAL_POINTER").length,
  conflicts:gates.filter(g=>g.status==="IDENTITY_CONFLICT").length,
  qualified:false as const};
}
