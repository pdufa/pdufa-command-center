/** Disease-specific evidence review for FDA cycles not covered in the original specialty casebooks.
 * Public-source medical reasoning only; not an MD-authored or signed report.
 */
import type {SpecialistCase} from "./medical-intelligence-specialist-casebook";
export const SPECIALIST_WAVE_ONE:readonly SpecialistCase[]=[
  {
    "cycleId": "achv-cytisinicline",
    "specialty": "Addiction medicine / tobacco cessation",
    "medicalQuestion": "Do sustained biologically verified quit rates establish clinically important cessation, and has FDA's actual manufacturing/label CRL been corrected?",
    "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700",
    "sourceTitle": "Peer-reviewed ORCA-3 phase 3 replication trial",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Smoking dependence phenotype",
        "observedClinicalEvidence": "ORCA-3 enrolled smokers averaging roughly 20 cigarettes daily, with years of nicotine exposure and repeated previous quit attempts.",
        "specialistInterpretation": "This is a clinically high-relapse group; treatment relevance depends on durability and behavioral support, not only early self-reported quitting.",
        "neededToResolve": "Examine cotinine/CO verification, dependence severity, psychiatric comorbidity, and subgroup response.",
        "sourceDate": "2025-04-21",
        "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700"
      },
      {
        "topic": "Replicated abstinence evidence",
        "observedClinicalEvidence": "ORCA-2 and ORCA-3 both reported improved biochemically verified continuous abstinence with 12 weeks cytisinicline compared with placebo through Week 24.",
        "specialistInterpretation": "Reproducibility of sustained quitting is more meaningful than transient point-prevalence abstinence; placebo and counseling context matter.",
        "neededToResolve": "Reproduce absolute risk differences, missing-as-smoking rules, quit-window definitions and confidence intervals.",
        "sourceDate": "2025-04-21",
        "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700"
      },
      {
        "topic": "Durability after treatment",
        "observedClinicalEvidence": "ORCA-3 reported continuous abstinence for Weeks 9–24 of 20.5% for 12-week cytisinicline versus 4.2% placebo (OR 5.79, p<0.0001).",
        "specialistInterpretation": "A sustained six-month benefit is a credible cessation outcome, but the majority did not maintain continuous abstinence.",
        "neededToResolve": "Review relapse after 24 weeks, tobacco exposure biomarkers, long-term cessation without selection from extension trials.",
        "sourceDate": "2025-04-21",
        "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700"
      },
      {
        "topic": "Treatment tolerability",
        "observedClinicalEvidence": "ORCA-3 reported insomnia, nausea, abnormal dreams and headache among common adverse events, without treatment-related serious adverse events in the company's summary.",
        "specialistInterpretation": "In patients with depression, anxiety and cardiovascular illness, tolerability and treatment adherence influence whether trial efficacy generalizes to practice.",
        "neededToResolve": "Retrieve complete adverse event severity, treatment discontinuation, neuropsychiatric monitoring, co-medications and older-user exposure.",
        "sourceDate": "2025-04-21",
        "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700"
      },
      {
        "topic": "Comparison to established care",
        "observedClinicalEvidence": "Cytisinicline is a non-nicotine, nicotinic receptor partial agonist; patients may have previously tried varenicline or bupropion.",
        "specialistInterpretation": "Mechanism can support an alternative treatment choice, but placebo-controlled quit odds do not prove superiority to existing pharmacotherapy.",
        "neededToResolve": "Use contemporaneous head-to-head studies or appropriately adjusted evidence, and compare counseling intensity and adherence.",
        "sourceDate": "2025-04-21",
        "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700"
      },
      {
        "topic": "Long-term open-label evidence",
        "observedClinicalEvidence": "A 52-week open-label study selected participants who continued smoking/vaping after prior ORCA trials and reported 31.2% four-week abstinence at Weeks 49–52.",
        "specialistInterpretation": "Chosen re-treatment volunteers create selection bias; these data contribute exposure and feasibility, not replicated randomized cessation efficacy.",
        "neededToResolve": "Reconcile participants enrolled/retained, ascertainment, relapse, and treatment-emergent events during repeat use.",
        "sourceDate": "2026-10-21",
        "sourceUrl": "https://ir.achievelifesciences.com/news-events/press-releases/detail/274/achieve-life-sciences-presents-52-week-cytisinicline-results-for-smoking-and-vaping-cessation-at-chest-2026"
      },
      {
        "topic": "Actual FDA failure mechanism",
        "observedClinicalEvidence": "The June 2026 cytisinicline CRL cited previous contract-manufacturer CGMP facility deficiencies and draft labeling, not clinical efficacy/safety concerns per sponsor and the public redacted CRL.",
        "specialistInterpretation": "A clinical efficacy investigation cannot be substituted for commercial process remediation; the strongest demonstrated failure pathway is application manufacturing and labeling readiness.",
        "neededToResolve": "Verify Adare process qualification, release testing, stability, facility inspection and formal FDA acceptance of any resubmission.",
        "sourceDate": "2026-08-11",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/949858/000119312526344624/achv-20260630.htm"
      }
    ]
  },
  {
    "cycleId": "apmd-ad109",
    "specialty": "Sleep medicine / pulmonology",
    "medicalQuestion": "Do AD109's sleep-study improvements change meaningful daytime functioning despite treatment-policy versus on-treatment differences and adverse-event dropout?",
    "source": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526300909/apni-20260710.htm",
    "sourceTitle": "Apnimed 2026 SEC S-1, two Phase 3 OSA studies",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "OSA severity and functional burden",
        "observedClinicalEvidence": "SynAIRgy enrolled 646 participants (median AHI 19.6 events/hour, median BMI 32.4), with mild, moderate and severe OSA represented.",
        "specialistInterpretation": "AHI measures airway obstruction, but sleepiness, driving safety, oxygen desaturation and quality of life vary substantially at the same AHI.",
        "neededToResolve": "Assess daytime somnolence, obesity, PAP intolerance, baseline hypoxic burden, hypertension and cardiovascular risk.",
        "sourceDate": "2026-05-18",
        "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/42148495/"
      },
      {
        "topic": "Treatment-policy primary estimand",
        "observedClinicalEvidence": "At Week 26, sponsor SEC filing reports mean AHI reductions 44.1% versus 17.6% placebo in SynAIRgy and 33.7% versus 7.3% in LunAIRo (both p<0.0001).",
        "specialistInterpretation": "Repeated evidence of reduced AHI supports physiological efficacy, but absolute change and functional outcomes determine the value to patients.",
        "neededToResolve": "Recalculate arm differences and confidence intervals, check within-study multiplicity, baseline OSA categories and night-to-night variability.",
        "sourceDate": "2026-07-10",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526300909/apni-20260710.htm"
      },
      {
        "topic": "Estimand sensitivity and discontinuation",
        "observedClinicalEvidence": "The on-treatment AHI reductions were larger: 55.6% in SynAIRgy and 46.8% in LunAIRo; sensitivity to intercurrent events was evident in secondary responder analyses.",
        "specialistInterpretation": "A larger effect among those continuing the drug does not equal effectiveness under a real-world treatment-policy strategy.",
        "neededToResolve": "Audit missing-data rules, treatment discontinuation and control-based imputation for primary and responder analyses.",
        "sourceDate": "2026-07-10",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526300909/apni-20260710.htm"
      },
      {
        "topic": "Clinically interpretable responders",
        "observedClinicalEvidence": "In SynAIRgy, the ≥50% AHI reduction responder outcome was 25.8% versus 19.8% placebo (treatment-policy p=0.182), but 39.6% versus 22.3% under on-treatment (p<0.0001).",
        "specialistInterpretation": "This direct disagreement in a patient-facing threshold is a substantive analysis-method and adherence concern despite positive continuous AHI primaries.",
        "neededToResolve": "Review responder hierarchy, prevalence of baseline mild disease, treatment interruption and sensitivity of clinically relevant responder definitions.",
        "sourceDate": "2026-07-10",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526300909/apni-20260710.htm"
      },
      {
        "topic": "Oxygenation and symptoms",
        "observedClinicalEvidence": "Sponsor reported improved oxygen desaturation index and hypoxic burden, while the peer-reviewed SynAIRgy report found no statistically significant treatment difference in PROMIS-Fatigue.",
        "specialistInterpretation": "Physiological respiratory improvements do not necessarily translate to meaningful daytime symptom relief; a specialist would not substitute AHI for fatigue or safety outcomes.",
        "neededToResolve": "Examine ESS, PROMIS, psychomotor driving outcomes, actual hypoxic burden and patient-perceived function.",
        "sourceDate": "2026-05-18",
        "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/42148495/"
      },
      {
        "topic": "Treatment-limiting adverse events",
        "observedClinicalEvidence": "Peer-reviewed SynAIRgy reported 21.2% of AD109 participants versus 3.1% placebo discontinued therapy because of adverse events; typical symptoms included dry mouth, nausea, insomnia and urinary hesitation.",
        "specialistInterpretation": "An approximately 18-percentage-point discontinuation excess may materially reduce practical treatment benefit; this is an observed study finding, not a documented FDA CRL objection.",
        "neededToResolve": "Confirm discontinuation denominator, atomoxetine-related cardiovascular effects, anticholinergic urinary issues, ECG/blood pressure and repeat-use safety.",
        "sourceDate": "2026-05-18",
        "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/42148495/"
      },
      {
        "topic": "Clinical standard of care and FDA claim",
        "observedClinicalEvidence": "The proposed indication is oral treatment of OSA, potentially for patients who do not tolerate positive airway pressure; the study's physiological endpoint is distinct from demonstrated cardiovascular event reduction.",
        "specialistInterpretation": "Comparative value depends on demonstrated symptom, adherence and hypoxic-burden outcomes, not unsupported claims of heart-attack or stroke prevention.",
        "neededToResolve": "Verify accepted FDA label target, exact AHI definition, safety in comorbid cardiac disease and final CMC/inspection review.",
        "sourceDate": "2026-07-10",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526300909/apni-20260710.htm"
      }
    ]
  },
  {
    "cycleId": "axsm-axs12",
    "specialty": "Neurology / narcolepsy and sleep disorders",
    "medicalQuestion": "Does AXS-12 reproducibly reduce disruptive cataplexy attacks with durable daily-function benefit and tolerable noradrenergic adverse effects?",
    "source": "https://www.axsome.com/news/axsome-therapeutics-announces-axs-12-achieves-primary-endpoi-11721",
    "sourceTitle": "Axsome November 26 2024 ENCORE cataplexy Phase 3",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Narcolepsy phenotype",
        "observedClinicalEvidence": "Cataplexy episodes are sudden emotion-triggered transient muscle weakness, causing injuries, social limitation and unpredictability in narcolepsy patients.",
        "specialistInterpretation": "Frequency is important but duration, severity, falls and daytime functioning must be interpreted alongside reported attack counts.",
        "neededToResolve": "Inspect confirmation of cataplexy phenotype, diary adherence, baseline attack variation and concomitant stimulants.",
        "sourceDate": "2024-11-26",
        "sourceUrl": "https://www.axsome.com/news/axsome-therapeutics-announces-axs-12-achieves-primary-endpoi-11721"
      },
      {
        "topic": "Randomized response",
        "observedClinicalEvidence": "ENCORE met its randomized-withdrawal cataplexy primary endpoint compared with placebo (p=0.017), after long-term treatment and responder selection.",
        "specialistInterpretation": "Maintenance in an enriched responder group is valuable evidence but does not directly estimate initiating-treatment effectiveness in all eligible patients.",
        "neededToResolve": "Obtain full randomized-withdrawal design, relapse criteria, effect size with confidence limits and exact statistical model.",
        "sourceDate": "2024-11-26",
        "sourceUrl": "https://www.axsome.com/news/axsome-therapeutics-announces-axs-12-achieves-primary-endpoi-11721"
      },
      {
        "topic": "Magnitude and onset",
        "observedClinicalEvidence": "Company reported ≥50% cataplexy response in 72% after one month and 82% after six months of AXS-12 treatment.",
        "specialistInterpretation": "High observed response among retained participants supports plausibility but can inflate apparent durable efficacy if discontinuations are ignored.",
        "neededToResolve": "Audit denominator, retention, baseline attack rate and nonresponder imputation in open-label periods.",
        "sourceDate": "2024-11-26",
        "sourceUrl": "https://www.axsome.com/news/axsome-therapeutics-announces-axs-12-achieves-primary-endpoi-11721"
      },
      {
        "topic": "Cognition and everyday life",
        "observedClinicalEvidence": "The ENCORE program reported a positive prespecified cognition measure (p=0.011) and overall improvement by patient global impression (p=0.024).",
        "specialistInterpretation": "Cognitive changes may be meaningful but require validation of measurement, treatment hierarchy and differences from effects on arousal or mood.",
        "neededToResolve": "Study the Narcolepsy Symptom Assessment Questionnaire and patient-function relationships; clarify multiplicity and prespecification.",
        "sourceDate": "2024-11-26",
        "sourceUrl": "https://www.axsome.com/news/axsome-therapeutics-announces-axs-12-achieves-primary-endpoi-11721"
      },
      {
        "topic": "Replication by separate trials",
        "observedClinicalEvidence": "The sponsor's November 2026 materials describe favorable cataplexy outcomes across CONCERT and SYMPHONY in addition to ENCORE.",
        "specialistInterpretation": "Multiple controlled comparisons may strengthen evidence if trial endpoints, treatment exposures and analyzed populations are comparable.",
        "neededToResolve": "Obtain original separate NCT mapping, rate ratios, confidence intervals and the full FDA-submitted integrated efficacy analysis.",
        "sourceDate": "2026-11-02",
        "sourceUrl": "https://axsometherapeuticsinc.gcs-web.com/static-files/7fb1eb08-7b45-42cc-a44f-d8dd57057698"
      },
      {
        "topic": "Noradrenergic safety and adherence",
        "observedClinicalEvidence": "Reboxetine affects norepinephrine reuptake; insomnia, tachycardia, blood-pressure changes, psychiatric symptoms and withdrawal need disease-specific clinical attention.",
        "specialistInterpretation": "Mechanism-based concerns must be distinguished from actual adverse-event patterns in the full development program.",
        "neededToResolve": "Review treatment-emergent serious events, mood symptoms, cardiovascular monitoring and discontinuation by dose.",
        "sourceDate": "2024-11-26",
        "sourceUrl": "https://www.axsome.com/news/axsome-therapeutics-announces-axs-12-achieves-primary-endpoi-11721"
      },
      {
        "topic": "Accepted FDA review identity",
        "observedClinicalEvidence": "The FDA accepted the AXS-12 NDA for cataplexy in narcolepsy with a May 1, 2027 target in the July 2026 sponsor SEC filing.",
        "specialistInterpretation": "A date and filed application are not proof the final benefit-risk and CMC assessment is complete.",
        "neededToResolve": "Verify labeling population, extent of long-term exposure, regulatory correspondence and current review-clock status.",
        "sourceDate": "2026-07-15",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1579428/000119312526304039/axsm-ex99_1.htm"
      }
    ]
  },
  {
    "cycleId": "cldx-barzolvolimab",
    "specialty": "Clinical allergy and immunology / chronic spontaneous urticaria",
    "medicalQuestion": "Do replicated complete urticaria responses justify immunomodulatory barzolvolimab in biologic-refractory patients, with durable disease control and acceptable longer-term safety?",
    "source": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm",
    "sourceTitle": "Celldex November 2026 SEC 10-Q, EMBARQ-CSU1/2 results",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "CSU disease phenotype",
        "observedClinicalEvidence": "Chronic spontaneous urticaria causes recurrent itchy wheals and sometimes angioedema without a single external trigger, impairing sleep and daily function.",
        "specialistInterpretation": "The clinical question is control of itch, hives and angioedema beyond an antihistamine- or omalizumab-resistant baseline.",
        "neededToResolve": "Verify eligibility, concomitant H1 therapy, prior omalizumab exposure and patient-reported function.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      },
      {
        "topic": "Replicated UAS7 endpoints",
        "observedClinicalEvidence": "For 150 mg every four weeks, EMBARQ-CSU1 and 2 showed Week 12 UAS7 mean changes −20.2 each versus −10.7 and −11.4 placebo (reported p<0.00001).",
        "specialistInterpretation": "Strong replication of symptom-activity reduction supports efficacy, but mean reduction alone does not indicate complete symptom control.",
        "neededToResolve": "Verify effect-size CIs, full UAS7 distribution, responder criteria and baseline medication washouts.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      },
      {
        "topic": "Complete disease control",
        "observedClinicalEvidence": "Week 12 UAS7=0 complete-response rates were 42.4% and 45.7% on 150 mg versus 9.3% and 12.6% placebo in CSU1 and CSU2.",
        "specialistInterpretation": "Disease-complete response is especially relevant to quality of life, but durability after stopping therapy and rebound are distinct concerns.",
        "neededToResolve": "Analyze Week 24/52 complete responses, relapse after drug discontinuation and time-to-response.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      },
      {
        "topic": "Omalizumab-refractory patients",
        "observedClinicalEvidence": "In prespecified refractory groups, Week 12 UAS7=0 with 150 mg was 55.3% versus 9.3% placebo in CSU1 and 41.7% versus 15.1% in CSU2.",
        "specialistInterpretation": "Benefit in prior biologic failure may fill a major treatment gap, but smaller subset denominators and interactions need care.",
        "neededToResolve": "Obtain subgroup n, outcome CI, confirmed prior biologic failure definition and treatment-effect interaction.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      },
      {
        "topic": "Angioedema outcomes",
        "observedClinicalEvidence": "Among participants with baseline AAS7 above zero, Week 12 angioedema-free responses with 150 mg were 62.7% vs 33.8% and 74.3% vs 33.7% placebo.",
        "specialistInterpretation": "Angioedema remission is meaningful for patients, but anatomical swelling severity and rescue medication use still matter.",
        "neededToResolve": "Audit adjudication of angioedema, severe events, steroid rescue and patient function.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      },
      {
        "topic": "Safety of prolonged mast-cell suppression",
        "observedClinicalEvidence": "Barzolvolimab targets KIT and mast cells; the sponsor reported a generally tolerable profile through 24-week blinded treatment and ongoing 52-week extension.",
        "specialistInterpretation": "Mechanistic immune and mast-cell effects warrant skin/hair, blood-count, infection and long-term safety review; theoretical risk is not an established event imbalance.",
        "neededToResolve": "Obtain complete grade 3+ events, pigment changes, neutrophils, infection, serious event exposure and dose-related discontinuations.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      },
      {
        "topic": "Filing stage and clinical inference",
        "observedClinicalEvidence": "Sponsor plans a future 2027 BLA after positive pivotal studies; a regulatory approval clock was not assigned in the reviewed November disclosure.",
        "specialistInterpretation": "Two successful trials are a strong efficacy basis, but submission completeness, long-term safety, manufacture and review acceptance remain separate stages.",
        "neededToResolve": "Verify final Week 52 data, full BLA source/label and later FDA acceptance before any PDUFA timing prediction.",
        "sourceDate": "2026-11-05",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
      }
    ]
  },
  {
    "cycleId": "cytk-aficamten-ohcm",
    "specialty": "Cardiology / obstructive hypertrophic cardiomyopathy",
    "medicalQuestion": "What additional clinically meaningful evidence does MAPLE-HCM contribute to an obstructive-HCM indication already approved by FDA, and which recorded goal date must be corrected?",
    "source": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx",
    "sourceTitle": "Cytokinetics ESC 2026 MAPLE-HCM and ACACIA-HCM report",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Obstruction physiology",
        "observedClinicalEvidence": "Obstructive HCM combines excessive myocardial contractility, dynamic outflow-tract obstruction and exertional symptoms; MAPLE-HCM enrolled symptomatic oHCM patients with defined gradients.",
        "specialistInterpretation": "The goal of myosin inhibition is reducing obstruction and improving exercise tolerance without excessive systolic depression.",
        "neededToResolve": "Review resting/provoked gradients, genotype, background beta blockers and baseline ejection fraction.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      },
      {
        "topic": "Head-to-head clinical evidence",
        "observedClinicalEvidence": "MAPLE-HCM reported peak oxygen-uptake advantage versus metoprolol of +2.3 mL/kg/min at Week 24 (p<0.001).",
        "specialistInterpretation": "A randomized active comparator provides clinically useful evidence that a symptom-focused myosin inhibitor can exceed a traditional beta blocker on exercise performance.",
        "neededToResolve": "Check exact prespecified primary analysis, clinical meaningfulness, confidence intervals and other clinical outcomes.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      },
      {
        "topic": "Subgroups and treatment positioning",
        "observedClinicalEvidence": "In exploratory strata, peak VO2 advantages were +3.1 for beta-blocker-naive and +1.9 mL/kg/min for prior beta-blocker-treated participants; interaction p=0.133.",
        "specialistInterpretation": "Different nominal subgroup estimates do not establish a significant differential effect, and washout protocols differ from real-world sequencing.",
        "neededToResolve": "Evaluate pretrial medication washout, subgroup interaction and whether the label allows concomitant background therapy.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      },
      {
        "topic": "Patient-important daily function",
        "observedClinicalEvidence": "The sponsor reported supporting KCCQ clinical summary and NYHA functional-class improvements alongside reduced LVOT gradient.",
        "specialistInterpretation": "Symptom/function outcomes can validate a physiological mechanism, but interpretation requires absolute response rates and responder thresholds.",
        "neededToResolve": "Review KCCQ responder analysis, NYHA adjudication, exertional syncope, and exercise-test reproducibility.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      },
      {
        "topic": "Systolic depression risk",
        "observedClinicalEvidence": "Cardiac myosin inhibition can suppress ejection fraction; dose titration uses echocardiographic checks to avoid excessive contractility suppression.",
        "specialistInterpretation": "The treatment's benefit-risk can be limited by monitoring and transient systolic dysfunction despite positive exercise physiology.",
        "neededToResolve": "Obtain LVEF <50% events, hospitalizations, exposure, drug interactions and repeat echo surveillance.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      },
      {
        "topic": "Critical FDA application distinction",
        "observedClinicalEvidence": "FDA approved MYQORZO for symptomatic oHCM on December 19, 2025 on the SEQUOIA-HCM package, prior to the FOCUS-recorded Nov 14, 2026 goal.",
        "specialistInterpretation": "A predicted initial oHCM approval or CRL in Nov 2026 would be categorically wrong for an already-approved indication; MAPLE-HCM does not create an automatic second initial cycle.",
        "neededToResolve": "Identify exact NDA, supplementary application (if any), and origin of outdated FOCUS date before using it as a trading catalyst.",
        "sourceDate": "2025-12-19",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Announces-FDA-Approval-of-MYQORZO-aficamten-for-the-Treatment-of-Adults-with-Symptomatic-Obstructive-Hypertrophic-Cardiomyopathy-to-Improve-Functional-Capacity-and-Symptoms/"
      },
      {
        "topic": "Independent clinical synthesis",
        "observedClinicalEvidence": "MAPLE-HCM supports additional comparative efficacy evidence for an approved oHCM treatment; it does not determine a future action date on the separate non-obstructive development program.",
        "specialistInterpretation": "When a trial is already part of an approved indication, the correct output is an application-identity warning, not an indeterminate initial approval prediction.",
        "neededToResolve": "Verify FDA-approved labeling and any currently filed supplemental claim while separately reviewing nHCM data.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      }
    ]
  },
  {
    "cycleId": "cytk-aficamten-nhcm",
    "specialty": "Cardiology / non-obstructive hypertrophic cardiomyopathy",
    "medicalQuestion": "Are the modest placebo-adjusted symptom/exercise improvements in ACACIA-HCM clinically valuable enough to justify meaningful rates of reduced LVEF and heart failure events?",
    "source": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx",
    "sourceTitle": "Cytokinetics May 2026 ACACIA-HCM Phase 3 results",
    "completedSpecialistSignoff": false,
    "conclusion": "PARTIAL_SOURCED_RESEARCH",
    "dimensions": [
      {
        "topic": "Non-obstructive pathophysiology",
        "observedClinicalEvidence": "ACACIA-HCM targeted symptomatic non-obstructive HCM with low LVOT gradients, LVEF at least 60%, NYHA II/III symptoms and limited exercise capacity.",
        "specialistInterpretation": "The treatment cannot rely on relief of dynamic obstruction as the only mechanism; a different patient phenotype needs a distinct benefit-risk case.",
        "neededToResolve": "Confirm genotype, non-obstructive exclusion criteria, diastolic dysfunction and atrial fibrillation strata.",
        "sourceDate": "2026-05-05",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx"
      },
      {
        "topic": "Patient-reported symptom magnitude",
        "observedClinicalEvidence": "Week 36 KCCQ-CSS placebo-adjusted difference was +3.0 points (95% CI 0.5–5.5), p=0.021.",
        "specialistInterpretation": "Statistically positive average KCCQ effect may be modest relative to frequently used 5-point patient-important improvement thresholds.",
        "neededToResolve": "Request proportions achieving ≥5 or ≥10 point KCCQ improvement, baseline symptoms and confidence intervals for responder differences.",
        "sourceDate": "2026-05-05",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx"
      },
      {
        "topic": "Exercise capacity magnitude",
        "observedClinicalEvidence": "Week 36 peak VO2 placebo-adjusted difference was +0.67 mL/kg/min (95% CI 0.22–1.10), p=0.003.",
        "specialistInterpretation": "The physiological effect is positive but small in absolute terms; clinical value depends on activity, breathlessness and cardiomyopathy severity.",
        "neededToResolve": "Assess patient-level pVO2 responders, reproducibility, maximal-effort criteria and clinically meaningful exercise changes.",
        "sourceDate": "2026-05-05",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx"
      },
      {
        "topic": "Objective cardiac secondary evidence",
        "observedClinicalEvidence": "The sponsor reported supportive NYHA-class improvement, NT-proBNP reductions and ventilatory efficiency secondary findings.",
        "specialistInterpretation": "Agreement across biological and functional measures strengthens the hypothesis, but multiplicity and simultaneous clinical burden matter.",
        "neededToResolve": "Reconstruct hierarchical testing, NT-proBNP confounding and adjudicated hospitalization or arrhythmia outcomes.",
        "sourceDate": "2026-05-05",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx"
      },
      {
        "topic": "Loss of systolic function",
        "observedClinicalEvidence": "LVEF below 50% occurred in 10% of aficamten-treated participants versus about 1% of placebo; two active-treatment participants had serious heart failure associated with reduced LVEF.",
        "specialistInterpretation": "This is an observed on-target safety signal; the key clinical question is reversibility and whether echo monitoring prevents consequential heart failure.",
        "neededToResolve": "Review dose adjustments, LVEF nadirs, time to recovery, withdrawal and serious heart-failure incidence by achieved exposure.",
        "sourceDate": "2026-05-05",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx"
      },
      {
        "topic": "Monitoring burden and generalizability",
        "observedClinicalEvidence": "The trial used serial echocardiography at Weeks 2, 4 and 6 and dose escalation only with LVEF at least 60%.",
        "specialistInterpretation": "A closely monitored trial can underestimate the risk in routine practice where imaging, adherence or rapid dose adjustment are less consistent.",
        "neededToResolve": "Assess monitoring burden, treatment cessation, patients with AF or higher CKD burden and safety in clinical practice.",
        "sourceDate": "2026-08-31",
        "sourceUrl": "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
      },
      {
        "topic": "Separate FDA filing stage",
        "observedClinicalEvidence": "The non-obstructive HCM supplement was planned in Q4 2026 according to the Nov 2026 SEC filing, not established as accepted with a PDUFA goal.",
        "specialistInterpretation": "A positive Phase 3 dataset does not establish a filed or accepted sNDA or approval timing; record the two distinct oHCM and nHCM cycles.",
        "neededToResolve": "Verify exact submission and acceptance, proposed label, safety/REMS requirements and updated FDA commentary.",
        "sourceDate": "2026-11-04",
        "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm"
      }
    ]
  }
] as const;
export function waveOneSpecialistCase(id:string):SpecialistCase|null{
 return SPECIALIST_WAVE_ONE.find(c=>c.cycleId===id)||null;
}
