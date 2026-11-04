/** Dated, public ClinicalTrials.gov provenance for the full RAAS research pool.
 * Registry outcomes do NOT classify issuer-public Phase 3 announcements.
 * No numerical RAAS scores or trading suggestions are calculated here.
 */
import {NextResponse} from "next/server";
import evidence from "../../../data/raas-registry-evidence-census.json";
export const dynamic="force-dynamic";
export async function GET(){
 if(evidence.schemaVersion!==1||
   evidence.scope!=="RAAS_REGISTRY_EVIDENCE_SOURCE_CENSUS"||
   evidence.counts.total!==762||evidence.records.length!==762)
  return NextResponse.json({error:"RAAS_REGISTRY_CENSUS_INVALID"},{status:503});
 return NextResponse.json({
   sourceAsOf:evidence.sourceAsOf,
   counts:evidence.counts,
   rows:evidence.records.map(r=>({
    nctId:r.nctId,ticker:r.ticker,captureStatus:r.captureStatus,
    capturedAt:r.capturedAt,registryUpdatedAt:r.registryUpdatedAt,
    registryStatus:r.registryStatus,hasPostedResults:r.hasPostedResults,
    analysisCount:r.analysisCount,primaryOutcomeCount:r.primaryOutcomeCount,
    firstPrimaryEndpoint:r.firstPrimaryEndpoint,
    sourceUrl:r.sourceUrl,issuerReadoutStage:null,approvedRaasScore:null
   }))
 },{headers:{"Cache-Control":"public, s-maxage=300, stale-while-revalidate=1200"}});
}
