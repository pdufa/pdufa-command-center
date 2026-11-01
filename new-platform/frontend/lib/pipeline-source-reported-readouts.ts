/** Exact-NCT, source-reported Phase 3 evidence snapshots.
 * These are research pointers extracted from dated original sponsor releases.
 * Sponsor-reported primary endpoints are NOT independently validated efficacy,
 * a licensed indication, a current issuer market-cap check, FDA PASS, PDUFA
 * booking, proof of comparative superiority or a trading recommendation.
 */
export type SponsorReadout={
 nctId:string; ticker:"ABVX"; programKey:"ABVX|OBEFAZIMOD|ULCERATIVE_COLITIS";
 study:string; therapy:string; indication:string;
 sourcePublished:string; sourceUrl:string;
 weeks:number; investigationalArm:"obefazimod 50 mg daily"; comparator:"placebo";
 remissionExperimentalPct:number; remissionPlaceboPct:number;
 placeboAdjustedDifferencePp:number; pValue:string;
 treatmentN:number; treatmentEvents:number; placeboN:number; placeboEvents:number;
 population:string; caveat:string;
 sourceType:"ORIGINAL_SPONSOR_TOPLINE"; reviewerStatus:"REVIEW_REQUIRED";
 programEligibility:"NOT_ESTABLISHED"; pdufaTarget:null;
};
const induction="https://ir.abivax.com/news-releases/news-release-details/abivax-announces-positive-phase-3-results-both-abtect-8-week";
const maintenance="https://ir.abivax.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial";
const common={
 ticker:"ABVX" as const,
 programKey:"ABVX|OBEFAZIMOD|ULCERATIVE_COLITIS" as const,
 therapy:"Obefazimod (ABX464)",
 indication:"Moderately to severely active ulcerative colitis",
 investigationalArm:"obefazimod 50 mg daily" as const,
 comparator:"placebo" as const,
 sourceType:"ORIGINAL_SPONSOR_TOPLINE" as const,
 reviewerStatus:"REVIEW_REQUIRED" as const,
 programEligibility:"NOT_ESTABLISHED" as const,
 pdufaTarget:null,
};
export const SPONSOR_PHASE3_READOUTS:readonly SponsorReadout[]=[
 {...common,nctId:"NCT05507203",study:"ABTECT-1 · pivotal induction (Study 105)",sourcePublished:"2025-07-22",sourceUrl:induction,
  weeks:8,remissionExperimentalPct:21.7,remissionPlaceboPct:2.5,placeboAdjustedDifferencePp:19.3,pValue:"p < 0.0001",
  treatmentN:318,treatmentEvents:69,placeboN:158,placeboEvents:4,
  population:"8-week randomized double-blind UC induction population",
  caveat:"The reported adjusted difference is the source's stratification-adjusted difference; crude observed rates subtract to a different value. This is not head-to-head evidence against an approved therapy."},
 {...common,nctId:"NCT05507216",study:"ABTECT-2 · pivotal induction (Study 106)",sourcePublished:"2025-07-22",sourceUrl:induction,
  weeks:8,remissionExperimentalPct:19.8,remissionPlaceboPct:6.3,placeboAdjustedDifferencePp:13.4,pValue:"p = 0.0001",
  treatmentN:318,treatmentEvents:63,placeboN:159,placeboEvents:10,
  population:"8-week randomized double-blind UC induction population",
  caveat:"For the 25 mg dose, the primary endpoint was not statistically significant in ABTECT-2. Rates are placebo comparisons only, not an approved-drug ranking."},
 {...common,nctId:"NCT05535946",study:"ABTECT Maintenance · pivotal 44-week maintenance (Study 107)",
  sourcePublished:"2026-06-01",sourceUrl:maintenance,
  weeks:44,remissionExperimentalPct:51.3,remissionPlaceboPct:10.4,placeboAdjustedDifferencePp:40.3,pValue:"p < 0.0001",
  treatmentN:195,treatmentEvents:100,placeboN:192,placeboEvents:20,
  population:"Induction responders re-randomized for maintenance; 580 maintenance participants overall",
  caveat:"Responder-enriched, re-randomized maintenance cohort. Do not compare its rates directly with unselected induction populations or unrelated therapy trials."}
];
export function getSponsorPhase3Readout(nctId:string,ticker:string):SponsorReadout|null{
 if(ticker!=="ABVX"||!/^NCT\d{8}$/.test(nctId))return null;
 return SPONSOR_PHASE3_READOUTS.find(x=>x.nctId===nctId)||null;
}
export function sponsorReadoutProgramCount():number{
 return new Set(SPONSOR_PHASE3_READOUTS.map(x=>x.programKey)).size;
}
