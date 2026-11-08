/**
 * Failure-first regulatory research notes, curated as of 2026-11-07.
 * Do not interpret issue classification as a projected outcome, probability,
 * proof of unresolved current-cycle deficiencies, or a complete FDA review.
 */
export type IssueEvidenceClass =
  |"FDA_REVIEWER_OBJECTION"
  |"TRIAL_SIGNAL"
  |"PREVIOUS_CRL"
  |"PRIOR_EXTENSION"
  |"SPONSOR_MITIGATION"
  |"REVIEW_GAP";
export type Consequence="POTENTIAL_CRL"|"LABEL_OR_BENEFIT_RISK"|"REVIEW_TIMING"|"NEEDS_VERIFICATION";
export type ReviewIssue={
  id:string;
  cycleId:string;
  title:string;
  evidenceClass:IssueEvidenceClass;
  consequence:Consequence;
  sourceDate:string;
  sourceType:"FDA"|"SEC_SPONSOR"|"SPONSOR";
  sourceTitle:string;
  sourceUrl:string;
  observation:string;
  whyItMatters:string;
  responseOrCounterevidence:string;
  resolutionState:"NOT_ESTABLISHED"|"HISTORICAL_EVENT"|"OPEN_EVIDENCE_DISPUTE"|"UNDER_REVIEW";
  decisiveFollowUp:string;
};
export const FAILURE_DESK_AS_OF="2026-11-07";
export const FAILURE_DESK:readonly ReviewIssue[]=[
  {
    id:"capr-fda-pul",cycleId:"capr-deramiocel",title:"FDA reviewer disagrees that pivotal HOPE-3 demonstrated primary efficacy",
    evidenceClass:"FDA_REVIEWER_OBJECTION",consequence:"POTENTIAL_CRL",sourceDate:"2026-07-29",sourceType:"FDA",
    sourceTitle:"FDA July 29 advisory committee presentation, slide 33",
    sourceUrl:"https://www.fda.gov/media/193912/download",
    observation:"FDA's own July 2026 statistical review concluded neither the HOPE-3 prespecified primary PUL 2.0 nor key LVEF secondary demonstrated significance under analyses it considered appropriate, criticizing post-completion SAP revisions, missing-placebo-data treatment and post-hoc choices.",
    whyItMatters:"A disputed pivotal primary analysis is directly relevant to substantial evidence of effectiveness, potentially the central approval obstacle.",
    responseOrCounterevidence:"Sponsor reported PUL 2.0 p=0.029 under its analysis and submitted additional sensitivity work and a refined upper-limb indication.",
    resolutionState:"OPEN_EVIDENCE_DISPUTE",
    decisiveFollowUp:"Obtain FDA's assessment of the amended prespecified analyses, alternative missing-data methods and upper-limb indication; do not treat sponsor p=0.029 as FDA acceptance."
  },
  {
    id:"capr-ole",cycleId:"capr-deramiocel",title:"New 24-month open-label data are supportive but not randomized confirmation",
    evidenceClass:"SPONSOR_MITIGATION",consequence:"NEEDS_VERIFICATION",sourceDate:"2026-10-05",sourceType:"SPONSOR",
    sourceTitle:"Capricor October 5, 2026 HOPE-3 open-label extension release",
    sourceUrl:"https://www.capricor.com/investors/news-events/press-releases/detail/356/capricor-therapeutics-presents-positive-hope-3-open-label",
    observation:"Delayed-start crossover patients had less upper-limb decline during their treated year than their previous placebo year, but the sponsor expressly states no alpha was allocated and the extension was not powered for Month 24 comparisons.",
    whyItMatters:"An uncontrolled extension and natural-history contrasts may support biological plausibility but are vulnerable to selection, regression and period effects.",
    responseOrCounterevidence:"Descriptive longitudinal findings show a pattern of slower decline and may provide supportive clinical context for a progressive disease.",
    resolutionState:"UNDER_REVIEW",
    decisiveFollowUp:"Determine whether FDA accepts additional analyses as confirmatory rather than treating nonrandomized comparisons as decisive proof."
  },
  {
    id:"capr-extension",cycleId:"capr-deramiocel",title:"Three-month PDUFA extension is already documented",
    evidenceClass:"PRIOR_EXTENSION",consequence:"REVIEW_TIMING",sourceDate:"2026-08-24",sourceType:"SPONSOR",
    sourceTitle:"Capricor August 24 PDUFA amendment announcement",
    sourceUrl:"https://www.capricor.com/investors/news-events/press-releases/detail/354/capricor-therapeutics-announces-extension-of-pdufa-target",
    observation:"FDA treated the amended BLA containing additional HOPE-3 results and indication revision as a major amendment, extending goal August 22 to November 22, 2026.",
    whyItMatters:"This is a prior timing event. Do not extrapolate it into a prediction of another extension or mistake it for a CRL.",
    responseOrCounterevidence:"The additional review window permits assessment of the sponsor's response to earlier objections.",
    resolutionState:"HISTORICAL_EVENT",
    decisiveFollowUp:"Check for any later FDA-confirmed goal change before attributing a missed goal date."
  },
  {
    id:"svra-extension-context",cycleId:"svra-molgramostim",title:"Major-amendment extension did not cite a clinical or CMC deficiency",
    evidenceClass:"PRIOR_EXTENSION",consequence:"REVIEW_TIMING",sourceDate:"2026-04-15",sourceType:"SPONSOR",
    sourceTitle:"Savara April 15, 2026 molgramostim BLA review extension",
    sourceUrl:"https://investors.savarapharma.com/news/news-details/2026/Savara-Announces-the-U-S--Food--Drug-Administration-FDA-Has-Extended-the-Review-Period-for-the-Molgramostim-Inhalation-Solution-Molgramostim-Biologics-License-Application-BLA-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP/default.aspx",
    observation:"Company reported FDA classified responses to information requests as a major amendment and extended the goal to November 22; the agency correspondence did not cite safety, efficacy or manufacturing concerns according to the sponsor.",
    whyItMatters:"An extension alone does not establish a specific clinical or manufacturing blocker.",
    responseOrCounterevidence:"The company reports no stated deficiencies in this extension communication; this is not independent FDA confirmation that its application is otherwise risk-free.",
    resolutionState:"HISTORICAL_EVENT",
    decisiveFollowUp:"Locate exact contents of amendment, any later FDA communications, and independently evaluate clinical/CMC readiness."
  },
  {
    id:"svra-qol",cycleId:"svra-molgramostim",title:"A later quality-of-life assessment was not statistically significant",
    evidenceClass:"TRIAL_SIGNAL",consequence:"LABEL_OR_BENEFIT_RISK",sourceDate:"2024-06-26",sourceType:"SPONSOR",
    sourceTitle:"Savara pivotal IMPALA-2 topline clinical results",
    sourceUrl:"https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx",
    observation:"Week 24 DLCO primary improved (reported p=0.0007), but Week 48 SGRQ total quality-of-life outcome was reported p=0.1046.",
    whyItMatters:"The primary physiological evidence is supportive, yet the long-term patient-reported benefit and endpoint hierarchy should be reviewed.",
    responseOrCounterevidence:"Week 24 respiratory quality-of-life SGRQ total reportedly improved (p=0.0072), with subsequent open-label results suggesting durability.",
    resolutionState:"UNDER_REVIEW",
    decisiveFollowUp:"Examine endpoint hierarchy, confidence intervals, missing data, clinical meaningfulness and unblinded-extension interpretation."
  },
  {
    id:"svra-posthoc",cycleId:"svra-molgramostim",title:"Mild-diffusion subgroup findings are explicitly exploratory",
    evidenceClass:"SPONSOR_MITIGATION",consequence:"NEEDS_VERIFICATION",sourceDate:"2026-10-21",sourceType:"SPONSOR",
    sourceTitle:"Savara CHEST 2026 exploratory aPAP subgroup analysis",
    sourceUrl:"https://investors.savarapharma.com/news/news-details/2026/Savara-Presented-New-Data-Showing-Molgramostim-Inhalation-Solution-Molgramostim-Treatment-Effects-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-aPAP-Patients-with-Mild-Diffusion-Impairment/default.aspx",
    observation:"Post-hoc analysis in patients with baseline DLCO above 70% was small and explicitly described by sponsor as descriptive, exploratory and hypothesis-generating.",
    whyItMatters:"Do not infer approval for a broader mild-disease population solely from underpowered exploratory subgroup findings.",
    responseOrCounterevidence:"The original IMPALA-2 randomized primary data remain the core efficacy evidence; this subgroup is supplemental.",
    resolutionState:"UNDER_REVIEW",
    decisiveFollowUp:"Verify claimed label population versus trial inclusion thresholds and subgroup interaction evidence."
  },
  {
    id:"cogt-hepatic",cycleId:"cogt-gist",title:"Grade 3+ liver-enzyme imbalance with the combination",
    evidenceClass:"TRIAL_SIGNAL",consequence:"LABEL_OR_BENEFIT_RISK",sourceDate:"2026-05-30",sourceType:"SPONSOR",
    sourceTitle:"Cogent PEAK 2026 ASCO detailed clinical data and safety tables",
    sourceUrl:"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3",
    observation:"Sponsor reported Grade 3+ ALT/AST elevations 10.8% with bezuclastinib plus sunitinib versus 1.4% sunitinib alone, and treatment-related discontinuations of 7.4% vs 3.8%.",
    whyItMatters:"A liver-safety imbalance may affect benefit-risk, laboratory monitoring, dose management or labeling; it is not a confirmed FDA rejection reason.",
    responseOrCounterevidence:"Sponsor described abnormalities as predominantly transient/manageable; Grade 3 elevations resolved and no Grade 4 elevations were reported.",
    resolutionState:"UNDER_REVIEW",
    decisiveFollowUp:"Review drug-induced liver injury adjudication, Hy's law, lab abnormalities, rechallenge, baseline liver disease, dose reductions and FDA inspection/labeling communications."
  },
  {
    id:"cogt-pfs",cycleId:"cogt-gist",title:"Active-comparator progression-free-survival effect supports efficacy",
    evidenceClass:"SPONSOR_MITIGATION",consequence:"NEEDS_VERIFICATION",sourceDate:"2026-05-28",sourceType:"SPONSOR",
    sourceTitle:"Cogent PEAK May 2026 positive Phase 3 and NDA acceptance",
    sourceUrl:"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-fda-acceptance-new-drug-0",
    observation:"Sponsor reported median progression-free survival of 16.5 months for combination therapy versus 9.2 months for sunitinib; hazard ratio 0.50, 95% CI 0.39–0.65, p<0.0001.",
    whyItMatters:"Substantial randomized active-comparator benefit can support a positive clinical benefit-risk assessment, but does not establish CMC or inspection readiness.",
    responseOrCounterevidence:"The combination adds some treatment-related adverse effects, including hepatic lab abnormalities.",
    resolutionState:"UNDER_REVIEW",
    decisiveFollowUp:"Compare investigator and independent central review, subgroup effects, overall survival maturity and integrated safety before drawing an application decision."
  },
  {
    id:"cort-crl",cycleId:"cort-relacorilant",title:"Prior CRL explicitly sought more evidence of efficacy despite positive GRACE",
    evidenceClass:"PREVIOUS_CRL",consequence:"POTENTIAL_CRL",sourceDate:"2026-11-03",sourceType:"SEC_SPONSOR",
    sourceTitle:"Corcept November 2026 Form 10-Q, relacorilant resubmission",
    sourceUrl:"https://ir.corcept.com/node/18326/html",
    observation:"December 30, 2025 CRL stated additional evidence of effectiveness was required, while acknowledging GRACE met primary and GRADIENT was supportive. Sponsor resubmitted June 17 after requested global statistical analyses.",
    whyItMatters:"A real FDA efficacy deficiency exists in the prior review cycle; whether the current resubmission cures it is the key live question.",
    responseOrCounterevidence:"FDA requested analyses of existing data, and sponsor reports the new three-domain global statistical test was positive.",
    resolutionState:"OPEN_EVIDENCE_DISPUTE",
    decisiveFollowUp:"Reconstruct the global test's null hypothesis, prespecification, multiplicity, component effects, missing data and FDA's resubmission adequacy assessment."
  },
  {
    id:"cort-gradient-bp",cycleId:"cort-relacorilant",title:"GRADIENT between-arm blood-pressure difference did not reach significance",
    evidenceClass:"TRIAL_SIGNAL",consequence:"POTENTIAL_CRL",sourceDate:"2026-11-03",sourceType:"SEC_SPONSOR",
    sourceTitle:"Corcept November 2026 Form 10-Q GRADIENT comparative data",
    sourceUrl:"https://ir.corcept.com/node/18326/html",
    observation:"Sponsor describes a −6.6 mmHg within-arm SBP change on relacorilant and −2.1 mmHg on placebo, but explicitly states the between-arm hypertension comparison was not statistically significant.",
    whyItMatters:"Within-group significance is not between-group proof. This could weaken the hypertension component of the FDA-requested global test.",
    responseOrCounterevidence:"Placebo-adjusted fasting glucose and body-weight differences were favorable; the global test addresses a heterogeneous condition with multiple manifestations.",
    resolutionState:"OPEN_EVIDENCE_DISPUTE",
    decisiveFollowUp:"Examine exact intercurrent-event rules and global-test weighting, contribution of non-hypertension components, effect sizes and prespecification."
  },
  {
    id:"mlys-kidney-safety",cycleId:"mlys-lorundrostat",title:"Aldosterone-pathway potassium and renal safety require integrated review",
    evidenceClass:"REVIEW_GAP",consequence:"NEEDS_VERIFICATION",sourceDate:"2026-11-04",sourceType:"SPONSOR",
    sourceTitle:"Mineralys November 2026 Launch-HTN and Explore-OSA clinical update",
    sourceUrl:"https://ir.mineralystx.com/news-events/press-releases/detail/127/mineralys-therapeutics-reports-third-quarter-2026-financial",
    observation:"Lorundrostat's aldosterone-synthase inhibition makes potassium, kidney function and hypotension prespecified topics for safety review, especially in CKD and combination antihypertensive use. The cited sponsor update reports no serious hyperkalemia in the separate Phase 2 Explore-OSA study; it does NOT establish a Launch-HTN safety problem.",
    whyItMatters:"Safety in comorbid CKD and interacting therapies can influence treatment labeling; theoretical class risks must be verified against actual trial and integrated-study data.",
    responseOrCounterevidence:"Sponsor described consistent blood-pressure lowering in CKD subgroups and albuminuria reductions with no serious hyperkalemia in its OSA trial.",
    resolutionState:"NOT_ESTABLISHED",
    decisiveFollowUp:"Obtain all Launch-HTN and integrated-study potassium elevation incidence, renal decline, discontinuations, exposure and protocol monitoring thresholds."
  },
  {
    id:"achv-cmc",cycleId:"achv-cytisinicline",title:"A previous CRL was caused by contract-facility CGMP defects",
    evidenceClass:"PREVIOUS_CRL",consequence:"POTENTIAL_CRL",sourceDate:"2026-08-11",sourceType:"SEC_SPONSOR",
    sourceTitle:"Achieve August 2026 SEC filing on cytisinicline manufacturing CRL",
    sourceUrl:"https://ir.achievelifesciences.com/sec-filings/all-sec-filings/content/0001193125-26-344624/achv-20260630.htm",
    observation:"Company disclosed June 2026 cytisinicline CRL concerning third-party manufacturing-facility CGMP deficiencies and unfinished draft labeling, not clinical efficacy or safety.",
    whyItMatters:"An unresolved commercial manufacturing supply-chain deficiency can defeat an application even where efficacy is otherwise persuasive.",
    responseOrCounterevidence:"Sponsor said it transferred methods to a replacement manufacturer and planned resubmission.",
    resolutionState:"OPEN_EVIDENCE_DISPUTE",
    decisiveFollowUp:"Confirm resubmission acceptance, facility process validation, regulatory inspections and CMC deficiency clearance before assigning any review goal or approval outlook."
  }
];
export const FAILURE_DESK_CYCLE_IDS=Array.from(new Set(FAILURE_DESK.map(x=>x.cycleId)));
export function deskIssuesForCycle(cycleId:string):ReviewIssue[]{
  return FAILURE_DESK.filter(x=>x.cycleId===cycleId);
}
