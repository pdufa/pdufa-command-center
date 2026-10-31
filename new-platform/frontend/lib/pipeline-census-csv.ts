/** Authenticated export of the pinned historical Phase 3 review queue.
 * Never promotes registry-completed studies into qualifying post-Phase-3 programs.
 * One record per exact NCT, with source identity, source date and explicit gaps.
 */
import type { FunnelResult } from "./pool-pipeline-funnel";

export const CENSUS_CSV_HEADERS = [
 "nct_id","ticker","company","registry_status","historical_market_cap_usd",
 "market_cap_checked_utc","clinicaltrials_source_url","pool_identity_link",
 "post_phase3_registry_status","phase3_public_release_date","pdufa_date",
 "pipeline_qualification","research_review_notes","historical_census_as_of"
] as const;

function safeCell(input:unknown):string {
 const raw=String(input??"");
 // CSV-import spreadsheet formula injection prevention: never execute source text.
 const safe=/^[\t\r\n ]*[=+\-@]/.test(raw)?"'"+raw:raw;
 return '"'+safe.replaceAll('"','""')+'"';
}

export function renderPhase3CensusCsv(data:FunnelResult):string {
 const {reviewRows,overview}=data;
 if(reviewRows.length!==741||overview.historicalPhase3Records!==741
    ||overview.historicalCompletedRecords!==375
    ||!overview.censusAsOf||new Set(reviewRows.map(r=>r.nctId)).size!==741)
  throw Error("Historical Phase 3 source corpus incomplete or changed");
 const rows=reviewRows.slice().sort((a,b)=>a.nctId.localeCompare(b.nctId)).map(r=>{
  if(!/^NCT\d{8}$/.test(r.nctId)||r.sourceUrl!=="https://clinicaltrials.gov/study/"+r.nctId
     ||r.qualification!=="NEEDS_REVIEW"||!r.capAsOf||!Number.isFinite(r.capUsd)
     ||r.capUsd<300_000_000||r.capUsd>10_000_000_000)
    throw Error("Historical Phase 3 export source invalid");
  return [
   r.nctId,r.ticker,r.company,r.censusStatus,r.capUsd,
   r.capAsOf,r.sourceUrl,r.poolStatus,r.postPhase3Evidence,
   r.timeline?.phase3DataRelease?.date||"",
   r.timeline?.pdufaTarget?.date||"",
   r.qualification,
   "Historic research pointer only; reverify current listing, cap, readout, drug/indication and commercial rights",
   overview.censusAsOf,
  ];
 });
 return [CENSUS_CSV_HEADERS,...rows].map(row=>row.map(safeCell).join(",")).join("\r\n")+"\r\n";
}
