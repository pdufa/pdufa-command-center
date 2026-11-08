/**
 * Published source-backed findings as of 2026-11-07. Independent from any survey/RAAS.
 * Entries are manually curated and bounded: FDA reviews may disagree with sponsor claims.
 * A published signal is not an FDA decision or a calibrated forecast.
 */
export type FindingEvidence = "FDA_PRIMARY"|"SEC_COMPANY_DISCLOSURE"|"SPONSOR_RELEASE"|"PEER_REVIEWED";
export type FindingType = "REGULATORY_OBJECTION"|"PREVIOUS_CRL"|"INSPECTION_OBSERVATION"|"EXTENSION_CONFIRMED"|"EFFICACY_EVIDENCE"|"REVIEW_STATUS"|"SCIENTIFIC_UNCERTAINTY";
export type ReviewedFinding={
  id:string;
  relatedNcts:readonly string[];
  company:string;
  drug:string;
  indication:string;
  domain:string;
  type:FindingType;
  evidence:FindingEvidence;
  published:string;
  headline:string;
  detail:string;
  fdaRelevance:string;
  counterpoint:string;
  remainingQuestion:string;
  sourceTitle:string;
  sourceUrl:string;
};
export const REVIEW_AS_OF="2026-11-07";
export const REVIEWED_FINDINGS:readonly ReviewedFinding[]=[
  {
    id:"capr-prior-crl",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"prior",type:"PREVIOUS_CRL",evidence:"FDA_PRIMARY",published:"2026-07-29",
    headline:"FDA documented prior July 2025 CRL on an earlier deramiocel BLA submission",
    detail:"FDA's July 2026 advisory presentation describes a July 9, 2025 CRL after finding that HOPE-2 and its open-label extension did not provide evidence of effectiveness. The 2026 review concerns a resubmission supported by HOPE-3.",
    fdaRelevance:"Historical FDA efficacy deficiency is established; determine how the new pivotal evidence changes that finding.",
    counterpoint:"The new resubmission included Phase 3 HOPE-3 rather than relying only on the earlier HOPE-2 evidence.",
    remainingQuestion:"What FDA objections to the 2026 Phase 3 dataset remained after the August amendment?",
    sourceTitle:"FDA July 29, 2026 CTGTAC presentation, regulatory history",
    sourceUrl:"https://www.fda.gov/media/193912/download"
  },
  {
    id:"capr-sap",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"statistics",type:"REGULATORY_OBJECTION",evidence:"FDA_PRIMARY",published:"2026-07-29",
    headline:"FDA objected to late statistical-plan changes and fragile efficacy conclusions",
    detail:"FDA reviewers cited changes to endpoints/analysis after complete data collection, post-hoc alterations, and sensitivity to analytical choices and missing data for two placebo participants. FDA stated these concerns call substantial evidence of effectiveness into question.",
    fdaRelevance:"Confirmed contemporaneous FDA efficacy/statistical objections, materially relevant to a potential CRL; not itself a final CRL decision.",
    counterpoint:"Sponsor disputes the characterization of its statistical analysis plan and presented supportive upper-limb findings.",
    remainingQuestion:"Have new 24-month data, prespecified sensitivity analyses or amended proposed labeling adequately answered FDA's objections?",
    sourceTitle:"FDA July 29, 2026 CTGTAC presentation, statistical review pp.31–33",
    sourceUrl:"https://www.fda.gov/media/193912/download"
  },
  {
    id:"capr-indication",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"disease",type:"SCIENTIFIC_UNCERTAINTY",evidence:"FDA_PRIMARY",published:"2026-07-29",
    headline:"FDA briefing highlights mismatch between cardiomyopathy claim and patient inclusion",
    detail:"The FDA summarized HOPE-3 as having no eligibility requirement for diagnosed cardiomyopathy or reduced LVEF, while the original application indication was treatment of DMD cardiomyopathy.",
    fdaRelevance:"Potential disease-population and endpoint applicability objection for the original cardiac claim.",
    counterpoint:"The sponsor subsequently asked FDA to evaluate a refined proposed indication focused on upper limb function.",
    remainingQuestion:"Does the refined indication align with reliable, clinically meaningful PUL 2.0 evidence?",
    sourceTitle:"FDA July 29, 2026 CTGTAC presentation, HOPE-3 trial design",
    sourceUrl:"https://www.fda.gov/media/193912/download"
  },
  {
    id:"capr-adcom",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"prior",type:"REGULATORY_OBJECTION",evidence:"SEC_COMPANY_DISCLOSURE",published:"2026-08-13",
    headline:"Advisory committee voted 9–3 against evidence for the cardiomyopathy indication",
    detail:"The July 29 advisory committee voted 3 in favor and 9 against on adequacy of effectiveness evidence specifically for DMD cardiomyopathy; the vote was advisory, not a binding FDA disposition.",
    fdaRelevance:"Substantive negative signal for the originally debated cardiac claim.",
    counterpoint:"The committee was not asked to vote on the HOPE-3 upper-limb primary endpoint or the overall benefit-risk profile; the application later sought a refined indication.",
    remainingQuestion:"What effect will the narrowed indication and new analyses have on the agency's final review?",
    sourceTitle:"Capricor SEC-furnished August 13, 2026 regulatory update",
    sourceUrl:"https://www.sec.gov/Archives/edgar/data/1133869/000110465926095908/capr-20260813xex99d1.htm"
  },
  {
    id:"capr-bimo",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"integrity",type:"INSPECTION_OBSERVATION",evidence:"SEC_COMPANY_DISCLOSURE",published:"2026-08-13",
    headline:"Company disclosed an FDA BIMO Form 483 observation",
    detail:"Capricor reported one inspection observation relating principally to standard procedures, documentation, vendor oversight and audit timeliness in HOPE-3 clinical operations; it submitted a response and said it was awaiting feedback.",
    fdaRelevance:"A documented inspection observation requires follow-up. It does not establish invalid trial data or an unresolved FDA deficiency.",
    counterpoint:"The sponsor stated it did not believe the observation compromised HOPE-3 data integrity.",
    remainingQuestion:"Has FDA closed or otherwise resolved the observation, and is any residual issue decision-relevant?",
    sourceTitle:"Capricor August 13, 2026 regulatory update / SEC exhibit",
    sourceUrl:"https://www.sec.gov/Archives/edgar/data/1133869/000110465926095908/capr-20260813xex99d1.htm"
  },
  {
    id:"capr-ext",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"timing",type:"EXTENSION_CONFIRMED",evidence:"SPONSOR_RELEASE",published:"2026-08-24",
    headline:"Formal PDUFA goal-date extension from Aug 22 to Nov 22, 2026",
    detail:"Capricor announced a three-month extension after an amendment containing HOPE-3 open-label extension data, additional robustness analyses and a refined proposed indication.",
    fdaRelevance:"A completed, documented timing event, not a forecast of another extension or a CRL.",
    counterpoint:"FDA's acceptance of review time for additional evidence does not determine the ultimate application disposition.",
    remainingQuestion:"Is November 22 still the confirmed current goal, and have any further material amendments been disclosed?",
    sourceTitle:"Capricor August 24, 2026 PDUFA extension announcement",
    sourceUrl:"https://www.capricor.com/investors/news-events/press-releases/detail/354/capricor-therapeutics-announces-extension-of-pdufa-target"
  },
  {
    id:"capr-pul",relatedNcts:["NCT05126758"],company:"Capricor",drug:"Deramiocel",indication:"Duchenne muscular dystrophy",
    domain:"endpoint",type:"EFFICACY_EVIDENCE",evidence:"SEC_COMPANY_DISCLOSURE",published:"2026-08-13",
    headline:"Sponsor reported a positive upper-limb endpoint but revised cardiac significance",
    detail:"Capricor reported an upper-limb PUL 2.0 result at p=0.029; after a model correction LVEF was p=0.09 rather than earlier p=0.04, with additional endpoints nominal under the hierarchy.",
    fdaRelevance:"Positive sponsor analysis and revised cardiac result must be distinguished from FDA's own contrary statistical interpretation.",
    counterpoint:"FDA's July advisory briefing challenged the robustness and analysis-plan choices underlying the submitted efficacy analyses.",
    remainingQuestion:"Do the latest FDA-acceptable analyses provide sufficient evidence for the narrowed upper-limb claim?",
    sourceTitle:"Capricor August 13, 2026 HOPE-3 clinical results update",
    sourceUrl:"https://www.sec.gov/Archives/edgar/data/1133869/000110465926095908/capr-20260813xex99d1.htm"
  },
  {
    id:"cort-prior",relatedNcts:["NCT03697109","NCT04308590"],company:"Corcept",drug:"Relacorilant",indication:"Endogenous Cushing syndrome / hypercortisolism",
    domain:"prior",type:"PREVIOUS_CRL",evidence:"SEC_COMPANY_DISCLOSURE",published:"2026-11-03",
    headline:"Previous December 30, 2025 CRL required additional evidence of efficacy",
    detail:"Corcept's November 2026 Form 10-Q says FDA acknowledged that GRACE met its primary endpoint and that GRADIENT was confirmatory, but still sought additional evidence of effectiveness in the original NDA.",
    fdaRelevance:"Confirmed prior CRL for this application pathway; a positive Phase 3 endpoint was not sufficient for approval.",
    counterpoint:"FDA subsequently requested further analyses of existing submitted data rather than immediately requiring another new trial.",
    remainingQuestion:"Did the global statistical test adequately resolve FDA's efficacy objection?",
    sourceTitle:"Corcept November 3, 2026 Form 10-Q",
    sourceUrl:"https://www.sec.gov/Archives/edgar/data/1088856/000162828026069501/cort-20260930.htm"
  },
  {
    id:"cort-gst",relatedNcts:["NCT03697109","NCT04308590"],company:"Corcept",drug:"Relacorilant",indication:"Endogenous Cushing syndrome / hypercortisolism",
    domain:"statistics",type:"REVIEW_STATUS",evidence:"SEC_COMPANY_DISCLOSURE",published:"2026-11-03",
    headline:"FDA requested a global statistical test; NDA resubmitted June 17, 2026",
    detail:"The company reports FDA requested a global test of hypertension, hyperglycemia and body weight after the prior CRL. Corcept said the analysis was positive and resubmitted its NDA; the new PDUFA goal is December 17, 2026.",
    fdaRelevance:"Concrete FDA question and sponsor mitigation can be traced; response adequacy is not publicly adjudicated.",
    counterpoint:"Positive sponsor-described analysis does not establish the regulator has accepted the efficacy case.",
    remainingQuestion:"Are the test definition, prespecification, multiplicity and clinical interpretation adequate for approval?",
    sourceTitle:"Corcept November 3, 2026 Form 10-Q",
    sourceUrl:"https://www.sec.gov/Archives/edgar/data/1088856/000162828026069501/cort-20260930.htm"
  },
  {
    id:"cort-grace",relatedNcts:["NCT03697109"],company:"Corcept",drug:"Relacorilant",indication:"Endogenous Cushing syndrome / hypercortisolism",
    domain:"design",type:"EFFICACY_EVIDENCE",evidence:"PEER_REVIEWED",published:"2026-02-20",
    headline:"Randomized withdrawal GRACE results support maintenance of blood-pressure control",
    detail:"Published GRACE trial reports 62 participants randomized after open-label response enrichment, 30 continuing relacorilant versus 32 placebo, and an odds ratio of 0.17 (95% CI 0.04–0.77; p=0.022) for loss of hypertension control in the prespecified comparison.",
    fdaRelevance:"Randomized-withdrawal design and enrichment require careful interpretation for the full proposed indication and global multicomponent endpoint.",
    counterpoint:"The publication supports a treatment effect in a selected responsive population; it cannot independently overturn the prior CRL.",
    remainingQuestion:"How well do trial-enriched responders represent the intended labeled population?",
    sourceTitle:"Published GRACE randomized withdrawal study, PMC",
    sourceUrl:"https://pmc.ncbi.nlm.nih.gov/articles/PMC13220893/"
  },
  {
    id:"svra-extension",relatedNcts:["NCT04544293"],company:"Savara",drug:"Molgramostim inhalation solution",indication:"Autoimmune pulmonary alveolar proteinosis",
    domain:"timing",type:"EXTENSION_CONFIRMED",evidence:"SPONSOR_RELEASE",published:"2026-04-15",
    headline:"FDA extended review to Nov 22 following responses deemed a major amendment",
    detail:"Savara reported a three-month formal extension following FDA information-request responses considered a major BLA amendment; it reported that the correspondence did not cite safety, efficacy or manufacturing concerns.",
    fdaRelevance:"A known extension event. Its stated trigger must not be mislabeled as a documented efficacy or CMC defect.",
    counterpoint:"The company's description does not prove the entire application is free of deficiencies.",
    remainingQuestion:"What was included in the amendment, and have new regulatory concerns been publicly disclosed since April?",
    sourceTitle:"Savara April 15, 2026 FDA review extension announcement",
    sourceUrl:"https://investors.savarapharma.com/news/news-details/2026/Savara-Announces-the-U-S--Food--Drug-Administration-FDA-Has-Extended-the-Review-Period-for-the-Molgramostim-Inhalation-Solution-Molgramostim-Biologics-License-Application-BLA-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP/default.aspx"
  },
  {
    id:"svra-impala",relatedNcts:["NCT04544293"],company:"Savara",drug:"Molgramostim inhalation solution",indication:"Autoimmune pulmonary alveolar proteinosis",
    domain:"endpoint",type:"EFFICACY_EVIDENCE",evidence:"SPONSOR_RELEASE",published:"2024-06-26",
    headline:"IMPALA-2 sponsor-reported positive DLCO primary endpoint",
    detail:"The company reported a placebo-adjusted 6.00-percentage-point benefit for Week-24 DLCO % predicted (p=0.0007) and Week-24 SGRQ total difference −6.59 points (p=0.0072); Week-48 SGRQ total was not significant (p=0.1046).",
    fdaRelevance:"Positive primary gas-exchange evidence; assess patient-important clinical meaning, durability and secondary endpoint hierarchy.",
    counterpoint:"A non-significant Week-48 quality-of-life result limits claims of uniformly sustained patient-reported benefit.",
    remainingQuestion:"Are DLCO improvement and quality-of-life findings sufficient for benefit-risk and the proposed label?",
    sourceTitle:"Savara June 26, 2024 pivotal IMPALA-2 results",
    sourceUrl:"https://investors.savarapharma.com/news/news-details/2024/Savara-Announces-Molgramostim-Nebulizer-Solution-Molgramostim-Achieved-Statistical-Significance-for-Primary-Endpoint-and-Multiple-Secondary-Endpoints-in-IMPALA-2-a-Pivotal-Phase-3-Clinical-Trial-in-Autoimmune-Pulmonary-Alveolar--06-26-2024/default.aspx"
  },
  {
    id:"cogt-peak",relatedNcts:["NCT05208047"],company:"Cogent",drug:"Bezuclastinib plus sunitinib",indication:"Gastrointestinal stromal tumor following imatinib",
    domain:"endpoint",type:"EFFICACY_EVIDENCE",evidence:"SPONSOR_RELEASE",published:"2026-05-28",
    headline:"PEAK trial reported large active-comparator PFS improvement",
    detail:"The company reported median PFS 16.5 versus 9.2 months for bezuclastinib+sunitinib versus sunitinib, HR 0.50 (95% CI 0.39–0.65, p<0.0001).",
    fdaRelevance:"Substantial efficacy support against an active comparator; investigate clinical relevance, safety, dose tolerability and mutation-specific consistency.",
    counterpoint:"Positive PFS findings do not establish adequate CMC readiness or final FDA benefit-risk approval.",
    remainingQuestion:"Are integrated safety, subgroup and manufacturing assessments consistent with approval?",
    sourceTitle:"Cogent May 28, 2026 FDA acceptance and PEAK results release",
    sourceUrl:"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-fda-acceptance-new-drug-0"
  },
  {
    id:"cogt-status",relatedNcts:["NCT05208047"],company:"Cogent",drug:"Bezuclastinib plus sunitinib",indication:"Gastrointestinal stromal tumor following imatinib",
    domain:"timing",type:"REVIEW_STATUS",evidence:"SEC_COMPANY_DISCLOSURE",published:"2026-11-05",
    headline:"Company reaffirmed November 30, 2026 PDUFA target date",
    detail:"The November 5, 2026 company SEC exhibit lists a possible GIST approval and current target action date of November 30, 2026.",
    fdaRelevance:"Supports current calendar tracking for the GIST application; this is distinct from the same drug's systemic mastocytosis review cycles.",
    counterpoint:"A goal date does not guarantee an FDA decision or approval, and manufacturing/inspection issues may not be publicly disclosed.",
    remainingQuestion:"Is there any newer dated FDA correspondence, major amendment, advisory review or inspection disclosure?",
    sourceTitle:"Cogent November 5, 2026 Form 8-K Exhibit 99.1",
    sourceUrl:"https://www.sec.gov/Archives/edgar/data/1622229/000119312526449926/cogt-ex99_1.htm"
  }
];
export function findingsForNct(nct:string):ReviewedFinding[]{
  if(!/^NCT\d{8}$/.test(nct))return [];
  return REVIEWED_FINDINGS.filter(f=>f.relatedNcts.includes(nct));
}
export const REVIEW_COVERAGE={
  reviewedNcts:new Set(REVIEWED_FINDINGS.flatMap(f=>f.relatedNcts)).size,
  documentedFindings:REVIEWED_FINDINGS.length,
  reviewedPrograms:new Set(REVIEWED_FINDINGS.map(f=>f.company+":"+f.drug+":"+f.indication)).size
};
