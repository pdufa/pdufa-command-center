/** PEAK GO18 source review queue. Research-only, not independent regulatory adjudication. */
export const PEAK_GO18_REVIEW = {
  trialId: "NCT05208047",
  asOf: "2026-10-26",
  certified: false,
  approvalProbability: null,
  observations: [
    {assessmentId:"S07", topic:"Multiplicity and type-I error", publishedObservation:"PFS and ORR p<0.0001 reported; no full multiplicity plan reviewed", sourceUrl:"https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.11500", evidenceState:"PARTIAL_SOURCE", gap:"Obtain final SAP, endpoint hierarchy and alpha-spending rules"},
    {assessmentId:"S08", topic:"Missing data and intercurrent events", publishedObservation:"Crossover allowed at BICR-confirmed progression", sourceUrl:"https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.11500", evidenceState:"PARTIAL_SOURCE", gap:"Obtain estimand, censoring, crossover and missing-data sensitivity methods"},
    {assessmentId:"S12", topic:"Comparator suitability", publishedObservation:"Active comparator sunitinib 37.5 mg daily", sourceUrl:"https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.11500", evidenceState:"PARTIAL_SOURCE", gap:"Independent standard-of-care and dosing suitability review"},
    {assessmentId:"S16", topic:"Serious adverse events", publishedObservation:"Sponsor SEC exhibit reports serious adverse reactions 16.7% vs 11.5%", sourceUrl:"https://www.sec.gov/Archives/edgar/data/1622229/000119312525273315/d54064dex991.htm", evidenceState:"PARTIAL_SOURCE", gap:"Obtain complete SAE narratives, causality and exposure-adjusted analyses"},
    {assessmentId:"S19", topic:"Long-term safety", publishedObservation:"ASCO reports hepatic events managed with dose modifications", sourceUrl:"https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.11500", evidenceState:"PARTIAL_SOURCE", gap:"Obtain long-term follow-up and cumulative exposure data"},
    {assessmentId:"S20", topic:"Benefit-risk", publishedObservation:"PFS benefit with greater grade 3+ ALT/AST and anemia rates", sourceUrl:"https://ascopubs.org/doi/10.1200/JCO.2026.44.16_suppl.11500", evidenceState:"PARTIAL_SOURCE", gap:"Independent integrated efficacy-safety benefit-risk adjudication"},
    {assessmentId:"S15", topic:"Protocol amendments and deviations", publishedObservation:null, sourceUrl:null, evidenceState:"MISSING", gap:"Obtain protocol versions, amendments and deviation tables"},
    {assessmentId:"S31", topic:"Manufacturing process characterization", publishedObservation:null, sourceUrl:null, evidenceState:"MISSING", gap:"Obtain validated process characterization documentation"},
    {assessmentId:"S32", topic:"Commercial validation", publishedObservation:null, sourceUrl:null, evidenceState:"MISSING", gap:"Obtain process validation and commercial readiness records"},
    {assessmentId:"S33", topic:"Stability and analytical methods", publishedObservation:null, sourceUrl:null, evidenceState:"MISSING", gap:"Obtain stability, specifications and validated methods"},
    {assessmentId:"S34", topic:"Facilities and quality systems", publishedObservation:null, sourceUrl:null, evidenceState:"MISSING", gap:"Obtain relevant facility and inspection status"},
    {assessmentId:"S35", topic:"CMC deficiencies and supply", publishedObservation:null, sourceUrl:null, evidenceState:"MISSING", gap:"Obtain regulator correspondence and supply risk assessment"},
  ],
} as const;
