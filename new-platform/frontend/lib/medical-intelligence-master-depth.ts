/**
 * Standalone PDUFA Medical Master Depth:
 * 8 subject layers * 5 scientific assessments * 20 cognitive/scientific levels
 * = 800 evidence-gated investigation positions PER FOCUS trial, not 800 fabricated findings.
 * Unreviewed positions never count as completed analysis.
 * Designed from the user's existing 20-level clinical scientific investigation standard.
 */
export type DeepLayerId="disease"|"molecular"|"translational"|"trial"|"clinical"|"comparative"|"regulatory"|"integration";
export type DeepAssessment={
 id:string;layerId:DeepLayerId;label:string;objective:string;failureMechanism:string;requiredSources:string;
};
export type DeepLayer={id:DeepLayerId;title:string;assessments:readonly DeepAssessment[]};
export type DeepLevel={id:number;name:string;method:string;deliverable:string};
export const SCIENTIFIC_LEVELS:readonly DeepLevel[]=[
  {
    "id": 1,
    "name": "Document extraction and source authentication",
    "method": "Authenticate dated original protocol/SAP, clinical/FDA documents and every factual claim",
    "deliverable": "Source ledger with precise references, date and version"
  },
  {
    "id": 2,
    "name": "Scientific hypothesis reconstruction",
    "method": "Translate the candidate mechanism into falsifiable medical expectations",
    "deliverable": "Clear causal hypothesis and falsifiers"
  },
  {
    "id": 3,
    "name": "Biological plausibility investigation",
    "method": "Trace molecular and organ-level mechanisms and biological alternatives",
    "deliverable": "Mechanism evidence and contradictory biology"
  },
  {
    "id": 4,
    "name": "Evidence quality validation",
    "method": "Audit study methods, measurements, provenance and quality",
    "deliverable": "Methodological reliability and data gaps"
  },
  {
    "id": 5,
    "name": "Critical challenge",
    "method": "Seek primary contradictions, biases and alternative explanations",
    "deliverable": "Failure mechanisms and strongest counterargument"
  },
  {
    "id": 6,
    "name": "Cross-disciplinary integration",
    "method": "Compare disease biology, pharmacology, clinical design and regulation",
    "deliverable": "Cross-domain consistency/conflict"
  },
  {
    "id": 7,
    "name": "Predictive scenario modeling",
    "method": "Define approval/CRL/delay counterfactuals; never fabricate probabilities",
    "deliverable": "Qualitative scenarios and missing validation"
  },
  {
    "id": 8,
    "name": "Scientific synthesis",
    "method": "Distinguish supported, mixed and unsupported evidence",
    "deliverable": "Bounded independent synthesis"
  },
  {
    "id": 9,
    "name": "Causal inference",
    "method": "Assess what observations can truly establish drug-caused benefit",
    "deliverable": "Causal graph, confounding and identification limits"
  },
  {
    "id": 10,
    "name": "Systems biology",
    "method": "Examine feedback networks, compensation and systemic off-target pathways",
    "deliverable": "Network consequences and testability"
  },
  {
    "id": 11,
    "name": "Adversarial scientific review",
    "method": "Actively disprove strongest favorable conclusion",
    "deliverable": "Pre-registered challenge and failure check"
  },
  {
    "id": 12,
    "name": "Multi-method adjudication",
    "method": "Reconcile prespecified, FDA, company, alternative and sensitivity estimates",
    "deliverable": "Analysis-by-analysis evidence table"
  },
  {
    "id": 13,
    "name": "Quantitative pharmacology",
    "method": "Evaluate dose/exposure/response/target engagement when data permit",
    "deliverable": "PK/PD assumptions, calculations and limits"
  },
  {
    "id": 14,
    "name": "Patient heterogeneity",
    "method": "Test interaction, population transportability and biomarker-specific outcomes",
    "deliverable": "Effect-modification evidence and precision"
  },
  {
    "id": 15,
    "name": "Bayesian evidence integration",
    "method": "Update uncertainty only with defendable priors/data; avoid false posterior precision",
    "deliverable": "Transparent prior, likelihood and sensitivity if feasible"
  },
  {
    "id": 16,
    "name": "External validity",
    "method": "Compare trial patients, delivery setting and outcomes to labeled use",
    "deliverable": "Transportability limitations and label fit"
  },
  {
    "id": 17,
    "name": "Historical failure patterns",
    "method": "Find similar FDA CRLs and identify genuine versus superficial analogies",
    "deliverable": "Precedent mechanisms and differences"
  },
  {
    "id": 18,
    "name": "Regulatory counterfactuals",
    "method": "Simulate scientifically plausible FDA reviewer interpretations and alternative labeling",
    "deliverable": "CRL, approval, label, extension mechanisms"
  },
  {
    "id": 19,
    "name": "Independent reproducibility audit",
    "method": "Reproduce equations, effect metrics and p-values only with sufficient inputs",
    "deliverable": "Verified calculations, discrepancies, reproducibility status"
  },
  {
    "id": 20,
    "name": "Final red-team adjudication",
    "method": "Force independent opposition and scientific judgment with decision-reversal triggers",
    "deliverable": "Adjudicated evidence state and unresolved blockers"
  }
] as const;
export const SCIENTIFIC_LAYERS:readonly DeepLayer[]=[
  {
    "id": "disease",
    "title": "Disease biology & pathophysiology",
    "assessments": [
      {
        "id": "1.1",
        "layerId": "disease",
        "label": "disease-mechanism",
        "objective": "Molecular cause and pathogenesis",
        "failureMechanism": "Connect disease-driving pathology to candidate's therapeutic target",
        "requiredSources": "Mechanistic mismatch could undercut causal plausibility"
      },
      {
        "id": "1.2",
        "layerId": "disease",
        "label": "natural-history",
        "objective": "Untreated progression and variability",
        "failureMechanism": "Quantify untreated progression, spontaneous remission, measurement variability and prognosis",
        "requiredSources": "Natural history could explain apparent response or weaken endpoint sensitivity"
      },
      {
        "id": "1.3",
        "layerId": "disease",
        "label": "disease-biomarkers",
        "objective": "Disease biomarkers and surrogate validity",
        "failureMechanism": "Examine biomarker analytical validity, clinical meaning and surrogate qualification",
        "requiredSources": "A surrogate may not reliably predict patient benefit"
      },
      {
        "id": "1.4",
        "layerId": "disease",
        "label": "unmet-need",
        "objective": "Current treatment burden and unmet need",
        "failureMechanism": "Define therapeutic baseline and patient-important outcomes for indication",
        "requiredSources": "Benefit-risk context may not justify tolerability burden"
      },
      {
        "id": "1.5",
        "layerId": "disease",
        "label": "heterogeneity",
        "objective": "Diagnostic and population heterogeneity",
        "failureMechanism": "Assess diagnostic error, organ severity, genetic, demographic and responder subtypes",
        "requiredSources": "Misclassification or restricted efficacy may limit proposed indication"
      }
    ]
  },
  {
    "id": "molecular",
    "title": "Molecular mechanism & drug action",
    "assessments": [
      {
        "id": "2.1",
        "layerId": "molecular",
        "label": "target",
        "objective": "Drug target validation",
        "failureMechanism": "Trace target specificity and causal importance in disease biology",
        "requiredSources": "Target is noncausal or poorly validated"
      },
      {
        "id": "2.2",
        "layerId": "molecular",
        "label": "action",
        "objective": "Mechanism of action and target engagement",
        "failureMechanism": "Validate engagement, tissue penetration, occupancy, and downstream activity",
        "requiredSources": "Exposure may not reach relevant tissue or achieve the proposed mechanism"
      },
      {
        "id": "2.3",
        "layerId": "molecular",
        "label": "selectivity",
        "objective": "Selectivity and off-target liabilities",
        "failureMechanism": "Assess selectivity, unintended pathways and differential tissue safety",
        "requiredSources": "Off-target toxicity may offset observed efficacy"
      },
      {
        "id": "2.4",
        "layerId": "molecular",
        "label": "network",
        "objective": "Systems/pathway feedback and compensation",
        "failureMechanism": "Model cross-pathway effects, feedback and alternative causal hypotheses",
        "requiredSources": "Compensatory biology may blunt durable effect or increase risk"
      },
      {
        "id": "2.5",
        "layerId": "molecular",
        "label": "resistance",
        "objective": "Resistance and loss of response",
        "failureMechanism": "Examine target escape, neutralizing antibodies, tolerance and durability",
        "requiredSources": "Loss of action could undermine long-term benefit"
      }
    ]
  },
  {
    "id": "translational",
    "title": "Preclinical & translational evidence",
    "assessments": [
      {
        "id": "3.1",
        "layerId": "translational",
        "label": "in-vitro",
        "objective": "Cellular potency and reproducibility",
        "failureMechanism": "Assess preclinical assays, controls, batch-to-batch reliability",
        "requiredSources": "Assay artifacts or inconsistent product potency"
      },
      {
        "id": "3.2",
        "layerId": "translational",
        "label": "in-vivo",
        "objective": "Animal models and model fitness",
        "failureMechanism": "Test construct, external and translational validity of animal models",
        "requiredSources": "Nonpredictive models can exaggerate expected benefit"
      },
      {
        "id": "3.3",
        "layerId": "translational",
        "label": "pkpd",
        "objective": "Human PK/PD and exposure–response",
        "failureMechanism": "Compare dose, exposure, target saturation, exposure-efficacy and exposure-safety",
        "requiredSources": "Inadequate dose selection or pharmacology evidence"
      },
      {
        "id": "3.4",
        "layerId": "translational",
        "label": "tox",
        "objective": "Nonclinical toxicology and margins",
        "failureMechanism": "Assess carcinogenicity, reproductive safety, chronic toxicity and organ-risk margins as applicable",
        "requiredSources": "Unresolved nonclinical risks may restrict approval/label"
      },
      {
        "id": "3.5",
        "layerId": "translational",
        "label": "translation",
        "objective": "Cross-stage translational coherence",
        "failureMechanism": "Trace changes in mechanism, effect size, dose and biomarker from early to pivotal trials",
        "requiredSources": "Phase-to-phase inconsistency may reflect model fragility"
      }
    ]
  },
  {
    "id": "trial",
    "title": "Trial design & statistical integrity",
    "assessments": [
      {
        "id": "4.1",
        "layerId": "trial",
        "label": "design",
        "objective": "Randomization, blinding and comparator",
        "failureMechanism": "Evaluate randomization, concealment, masking, site conduct and control appropriateness",
        "requiredSources": "Bias or invalid comparator can invalidate efficacy evidence"
      },
      {
        "id": "4.2",
        "layerId": "trial",
        "label": "endpoint",
        "objective": "Endpoint selection and clinical meaning",
        "failureMechanism": "Reconstruct endpoint definitions, validation, hierarchy and change dates",
        "requiredSources": "Unacceptable endpoint or clinically marginal effect"
      },
      {
        "id": "4.3",
        "layerId": "trial",
        "label": "estimand",
        "objective": "Estimands, intercurrent events and missingness",
        "failureMechanism": "Match estimand to treatment-policy/hypothetical/composite strategy; test missingness",
        "requiredSources": "Selective censoring/imputation can reverse the outcome"
      },
      {
        "id": "4.4",
        "layerId": "trial",
        "label": "pop",
        "objective": "Population, allocation and statistical power",
        "failureMechanism": "Review target population, sample size, subgroup power, eligibility and attrition",
        "requiredSources": "Underpowered/misaligned population can invalidate claim"
      },
      {
        "id": "4.5",
        "layerId": "trial",
        "label": "conduct",
        "objective": "Conduct, deviations and data integrity",
        "failureMechanism": "Examine sites, protocol changes, adjudication, withdrawals and inspections",
        "requiredSources": "Data or conduct findings may trigger FDA objections"
      }
    ]
  },
  {
    "id": "clinical",
    "title": "Clinical efficacy, safety & replication",
    "assessments": [
      {
        "id": "5.1",
        "layerId": "clinical",
        "label": "primary",
        "objective": "Pivotal primary efficacy",
        "failureMechanism": "Compare prespecified primary treatment effect, CI, p and clinical effect thresholds",
        "requiredSources": "Primary failure may directly prevent approval"
      },
      {
        "id": "5.2",
        "layerId": "clinical",
        "label": "secondary",
        "objective": "Secondary endpoints, multiplicity and hierarchy",
        "failureMechanism": "Check testing sequence, adjustment and label-claim boundaries",
        "requiredSources": "Nominal or post-hoc endpoints cannot rescue a failed primary without strong context"
      },
      {
        "id": "5.3",
        "layerId": "clinical",
        "label": "safety",
        "objective": "Integrated safety and competing harms",
        "failureMechanism": "Analyze serious AEs, death, organ toxicity, rates, time at risk and causality",
        "requiredSources": "Benefit-risk may be unfavorable or require restrictions"
      },
      {
        "id": "5.4",
        "layerId": "clinical",
        "label": "subgroups",
        "objective": "Subgroups, effect modification and robustness",
        "failureMechanism": "Test true treatment–subgroup interaction, missingness and consistency",
        "requiredSources": "Apparent overall effect may not generalize to label"
      },
      {
        "id": "5.5",
        "layerId": "clinical",
        "label": "replication",
        "objective": "Replication, durability and long-term effects",
        "failureMechanism": "Assess study-to-study consistency, external validation and attrition of follow-up",
        "requiredSources": "Transient efficacy or non-reproducibility could limit approval"
      }
    ]
  },
  {
    "id": "comparative",
    "title": "Comparative therapeutic science",
    "assessments": [
      {
        "id": "6.1",
        "layerId": "comparative",
        "label": "standard",
        "objective": "Current standard-of-care performance",
        "failureMechanism": "Establish relevant comparator and expected patient outcomes",
        "requiredSources": "Misleading placebo-only or historical comparison"
      },
      {
        "id": "6.2",
        "layerId": "comparative",
        "label": "competitors",
        "objective": "Competing assets and alternatives",
        "failureMechanism": "Compare efficacy, safety and stage-matched populations without invalid cross-trial claims",
        "requiredSources": "Indirect comparison may overstate differentiating benefits"
      },
      {
        "id": "6.3",
        "layerId": "comparative",
        "label": "class",
        "objective": "Class effects and precedent failures",
        "failureMechanism": "Examine class-wide efficacy, severe events and regulatory warnings",
        "requiredSources": "Shared mechanism may import risk not seen in small studies"
      },
      {
        "id": "6.4",
        "layerId": "comparative",
        "label": "differentiation",
        "objective": "Clinically meaningful differentiation",
        "failureMechanism": "Quantify NNT/NNH, PROs, dosing burden and practical utility where valid",
        "requiredSources": "Marginal incremental benefit might not offset risk"
      },
      {
        "id": "6.5",
        "layerId": "comparative",
        "label": "combination",
        "objective": "Combination therapy and sequencing",
        "failureMechanism": "Analyze interaction, additive harms, pharmacology, and role in therapy",
        "requiredSources": "Drug interactions or positioning weaknesses may affect label"
      }
    ]
  },
  {
    "id": "regulatory",
    "title": "FDA regulatory science & approval readiness",
    "assessments": [
      {
        "id": "7.1",
        "layerId": "regulatory",
        "label": "pathway",
        "objective": "Application and review-cycle identity",
        "failureMechanism": "Verify NDA/BLA/supplement, indication, pathways, goal and prior action letters",
        "requiredSources": "Wrong cycle or unaccepted filing makes prediction invalid"
      },
      {
        "id": "7.2",
        "layerId": "regulatory",
        "label": "feedback",
        "objective": "FDA communications and prior objections",
        "failureMechanism": "Trace agency comments, prior deficiencies and applicant remediation",
        "requiredSources": "Unresolved stated FDA concern may trigger CRL"
      },
      {
        "id": "7.3",
        "layerId": "regulatory",
        "label": "label",
        "objective": "Label, population, endpoint and indication fit",
        "failureMechanism": "Compare requested claim against studied population and supported clinical benefit",
        "requiredSources": "Unsupported indication or claim may be rejected or narrowed"
      },
      {
        "id": "7.4",
        "layerId": "regulatory",
        "label": "remssafety",
        "objective": "REMS, safety management and inspections",
        "failureMechanism": "Examine tolerability, REMS, pharmacovigilance, BIMO and inspection findings",
        "requiredSources": "Unresolved safety or inspection problems may prevent approval"
      },
      {
        "id": "7.5",
        "layerId": "regulatory",
        "label": "cmc",
        "objective": "CMC, facilities, stability and major amendment timing",
        "failureMechanism": "Assess process control, identity/purity/potency, facility status and amendments",
        "requiredSources": "Unresolved quality deficiency may cause CRL; major amendment may extend clock"
      }
    ]
  },
  {
    "id": "integration",
    "title": "Integrated scientific inference & red-team",
    "assessments": [
      {
        "id": "8.1",
        "layerId": "integration",
        "label": "benefitrisk",
        "objective": "Integrated clinical benefit-risk",
        "failureMechanism": "Integrate magnitude, uncertainty, severity, treatment options, safety tradeoffs",
        "requiredSources": "Insufficient evidence of favorable benefit-risk"
      },
      {
        "id": "8.2",
        "layerId": "integration",
        "label": "contradictions",
        "objective": "Contradictions and missing-data map",
        "failureMechanism": "Audit discrepancies between FDA, publications, SEC releases and trial registry",
        "requiredSources": "Unresolved contradictions erode reproducibility and FDA-readiness"
      },
      {
        "id": "8.3",
        "layerId": "integration",
        "label": "failuremodes",
        "objective": "CRL, delay and withdrawal pathways",
        "failureMechanism": "Build separate causal routes for efficacy, safety, CMC, integrity and timing",
        "requiredSources": "Failure modes may be missed if focus only on positive top-line"
      },
      {
        "id": "8.4",
        "layerId": "integration",
        "label": "generalize",
        "objective": "Real-world effectiveness, external validity and label restrictions",
        "failureMechanism": "Assess transportability, dose burden, population and health-system factors",
        "requiredSources": "Limited external validity may shrink intended label"
      },
      {
        "id": "8.5",
        "layerId": "integration",
        "label": "judgment",
        "objective": "Independent scientific judgment and reversal conditions",
        "failureMechanism": "Red-team all claims, test counterfactuals, document strongest objection and what changes judgment",
        "requiredSources": "Overconfidence or hidden assumptions produce false forecasts"
      }
    ]
  }
] as const;
export const DEEP_ASSESSMENTS:readonly DeepAssessment[]=SCIENTIFIC_LAYERS.flatMap(layer=>layer.assessments);
export const DEPTH_SLOT_COUNT=SCIENTIFIC_LEVELS.length*DEEP_ASSESSMENTS.length;
export type DepthSlot={
 id:string;assessmentId:string;level:number;
 question:string;method:string;requiredSources:string;output:string;
 status:"UNREVIEWED";
};
export function getDepthSlot(assessmentId:string,levelId:number):DepthSlot|null{
 const a=DEEP_ASSESSMENTS.find(x=>x.id===assessmentId),l=SCIENTIFIC_LEVELS.find(x=>x.id===levelId);
 if(!a||!l)return null;
 return {
  id:a.id+":L"+l.id,assessmentId:a.id,level:l.id,
  question:"For "+a.label+": "+a.objective+"; specifically investigate whether "+a.failureMechanism.toLowerCase()+".",
  method:l.method+" in the context of "+a.label.toLowerCase()+".",
  requiredSources:a.requiredSources,
  output:l.deliverable+"; list supportive and opposing facts, uncertainty, FDA consequence, missing evidence and what would reverse the conclusion.",
  status:"UNREVIEWED"
 };
}
export const THERAPEUTIC_STRATEGY_QUESTIONS:readonly {id:string;group:string;question:string}[]=[
  {
    "id": "T1.01",
    "group": "Target and mechanism",
    "question": "Target causality — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.02",
    "group": "Target and mechanism",
    "question": "Target tissue relevance — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.03",
    "group": "Target and mechanism",
    "question": "Genetic validation — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.04",
    "group": "Target and mechanism",
    "question": "Target occupancy — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.05",
    "group": "Target and mechanism",
    "question": "Potency versus exposure — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.06",
    "group": "Target and mechanism",
    "question": "Cellular uptake — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.07",
    "group": "Target and mechanism",
    "question": "Signal transduction — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.08",
    "group": "Target and mechanism",
    "question": "Feedback loops — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.09",
    "group": "Target and mechanism",
    "question": "Immune activation — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.10",
    "group": "Target and mechanism",
    "question": "Adaptive resistance — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.11",
    "group": "Target and mechanism",
    "question": "Receptor selectivity — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.12",
    "group": "Target and mechanism",
    "question": "Epigenetic interactions — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.13",
    "group": "Target and mechanism",
    "question": "Biomarker connection — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.14",
    "group": "Target and mechanism",
    "question": "Mechanism novelty risks — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T1.15",
    "group": "Target and mechanism",
    "question": "Translational alternate mechanism — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.01",
    "group": "Dose and delivery",
    "question": "First-dose exposure — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.02",
    "group": "Dose and delivery",
    "question": "Dose-response curve — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.03",
    "group": "Dose and delivery",
    "question": "Titration adequacy — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.04",
    "group": "Dose and delivery",
    "question": "Interpatient PK variability — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.05",
    "group": "Dose and delivery",
    "question": "Metabolite activity — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.06",
    "group": "Dose and delivery",
    "question": "Renal impairment — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.07",
    "group": "Dose and delivery",
    "question": "Hepatic impairment — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.08",
    "group": "Dose and delivery",
    "question": "Pediatric exposure — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.09",
    "group": "Dose and delivery",
    "question": "Elderly exposure — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.10",
    "group": "Dose and delivery",
    "question": "DDI interactions — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.11",
    "group": "Dose and delivery",
    "question": "Therapeutic index — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.12",
    "group": "Dose and delivery",
    "question": "Adherence and burden — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.13",
    "group": "Dose and delivery",
    "question": "Formulation equivalence — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.14",
    "group": "Dose and delivery",
    "question": "Immunogenicity with repeat dose — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T2.15",
    "group": "Dose and delivery",
    "question": "Dose interruption effects — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.01",
    "group": "Disease and population",
    "question": "Diagnosis accuracy — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.02",
    "group": "Disease and population",
    "question": "Subtype effect — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.03",
    "group": "Disease and population",
    "question": "Disease severity — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.04",
    "group": "Disease and population",
    "question": "Prior treatment exposure — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.05",
    "group": "Disease and population",
    "question": "Standard-of-care interaction — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.06",
    "group": "Disease and population",
    "question": "Natural-history comparator — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.07",
    "group": "Disease and population",
    "question": "Baseline biomarker strata — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.08",
    "group": "Disease and population",
    "question": "Disease duration — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.09",
    "group": "Disease and population",
    "question": "Comorbidity influence — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.10",
    "group": "Disease and population",
    "question": "Compensatory pathways — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.11",
    "group": "Disease and population",
    "question": "Resistant patients — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.12",
    "group": "Disease and population",
    "question": "Geographic transportability — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.13",
    "group": "Disease and population",
    "question": "Rare disease heterogeneity — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.14",
    "group": "Disease and population",
    "question": "Sex/age interactions — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T3.15",
    "group": "Disease and population",
    "question": "Patient important outcomes — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.01",
    "group": "Clinical translation",
    "question": "Endpoint construct validity — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.02",
    "group": "Clinical translation",
    "question": "Surrogate-to-benefit link — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.03",
    "group": "Clinical translation",
    "question": "Time to effect — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.04",
    "group": "Clinical translation",
    "question": "Durability — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.05",
    "group": "Clinical translation",
    "question": "Relapse after stopping — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.06",
    "group": "Clinical translation",
    "question": "Missingness by arm — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.07",
    "group": "Clinical translation",
    "question": "Censoring and rescue — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.08",
    "group": "Clinical translation",
    "question": "Multiplicity — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.09",
    "group": "Clinical translation",
    "question": "Interim analysis bias — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.10",
    "group": "Clinical translation",
    "question": "Open label selection — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.11",
    "group": "Clinical translation",
    "question": "Central adjudication quality — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.12",
    "group": "Clinical translation",
    "question": "Subgroup interaction — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.13",
    "group": "Clinical translation",
    "question": "Cross-study replicability — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.14",
    "group": "Clinical translation",
    "question": "Dose-limiting events — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T4.15",
    "group": "Clinical translation",
    "question": "Risk-benefit across doses — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.01",
    "group": "Regulatory competitiveness",
    "question": "Historical class CRLs — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.02",
    "group": "Regulatory competitiveness",
    "question": "Precedent for endpoint — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.03",
    "group": "Regulatory competitiveness",
    "question": "Proposed label scope — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.04",
    "group": "Regulatory competitiveness",
    "question": "Risk-management burden — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.05",
    "group": "Regulatory competitiveness",
    "question": "Manufacturing comparability — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.06",
    "group": "Regulatory competitiveness",
    "question": "Potency assay validation — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.07",
    "group": "Regulatory competitiveness",
    "question": "Device combinations — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.08",
    "group": "Regulatory competitiveness",
    "question": "Inspection readiness — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.09",
    "group": "Regulatory competitiveness",
    "question": "Product stability — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.10",
    "group": "Regulatory competitiveness",
    "question": "Benefit versus approved alternatives — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.11",
    "group": "Regulatory competitiveness",
    "question": "Orphan/priority designation effects — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.12",
    "group": "Regulatory competitiveness",
    "question": "Advisory committee precedent — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.13",
    "group": "Regulatory competitiveness",
    "question": "Major amendment trigger — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.14",
    "group": "Regulatory competitiveness",
    "question": "Postmarketing commitments — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  },
  {
    "id": "T5.15",
    "group": "Regulatory competitiveness",
    "question": "What would change FDA decision — what evidence supports or contradicts this specific therapeutic strategy and its FDA relevance?"
  }
] as const;
export const FDA_GUIDANCE_SOURCES=[
 {title:"ICH E9(R1) Estimands and sensitivity analysis",url:"https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e9r1-statistical-principles-clinical-trials-addendum-estimands-and-sensitivity-analysis-clinical"},
 {title:"FDA Multiple Endpoints Guidance",url:"https://www.fda.gov/regulatory-information/search-fda-guidance-documents/multiple-endpoints-clinical-trials"},
 {title:"PDUFA review performance and major amendment guidance",url:"https://www.fda.gov/media/191112/download"}
] as const;
