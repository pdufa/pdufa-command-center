/** Source-limited specialty-style clinical analyses. Authored as analytical research, not a licensed physician review. */
export type SpecialistInterpretation={
 topic:string; observedClinicalEvidence:string; specialistInterpretation:string; neededToResolve:string;
};
export type SpecialistCase={
 cycleId:string;specialty:string;medicalQuestion:string;source:string;sourceTitle:string;
 completedSpecialistSignoff:false;conclusion:"PARTIAL_SOURCED_RESEARCH";
 dimensions:readonly SpecialistInterpretation[];
};
export const SPECIALIST_CASES:readonly SpecialistCase[]=[
  {
    "cycleId": "capr-deramiocel",
    "specialty": "Neuromuscular medicine",
    "medicalQuestion": "Does the available HOPE-3 evidence establish a clinically important slowing of upper-limb functional decline in the specific DMD population proposed for treatment?",
    "source": "https://www.fda.gov/media/193839/download",
    "sourceTitle": "FDA July 2026 deramiocel advisory briefing (clinical and statistical sections)",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Disease phenotype",
        "observedClinicalEvidence": "Later-stage DMD causes progressive loss of proximal and distal upper-limb skills, while cardiomyopathy is a distinct clinical manifestation.",
        "specialistInterpretation": "A functional upper-limb claim cannot be established merely by changes in cardiac imaging, nor can a cardiomyopathy claim be assumed from a trial that did not require cardiomyopathy at entry.",
        "neededToResolve": "Clinically verify baseline function, steroid exposure, ambulatory status and the exact population in revised labeling."
      },
      {
        "topic": "Outcome meaningfulness",
        "observedClinicalEvidence": "The FDA original PUL 2.0 primary analysis difference was 0.66 PUL points (95% CI −0.45 to 1.77; p=0.24).",
        "specialistInterpretation": "An average change smaller than measurement variability or meaningful-task threshold could lack patient-important impact even if an alternative analysis becomes nominally significant.",
        "neededToResolve": "Obtain reliable PUL 2.0 patient-important change thresholds, patient-level distributions, responder classifications and blinded adjudication."
      },
      {
        "topic": "Statistical credibility",
        "observedClinicalEvidence": "The applicant's late CSR model yielded a reported 4.55% PUL difference (p=0.029) under materially different analysis choices.",
        "specialistInterpretation": "Different scales, SAP timing, covariates and handling of missing follow-up produce fundamentally different evidentiary claims; do not vote on p-values.",
        "neededToResolve": "Reconstruct original SAP, every amendment, missing-data mechanisms, sensitivity analyses and FDA's response to the latest package."
      },
      {
        "topic": "Long-term disease course",
        "observedClinicalEvidence": "An open-label extension suggested less upper-limb decline in delayed-start patients during their treated versus prior untreated year.",
        "specialistInterpretation": "Changing calendar period and selection among open-label survivors can mimic drug benefit in progressive disease; supporting evidence is not the same as randomized confirmation.",
        "neededToResolve": "Compare placebo period to treated period with disease natural history, attrition, steroid modifications and prespecified longitudinal models."
      },
      {
        "topic": "Cardiac and respiratory benefit",
        "observedClinicalEvidence": "DMD patients face important cardiomyopathy and respiratory morbidity; baseline cardiomyopathy was not mandatory in HOPE-3.",
        "specialistInterpretation": "A cardiac claim requires an adequately defined target population and robust clinically meaningful cardiac results separate from upper-limb benefit.",
        "neededToResolve": "Investigate LVEF measurement variation, echocardiography/MRI adjudication, cardiac event outcomes, and respiratory measures."
      },
      {
        "topic": "Tolerability and treatment burden",
        "observedClinicalEvidence": "The public source package does not permit complete independent evaluation of cumulative infusion, cell-product or long-term organ-specific risks.",
        "specialistInterpretation": "A modest functional effect must be weighed against treatment burden and adverse-event uncertainty, particularly in medically fragile adolescents.",
        "neededToResolve": "Obtain pooled adjudicated SAE and exposure details, cardiopulmonary monitoring and full long-term safety."
      },
      {
        "topic": "FDA reviewer challenge",
        "observedClinicalEvidence": "FDA documented substantial effectiveness concerns and July 2025 CRL history; a major amendment introduced new analyses and refined indication.",
        "specialistInterpretation": "The chief clinical failure pathway is inadequate substantial evidence for the exact claim, independent of separate CMC or inspection review.",
        "neededToResolve": "Locate FDA's current-cycle response to new analyses, evaluate original pre-specified effect and determine remaining current-cycle objections."
      }
    ]
  },
  {
    "cycleId": "cort-relacorilant",
    "specialty": "Endocrinology / pituitary-adrenal disease",
    "medicalQuestion": "Does relacorilant meaningfully reverse cortisol-associated morbidity across affected organs, and does the resubmission address FDA's prior lack-of-efficacy conclusion?",
    "source": "https://www.sec.gov/Archives/edgar/data/1088856/000162828026069501/cort-20260930.htm",
    "sourceTitle": "Corcept November 2026 SEC 10-Q: GRACE, GRADIENT, prior CRL, and requested global analysis",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Endocrine disease construct",
        "observedClinicalEvidence": "Chronic cortisol excess has heterogeneous hemodynamic, metabolic, adiposity and neuropsychiatric manifestations.",
        "specialistInterpretation": "A single surrogate or within-arm biomarker change may fail to capture meaningful improvement across heterogeneous disease manifestations.",
        "neededToResolve": "Require biochemically confirmed etiology, cortisol severity, stable background care and organ-specific morbidity."
      },
      {
        "topic": "Trial population and enrichment",
        "observedClinicalEvidence": "GRACE employed randomized withdrawal in patients previously selected as responders during treatment exposure.",
        "specialistInterpretation": "This demonstrates maintenance of effect within an enriched population, not necessarily initial efficacy among all eligible hypercortisolism patients.",
        "neededToResolve": "Reconstruct screening, open-label response enrichment, withdrawal attrition, rescue therapy, and generalizability."
      },
      {
        "topic": "Blood-pressure evidence",
        "observedClinicalEvidence": "In GRADIENT, treatment-arm systolic BP decreased 6.6 mmHg while placebo decreased 2.1 mmHg; the sponsor said the between-arm contrast was not statistically significant.",
        "specialistInterpretation": "Within-group p-values do not establish comparative antihypertensive benefit; this is an especially important endocrine clinical endpoint.",
        "neededToResolve": "Obtain placebo-adjusted estimates, CIs, ambulatory versus office measures, baseline medications and sensitivity to rescue."
      },
      {
        "topic": "Other organ outcomes",
        "observedClinicalEvidence": "The sponsor reported favorable glycemic and weight outcomes in GRADIENT and a positive FDA-requested global test.",
        "specialistInterpretation": "A positive composite can be driven by one component; patient importance and multiplicity must be evaluated separately from the overall result.",
        "neededToResolve": "Obtain exact multicomponent global statistical method, weighting, missing data handling, components, clinically meaningful thresholds."
      },
      {
        "topic": "Safety and adrenal physiology",
        "observedClinicalEvidence": "A glucocorticoid receptor modulator alters tissue response to cortisol; monitoring of adrenal insufficiency and interactions is disease-specific.",
        "specialistInterpretation": "Traditional biochemical cortisol measurements may not track clinical glucocorticoid effect directly; symptoms, edema, electrolytes and concomitant drugs matter.",
        "neededToResolve": "Review receptor-related physiology, clinical deterioration, adrenal-crisis-like events, interactions and long-term exposure."
      },
      {
        "topic": "Clinical decision context",
        "observedClinicalEvidence": "Cushing syndrome may be surgically curable in some etiologies; persistent/recurrent disease has specialized endocrine treatment pathways.",
        "specialistInterpretation": "The labeled population must match the scenario in which medical therapy is appropriate versus surgery, radiotherapy or alternative drugs.",
        "neededToResolve": "Document previous curative treatment, alternative pharmacology and direct comparison limits."
      },
      {
        "topic": "FDA reviewer challenge",
        "observedClinicalEvidence": "December 2025 efficacy CRL preceded the June 2026 resubmission with further analyses requested by FDA.",
        "specialistInterpretation": "The current risk is whether the sponsor's amended global efficacy argument is adequate, not whether the earlier CRL itself predicts a new one.",
        "neededToResolve": "Verify updated FDA correspondence and original/global statistical plan; analyze organ-specific effect precision and safety."
      }
    ]
  },
  {
    "cycleId": "cogt-gist",
    "specialty": "Medical oncology / gastrointestinal stromal tumor",
    "medicalQuestion": "Is the randomized progression benefit of combination bezuclastinib and sunitinib clinically compelling after imatinib despite its additional grade 3 or higher hepatic enzyme abnormalities?",
    "source": "https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3",
    "sourceTitle": "Cogent detailed PEAK Phase 3 2026 clinical results",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Molecular disease subtype",
        "observedClinicalEvidence": "Advanced GIST often depends on KIT or PDGFRA activating variants, with variable acquired resistance to TKIs.",
        "specialistInterpretation": "All-comer pooled efficacy may conceal lack of benefit in resistant mutation subgroups; direct clinical relevance depends on distribution of mutations.",
        "neededToResolve": "Require mutation-stratified PFS, overall survival maturity, circulating tumor DNA data and prior TKI exposure."
      },
      {
        "topic": "Active comparator choice",
        "observedClinicalEvidence": "PEAK randomized combination therapy against sunitinib in the post-imatinib setting.",
        "specialistInterpretation": "An active-comparator effect is more clinically direct than comparing unrelated trials; assess whether dosing intensity and prior treatment are balanced.",
        "neededToResolve": "Review actual sunitinib dose, modifications, line of therapy, image review and site geography."
      },
      {
        "topic": "Magnitude of benefit",
        "observedClinicalEvidence": "Sponsor reported median PFS 16.5 vs 9.2 months, HR 0.50 (95% CI 0.39–0.65), p<0.0001.",
        "specialistInterpretation": "An approximately 7.3-month median PFS separation is clinically consequential if unbiased and sustained; it does not guarantee overall survival gain.",
        "neededToResolve": "Inspect independent central PFS review, censoring, response, post-progression therapy, OS events and PROs."
      },
      {
        "topic": "Liver-safety imbalance",
        "observedClinicalEvidence": "Reported grade ≥3 ALT/AST elevations were 10.8% on combination versus 1.4% on sunitinib alone.",
        "specialistInterpretation": "The observed absolute excess of 9.4 percentage points warrants investigation of clinically serious DILI, reversibility and monitorability; it is not itself a confirmed FDA CRL concern.",
        "neededToResolve": "Review Hy's law adjudication, bilirubin, baseline hepatic metastases, time to onset, rechallenge, severe-event denominator and withdrawal."
      },
      {
        "topic": "Dose and adherence",
        "observedClinicalEvidence": "Combination kinase inhibitor exposure creates potential dose-interruption and dose-reduction issues.",
        "specialistInterpretation": "Treatment effects may attenuate if a large share cannot maintain intensity; a tolerability assessment should use exposure-adjusted rates and dose histories.",
        "neededToResolve": "Obtain achieved dose intensity, treatment discontinuations, reduction frequency and exposure-response analyses."
      },
      {
        "topic": "Patient function and therapeutic sequence",
        "observedClinicalEvidence": "Patients with unresectable/metastatic GIST require sequential TKIs; progression may reduce function and increase symptomatic burden.",
        "specialistInterpretation": "Progression control is valuable, but any gains should be interpreted with toxicity, performance status and later therapy options.",
        "neededToResolve": "Inspect EORTC/PRO measures, quality-of-life results, time to symptomatic progression and treatment switching."
      },
      {
        "topic": "FDA reviewer challenge",
        "observedClinicalEvidence": "PFS efficacy is persuasive while grade 3+ hepatic lab imbalance needs full benefit-risk review; public evidence does not include final CMC or inspection adjudication.",
        "specialistInterpretation": "A hypothetical CRL should not be assigned solely on liver laboratory percentages; clinical and manufacturing clearance requires source verification.",
        "neededToResolve": "Obtain final agency safety discussions, product label monitoring, inspection status and totality-of-evidence decision."
      }
    ]
  }
] as const;
export function specialistCaseForCycle(cycleId:string):SpecialistCase|null{
 return SPECIALIST_CASES.find(c=>c.cycleId===cycleId)||null;
}
