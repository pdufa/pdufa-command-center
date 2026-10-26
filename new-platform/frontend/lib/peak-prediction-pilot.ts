import { PREDICTION_METRICS } from "./prediction-priority-metrics";

/**
 * Source-linked, manually assembled one-trial research demonstration.
 * FROZEN October 26, 2026. NOT a candidate-assessments runtime score,
 * an adjudicated HOP historical cohort, an FDA approval prediction, or
 * a replacement for reviewer-certified SCIENCE-40 investigation.
 */
export const PEAK_PILOT = {
  snapshotDate: "2026-10-26",
  membershipLastSeen: "2026-10-25",
  stage: "GEM",
  exactPipelineId: "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130",
  ticker: "COGT",
  drug: "Bezuclastinib + sunitinib",
  trialName: "PEAK Phase 3",
  indication: "GIST after prior imatinib",
  nctId: "NCT05208047",
  pdufaDate: "2026-11-30",
  modelEligibleHistoricalCases: 0,
  researchedHistoricalPrecedents: 3,
  randomizedPatients: 413,
  combinationN: 204,
  activeControlN: 209,
  medianPfsCombinationMonths: 16.5,
  medianPfsControlMonths: 9.2,
  hazardRatioPfs: 0.50,
  hazardRatioLow95: 0.39,
  hazardRatioHigh95: 0.65,
  orrCombinationPct: 46,
  orrControlPct: 26,
  grade3LiverEnzymeCombinationPct: 10.8,
  grade3LiverEnzymeControlPct: 1.4,
  trtAeDiscontinuationCombinationPct: 7.4,
  trtAeDiscontinuationControlPct: 3.8,
} as const;

export const PEAK_SOURCES = {
  membership: {
    name:"Saved GEM membership snapshot, 2026-10-25",
    url:"https://github.com/pdufa/pdufa-command-center/blob/main/data/gem_stage_membership.json",
  },
  asco: {
    name:"ASCO/JCO PEAK Phase 3 abstract (May 2026)",
    url:"https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.11500",
  },
  sec: {
    name:"Cogent SEC 10-Q (August 2026)",
    url:"https://www.sec.gov/Archives/edgar/data/1622229/000119312526342393/cogt-20260630.htm",
  },
  company: {
    name:"Cogent detailed PEAK results (May 30, 2026)",
    url:"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3",
  },
  fdaFiling: {
    name:"Cogent reports FDA NDA acceptance and Priority Review (May 28, 2026)",
    url:"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-fda-acceptance-new-drug-0",
  },
  sunitinib: {
    name:"FDA-approved SUTENT labeling, GIST pivotal study",
    url:"https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=43a4d7f8-48ae-4a63-9108-2fa8e3ea9d9c",
  },
  regorafenib: {
    name:"NCI GIST treatment summary, GRID trial",
    url:"https://www.cancer.gov/types/soft-tissue-sarcoma/hp/gist-treatment-pdq",
  },
  regorafenibFDA: {
    name:"FDA orphan-drug approval entry, regorafenib in GIST",
    url:"https://www.accessdata.fda.gov/scripts/opdlisting/oopd/detailedIndex.cfm?cfgridkey=329410",
  },
  ripretinib: {
    name:"FDA authors' approval summary for ripretinib (INVICTUS)",
    url:"https://pubmed.ncbi.nlm.nih.gov/36485007/",
  },
} as const;

export type PilotMetricReview = {
  rank: number;
  label: string;
  observed: string;
  status: "PUBLISHED" | "PARTIAL" | "NOT_REVIEWED";
  source: keyof typeof PEAK_SOURCES | null;
  note: string;
};

