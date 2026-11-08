/** Remaining clinical specialty cases for FOCUS applications.
 * Public-source interpretation only, no licensed physician certification or prediction.
 */
import type {SpecialistCase} from "./medical-intelligence-specialist-casebook";
export const SPECIALIST_WAVE_TWO:readonly SpecialistCase[]=[
  {
    "cycleId": "imnm-desmoid",
    "specialty": "Soft tissue sarcoma oncology / desmoid tumors",
    "medicalQuestion": "Does varegacestat meaningfully prevent desmoid progression, reduce tumor-related pain and protect function enough to justify chronic gamma-secretase inhibitor exposure?",
    "source": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/",
    "sourceTitle": "Immunome October 2026 ESMO RINGSIDE Phase 3 patient outcomes",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Desmoid disease phenotype",
        "observedClinicalEvidence": "Progressing desmoid tumors infiltrate soft tissue locally and can cause pain or organ dysfunction despite not being typically metastatic.",
        "specialistInterpretation": "Progression-free survival is meaningful when it correlates with pain, disability and avoidance of mutilating surgery; historical spontaneous stabilization is a control consideration.",
        "neededToResolve": "Evaluate progression prior to entry, disease location, functional deficit, prior observation and surgical/radiation history.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
      },
      {
        "topic": "Randomized progression advantage",
        "observedClinicalEvidence": "RINGSIDE reported PFS hazard ratio 0.16 versus placebo (95% CI 0.071–0.375), p<0.0001, representing an 84% relative hazard reduction.",
        "specialistInterpretation": "A strong blinded randomized contrast makes spontaneous regression less likely to explain the whole result; absolute event times and crossover still matter.",
        "neededToResolve": "Retrieve Kaplan–Meier curves, number of progression events, censoring by arm and prespecified RECIST adjudication.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
      },
      {
        "topic": "Radiographic tumor response",
        "observedClinicalEvidence": "Independent central review reported a confirmed objective response rate of 56% on varegacestat versus 9% placebo (p<0.0001).",
        "specialistInterpretation": "Sizable volume reduction supports biological antitumor activity but not every partial response yields a proportional functional benefit.",
        "neededToResolve": "Review lesion location, response duration, independent imaging reproducibility and organ-specific symptom correlations.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
      },
      {
        "topic": "Pain and patient function",
        "observedClinicalEvidence": "RINGSIDE reported significant improvement in worst pain intensity at Week 12 (p<0.0001) and a clinically meaningful difference evident by Week 4.",
        "specialistInterpretation": "Patient-reported pain adds direct symptomatic corroboration to tumor measurements, but analgesic use and missing data can distort magnitude.",
        "neededToResolve": "Audit pain instruments, prespecified clinically important difference, baseline pain, rescue analgesia and quality of life.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
      },
      {
        "topic": "Mechanism and target class",
        "observedClinicalEvidence": "Varegacestat inhibits gamma secretase, a pathway connected to desmoid biology; class exposures can have GI and systemic consequences.",
        "specialistInterpretation": "A clinically coherent molecular mechanism strengthens expectation of tumor growth control, without implying a clean long-term toxicity profile.",
        "neededToResolve": "Review NOTCH-related off-target physiology, exposure-response, drug interactions and phase-specific reproductive risk assessment.",
        "sourceDate": "2026-10-06",
        "sourceUrl": "https://ascopubs.org/doi/10.1200/JCO-26-00725"
      },
      {
        "topic": "Safety and persistence",
        "observedClinicalEvidence": "Sponsor identified diarrhea, fatigue, rash, nausea and cough as common treatment-emergent events during RINGSIDE development.",
        "specialistInterpretation": "Desmoid disease may require long therapy; dose-related fatigue or diarrhea can meaningfully limit the benefit of tumor control.",
        "neededToResolve": "Obtain grade ≥3 events, dose modifications, ovarian function/fertility data, long-term exposure and adverse event discontinuation.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
      },
      {
        "topic": "Current FDA approval question",
        "observedClinicalEvidence": "The sponsor described the RINGSIDE randomized evidence as the basis for its filed application with an April 28, 2027 target in the FOCUS record.",
        "specialistInterpretation": "A strong PFS/response result does not establish CMC, final benefit-risk, inspection closure or label breadth.",
        "neededToResolve": "Verify published FDA acceptance and scope, complete safety/label plan, reproductive monitoring and active review clock.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
      }
    ]
  },
  {
    "cycleId": "phvs-ondemand",
    "specialty": "Allergy/immunology / acute hereditary angioedema",
    "medicalQuestion": "Does oral deucrictibant IR give sufficiently fast, dependable control of potentially dangerous hereditary-angioedema attacks while minimizing rescue needs and delayed treatment?",
    "source": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study",
    "sourceTitle": "Pharvaris December 3 2025 pivotal RAPIDe-3 results",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Bradykinin-mediated phenotype",
        "observedClinicalEvidence": "RAPIDe-3 enrolled hereditary angioedema patients, including C1 inhibitor deficiency and normal-C1-inhibitor phenotypes, with attacks at varied body locations.",
        "specialistInterpretation": "Bradykinin-mediated swelling is fundamentally different from histamine allergy; airway involvement and subtype accuracy are critical for safe clinical generalization.",
        "neededToResolve": "Reconstruct subtype confirmation, anatomical attack locations, age distribution, severity and prophylaxis co-treatment.",
        "sourceDate": "2025-12-03",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
      },
      {
        "topic": "Onset of symptom relief",
        "observedClinicalEvidence": "The randomized RAPIDe-3 primary median time to initial patient-reported relief was 1.28 hours on deucrictibant IR versus more than 12 hours placebo (p<0.0001).",
        "specialistInterpretation": "A large reduction in time with painful or function-limiting swelling is patient-important if the drug can be taken quickly and safely.",
        "neededToResolve": "Audit attack timing from symptom onset to dose, symptom assessment frequency, landmark responses and placebo censoring.",
        "sourceDate": "2025-12-03",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
      },
      {
        "topic": "End-of-progression and full relief",
        "observedClinicalEvidence": "Median end of attack progression was 17.47 versus 228.67 minutes; median complete resolution 11.95 hours versus more than 24 hours placebo (reported p<0.0001).",
        "specialistInterpretation": "The concordance of rapid arrest and complete relief strengthens clinically interpretable benefit; distinct time-to-event endpoints require multiplicity and attack-level correlation checks.",
        "neededToResolve": "Verify hierarchical test plan, competing rescue treatments, censoring, repeated attacks and severity-based consistency.",
        "sourceDate": "2025-12-03",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
      },
      {
        "topic": "Repeated-attack crossover design",
        "observedClinicalEvidence": "The primary efficacy set included people treating attacks in a 2×2 randomized crossover design, enabling participant-level comparison across episodes.",
        "specialistInterpretation": "Within-patient crossover can reduce interperson heterogeneity, but attacks vary in location, intensity and timing and carryover needs exclusion.",
        "neededToResolve": "Examine randomization sequence, washout, attack eligibility, rescue rules and intra-subject independence.",
        "sourceDate": "2025-12-03",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
      },
      {
        "topic": "Rescue and airway-risk limits",
        "observedClinicalEvidence": "Sponsor reported 83.0% of treated attacks controlled with one capsule and 93.2% treated without rescue medication.",
        "specialistInterpretation": "Low rescue use is clinically appealing but serious laryngeal attacks may require immediate emergency treatment even when oral therapy is available.",
        "neededToResolve": "Verify rescue timing, severity and laryngeal involvement; confirm label warnings and emergency-care instructions.",
        "sourceDate": "2025-12-03",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
      },
      {
        "topic": "Safety and formulation onset",
        "observedClinicalEvidence": "Deucrictibant IR is a small-molecule bradykinin B2 antagonist, distinct from the extended-release prophylactic formulation.",
        "specialistInterpretation": "Pharmacokinetic onset and safety are integral to attack treatment; prevention results for XR cannot substitute for IR onset/efficacy data.",
        "neededToResolve": "Review oral absorption in nausea/vomiting, drug interactions, adverse events, repeat dosing and pregnancy considerations.",
        "sourceDate": "2025-12-03",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
      },
      {
        "topic": "Accepted current application",
        "observedClinicalEvidence": "The company reported the IR on-demand NDA is under FDA review with April 23, 2027 action goal.",
        "specialistInterpretation": "This is a distinct regulatory product/formulation/label decision from the planned prophylaxis XR NDA; failure modes differ.",
        "neededToResolve": "Confirm current FDA filing status, CMC for immediate-release capsule and indication-specific safety/label information.",
        "sourceDate": "2026-08-12",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-reports-second-quarter-2026-financial-results-and"
      }
    ]
  },
  {
    "cycleId": "phvs-prophylaxis",
    "specialty": "Allergy/immunology / HAE preventive therapy",
    "medicalQuestion": "Does once-daily deucrictibant XR provide durable prevention of life-disrupting HAE attacks in specific HAE subtypes, with enough long-term exposure to support preventive daily treatment?",
    "source": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal",
    "sourceTitle": "Pharvaris September 8 2026 CHAPTER-3 topline",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Clinical subtypes and baseline burden",
        "observedClinicalEvidence": "CHAPTER-3 randomized 85 patients (55 XR, 30 placebo) with HAE type I, type II or normal C1 inhibitor across 21 countries.",
        "specialistInterpretation": "The normal-C1-inhibitor population was very small relative to other HAE types; equal efficacy or safety precision cannot be assumed.",
        "neededToResolve": "Extract exact subtype denominators, baseline frequency/severity, airway history and concurrent rescue therapies.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      },
      {
        "topic": "Primary attack-frequency prevention",
        "observedClinicalEvidence": "Across all HAE types, the reported mean monthly attack rate was 83% lower with XR versus placebo (p<0.0001) over 24 weeks.",
        "specialistInterpretation": "Large frequency suppression is clinically compelling for recurrent unpredictable attacks, but primary-model handling of periods with no attacks must be checked.",
        "neededToResolve": "Obtain rate model, overdispersion, patient-level attack distribution, attack adjudication and absolute attacks prevented.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      },
      {
        "topic": "Subtype treatment effect",
        "observedClinicalEvidence": "Among 80 type I/II participants, reported attack-rate reduction was 87% versus placebo.",
        "specialistInterpretation": "This supports traditional C1-inhibitor-deficient HAE while leaving uncertainty for the few normal-C1-inhibitor participants.",
        "neededToResolve": "Check formal interaction tests, genotype/diagnostic criteria, confidence intervals and case-level attacks in normal C1-inhibitor group.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      },
      {
        "topic": "Early and sustained disease control",
        "observedClinicalEvidence": "The sponsor reported prophylaxis beginning within the first week and benefit maintained through the six-month randomized trial.",
        "specialistInterpretation": "For prophylaxis, durability and sustained low attack burden matter more than a single week of response.",
        "neededToResolve": "Examine week-by-week attack frequency, time to first attack, rescue use, patient-reported anxiety and quality of life.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      },
      {
        "topic": "Responder and corticosteroid alternatives",
        "observedClinicalEvidence": "All sequenced secondary efficacy endpoints reportedly achieved statistical significance, including increases in attack-free patients.",
        "specialistInterpretation": "Attack-free proportions directly affect patient living, but reporting only relative frequency reductions may obscure the subset still having severe attacks.",
        "neededToResolve": "Verify denominators for attack-free status, severe/laryngeal attacks and absolute quality-of-life change.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      },
      {
        "topic": "Daily-exposure risk and immunology",
        "observedClinicalEvidence": "The company said most adverse events were mild/moderate, with one participant in each arm discontinuing due to adverse events and no treatment-related serious events.",
        "specialistInterpretation": "A 24-week study of 85 participants cannot exclude uncommon harms or definitively characterize drug interactions during chronic daily treatment.",
        "neededToResolve": "Obtain full long-term extension safety, hepatic/renal analyses, ECG, exposure-adjusted serious events, and pregnancy effects.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      },
      {
        "topic": "Distinct filing and timing",
        "observedClinicalEvidence": "The company planned the XR prevention NDA for first half 2027; the April 2027 IR on-demand action goal is not the preventive XR review goal.",
        "specialistInterpretation": "The review should not merge dosage forms or fabricate a PDUFA date before an XR application is submitted and accepted.",
        "neededToResolve": "Verify actual submission, acceptance and FDA evidence requirements for the expanded HAE subtype indication.",
        "sourceDate": "2026-09-08",
        "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal"
      }
    ]
  },
  {
    "cycleId": "prax-ulixacaltamide",
    "specialty": "Movement disorders neurology / essential tremor",
    "medicalQuestion": "Does ulixacaltamide meaningfully restore hand-function independence despite frequent CNS adverse effects, treatment discontinuations and responder-enriched withdrawal design?",
    "source": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1",
    "sourceTitle": "Praxis ESSENTIAL3 Study 1/2 original Phase 3 tables",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Essential tremor phenotype",
        "observedClinicalEvidence": "ESSENTIAL3 enrolled patients with longstanding disabling action tremor and meaningful baseline limitations in daily tasks.",
        "specialistInterpretation": "A drug's value lies in using utensils, writing, work and independence; changing a numerical tremor score alone is insufficient.",
        "neededToResolve": "Examine essential tremor diagnosis, baseline ADL disability, coexistent cerebellar symptoms and background propranolol/primidone.",
        "sourceDate": "2025-12-17",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1"
      },
      {
        "topic": "Parallel-group functional endpoint",
        "observedClinicalEvidence": "In ESSENTIAL3 Study 1, mADL11 improvement to Day 56 averaged −4.3 on ulixacaltamide versus −1.7 placebo (p<0.0001).",
        "specialistInterpretation": "An approximately 2.6-point placebo-adjusted functional improvement supports efficacy, provided its patient-important threshold and daily-task components are established.",
        "neededToResolve": "Assess per-task improvements, baseline scores, minimal clinically important difference and treatment-policy analysis.",
        "sourceDate": "2025-12-17",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1"
      },
      {
        "topic": "Alternative missing-data models",
        "observedClinicalEvidence": "A sponsor-reported prespecified delta-adjusted tipping-point analysis retained nominal significance under missing-not-at-random assumptions (p=0.0026).",
        "specialistInterpretation": "This is supportive robustness evidence, not an independent trial; sensitivity under alternative missingness depends on the range and realism of shifts tested.",
        "neededToResolve": "Retrieve full prespecified SAP, dropout by arm, tipping-point grid and alternative nonresponder rules.",
        "sourceDate": "2025-12-17",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1"
      },
      {
        "topic": "Randomized withdrawal responder enrichment",
        "observedClinicalEvidence": "Study 2 randomized 80 stable responders; 55% continued to meet response versus 33% switched to placebo (p=0.037, OR 2.7 [1.06–6.92]).",
        "specialistInterpretation": "Benefit maintenance among selected responders can corroborate initial functional improvement but not estimate effectiveness for all new patients.",
        "neededToResolve": "Study responder screening, rescue criteria, clinical meaning of a ≥3-point change and rebound after withdrawal.",
        "sourceDate": "2025-12-17",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1"
      },
      {
        "topic": "Discontinuation and CNS adverse events",
        "observedClinicalEvidence": "Sponsor safety tables report Study 1 drug-related adverse-event discontinuation of 27.0% on ulixacaltamide versus 1.7% placebo, with dizziness, brain fog, constipation and other CNS effects common.",
        "specialistInterpretation": "A high discontinuation imbalance materially threatens real-world effectiveness even when the functional endpoint is statistically strong.",
        "neededToResolve": "Check dose titration, grade, time-to-resolution, falls, driving safety, retention bias and functional outcomes among discontinuers.",
        "sourceDate": "2025-12-17",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1"
      },
      {
        "topic": "Secondary clinical outcomes",
        "observedClinicalEvidence": "Patient Global Impression and Clinical Global Impression were significant in Study 1, but some comparable Study 2 withdrawal secondaries were not (PGI-C p=0.087 and CGI-S p=0.055).",
        "specialistInterpretation": "Different trials address new-treatment improvement versus withdrawal maintenance; nominal failures must remain visible instead of being buried under two positive primaries.",
        "neededToResolve": "Verify multiplicity order, estimated treatment differences and long-term durability after initial response.",
        "sourceDate": "2025-12-17",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1"
      },
      {
        "topic": "Regulatory clinical challenge",
        "observedClinicalEvidence": "The sponsor reports FDA review with January 29, 2027 goal and favorable mid-cycle inspection disclosure in August 2026.",
        "specialistInterpretation": "Approval consideration should weigh functional benefit against substantial CNS intolerance and missingness, independent of manufacturing and final labeling.",
        "neededToResolve": "Obtain final FDA safety/efficacy review, CMC and dosing recommendations, inspection findings and REMS/label conditions.",
        "sourceDate": "2026-08-06",
        "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-provides-corporate-update-and-20"
      }
    ]
  },
  {
    "cycleId": "urgn-ugn103",
    "specialty": "Urologic oncology / non-muscle-invasive bladder cancer",
    "medicalQuestion": "Does a single-arm intravesical mitomycin trial provide convincing treatment benefit and durability for recurrent low-grade intermediate-risk NMIBC without excessive local toxicity or misleading historical comparisons?",
    "source": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8",
    "sourceTitle": "UroGen November 4 2026 SEC 10-Q UTOPIA study",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Bladder cancer risk phenotype",
        "observedClinicalEvidence": "UTOPIA evaluated recurrent low-grade intermediate-risk non-muscle-invasive bladder cancer, distinct from high-grade invasive or BCG-unresponsive disease.",
        "specialistInterpretation": "Local recurrence and repeated resections burden patients, while progression risk and treatment threshold vary by grade and recurrence history.",
        "neededToResolve": "Verify histologic grade, papillary tumor burden, recurrence history, prior intravesical therapy and cystoscopy surveillance.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      },
      {
        "topic": "Intravesical regimen and delivery",
        "observedClinicalEvidence": "Patients received 75 mg mitomycin by bladder instillation weekly for six doses, followed by cystoscopic assessment at three months.",
        "specialistInterpretation": "Local drug exposure depends on formulation retention, dwell time, urine conditions, adherence and delivery reliability.",
        "neededToResolve": "Obtain formulation comparability, bladder dwell performance, completion of 6 doses and local administration harms.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      },
      {
        "topic": "Three-month objective complete response",
        "observedClinicalEvidence": "UTOPIA reported 77.8% complete response at three months (95% CI 68.3–85.5) in its treated population.",
        "specialistInterpretation": "A high observed clearance proportion is encouraging but a single-arm study cannot estimate placebo or contemporary standard-treatment benefit directly.",
        "neededToResolve": "Study blinded pathology, independent cystoscopy, missing response assessments and the prespecified success threshold.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      },
      {
        "topic": "Response durability conditional on early success",
        "observedClinicalEvidence": "Six-month duration of response by Kaplan–Meier was 94.5% (95% CI 86.1–97.9) among those qualifying for CR.",
        "specialistInterpretation": "This conditional estimate does not imply 94.5% of all treated patients are recurrence-free at nine months or longer.",
        "neededToResolve": "Extract number at risk, recurrence timing, 12-month DOR, competing risks and loss to follow-up.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      },
      {
        "topic": "Historical comparison against related medicine",
        "observedClinicalEvidence": "Sponsor reported consistency with prior ENVISION results of its separately approved related product ZUSDURI.",
        "specialistInterpretation": "Cross-trial similarity is supportive but not randomized noninferiority or proof that UGN-103 formulation is interchangeable.",
        "neededToResolve": "Evaluate inclusion criteria, diagnostic methods, follow-up and tolerability against ENVISION and approved product label.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      },
      {
        "topic": "Bladder-specific harms",
        "observedClinicalEvidence": "Intravesical mitomycin may cause local irritation, painful urination, urinary infection, hematuria or treatment discontinuation.",
        "specialistInterpretation": "For low-grade recurrent disease, avoiding repeat surgery must be balanced against procedural burden and bladder symptoms.",
        "neededToResolve": "Obtain AE rates, treatment cessation, catheterization complications, bladder contraction and urinary function metrics.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      },
      {
        "topic": "Actual FDA cycle and extended follow-up",
        "observedClinicalEvidence": "The UGN-103 NDA was accepted in October 2026 with June 14, 2027 PDUFA target; the sponsor plans submission of 12-month response-duration follow-up during review.",
        "specialistInterpretation": "An application with pending mature durability can be subject to information requests or amendments, but the public record does not establish an extension or CRL.",
        "neededToResolve": "Verify FDA communications, exact role of supplemental follow-up, process controls and formulation stability.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://investors.urogen.com/static-files/7c4f77a2-074b-41ed-b585-ac3fa59a8be8"
      }
    ]
  },
  {
    "cycleId": "zbio-obexelimab",
    "specialty": "Rheumatology / clinical immunology / IgG4-related disease",
    "medicalQuestion": "Does obexelimab durably prevent organ-threatening IgG4-related disease flare while reducing corticosteroid exposure without clinically important cumulative immune suppression?",
    "source": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337",
    "sourceTitle": "NEJM 2026 INDIGO randomized IgG4-related disease study",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Fibroinflammatory disease heterogeneity",
        "observedClinicalEvidence": "IgG4-related disease can involve salivary glands, pancreas, kidneys, retroperitoneum and other organs with variable flare and irreversible fibrosis.",
        "specialistInterpretation": "A pooled flare benefit matters, but permanent damage or differing organ physiology can change the clinical response and proposed label applicability.",
        "neededToResolve": "Review organ-specific baseline counts, biopsy confirmation, damage scores, disease-duration and flare-history balance.",
        "sourceDate": "2026-06-02",
        "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
      },
      {
        "topic": "Mechanism without B-cell depletion",
        "observedClinicalEvidence": "Obexelimab co-engages CD19 and inhibitory FcγRIIb on B cells, suppressing activity without directly depleting B-cell populations.",
        "specialistInterpretation": "This provides a biologically plausible steroid-sparing immunomodulation, but functional immune effects and infection risk still require surveillance.",
        "neededToResolve": "Confirm exposure–B-cell functional changes, immunoglobulin trends, immunization response and long-term immunology.",
        "sourceDate": "2026-06-02",
        "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
      },
      {
        "topic": "Controlled flare primary endpoint",
        "observedClinicalEvidence": "INDIGO randomized 194 patients, 97 each; flare requiring rescue therapy occurred in 26.8% on obexelimab versus 54.6% placebo, HR 0.44 (95% CI 0.28–0.71), p<0.001.",
        "specialistInterpretation": "The observed absolute 27.8-point lower flare incidence adds clinical relevance to relative hazard reduction, provided adjudication is consistent.",
        "neededToResolve": "Obtain time-to-first flare, event definition, adjudicator agreement, competing rescue patterns and organ-specific flare severity.",
        "sourceDate": "2026-06-02",
        "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
      },
      {
        "topic": "Steroid taper standardization",
        "observedClinicalEvidence": "Both trial groups underwent structured steroid tapering to discontinuation by Week 8, creating a challenging test of disease control.",
        "specialistInterpretation": "Uniform steroid withdrawal helps interpret whether medicine maintains remission without glucocorticoids but may differ from individualized practice.",
        "neededToResolve": "Inspect taper deviations, steroid-rescue indication, other immunosuppressive drugs and flare during taper.",
        "sourceDate": "2026-06-02",
        "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
      },
      {
        "topic": "Clinical remission and steroid exposure",
        "observedClinicalEvidence": "Complete remission at Week 52 was 37.1% versus 19.6% (p=0.005); cumulative rescue glucocorticoid dose 329.5 mg versus 929.8 mg (p=0.004).",
        "specialistInterpretation": "Lower steroid exposure is directly meaningful for patients at risk of infection, osteoporosis or metabolic disease, but long-term organ protection remains unproven.",
        "neededToResolve": "Assess remission component validity, irreversible damage, rescue strategy and longer-term sustained drug-free outcomes.",
        "sourceDate": "2026-06-02",
        "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
      },
      {
        "topic": "Adverse events and immunologic safety",
        "observedClinicalEvidence": "The peer-reviewed trial reported serious adverse events 10.3% on obexelimab versus 18.6% placebo; hypersensitivity 16.5% versus 11.3%.",
        "specialistInterpretation": "A numerical SAE difference in a 194-person trial is not proof of improved safety; uncommon infections or vaccine response loss require larger long-term surveillance.",
        "neededToResolve": "Obtain infection severity, serious infusion/injection hypersensitivity, vaccine sub-study limitations and immune surveillance.",
        "sourceDate": "2026-06-02",
        "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
      },
      {
        "topic": "Long-term evidence and FDA review",
        "observedClinicalEvidence": "Zenas reports a 12-month open-label-extension flare-free probability of 0.93 by adjudicated flares and a May 27, 2027 PDUFA target.",
        "specialistInterpretation": "Open-label continuation can select stable patients and lacks an ongoing randomized comparator; it supports durability hypothesis but not a second independent controlled trial.",
        "neededToResolve": "Check extension retention, adverse events, flare ascertainment and FDA review of label population, CMC and safety.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1953926/000110465926123040/zbio-20260930x10q.htm"
      }
    ]
  }
] as const;
export function waveTwoSpecialistCase(id:string):SpecialistCase|null{
 return SPECIALIST_WAVE_TWO.find(c=>c.cycleId===id)||null;
}
