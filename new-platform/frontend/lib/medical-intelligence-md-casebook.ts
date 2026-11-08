/**
 * Medical Master-depth source-audited casebook.
 * Every review entry is a discrete source-anchored scientific observation, NOT a
 * completed 20-level × 40-assessment investigation, prediction, medical credential,
 * FDA finding in a later review cycle, or patient-level reanalysis.
 */
export type CaseRecord={
 cycleId:string;name:string;ticker:string;nct:string;indication:string;reviewCycle:string;
 finding:string;mainRisk:string;decision:"INDETERMINATE";confidence:string;
 facts:readonly {label:string;value:string;source:string}[];
 source:string;sourceDate:string;sourceTitle:string;
 uncertainties:readonly string[];strongestCounter:string;
 investigations:readonly {level:number;assessmentId:string;sourceObservation:string;medicalInterpretation:string;sourceSection:string;sourceUrl?:string}[];
};
export const MEDICAL_CASES:readonly CaseRecord[]=[
  {
    "cycleId": "capr-deramiocel",
    "name": "Deramiocel / HOPE-3",
    "ticker": "CAPR",
    "nct": "NCT05126758",
    "indication": "Duchenne muscular dystrophy",
    "reviewCycle": "BLA 125842 Class 2 resubmission; Nov 22 2026 recorded goal",
    "finding": "A direct FDA primary efficacy and statistical analysis objection is supported by the July 2026 advisory review. The subsequent amended indication and sensitivity data require current-cycle adjudication.",
    "mainRisk": "Pivotal evidence reproducibility and indication relevance",
    "decision": "INDETERMINATE",
    "confidence": "Confirmed FDA objection; outcome not calibrated",
    "facts": [
      {
        "label": "Trial randomized",
        "value": "106 (54 treatment / 52 placebo)",
        "source": "FDA"
      },
      {
        "label": "FDA prespecified PUL 2.0 estimate",
        "value": "0.66 points (95% CI −0.45 to 1.77), p=0.24",
        "source": "FDA"
      },
      {
        "label": "Sponsor modified CSR PUL 2.0 estimate",
        "value": "4.55% (95% CI 0.47%–8.63%), p=0.029",
        "source": "FDA comparison of applicant analyses"
      },
      {
        "label": "FDA prespecified LVEF",
        "value": "−0.041 percentage points (95% CI −2.58 to 2.49), p=0.97",
        "source": "FDA"
      },
      {
        "label": "Cardiomyopathy eligibility",
        "value": "Not required in HOPE-3 trial",
        "source": "FDA"
      }
    ],
    "source": "https://www.fda.gov/media/193839/download",
    "sourceDate": "2026-07-29",
    "sourceTitle": "FDA July 2026 deramiocel advisory briefing, pp. 24–46; Tables 7 and 9",
    "uncertainties": [
      "FDA acceptance of the amended upper-limb indication and new response package",
      "Whether additional submitted data adequately address the original prespecified efficacy objection",
      "Full sponsor and FDA review of bioresearch inspection response and CMC readiness",
      "Complete patient-level analyses, SAP amendments and missingness sensitivity cannot be independently rerun from public tables"
    ],
    "strongestCounter": "Sponsor reports a positive post-amendment model, a clinically meaningful upper-limb change in advanced DMD, supportive 24-month open-label data, and a refined indication. These do not erase FDA's earlier alternative-analysis findings.",
    "investigations": [
      {
        "level": 1,
        "assessmentId": "4.3",
        "sourceObservation": "FDA independently enumerated SAP 1.1, 2.0, 3.0 and CSR versions with distinct endpoints, models and imputation rules.",
        "medicalInterpretation": "Source extraction supports a dated analysis chronology; the original SAP predated database lock.",
        "sourceSection": "FDA briefing pp. 30–40"
      },
      {
        "level": 2,
        "assessmentId": "2.2",
        "sourceObservation": "Deramiocel is an allogeneic cardiosphere-derived cell therapy proposed to act through secreted factors and exosomes.",
        "medicalInterpretation": "Biological plausibility is stated, but human target engagement and mediation remain unconfirmed.",
        "sourceSection": "FDA clinical overview"
      },
      {
        "level": 3,
        "assessmentId": "1.1",
        "sourceObservation": "DMD lacks functional dystrophin with progressive skeletal and cardiac muscle dysfunction.",
        "medicalInterpretation": "Both pathways are disease-relevant; a cardiac treatment claim still needs cardiac population/outcome support.",
        "sourceSection": "FDA disease and study design sections"
      },
      {
        "level": 4,
        "assessmentId": "4.2",
        "sourceObservation": "The original study planned PUL 2.0 absolute change at Month 12; later analyses used percent change.",
        "medicalInterpretation": "Different effect scales complicate clinical interpretation and require the prespecified analysis hierarchy.",
        "sourceSection": "FDA briefing Table 7"
      },
      {
        "level": 5,
        "assessmentId": "4.3",
        "sourceObservation": "FDA reported that changing two placebo-subject missing-data treatments materially changed the estimated PUL treatment difference.",
        "medicalInterpretation": "Differential assumptions about adverse-event withdrawal and prohibited medication can bias causal inference.",
        "sourceSection": "FDA briefing pp. 38–40"
      },
      {
        "level": 6,
        "assessmentId": "7.3",
        "sourceObservation": "Original cardiomyopathy claim did not match an enrollment requirement for reduced LVEF or diagnosed cardiomyopathy.",
        "medicalInterpretation": "Possible indication-population mismatch; later amended indication needs separate FDA acceptance.",
        "sourceSection": "FDA briefing Study HOPE-3"
      },
      {
        "level": 8,
        "assessmentId": "8.1",
        "sourceObservation": "FDA's original planned PUL contrast had confidence interval spanning no effect; sponsor's modified model showed nominal significance.",
        "medicalInterpretation": "The central benefit-risk case depends on interpretation of competing statistical methods, not a vote among p-values.",
        "sourceSection": "FDA briefing Table 7"
      },
      {
        "level": 9,
        "assessmentId": "4.1",
        "sourceObservation": "HOPE-3 had two randomized manufacturing cohorts; FDA included cohort as a covariate in its analysis.",
        "medicalInterpretation": "Separate randomization cohorts require adjustment; this alone does not establish an FDA CMC deficiency.",
        "sourceSection": "FDA briefing pp. 38–40"
      },
      {
        "level": 11,
        "assessmentId": "8.2",
        "sourceObservation": "FDA challenged post-completion changes to SAP and further departures in the final CSR.",
        "medicalInterpretation": "The source-documented statistical objections are stronger evidence than a theoretical concern.",
        "sourceSection": "FDA briefing pp. 30–45"
      },
      {
        "level": 12,
        "assessmentId": "4.3",
        "sourceObservation": "FDA's seven reported PUL versions yield p-values 0.24, 0.11, 0.26, 0.08, 0.21, 0.045 and 0.029.",
        "medicalInterpretation": "Only the two late versions cross 0.05; this descriptive comparison does not estimate a reproducibility probability.",
        "sourceSection": "FDA briefing Table 7"
      },
      {
        "level": 14,
        "assessmentId": "5.4",
        "sourceObservation": "FDA subgroup PUL estimates included cohort A −0.09 (p=0.90), cohort B 1.75 (p=0.092), and nonambulatory 0.77 (p=0.19).",
        "medicalInterpretation": "None independently establish convincing effect modification; small subgroups and multiplicity constrain interpretation.",
        "sourceSection": "FDA briefing Table 8"
      },
      {
        "level": 16,
        "assessmentId": "1.5",
        "sourceObservation": "Trial mean age 15, mostly nonambulatory, with no cardiomyopathy diagnosis requirement.",
        "medicalInterpretation": "Generalizability to the precise revised proposed labeled patient population remains a live scientific question.",
        "sourceSection": "FDA presentation Study HOPE-3"
      },
      {
        "level": 17,
        "assessmentId": "7.2",
        "sourceObservation": "FDA issued a July 2025 CRL for earlier HOPE-2/OLE evidence and subsequently reviewed HOPE-3.",
        "medicalInterpretation": "Prior efficacy deficiency is confirmed; resubmission can resolve it only with sufficient new evidence.",
        "sourceSection": "FDA regulatory history"
      },
      {
        "level": 18,
        "assessmentId": "7.5",
        "sourceObservation": "Sponsor reported FDA classified additional HOPE-3 analyses/indication change as a major amendment and extended the goal to Nov 22.",
        "medicalInterpretation": "A formal extension is already an event, not a prediction of further delay.",
        "sourceSection": "Capricor August 24 2026 announcement",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1133869/000110465926100071/capr-20260824x8k.htm"
      },
      {
        "level": 19,
        "assessmentId": "5.5",
        "sourceObservation": "FDA reconstructed the full table of treatment effects and p-values across SAP choices, while raw individual patient data are not public.",
        "medicalInterpretation": "Public numerical table can be checked for consistency; independently rerunning MMRM requires IPD and complete analysis code.",
        "sourceSection": "FDA briefing Tables 7 and 9"
      },
      {
        "level": 20,
        "assessmentId": "8.5",
        "sourceObservation": "A confirmed FDA statistical objection is paired with a contested sponsor model and newer amendments under review.",
        "medicalInterpretation": "Failure-first clinical concern is substantiated; final approval/CRL/timing disposition remains indeterminate pending updated FDA interpretation.",
        "sourceSection": "FDA briefing and August 2026 regulatory update"
      }
    ]
  },
  {
    "cycleId": "cort-relacorilant",
    "name": "Relacorilant / GRACE & GRADIENT",
    "ticker": "CORT",
    "nct": "NCT03697109",
    "indication": "Endogenous hypercortisolism",
    "reviewCycle": "Resubmitted NDA, Dec 17 2026 recorded goal",
    "finding": "Prior efficacy CRL and a nonsignificant GRADIENT between-arm BP endpoint demand explicit analysis of the FDA-requested global statistical test.",
    "mainRisk": "Whether resubmitted integrated efficacy adequately resolves the previous FDA deficiency",
    "decision": "INDETERMINATE",
    "confidence": "Prior CRL established; resubmission adequacy unknown",
    "facts": [
      {
        "label": "GRADIENT within-arm SBP change",
        "value": "−6.6 mmHg treated (p=0.012) vs −2.1 placebo (n.s.)",
        "source": "Sponsor 10-Q"
      },
      {
        "label": "GRADIENT between-arm BP finding",
        "value": "Not statistically significant",
        "source": "Sponsor 10-Q"
      },
      {
        "label": "GRACE randomized-withdrawal BP-control odds ratio",
        "value": "0.17; reported p≈0.02",
        "source": "Sponsor 10-Q"
      },
      {
        "label": "Prior FDA CRL",
        "value": "Dec 30 2025—additional evidence of efficacy requested",
        "source": "Sponsor 10-Q"
      }
    ],
    "source": "https://www.sec.gov/Archives/edgar/data/1088856/000162828026069501/cort-20260930.htm",
    "sourceDate": "2026-11-03",
    "sourceTitle": "Corcept November 3, 2026 Form 10-Q, clinical efficacy and FDA resubmission",
    "uncertainties": [
      "Full prespecified global hypothesis testing plan and alpha handling",
      "Component contributions from BP, glucose and body weight",
      "The exact FDA assessment of the June resubmission",
      "Population generalizability of randomized-withdrawal responder enrichment"
    ],
    "strongestCounter": "The sponsor reports that GRACE achieved its prespecified endpoint and that the additional FDA-requested combined global analysis was positive; residual deficiencies cannot be inferred solely from the historical CRL.",
    "investigations": [
      {
        "level": 1,
        "assessmentId": "7.2",
        "sourceObservation": "Sponsor disclosed the efficacy CRL, FDA-requested new analyses and June 2026 resubmission.",
        "medicalInterpretation": "Reconstruct the exact sequence of agency objections and remediation.",
        "sourceSection": "Corcept Nov 2026 Form 10-Q"
      },
      {
        "level": 4,
        "assessmentId": "4.2",
        "sourceObservation": "GRADIENT prespecified a systolic BP comparison, while GRACE used randomized withdrawal.",
        "medicalInterpretation": "Different trial estimands support different clinical claims and cannot be conflated.",
        "sourceSection": "GRACE/GRADIENT clinical description"
      },
      {
        "level": 5,
        "assessmentId": "4.3",
        "sourceObservation": "Treatment-arm SBP fell 6.6 mmHg from baseline, but the trial did not show a significant between-group BP difference.",
        "medicalInterpretation": "Within-arm p=0.012 is not evidence of superiority over placebo.",
        "sourceSection": "Corcept 10-Q GRADIENT results"
      },
      {
        "level": 7,
        "assessmentId": "8.3",
        "sourceObservation": "Sponsor reports FDA requested a global test combining BP, glycemia and body weight.",
        "medicalInterpretation": "The global test may resolve a broad heterogeneous-symptom efficacy question, but without full SAP cannot quantify approval odds.",
        "sourceSection": "Corcept 10-Q"
      },
      {
        "level": 12,
        "assessmentId": "5.2",
        "sourceObservation": "GRADIENT had statistically significant placebo-adjusted glucose improvements and weight reduction.",
        "medicalInterpretation": "Post-primary inference depends on endpoints, multiplicity and FDA-agreed analysis model.",
        "sourceSection": "Corcept 10-Q"
      },
      {
        "level": 14,
        "assessmentId": "4.4",
        "sourceObservation": "GRACE enriched randomized-withdrawal responders before placebo comparison.",
        "medicalInterpretation": "Responder enrichment can demonstrate maintenance but limits extrapolation to all newly treated patients.",
        "sourceSection": "GRACE design"
      },
      {
        "level": 17,
        "assessmentId": "7.2",
        "sourceObservation": "A formal prior efficacy CRL was issued Dec 30 2025.",
        "medicalInterpretation": "This is historical objection evidence, not a future CRL decision.",
        "sourceSection": "Corcept 10-Q"
      },
      {
        "level": 20,
        "assessmentId": "8.5",
        "sourceObservation": "Clinical improvements coexist with a nonsignificant core BP comparison and an unresolved FDA-requested global test interpretation.",
        "medicalInterpretation": "Evidence is mixed; an FDA outcome decision requires full SAP and regulator feedback.",
        "sourceSection": "Corcept 10-Q"
      }
    ]
  },
  {
    "cycleId": "cogt-gist",
    "name": "Bezuclastinib + sunitinib / PEAK",
    "ticker": "COGT",
    "nct": "NCT05208047",
    "indication": "GIST after imatinib",
    "reviewCycle": "Accepted NDA; Nov 30 2026 recorded goal",
    "finding": "Randomized efficacy is substantial, but a higher incidence of serious ALT/AST laboratory abnormalities warrants liver-safety adjudication; no FDA liver deficiency is confirmed.",
    "mainRisk": "Balance of added hepatic toxicity against strong randomized PFS benefit",
    "decision": "INDETERMINATE",
    "confidence": "Efficacy and liver signal sponsor-reported; complete FDA review unavailable",
    "facts": [
      {
        "label": "Median PFS",
        "value": "16.5 vs 9.2 months",
        "source": "Sponsor PEAK release"
      },
      {
        "label": "PFS hazard ratio",
        "value": "0.50 (95% CI 0.39–0.65), p<0.0001",
        "source": "Sponsor PEAK release"
      },
      {
        "label": "Grade ≥3 ALT/AST abnormalities",
        "value": "10.8% combo vs 1.4% control",
        "source": "Sponsor ASCO presentation"
      },
      {
        "label": "Absolute difference in serious ALT/AST",
        "value": "+9.4 percentage points (descriptive)",
        "source": "Calculated from sponsor percentages"
      }
    ],
    "source": "https://cogentbiosciences.gcs-web.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3",
    "sourceDate": "2026-05-30",
    "sourceTitle": "Cogent May 30 2026 detailed PEAK results, efficacy and laboratory safety",
    "uncertainties": [
      "Distribution and time-to-event of Grade 3+ liver elevations, baseline labs and reversibility",
      "Hy's law cases and detailed liver-injury adjudication",
      "Dose modifications, withdrawals, liver monitoring and safety by subgroup",
      "Full agency CMC/inspection and labeling discussions"
    ],
    "strongestCounter": "A hazard ratio of 0.50 and 7.3-month median PFS separation in a randomized active-comparator trial are strong evidence of clinical efficacy; sponsor states serious liver abnormalities were manageable and resolved.",
    "investigations": [
      {
        "level": 1,
        "assessmentId": "5.1",
        "sourceObservation": "Reported median PFS 16.5 vs 9.2 months and hazard ratio 0.50.",
        "medicalInterpretation": "Identify source, statistical definition, confidence interval and publication date.",
        "sourceSection": "Cogent May 2026 PEAK report"
      },
      {
        "level": 3,
        "assessmentId": "1.1",
        "sourceObservation": "Metastatic GIST commonly depends on KIT/PDGFRA signaling and may develop imatinib resistance.",
        "medicalInterpretation": "Mutation-specific biological resistance motivates second-line kinase therapy.",
        "sourceSection": "NCI GIST disease background and PEAK design",
        "sourceUrl": "https://www.cancer.gov/types/soft-tissue-sarcoma/hp/gist-treatment-pdq"
      },
      {
        "level": 4,
        "assessmentId": "4.2",
        "sourceObservation": "PEAK compares the combination to active sunitinib, not unrelated placebo cohorts.",
        "medicalInterpretation": "Active comparator enhances direct comparative relevance.",
        "sourceSection": "PEAK sponsor release"
      },
      {
        "level": 5,
        "assessmentId": "5.3",
        "sourceObservation": "Grade ≥3 ALT/AST elevations were 10.8% vs 1.4%.",
        "medicalInterpretation": "The 9.4-percentage-point excess is descriptive; denominators and case-level causality are required.",
        "sourceSection": "Cogent ASCO May 2026"
      },
      {
        "level": 7,
        "assessmentId": "8.3",
        "sourceObservation": "A strong primary efficacy signal and hepatotoxicity signal can coexist.",
        "medicalInterpretation": "CRL versus restricted labeling cannot be assigned without an agency-level safety and CMC review.",
        "sourceSection": "PEAK efficacy and safety tables"
      },
      {
        "level": 12,
        "assessmentId": "5.1",
        "sourceObservation": "PFS HR=0.50 with 95% CI 0.39–0.65 excludes null in sponsor analysis.",
        "medicalInterpretation": "Effect is statistically persuasive, but other endpoints and sensitivity checks need independent review.",
        "sourceSection": "Cogent May 2026"
      },
      {
        "level": 13,
        "assessmentId": "3.3",
        "sourceObservation": "Combination dosing adds another kinase inhibitor to sunitinib.",
        "medicalInterpretation": "Interaction and exposure-safety analysis cannot be confirmed from published topline findings.",
        "sourceSection": "PEAK protocol/pharmacology data needed"
      },
      {
        "level": 18,
        "assessmentId": "7.4",
        "sourceObservation": "Monitoring or dose modification could manage hepatic risk if demonstrated.",
        "medicalInterpretation": "Label restrictions are plausible consequences, not established FDA demands.",
        "sourceSection": "PEAK treatment safety"
      },
      {
        "level": 20,
        "assessmentId": "8.5",
        "sourceObservation": "Substantial benefit with increased serious ALT/AST findings produces a measurable benefit-risk question.",
        "medicalInterpretation": "The clinically important safety signal must be weighed against survival/progression benefit before forecasting FDA action.",
        "sourceSection": "PEAK original sponsor results"
      }
    ]
  }
] as const;
export const CAPR_FDA_PUL_SAP_COMPARISONS:readonly {
 version:string;units:string;effect:number;lower:number;upper:number;pValue:number;
}[]=[
  {
    "version": "SAP 1.1, prespecified",
    "units": "absolute PUL points",
    "effect": 0.66,
    "lower": -0.45,
    "upper": 1.77,
    "pValue": 0.24
  },
  {
    "version": "SAP 1.1, FDA with imputation",
    "units": "absolute PUL points",
    "effect": 0.92,
    "lower": -0.21,
    "upper": 2.04,
    "pValue": 0.11
  },
  {
    "version": "SAP 2.0, FDA without imputation",
    "units": "percent change",
    "effect": 2.38,
    "lower": -1.78,
    "upper": 6.54,
    "pValue": 0.26
  },
  {
    "version": "SAP 2.0, FDA with imputation",
    "units": "percent change",
    "effect": 3.74,
    "lower": -0.44,
    "upper": 7.93,
    "pValue": 0.08
  },
  {
    "version": "SAP 3.0, FDA without imputation",
    "units": "percent change",
    "effect": 2.53,
    "lower": -1.48,
    "upper": 6.53,
    "pValue": 0.21
  },
  {
    "version": "SAP 3.0, FDA with imputation",
    "units": "percent change",
    "effect": 4.16,
    "lower": 0.09,
    "upper": 8.23,
    "pValue": 0.045
  },
  {
    "version": "SAP 3.0 modified in CSR, applicant",
    "units": "percent change",
    "effect": 4.55,
    "lower": 0.47,
    "upper": 8.63,
    "pValue": 0.029
  }
] as const;
export function caprSapComparisonSummary(){
 const rows=CAPR_FDA_PUL_SAP_COMPARISONS;
 const positive=rows.filter(r=>r.pValue<0.05).length;
 return {
   reportedAnalyses:rows.length,nominalBelow005:positive,
   fdaOriginallySpecified:rows[0],applicantModified:rows[rows.length-1],
   caution:"These analyses change endpoints/scales, models, handling of missing data and covariates. They are highly dependent and cannot be treated as seven independent confirmations or as a probability of FDA approval."
 };
}
export function cogtLiverSafetyDifference(){
 const combination=10.8,control=1.4;
 return {combinationPercent:combination,controlPercent:control,
  absoluteDifferencePercentagePoints:Number((combination-control).toFixed(1)),
  caution:"Descriptive treatment-group percentage difference only. Without original case-level denominators, ascertainment windows, timing and severity adjudication, no valid p-value, adjusted relative risk or causality estimate can be inferred."};
}
export function caseForCycle(cycleId:string):CaseRecord|null{
 return MEDICAL_CASES.find(c=>c.cycleId===cycleId)||null;
}
export function researchForSlot(cycleId:string,assessmentId:string,level:number){
 const c=caseForCycle(cycleId);
 return c?.investigations.find(x=>x.assessmentId===assessmentId&&x.level===level)||null;
}
