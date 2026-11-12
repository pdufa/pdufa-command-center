/** Proposed SCIENCE question catalog v0.1. Research-only: not a scored or certified dossier. */
export const SCIENCE_QUESTION_CATALOG_VERSION = "science-questions-v0.1-proposed" as const;
export const SCIENCE_QUESTION_CATALOG = [
  {
    "id": "S01",
    "layer": 1,
    "layerName": "Clinical efficacy",
    "question": "Was the primary endpoint met?",
    "requiredEvidence": "protocol and efficacy results"
  },
  {
    "id": "S02",
    "layer": 1,
    "layerName": "Clinical efficacy",
    "question": "Is the effect size clinically meaningful?",
    "requiredEvidence": "protocol and efficacy results"
  },
  {
    "id": "S03",
    "layer": 1,
    "layerName": "Clinical efficacy",
    "question": "Are secondary endpoints supportive?",
    "requiredEvidence": "protocol and efficacy results"
  },
  {
    "id": "S04",
    "layer": 1,
    "layerName": "Clinical efficacy",
    "question": "Are results consistent across relevant subgroups?",
    "requiredEvidence": "protocol and efficacy results"
  },
  {
    "id": "S05",
    "layer": 1,
    "layerName": "Clinical efficacy",
    "question": "Is durability of benefit adequately demonstrated?",
    "requiredEvidence": "protocol and efficacy results"
  },
  {
    "id": "S06",
    "layer": 2,
    "layerName": "Statistical integrity",
    "question": "Was the statistical analysis plan finalized before relevant data review?",
    "requiredEvidence": "SAP and statistical report"
  },
  {
    "id": "S07",
    "layer": 2,
    "layerName": "Statistical integrity",
    "question": "Were multiplicity and type I error controlled?",
    "requiredEvidence": "SAP and statistical report"
  },
  {
    "id": "S08",
    "layer": 2,
    "layerName": "Statistical integrity",
    "question": "Were missing data and intercurrent events appropriately handled?",
    "requiredEvidence": "SAP and statistical report"
  },
  {
    "id": "S09",
    "layer": 2,
    "layerName": "Statistical integrity",
    "question": "Are sensitivity analyses consistent with the primary result?",
    "requiredEvidence": "SAP and statistical report"
  },
  {
    "id": "S10",
    "layer": 2,
    "layerName": "Statistical integrity",
    "question": "Are uncertainty estimates and statistical assumptions credible?",
    "requiredEvidence": "SAP and statistical report"
  },
  {
    "id": "S11",
    "layer": 3,
    "layerName": "Trial design",
    "question": "Is the population appropriate for the proposed indication?",
    "requiredEvidence": "protocol and amendments"
  },
  {
    "id": "S12",
    "layer": 3,
    "layerName": "Trial design",
    "question": "Is the comparator clinically and regulatorily appropriate?",
    "requiredEvidence": "protocol and amendments"
  },
  {
    "id": "S13",
    "layer": 3,
    "layerName": "Trial design",
    "question": "Were randomization, blinding, and bias controls adequate?",
    "requiredEvidence": "protocol and amendments"
  },
  {
    "id": "S14",
    "layer": 3,
    "layerName": "Trial design",
    "question": "Were sample size and statistical power justified?",
    "requiredEvidence": "protocol and amendments"
  },
  {
    "id": "S15",
    "layer": 3,
    "layerName": "Trial design",
    "question": "Were protocol deviations and amendments adequately managed?",
    "requiredEvidence": "protocol and amendments"
  },
  {
    "id": "S16",
    "layer": 4,
    "layerName": "Safety",
    "question": "Are serious adverse events adequately characterized?",
    "requiredEvidence": "safety dataset and clinical study report"
  },
  {
    "id": "S17",
    "layer": 4,
    "layerName": "Safety",
    "question": "Are treatment-related discontinuations acceptable in context?",
    "requiredEvidence": "safety dataset and clinical study report"
  },
  {
    "id": "S18",
    "layer": 4,
    "layerName": "Safety",
    "question": "Are organ-specific and laboratory toxicities adequately assessed?",
    "requiredEvidence": "safety dataset and clinical study report"
  },
  {
    "id": "S19",
    "layer": 4,
    "layerName": "Safety",
    "question": "Are exposure duration and long-term safety sufficient?",
    "requiredEvidence": "safety dataset and clinical study report"
  },
  {
    "id": "S20",
    "layer": 4,
    "layerName": "Safety",
    "question": "Is the overall benefit-risk balance favorable for the intended population?",
    "requiredEvidence": "safety dataset and clinical study report"
  },
  {
    "id": "S21",
    "layer": 5,
    "layerName": "Reproducibility",
    "question": "Are results consistent across independent studies or cohorts?",
    "requiredEvidence": "registry, publication, and independent review"
  },
  {
    "id": "S22",
    "layer": 5,
    "layerName": "Reproducibility",
    "question": "Are published results consistent with registry and sponsor disclosures?",
    "requiredEvidence": "registry, publication, and independent review"
  },
  {
    "id": "S23",
    "layer": 5,
    "layerName": "Reproducibility",
    "question": "Can principal analyses be independently reproduced or verified?",
    "requiredEvidence": "registry, publication, and independent review"
  },
  {
    "id": "S24",
    "layer": 5,
    "layerName": "Reproducibility",
    "question": "Are data integrity and audit-trail requirements adequately supported?",
    "requiredEvidence": "registry, publication, and independent review"
  },
  {
    "id": "S25",
    "layer": 5,
    "layerName": "Reproducibility",
    "question": "Are unresolved inconsistencies and conflicting evidence addressed?",
    "requiredEvidence": "registry, publication, and independent review"
  },
  {
    "id": "S26",
    "layer": 6,
    "layerName": "Regulatory pathway",
    "question": "Is the application type and indication correctly identified?",
    "requiredEvidence": "FDA correspondence and application record"
  },
  {
    "id": "S27",
    "layer": 6,
    "layerName": "Regulatory pathway",
    "question": "Are relevant FDA interactions and agreements documented?",
    "requiredEvidence": "FDA correspondence and application record"
  },
  {
    "id": "S28",
    "layer": 6,
    "layerName": "Regulatory pathway",
    "question": "Are endpoint and evidence requirements appropriate for the pathway?",
    "requiredEvidence": "FDA correspondence and application record"
  },
  {
    "id": "S29",
    "layer": 6,
    "layerName": "Regulatory pathway",
    "question": "Are regulatory deficiencies, inspections, and review risks assessed?",
    "requiredEvidence": "FDA correspondence and application record"
  },
  {
    "id": "S30",
    "layer": 6,
    "layerName": "Regulatory pathway",
    "question": "Are special designations and their actual implications verified?",
    "requiredEvidence": "FDA correspondence and application record"
  },
  {
    "id": "S31",
    "layer": 7,
    "layerName": "Manufacturing and quality",
    "question": "Is the manufacturing process adequately characterized?",
    "requiredEvidence": "CMC quality and manufacturing records"
  },
  {
    "id": "S32",
    "layer": 7,
    "layerName": "Manufacturing and quality",
    "question": "Are process validation and commercial-scale readiness supported?",
    "requiredEvidence": "CMC quality and manufacturing records"
  },
  {
    "id": "S33",
    "layer": 7,
    "layerName": "Manufacturing and quality",
    "question": "Are specifications, stability, and analytical methods adequate?",
    "requiredEvidence": "CMC quality and manufacturing records"
  },
  {
    "id": "S34",
    "layer": 7,
    "layerName": "Manufacturing and quality",
    "question": "Are manufacturing facilities and quality systems review-ready?",
    "requiredEvidence": "CMC quality and manufacturing records"
  },
  {
    "id": "S35",
    "layer": 7,
    "layerName": "Manufacturing and quality",
    "question": "Are critical CMC deficiencies and supply-chain risks addressed?",
    "requiredEvidence": "CMC quality and manufacturing records"
  },
  {
    "id": "S36",
    "layer": 8,
    "layerName": "External validity and comparators",
    "question": "Does the trial population represent intended clinical use?",
    "requiredEvidence": "systematic comparator cohort and clinical context"
  },
  {
    "id": "S37",
    "layer": 8,
    "layerName": "External validity and comparators",
    "question": "Are treatment effects transferable to relevant clinical settings?",
    "requiredEvidence": "systematic comparator cohort and clinical context"
  },
  {
    "id": "S38",
    "layer": 8,
    "layerName": "External validity and comparators",
    "question": "Are historical FDA submissions identified without selection bias?",
    "requiredEvidence": "systematic comparator cohort and clinical context"
  },
  {
    "id": "S39",
    "layer": 8,
    "layerName": "External validity and comparators",
    "question": "Are differences in indication, mechanism, endpoint, and era accounted for?",
    "requiredEvidence": "systematic comparator cohort and clinical context"
  },
  {
    "id": "S40",
    "layer": 8,
    "layerName": "External validity and comparators",
    "question": "Are competing treatments and current standard of care considered?",
    "requiredEvidence": "systematic comparator cohort and clinical context"
  }
] as const;
/** Deliberately separate from existing SCIENCE readiness and 21 legacy list scores. */
export const SCIENCE_QUESTION_CATALOG_IS_CERTIFIED = false as const;