const observations: ReadonlyArray<readonly [
  string, PilotMetricReview["status"], PilotMetricReview["source"], string
]> = [
  ["PFS HR 0.50; p < 0.0001","PUBLISHED","asco","Primary PFS benefit as reported at ASCO; independent FDA efficacy review not yet available"],
  ["Median PFS +7.3 months; ORR +20 percentage points","PUBLISHED","asco","16.5 vs 9.2 months; 46% vs 26% responses"],
  ["—","NOT_REVIEWED",null,"Independent review of statistical analysis plan and multiplicity controls pending"],
  ["Randomized 1:1; open-label; blinded independent central PFS review","PUBLISHED","asco","Treatment was not blinded, although central endpoint adjudication was blinded"],
  ["0 treatment-related deaths reported in combination arm; SAE analysis pending","PARTIAL","asco","Cannot infer there were zero deaths overall or zero serious adverse events"],
  ["—","NOT_REVIEWED",null,"Full NDA CMC, manufacturing and facility inspection data not publicly adjudicated"],
  ["BICR-assessed PFS; independent endpoint suitability review pending","PARTIAL","asco","Documented endpoint does not equal a fully validated regulatory endpoint assessment"],
  ["Priority Review; no review issues identified at acceptance (company-reported)","PUBLISHED","fdaFiling","May 28, 2026 report; later issues cannot be ruled out"],
  ["PFS HR 95% CI 0.39–0.65; ORR difference 95% CI 10.6–28.6 pp","PUBLISHED","asco","CI is a clinical effect interval, not an approval-probability interval"],
  ["—","NOT_REVIEWED",null,"Missing-data mechanisms, protocol deviations and estimand handling unreviewed"],
  ["413 randomized (204 combination; 209 control), previously treated with imatinib","PUBLISHED","asco","Applicability to FDA labeled population requires application-level check"],
  ["Nov 2025 readout and May 2026 full data precede Oct 26, 2026 cutoff","PUBLISHED","sec","Only verified pre-cutoff public evidence can enter forecast inputs"],
];

export const PEAK_PILOT_METRICS: ReadonlyArray<PilotMetricReview> = observations.map(([observed,status,source,note],index)=>({
  rank:index+1,label:PREDICTION_METRICS[index].label,observed,status,source,note,
}));

export type HistoricalPrecedent = {
  drug: string;
  trial: string;
  treatmentLine: string;
  outcome: string;
  medianPfs: string;
  hazardRatio: string;
  source: keyof typeof PEAK_SOURCES;
  qualification: string;
};

export const PEAK_HISTORICAL_PRECEDENTS: ReadonlyArray<HistoricalPrecedent> = [
  {
    drug:"Sunitinib",
    trial:"Pivotal GIST study",
    treatmentLine:"Second-line after imatinib (closest line)",
    outcome:"FDA approved (2006)",
    medianPfs:"24.1 vs 6.0 weeks (sunitinib vs placebo)",
    hazardRatio:"0.33",
    source:"sunitinib",
    qualification:"Similar disease and treatment line, but placebo comparator and different study design",
  },
  {
    drug:"Regorafenib",
    trial:"GRID · NCT01271712",
    treatmentLine:"Third-line or later after imatinib and sunitinib",
    outcome:"FDA approved (2013)",
    medianPfs:"4.8 vs 0.9 months (regorafenib vs placebo)",
    hazardRatio:"0.27",
    source:"regorafenib",
    qualification:"Same disease and PFS endpoint, but later-line and placebo-controlled",
  },
  {
    drug:"Ripretinib",
    trial:"INVICTUS · NCT03353753",
    treatmentLine:"Fourth-line or later",
    outcome:"FDA approved (2020)",
    medianPfs:"6.3 vs 1.0 months (ripretinib vs placebo)",
    hazardRatio:"0.15",
    source:"ripretinib",
    qualification:"Same disease and endpoint; very different treatment line and placebo comparator",
  },
];

export const PEAK_SOURCE_COVERAGE = {
  directlyReported: PEAK_PILOT_METRICS.filter(m=>m.status==="PUBLISHED").length,
  partiallyReviewed:PEAK_PILOT_METRICS.filter(m=>m.status==="PARTIAL").length,
  notReviewed:PEAK_PILOT_METRICS.filter(m=>m.status==="NOT_REVIEWED").length,
} as const;

export function validatePeakPilot(): void {
  if(PEAK_PILOT_METRICS.length!==12
      || PEAK_SOURCE_COVERAGE.directlyReported+PEAK_SOURCE_COVERAGE.partiallyReviewed+PEAK_SOURCE_COVERAGE.notReviewed!==12
      || PEAK_PILOT_METRICS.some((row,i)=>row.rank!==i+1 || row.label!==PREDICTION_METRICS[i].label
        || (row.status==="NOT_REVIEWED" && row.observed!=="—")
        || (row.status==="PUBLISHED" && !row.source))
      || PEAK_HISTORICAL_PRECEDENTS.length!==3
      || PEAK_PILOT.modelEligibleHistoricalCases!==0
      || (PEAK_PILOT.medianPfsCombinationMonths-PEAK_PILOT.medianPfsControlMonths).toFixed(1)!=="7.3"
      || PEAK_PILOT.orrCombinationPct-PEAK_PILOT.orrControlPct!==20
      || PEAK_PILOT.randomizedPatients!==PEAK_PILOT.combinationN+PEAK_PILOT.activeControlN) {
    throw new Error("GEM PEAK pilot has contradictory trial identity, numbers, or evidence states");
  }
}
