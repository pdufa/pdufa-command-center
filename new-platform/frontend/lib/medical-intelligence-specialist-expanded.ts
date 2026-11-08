/** Source-linked, non-physician-signed clinical subspecialty case analyses.
 * Each interpretation needs its own original public source and explicit unresolved check.
 * FDA review-cycle status is not inferred from clinical efficacy alone.
 */
import type {SpecialistCase} from "./medical-intelligence-specialist-casebook";
export const EXPANDED_SPECIALIST_CASES:readonly SpecialistCase[]=[
  {
    "cycleId": "abvx-uc",
    "specialty": "Gastroenterology / inflammatory bowel disease",
    "medicalQuestion": "Across induction and responder-enriched maintenance studies, which obefazimod dose produces durable, clinically meaningful steroid-free remission without unacceptable long-term immunologic or dose-related harms?",
    "source": "https://ir.abivax.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial",
    "sourceTitle": "Abivax June 1 2026 Phase 3 ABTECT maintenance clinical results",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Clinical UC phenotype and eligibility",
        "observedClinicalEvidence": "The two ABTECT induction studies recruited adults with moderately or severely active UC and reported remission from stool frequency, rectal bleeding and endoscopy scores.",
        "specialistInterpretation": "Remission integrates symptoms with objective mucosal inflammation; clinical interpretation still depends on baseline severity, colonoscopic scoring consistency and prior treatment failures.",
        "neededToResolve": "Verify full diagnostic/endoscopic adjudication, prior advanced-therapy exposure and symptom changes by baseline disease severity.",
        "sourceDate": "2025-07-22",
        "sourceUrl": "https://ir.abivax.com/static-files/99de1b8a-f695-4e75-a38f-9d970eb52d52"
      },
      {
        "topic": "Dose-specific induction reproducibility",
        "observedClinicalEvidence": "Week 8 clinical remission at 50 mg was 21.7% versus 2.5% placebo in ABTECT-1 and 19.8% versus 6.3% in ABTECT-2 (both significant); the 25 mg ABTECT-2 arm was 11.3% versus 6.3% (p=0.1034).",
        "specialistInterpretation": "The strongest induction evidence is replicated for 50 mg; the lower dose has a clinically relevant efficacy inconsistency that should not be masked by pooling doses.",
        "neededToResolve": "Reconstruct multiplicity and induction dose-selection strategy, exact estimates, confidence intervals and whether the label asks for a 25 mg induction regimen.",
        "sourceDate": "2025-07-22",
        "sourceUrl": "https://ir.abivax.com/static-files/99de1b8a-f695-4e75-a38f-9d970eb52d52"
      },
      {
        "topic": "Maintenance and enriched population",
        "observedClinicalEvidence": "After response to the 8-week induction trial, 580 participants were re-randomized: Week 44 remission was 50.8% for 25 mg, 51.3% for 50 mg, and 10.4% for placebo (both p<0.0001).",
        "specialistInterpretation": "Strong maintenance effect applies to induction responders selected for re-randomization, not automatically to every newly treated patient or original non-responder.",
        "neededToResolve": "Determine the responder denominator, handling of induction nonresponse, discontinuation, rescue corticosteroids and the prespecified induction-to-maintenance estimand.",
        "sourceDate": "2026-06-01",
        "sourceUrl": "https://ir.abivax.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial"
      },
      {
        "topic": "Meaningful bowel function and steroid sparing",
        "observedClinicalEvidence": "The maintenance trial reported 47.7% corticosteroid-free clinical remission at Week 44 with 50 mg versus 9.9% placebo and endoscopic remission 47.7% versus 9.9%.",
        "specialistInterpretation": "Steroid-free and endoscopic outcomes offer patient-relevant benefits beyond an isolated stool or bleeding symptom score; verification of hierarchical inference and steroid taper is necessary.",
        "neededToResolve": "Review steroid-free definition, physician adjudication, durability past one year, hospitalization, urgent bowel symptoms and patient-reported function.",
        "sourceDate": "2026-06-01",
        "sourceUrl": "https://ir.abivax.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial"
      },
      {
        "topic": "Dose-related tolerability and safety",
        "observedClinicalEvidence": "Maintenance treatment-emergent adverse events were 71.8% with 50 mg, 58.0% with 25 mg and 50.0% with placebo; serious treatment-emergent events were 5.6%, 2.6%, and 4.2%, respectively.",
        "specialistInterpretation": "The higher all-grade adverse-event burden at 50 mg makes the efficacy–tolerability choice important; a numerical difference alone does not establish causality or clinical rejection.",
        "neededToResolve": "Break down adverse event types, exposure, grade, withdrawal and opportunistic infection; review long-term malignancy and pancreatitis safety in integrated studies.",
        "sourceDate": "2026-06-01",
        "sourceUrl": "https://ir.abivax.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial"
      },
      {
        "topic": "Induction nonresponder extension uncertainty",
        "observedClinicalEvidence": "Sponsor reported clinical remission in 37.2% of initial nonresponders continuing 50 mg in an open-label extension and 45.5% remission among 25-to-50 mg dose escalators after maintenance relapse.",
        "specialistInterpretation": "These data are promising for therapeutic sequencing but are exploratory and cannot be assumed placebo-adjusted or used to repair a failed randomized arm.",
        "neededToResolve": "Check selection and dropout, re-treatment time frame, objective endoscopic outcomes and absence of a concurrent randomized comparator.",
        "sourceDate": "2026-06-29",
        "sourceUrl": "https://ir.abivax.com/news-releases/news-release-details/abivax-reports-positive-abtect-maintenance-part-2-results"
      },
      {
        "topic": "Regulatory clinical challenge",
        "observedClinicalEvidence": "As of June 2026 the company planned an NDA for late Q4; induction at the selected 50 mg dose and maintenance were positive, but a full FDA review and integrated commercial CMC package were not yet published.",
        "specialistInterpretation": "The strongest medical case integrates 50 mg induction replication with responder-enriched maintenance and dose-specific safety; the 25 mg ABTECT-2 inconsistency needs explicit explanation.",
        "neededToResolve": "Obtain filed NDA dose/indication, prespecified SAP, agency feedback and manufacturing/safety integration before making an application outcome prediction.",
        "sourceDate": "2026-06-01",
        "sourceUrl": "https://ir.abivax.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial"
      }
    ]
  },
  {
    "cycleId": "svra-molgramostim",
    "specialty": "Pulmonology / rare interstitial lung disease",
    "medicalQuestion": "Does improvement in diffusion capacity from inhaled GM-CSF produce durable, tangible respiratory function and quality-of-life benefit across the proposed autoimmune PAP population?",
    "source": "https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx",
    "sourceTitle": "Savara 2024 IMPALA-2 Phase 3 primary and secondary endpoints",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Biological disease mechanism",
        "observedClinicalEvidence": "Autoimmune PAP impairs alveolar macrophage surfactant clearance, producing impaired gas exchange and respiratory limitations.",
        "specialistInterpretation": "Replacement of GM-CSF signaling is mechanistically plausible in this autoantibody-mediated setting, but mechanistic fit does not substitute for tangible functional benefit.",
        "neededToResolve": "Confirm anti-GM-CSF antibody diagnosis, baseline DLCO, imaging, oxygen requirement and differences from secondary or congenital PAP.",
        "sourceDate": "2024-06-26",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx"
      },
      {
        "topic": "Gas exchange surrogate",
        "observedClinicalEvidence": "IMPALA-2 reported placebo-adjusted hemoglobin-corrected DLCO % predicted improvement of 6.00 percentage points at Week 24 (p=0.0007), and 6.90 at Week 48 (p=0.0008).",
        "specialistInterpretation": "Physiological consistency is encouraging; DLCO testing depends on hemoglobin, effort, equipment and baseline disease severity, so clinical change thresholds should be evaluated.",
        "neededToResolve": "Find individual DLCO shift distribution, serial measurement quality, oxygenation and relation to functional outcomes.",
        "sourceDate": "2024-06-26",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx"
      },
      {
        "topic": "Longitudinal quality of life",
        "observedClinicalEvidence": "SGRQ total difference versus placebo was −6.59 points at Week 24 (p=0.0072), but −4.87 points at Week 48 (p=0.1046).",
        "specialistInterpretation": "Week 48 loss of nominal significance does not erase an earlier improvement; it makes durability, variance, multiplicity and patient-level functional change pivotal to interpretation.",
        "neededToResolve": "Inspect sample size, baseline SGRQ, missing data, minimal clinically important difference, multiplicity sequence and longer-term trajectory.",
        "sourceDate": "2024-06-26",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx"
      },
      {
        "topic": "Exercise capacity and daily function",
        "observedClinicalEvidence": "The reported peak-exercise-capacity difference was 0.41 METs at Week 24 (p=0.0845) and 0.55 METs at Week 48 (nominal p=0.0234).",
        "specialistInterpretation": "Exercise capacity offers a patient-important cross-check but Week 48 significance may be nominal rather than multiplicity-protected; it cannot by itself rescue or prove the application.",
        "neededToResolve": "Assess clinically meaningful exercise threshold, missing observations, variation across sites and prespecified endpoint hierarchy.",
        "sourceDate": "2024-06-26",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx"
      },
      {
        "topic": "Selection and severity",
        "observedClinicalEvidence": "aPAP can range from modest diffusion impairment to oxygen-dependent severe disease. Sponsor's later mild-impairment subgroup was explicitly exploratory.",
        "specialistInterpretation": "A subgroup's descriptive findings should not broaden a label without interaction evidence and enough precision.",
        "neededToResolve": "Evaluate baseline DLCO distributions, whole-lung-lavage need, risk by disease severity and interaction intervals.",
        "sourceDate": "2026-10-21",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2026/Savara-Presented-New-Data-Showing-Molgramostim-Inhalation-Solution-Molgramostim-Treatment-Effects-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-aPAP-Patients-with-Mild-Diffusion-Impairment/default.aspx"
      },
      {
        "topic": "Benefit-risk and inhaled treatment",
        "observedClinicalEvidence": "Inhaled GM-CSF treatment needs administration and long-term pulmonary/infection monitoring; the published topline alone does not establish comprehensive infection, lung inflammation or immunogenicity findings.",
        "specialistInterpretation": "A favorable gas exchange endpoint must be weighed against adverse events and treatment burden in a rare, chronic respiratory condition.",
        "neededToResolve": "Obtain integrated safety, inhaled device usability, pulmonary adverse events, adherence and age/severity exposure.",
        "sourceDate": "2024-06-26",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx"
      },
      {
        "topic": "FDA-review context and major amendment",
        "observedClinicalEvidence": "Savara reported a formal 3-month extension to November 22 after FDA treated information-request responses as a major amendment; the sponsor stated the correspondence did not cite efficacy, safety or CMC deficiencies.",
        "specialistInterpretation": "An already-completed review-clock extension is not evidence of clinical efficacy failure or a forecast of another delay.",
        "neededToResolve": "Seek contents of amendment and later agency remarks; separately review full CMC, inspection and label evidence.",
        "sourceDate": "2026-04-15",
        "sourceUrl": "https://investors.savarapharma.com/news/news-details/2026/Savara-Announces-the-U-S--Food--Drug-Administration-FDA-Has-Extended-the-Review-Period-for-the-Molgramostim-Inhalation-Solution-Molgramostim-Biologics-License-Application-BLA-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP/default.aspx"
      }
    ]
  },
  {
    "cycleId": "mltx-sonelokimab",
    "specialty": "Dermatology / hidradenitis suppurativa",
    "medicalQuestion": "Does sonelokimab produce clinically meaningful control of inflammatory lesions, painful draining tunnels and quality of life when VELA-2 misses the primary composite estimand?",
    "source": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and",
    "sourceTitle": "MoonLake Nov 4 2026 VELA studies, intercurrent events and BLA submission",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "HS disease phenotype and lived burden",
        "observedClinicalEvidence": "Moderate-to-severe hidradenitis suppurativa features recurring painful nodules, abscesses, draining tunnels, scarring and marked quality-of-life impairment.",
        "specialistInterpretation": "HiSCR75 is clinically compelling only when related pain, drainage, flare and function outcomes support meaningful relief.",
        "neededToResolve": "Assess baseline Hurley stage, tunnel burden, inflammatory-nodule and abscess counts, analgesic use and prior biologic failure.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      },
      {
        "topic": "Definition of high-stringency response",
        "observedClinicalEvidence": "HiSCR75 requires ≥75% reduction in abscess and inflammatory-nodule counts without increase in abscess or draining tunnels.",
        "specialistInterpretation": "The endpoint is more stringent than HiSCR50; the relationship to pain and persistent tunnel disease needs separate evaluation.",
        "neededToResolve": "Check blinded lesion counts, tunnel assessment reliability, subgroup differences and clinically important response changes.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      },
      {
        "topic": "Replicability across pivotal studies",
        "observedClinicalEvidence": "VELA-1 achieved a Week 16 HiSCR75 placebo-adjusted difference around 17 percentage points (p<0.001); VELA-2 showed about 9 points with composite-strategy p=0.053.",
        "specialistInterpretation": "The companion pivotal studies are directionally positive but not equally conclusive under the same primary estimand; cross-trial heterogeneity requires examination.",
        "neededToResolve": "Reconstruct prespecified analysis, placebo response variation, randomization, baseline severity, disease sites and trial interaction estimates.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      },
      {
        "topic": "Intercurrent events and estimand",
        "observedClinicalEvidence": "The sponsor attributed VELA-2 composite-primary non-significance to intercurrent events in a higher-than-expected placebo arm; alternative treatment-policy analysis was reported significant.",
        "specialistInterpretation": "Different assumptions about withdrawals and rescue can change the estimand and clinical interpretation; a favorable alternative strategy is not the same as passing the primary analysis.",
        "neededToResolve": "Obtain the locked SAP, exact intercurrent-event counts, handling by arm and FDA discussion of robustness.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      },
      {
        "topic": "52-week observed responses",
        "observedClinicalEvidence": "Across VELA-1/2, sponsor reported observed Week 52 HiSCR75 67.2% and HiSCR100 33.1% among treated participants (n=396).",
        "specialistInterpretation": "Observed open-label follow-up lacks a comparable randomized placebo arm and can overrepresent retained responders; it is supportive durability evidence, not a second blinded pivotal success.",
        "neededToResolve": "Examine denominator changes, discontinuations, nonresponder imputation and any blinded comparator results at Week 52.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      },
      {
        "topic": "Infection and immune-risk assessment",
        "observedClinicalEvidence": "IL-17-pathway biologics require infection and immunogenicity review; sponsor says the VELA safety profile showed no new signals.",
        "specialistInterpretation": "Mechanistic class risk should not be confused with a proven candidate-specific adverse event imbalance; assess actual infection, candida and inflammatory bowel outcomes.",
        "neededToResolve": "Review exposure-adjusted adverse events, serious infections, fungal infections, immunogenicity and inflammatory bowel disease exclusions.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      },
      {
        "topic": "Population and filing cycle",
        "observedClinicalEvidence": "The BLA for adults and adolescents ≥12 was submitted September 30, 2026; as of Nov 4 the company still expected FDA filing acceptance and a review goal.",
        "specialistInterpretation": "A pediatric extension of the proposed label increases the need for age-appropriate efficacy/safety evidence; no confirmed action date may be assumed before FDA acceptance.",
        "neededToResolve": "Verify acceptance and PDUFA goal, teen trial status, FDA's position on VELA-2 and required safety exposure.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and"
      }
    ]
  },
  {
    "cycleId": "vera-trutakna",
    "specialty": "Nephrology / glomerular disease",
    "medicalQuestion": "Does final ORIGIN 3 demonstrate direct slowing of kidney-function loss sufficient to resolve FDA's earlier reason for awarding accelerated rather than traditional approval?",
    "source": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761486Orig1s000IntegratedR.pdf",
    "sourceTitle": "FDA 2026 atacicept original integrated clinical review",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Renal disease mechanism and population",
        "observedClinicalEvidence": "IgA nephropathy may cause sustained proteinuria, inflammatory glomerular injury and eventual loss of kidney function; atacicept inhibits BAFF and APRIL.",
        "specialistInterpretation": "Reduction in proteinuria can be reasonably likely to predict benefit but is not itself definitive proof that progression to kidney failure slows.",
        "neededToResolve": "Confirm risk strata, baseline eGFR/proteinuria, optimized supportive care and relative effects in high-risk subgroups.",
        "sourceDate": "2026-07-07",
        "sourceUrl": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761486Orig1s000IntegratedR.pdf"
      },
      {
        "topic": "FDA's original approval-limiting observation",
        "observedClinicalEvidence": "FDA's original accelerated approval review found the longer-term eGFR dataset beyond Week 36 too sparse and dependent on unverified model assumptions to support traditional approval.",
        "specialistInterpretation": "This is a documented, precise historical FDA objection to the *then available kidney-function evidence*, not a claim the 2026 final data are inadequate.",
        "neededToResolve": "Compare exactly which additional observed timepoints, completeness and analysis models were supplied in the November supplemental BLA.",
        "sourceDate": "2026-07-07",
        "sourceUrl": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761486Orig1s000IntegratedR.pdf"
      },
      {
        "topic": "Final observed Week-52 eGFR effect",
        "observedClinicalEvidence": "The final 428-participant analysis reported Week 52 eGFR change −0.1 vs −5.7 mL/min/1.73m², treatment difference +5.6 (95% CI 3.7–7.5; p<0.0001).",
        "specialistInterpretation": "A sizeable placebo-adjusted preservation of renal function is clinically meaningful if based on sufficiently observed data with minimal informative dropout.",
        "neededToResolve": "Verify number directly observed at Week 52, visit completeness, slope modeling, attrition reasons and prespecified imputation.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1831828/000119312526449826/vera-20260930.htm"
      },
      {
        "topic": "Two-year slope and clinical progression",
        "observedClinicalEvidence": "Through Week 104, annualized eGFR slope difference was +5.0 mL/min/1.73m²/year (95% CI 3.6–6.5); kidney progression occurred in 11 vs 38, HR 0.24 (95% CI 0.12–0.48).",
        "specialistInterpretation": "Agreement between longitudinal function and progression endpoints strengthens the causal clinical case beyond proteinuria alone, subject to event definitions and censoring.",
        "neededToResolve": "Reconstruct endpoint adjudication, missingness, eGFR trajectory after stopping treatment, GFR variability and subgroup consistency.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1831828/000119312526449826/vera-20260930.htm"
      },
      {
        "topic": "Serious renal outcomes",
        "observedClinicalEvidence": "Through two years sponsor reported no dialysis/transplant/death among treated patients versus seven such events in placebo; details are event-count limited.",
        "specialistInterpretation": "These are patient-important outcomes but their number is small; inferential strength should focus on adequately powered composite endpoints and follow-up, not untested zero-cell comparisons.",
        "neededToResolve": "Verify events, censoring, death competing risks, timing and absolute Kaplan–Meier risk differences.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1831828/000119312526449826/vera-20260930.htm"
      },
      {
        "topic": "Immunologic and injection safety",
        "observedClinicalEvidence": "FDA's accelerated-approval review documented infections 32% vs 28% and local administration reactions 30% vs 5% on atacicept versus placebo.",
        "specialistInterpretation": "In a chronic CKD population, infection monitoring and immunoglobulin changes must be weighed against long-term renal protection; mild injection reactions are not equivalent to major organ harms.",
        "neededToResolve": "Review serious infections, immunoglobulin suppression, exposure-adjusted incidence and vaccination risk over 104 weeks.",
        "sourceDate": "2026-07-07",
        "sourceUrl": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2026/761486Orig1s000IntegratedR.pdf"
      },
      {
        "topic": "Supplement review identity",
        "observedClinicalEvidence": "FDA accelerated-approved TRUTAKNA on July 7, 2026 for proteinuria reduction; company reported submitting a supplemental BLA for full approval November 3, 2026.",
        "specialistInterpretation": "This is evaluation of a supplemental full-approval decision for an already-marketed agent, not a prediction of initial FDA authorization; a submission alone does not establish its next PDUFA goal.",
        "neededToResolve": "Confirm FDA acceptance, submitted final SAP and datasets, comparative safety updates and proposed expanded label language.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://veratherapeutics.gcs-web.com/news-releases/news-release-details/vera-therapeutics-provides-business-update-and-reports-third-3"
      }
    ]
  },
  {
    "cycleId": "srpt-casimersen",
    "specialty": "Neuromuscular medicine / exon 45 skipping",
    "medicalQuestion": "Given the failed ESSENCE confirmatory primary endpoint, is available clinical evidence sufficient to verify meaningful benefit for exon-45-amenable Duchenne patients already receiving AMONDYS 45 under accelerated approval?",
    "source": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm",
    "sourceTitle": "Sarepta Nov 2026 10-Q on ESSENCE and two supplemental applications",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Genotype-specific mechanism",
        "observedClinicalEvidence": "Casimersen is designed for DMD mutations amenable to exon 45 skipping, not the exon 53 population of golodirsen.",
        "specialistInterpretation": "Exon-specific substrate and dystrophin production must be evaluated separately; evidence cannot simply be copied from the shared confirmatory study to both drugs.",
        "neededToResolve": "Find exon-45 subgroup enrollment, baseline phenotype and dose/exposure-specific dystrophin changes.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      },
      {
        "topic": "Regulatory endpoint and failure",
        "observedClinicalEvidence": "Company disclosed the ESSENCE confirmatory study's primary endpoint did not meet statistical significance.",
        "specialistInterpretation": "This is a concrete failure of the confirmatory endpoint supporting verification of clinical benefit; it is not a new drug's initial Phase 3 failure.",
        "neededToResolve": "Retrieve the exact primary endpoint, effect size, CI, p-value, estimand and allocation of exon-45 participants.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      },
      {
        "topic": "Real-world clinical relevance",
        "observedClinicalEvidence": "The sponsor says supplemental applications contain real-world evidence in addition to ESSENCE data.",
        "specialistInterpretation": "Observational functional outcomes may be affected by genotype, steroid care, age, ambulation and selection; patient benefits must be independently checked.",
        "neededToResolve": "Extract contemporaneous natural-history controls, matching variables, timing of decline, missingness and negative-control analyses.",
        "sourceDate": "2026-06-30",
        "sourceUrl": "https://investorrelations.sarepta.com/news-releases/news-release-details/sarepta-announces-fda-acceptance-sndas-amondys-45r-and-vyondys"
      },
      {
        "topic": "Patient-important motor and respiratory function",
        "observedClinicalEvidence": "Loss of ambulation, upper-limb function, ventilation independence and cardiac decline are meaningful Duchenne outcomes.",
        "specialistInterpretation": "A biochemical dystrophin increase must be linked to a credible functional trajectory, not assumed clinically transformative.",
        "neededToResolve": "Determine whether motor function, pulmonary measures or hospitalization data support consistent clinical benefit in exon 45.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      },
      {
        "topic": "Long-term safety",
        "observedClinicalEvidence": "The sponsor cites favorable and consistent safety in its submissions, but adverse-event details are not fully present in the cited summary.",
        "specialistInterpretation": "Existing accelerated approval safety cannot automatically compensate for failure to verify clinical benefit.",
        "neededToResolve": "Obtain cumulative renal, infusion-related and treatment-specific serious events with exposure time.",
        "sourceDate": "2026-06-30",
        "sourceUrl": "https://investorrelations.sarepta.com/news-releases/news-release-details/sarepta-announces-fda-acceptance-sndas-amondys-45r-and-vyondys"
      },
      {
        "topic": "Current approved status",
        "observedClinicalEvidence": "AMONDYS 45 is already approved through accelerated approval; the accepted sNDA seeks conversion with February 28, 2027 action goal.",
        "specialistInterpretation": "The potential decision concerns conversion, labeling and conditions of existing approval; risks may include non-conversion or withdrawal pathways, not simply initial approval versus CRL.",
        "neededToResolve": "Trace accelerated approval obligations, FDA confirmatory-benefit standard and possible statutory follow-up actions.",
        "sourceDate": "2026-06-30",
        "sourceUrl": "https://investorrelations.sarepta.com/news-releases/news-release-details/sarepta-announces-fda-acceptance-sndas-amondys-45r-and-vyondys"
      },
      {
        "topic": "Specialist's skeptical countercase",
        "observedClinicalEvidence": "The public evidence demonstrates a failed confirmatory primary endpoint but does not provide complete separate exon-45 efficacy analyses.",
        "specialistInterpretation": "A specialist cannot dismiss the negative controlled result based solely on biological plausibility or uncontrolled comparisons; nor can current regulatory withdrawal be presumed.",
        "neededToResolve": "Demand exonic subgroup results, coherent causal linkage, and FDA's full assessment of proposed real-world corroboration.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      }
    ]
  },
  {
    "cycleId": "srpt-golodirsen",
    "specialty": "Neuromuscular medicine / exon 53 skipping",
    "medicalQuestion": "For exon-53-amenable Duchenne patients, does the total evidence verify clinically important benefit despite the failure of ESSENCE's shared confirmatory primary endpoint?",
    "source": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm",
    "sourceTitle": "Sarepta Nov 2026 10-Q on ESSENCE and two supplemental applications",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Exon-53 molecular specificity",
        "observedClinicalEvidence": "Golodirsen targets mutations amenable to exon 53 skipping, a different genotype-defined population from exon-45-amenable disease.",
        "specialistInterpretation": "Mechanistic rationale is genotype specific; pooled outcomes spanning different products may obscure drug-specific treatment effects.",
        "neededToResolve": "Obtain genotype-specific ESSENCE participant counts, pharmacodynamic dystrophin changes and clinical disease trajectories.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      },
      {
        "topic": "Confirmatory failure",
        "observedClinicalEvidence": "Sponsor disclosed ESSENCE's shared primary endpoint did not meet statistical significance.",
        "specialistInterpretation": "Failure of confirmatory significance is a direct concern to the evidentiary basis for full approval, not proof of an FDA withdrawal decision.",
        "neededToResolve": "Extract original endpoints, confidence intervals, multiplicity rules and exon-53-specific analyses.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      },
      {
        "topic": "Meaningful functional outcomes",
        "observedClinicalEvidence": "Progressive DMD causes motor, upper-limb and respiratory decline and loss of independence.",
        "specialistInterpretation": "The goal is demonstrated slowing of meaningful disability in an exon-53 group, beyond dystrophin expression alone.",
        "neededToResolve": "Examine functional thresholds, floor effects, disease progression and steroid / standard-of-care comparability.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      },
      {
        "topic": "Comparative observational evidence",
        "observedClinicalEvidence": "Sponsor included published real-world evidence in the supplement submissions.",
        "specialistInterpretation": "Genotype, baseline age, ambulatory status and prior treatment can confound observational comparisons; such studies should not be treated as randomized confirmation.",
        "neededToResolve": "Request matched controls, negative controls, survivor bias adjustment, missingness treatment and independent replication.",
        "sourceDate": "2026-06-30",
        "sourceUrl": "https://investorrelations.sarepta.com/news-releases/news-release-details/sarepta-announces-fda-acceptance-sndas-amondys-45r-and-vyondys"
      },
      {
        "topic": "Exposure and long-term safety",
        "observedClinicalEvidence": "Sponsor described a favorable safety record in support of ongoing treatment.",
        "specialistInterpretation": "Benefit-risk depends on specific long-term golodirsen adverse outcomes and infusion/renal burden, not just broad exon-skipping class familiarity.",
        "neededToResolve": "Compare grade ≥3 adverse events, infusion reactions, kidney surveillance and discontinuations against achieved clinical benefits.",
        "sourceDate": "2026-06-30",
        "sourceUrl": "https://investorrelations.sarepta.com/news-releases/news-release-details/sarepta-announces-fda-acceptance-sndas-amondys-45r-and-vyondys"
      },
      {
        "topic": "Regulatory application status",
        "observedClinicalEvidence": "VYONDYS 53 already has accelerated approval; a separately accepted sNDA seeks full approval with Feb 28, 2027 goal.",
        "specialistInterpretation": "This is not an initial approval review, and FDA might take different decisions for the two genotype-specific supplemental applications.",
        "neededToResolve": "Verify each supplement's precise evidentiary set, proposed label, postmarketing obligation and agency correspondence.",
        "sourceDate": "2026-06-30",
        "sourceUrl": "https://investorrelations.sarepta.com/news-releases/news-release-details/sarepta-announces-fda-acceptance-sndas-amondys-45r-and-vyondys"
      },
      {
        "topic": "Failure-first medical judgment",
        "observedClinicalEvidence": "A negative confirmatory primary result is a material clinical concern, but final review also considers totality of evidence and present accelerated status.",
        "specialistInterpretation": "Neither continued approval nor immediate withdrawal can be inferred; distinguish lack of conversion from all other possible FDA dispositions.",
        "neededToResolve": "Reconstruct FDA benefit-risk judgment from exon-53 subgroup data, quality of observational evidence and regulatory guidance.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
      }
    ]
  },
  {
    "cycleId": "blte-stargardt",
    "specialty": "Retina / inherited retinal degeneration",
    "medicalQuestion": "Does a 35.7% slowing of retinal atrophic-lesion enlargement with tinlarebant confer a meaningful preservation of visual function that justifies night-vision and retinal-cycle adverse effects?",
    "source": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite",
    "sourceTitle": "Belite DRAGON Phase 3 clinical results and safety",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Patient phenotype and progression",
        "observedClinicalEvidence": "The DRAGON trial enrolled adolescents diagnosed with STGD1 with at least one ABCA4 mutation, lesion size under three disc areas, and BCVA of 20/200 or better.",
        "specialistInterpretation": "Restricting trial entry to early or moderately preserved visual acuity may affect how treatment benefit transfers to advanced retinal atrophy or other genotypes.",
        "neededToResolve": "Verify age, ABCA4 variant severity, lesion location relative to fovea, baseline visual acuity and fellow-eye dependence.",
        "sourceDate": "2025-12-12",
        "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
      },
      {
        "topic": "Retinal imaging as the pivotal endpoint",
        "observedClinicalEvidence": "The sponsor reported 35.7% slowing of primary retinal atrophic-lesion growth with the prespecified unstructured MMRM (p=0.0033).",
        "specialistInterpretation": "A statistically significant retinal-imaging effect is evidence of disease modification, but it is not automatically proof of preserved reading, visual acuity or low-light function.",
        "neededToResolve": "Examine lesion adjudication, image reliability, foveal involvement, absolute lesion change and relationship with functional acuity outcomes.",
        "sourceDate": "2025-12-12",
        "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
      },
      {
        "topic": "Statistical model sensitivity",
        "observedClinicalEvidence": "The sponsor also reported a 35.4% lesion-growth reduction using a post-hoc autoregressive covariance MMRM (p<0.0001), alongside the prespecified p=0.0033.",
        "specialistInterpretation": "A smaller post-hoc p-value does not improve the hierarchy or replace the prespecified analysis; model choice and missing ocular follow-up remain important.",
        "neededToResolve": "Obtain original SAP, covariance diagnostics, repeated-measures completeness, masked imaging rules and multiplicity plan.",
        "sourceDate": "2025-12-12",
        "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
      },
      {
        "topic": "Bilateral consistency and biological effect",
        "observedClinicalEvidence": "The sponsor reported a 33.6% reduction in lesion growth in the fellow eye (p=0.041) and about 80% suppression of serum RBP4 at 5 mg/day.",
        "specialistInterpretation": "Bilateral imaging consistency and target engagement strengthen biological plausibility but dependence between two eyes must be considered in any inference.",
        "neededToResolve": "Check eye-level correlation, whether fellow-eye endpoint was prespecified, and whether stronger RBP4 suppression tracks visual benefit.",
        "sourceDate": "2025-12-12",
        "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
      },
      {
        "topic": "Patient-important vision outcomes",
        "observedClinicalEvidence": "STGD1 progressively impairs central vision, reading, face recognition and functional independence, while a lesion boundary may grow without immediate loss of visual acuity.",
        "specialistInterpretation": "Clinical relevance requires estimating whether a slowing in an anatomical lesion delays vision decline or disability over a patient's remaining years.",
        "neededToResolve": "Obtain BCVA and low-luminance visual acuity trajectories, reading speed, patient-reported visual function and lesion-location analyses.",
        "sourceDate": "2025-12-12",
        "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
      },
      {
        "topic": "Ocular tolerability and dark adaptation",
        "observedClinicalEvidence": "The sponsor reported xanthopsia, delayed dark adaptation and night-vision impairment as common drug-related ocular adverse events, generally mild and often resolving.",
        "specialistInterpretation": "The intended medicine affects a visual-cycle pathway; even reversible visual side effects matter to patients with reduced retinal reserve.",
        "neededToResolve": "Determine severity, duration, night-driving and daily-function impact, discontinuations, recovery and any deterioration on restarting.",
        "sourceDate": "2025-12-12",
        "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
      },
      {
        "topic": "Current FDA decision question",
        "observedClinicalEvidence": "FDA accepted the tinlarebant NDA for priority review with a reported February 12, 2027 PDUFA goal.",
        "specialistInterpretation": "Filing acceptance establishes an ongoing regulatory review, not FDA validation of anatomical endpoints, visual functioning or CMC adequacy.",
        "neededToResolve": "Compare proposed label and disease-severity range to DRAGON population; obtain full endpoint and safety interpretation and FDA communications.",
        "sourceDate": "2026-08-11",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1889109/000110465926094040/tm2622827d1_ex99-1.htm"
      }
    ]
  },
  {
    "cycleId": "mlys-lorundrostat",
    "specialty": "Hypertension cardiology / clinical nephrology",
    "medicalQuestion": "Can aldosterone-synthase inhibition meaningfully lower resistant hypertension in patients on multiple background drugs without clinically consequential hyperkalemia, kidney injury or hypotension?",
    "source": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm",
    "sourceTitle": "Mineralys November 4 2026 8-K clinical results and FDA review",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Resistant hypertension diagnosis",
        "observedClinicalEvidence": "Launch-HTN enrolled participants inadequately controlled despite two to five background antihypertensive medications.",
        "specialistInterpretation": "True resistant hypertension requires assessment of adherence, measurements, white-coat effect and appropriate concurrent therapy; a broader uncontrolled-HTN population can differ.",
        "neededToResolve": "Obtain ambulatory BP confirmation, medication adherence, sodium intake, secondary cause screening, CKD/OSA and baseline treatment mix.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://ir.mineralystx.com/news-events/press-releases/detail/123/mineralys-therapeutics-presents-new-lorundrostat-data-in"
      },
      {
        "topic": "Clinical measurement and primary effect",
        "observedClinicalEvidence": "The trial compared lorundrostat 50 mg, a dose-escalation strategy, and placebo, with Week 6 automated office systolic BP change as the primary endpoint.",
        "specialistInterpretation": "Automated office BP is objective and clinically relevant, but antihypertensive outcome inference still depends on placebo-adjusted effect, time of day and background-medication stability.",
        "neededToResolve": "Obtain the full Week 6 primary ANCOVA estimate and CI, ambulatory monitoring, medication changes and Week 12 persistence.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://ir.mineralystx.com/news-events/press-releases/detail/123/mineralys-therapeutics-presents-new-lorundrostat-data-in"
      },
      {
        "topic": "Patient-level target attainment",
        "observedClinicalEvidence": "Sponsor reported 46% on lorundrostat 50 mg achieved Week 12 office SBP below 130 mmHg and more than two-thirds achieved reduction ≥10 mmHg.",
        "specialistInterpretation": "Goal attainment can be meaningful, but treatment comparisons must account for baseline severity and placebo response; descriptive active-arm percentages are not independent comparative efficacy statistics.",
        "neededToResolve": "Obtain placebo target-achievement rate, responder risk difference, trial denominator and confidence intervals.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm"
      },
      {
        "topic": "CKD and proteinuria subgroup",
        "observedClinicalEvidence": "The company reported similar BP reductions with and without CKD and an exploratory reduction of albuminuria by 52% versus placebo.",
        "specialistInterpretation": "A potentially helpful renal signal is plausible through aldosterone reduction, but must be separated from primary BP efficacy and from definitive kidney-outcome benefit.",
        "neededToResolve": "Review albuminuria multiplicity, exact subgroup denominators, baseline eGFR, potassium and whether renal endpoints were prospectively controlled.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm"
      },
      {
        "topic": "Hyperkalemia and electrolyte harm",
        "observedClinicalEvidence": "Aldosterone-synthase inhibition may impair potassium excretion, especially with CKD or concomitant RAAS blockade; the reviewed public summary does not establish excess serious hyperkalemia in Launch-HTN.",
        "specialistInterpretation": "This is a disease-and-mechanism-specific risk to investigate, not a documented adverse effect imbalance or FDA objection.",
        "neededToResolve": "Obtain trial potassium frequency by grade, eGFR change, temporary interruptions, discontinuation, and monitoring protocol.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm"
      },
      {
        "topic": "Titration, polypharmacy and persistence",
        "observedClinicalEvidence": "Launch-HTN included a fixed 50 mg group and a strategy with optional escalation to 100 mg at Week 6 based on predefined criteria.",
        "specialistInterpretation": "The clinical product label may depend on titration benefit-risk, renal function, hypotension and interactions with multiple pre-existing antihypertensives.",
        "neededToResolve": "Determine the number escalated, absolute dose-specific effect, adverse-event risk and longer-term BP stability.",
        "sourceDate": "2026-10-26",
        "sourceUrl": "https://ir.mineralystx.com/news-events/press-releases/detail/123/mineralys-therapeutics-presents-new-lorundrostat-data-in"
      },
      {
        "topic": "Regulatory interpretation and timing",
        "observedClinicalEvidence": "FDA accepted the lorundrostat NDA for hypertension in combination with other therapies with a reported December 22, 2026 review goal.",
        "specialistInterpretation": "Positive BP results support review but cannot show manufacturing, safety and labeling readiness; review timing is a separate question from drug efficacy.",
        "neededToResolve": "Verify accepted dose/indication, regulatory communication, CMC and inspection status, and integrated long-term electrolyte-safety evidence.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm"
      }
    ]
  }
] as const;
export function expandedSpecialistCaseForCycle(id:string):SpecialistCase|null{
 return EXPANDED_SPECIALIST_CASES.find(c=>c.cycleId===id)||null;
}
