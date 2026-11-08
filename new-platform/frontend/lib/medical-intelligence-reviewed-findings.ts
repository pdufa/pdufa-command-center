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
  },
{
  "id": "abvx-induction-1",
  "relatedNcts": [
    "NCT05507203"
  ],
  "company": "Abivax",
  "drug": "Obefazimod",
  "indication": "Moderately to severely active ulcerative colitis",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2025-07-22",
  "headline": "ABTECT-1 achieved Week 8 clinical remission endpoint at both doses",
  "detail": "ABTECT-1 clinical remission: 25 mg 23.8% versus placebo 2.5% (p<0.0001), 50 mg 21.7% versus placebo 2.5% (p<0.0001).",
  "fdaRelevance": "Two doses showed statistically significant induction benefit in this pivotal trial; judge consistency in ABTECT-2 and confirm disease-relevant maintenance response.",
  "counterpoint": "One successful trial and sponsor-reported results do not establish FDA acceptance of the entire efficacy or safety package.",
  "remainingQuestion": "Do longer-term risks, treatment adherence and efficacy in prior-advanced-therapy subgroups support the proposed label?",
  "sourceTitle": "Abivax SEC furnished ABTECT induction primary-endpoint table",
  "sourceUrl": "https://ir.abivax.com/static-files/99de1b8a-f695-4e75-a38f-9d970eb52d52"
},
{
  "id": "abvx-induction-2",
  "relatedNcts": [
    "NCT05507216"
  ],
  "company": "Abivax",
  "drug": "Obefazimod",
  "indication": "Moderately to severely active ulcerative colitis",
  "domain": "statistics",
  "type": "SCIENTIFIC_UNCERTAINTY",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2025-07-22",
  "headline": "ABTECT-2 low-dose arm did not meet primary significance",
  "detail": "ABTECT-2 25 mg clinical remission was 11.3% versus 6.3% placebo (p=0.1034), whereas 50 mg achieved 19.8% versus 6.3% (p=0.0001).",
  "fdaRelevance": "Confirmed dose-specific failure of significance in one trial warrants dose-selection and multiplicity review; it is not proof of a forthcoming CRL.",
  "counterpoint": "The 50 mg dose met primary remission endpoints in both induction trials; maintenance efficacy was also reported at both doses.",
  "remainingQuestion": "Which dose and trial comparisons are intended for FDA labeling, and how was the multiplicity hierarchy handled?",
  "sourceTitle": "Abivax SEC furnished ABTECT-1/2 endpoint table",
  "sourceUrl": "https://ir.abivax.com/static-files/99de1b8a-f695-4e75-a38f-9d970eb52d52"
},
{
  "id": "achv-cmc-crl",
  "relatedNcts": [
    "NCT04576949",
    "NCT05206370"
  ],
  "company": "Achieve Life Sciences",
  "drug": "Cytisinicline",
  "indication": "Smoking cessation / nicotine dependence",
  "domain": "cmc",
  "type": "PREVIOUS_CRL",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-08-11",
  "headline": "June 2026 CRL tied to third-party facility CGMP deficiencies and labeling",
  "detail": "The NDA received a CRL after the prior contract manufacturer's OAI classification and warning letter following FDA CGMP inspection; draft labeling remained unfinished. Company reported no FDA clinical efficacy or safety deficiencies.",
  "fdaRelevance": "A real manufacturing-based prior CRL must be explicitly carried into the resubmission review rather than discounting positive cessation trials.",
  "counterpoint": "The cited observations were general facility matters rather than cytisinicline-specific; the sponsor has arranged a replacement manufacturer.",
  "remainingQuestion": "Can the replacement commercial facility complete technology transfer, validation, stability, inspection and label review satisfactorily?",
  "sourceTitle": "Achieve Life Sciences August 2026 Form 10-Q, NDA and CGMP risk disclosures",
  "sourceUrl": "https://ir.achievelifesciences.com/sec-filings/all-sec-filings/content/0001193125-26-344624/achv-20260630.htm"
},
{
  "id": "achv-remediation",
  "relatedNcts": [
    "NCT04576949",
    "NCT05206370"
  ],
  "company": "Achieve Life Sciences",
  "drug": "Cytisinicline",
  "indication": "Smoking cessation / nicotine dependence",
  "domain": "cmc",
  "type": "REVIEW_STATUS",
  "evidence": "SPONSOR_RELEASE",
  "published": "2026-06-22",
  "headline": "Replacement manufacturer identified; Q4 2026 NDA resubmission planned",
  "detail": "Achieve said it had transferred analytical methods to Adare Pharma Solutions, made an engineering batch and qualified testing procedures; planned to resubmit naming Adare, not the cited prior facility.",
  "fdaRelevance": "Concrete corrective work may address the prior CRL, but an engineering batch does not itself establish commercial process qualification or FDA approval.",
  "counterpoint": "The originally cited facility problem did not concern efficacy and safety of the candidate.",
  "remainingQuestion": "Has the sponsor actually resubmitted, and has FDA accepted all manufacturing documentation and inspections?",
  "sourceTitle": "Achieve June 22 2026 cytisinicline CRL response announcement",
  "sourceUrl": "https://ir.achievelifesciences.com/news-events/press-releases/detail/264/achieve-life-sciences-receives-complete-response-letter-from-fda-for-cytisinicline-nda"
},
{
  "id": "apmd-osa-efficacy",
  "relatedNcts": [
    "NCT05811247",
    "NCT05813275"
  ],
  "company": "Apnimed",
  "drug": "AD109 (aroxybutynin/atomoxetine)",
  "indication": "Obstructive sleep apnea",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-07-27",
  "headline": "SynAIRgy and LunAIRo achieved treatment-policy apnea-hypopnea improvements",
  "detail": "In Apnimed's S-1, Week 26 treatment-policy mean AHI reduction was 44.1% and 33.7% in SynAIRgy and LunAIRo, respectively, versus 17.6% and 7.3% on placebo (p≤0.0001).",
  "fdaRelevance": "Supports physiological OSA efficacy across two pivotal trials; clinical meaning and adherence remain important for labeling and benefit-risk.",
  "counterpoint": "Reduced AHI is not identical to demonstrated cardiovascular outcome benefit; full safety, clinical symptom and adherence evidence require review.",
  "remainingQuestion": "Do insomnia, anticholinergic effects, blood pressure, heart-rate and dropout patterns create a clinically important benefit-risk concern?",
  "sourceTitle": "Apnimed July 2026 SEC S-1, Phase 3 results discussion",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526316811/apni-20260727.htm"
},
{
  "id": "apmd-responder",
  "relatedNcts": [
    "NCT05811247",
    "NCT05813275"
  ],
  "company": "Apnimed",
  "drug": "AD109 (aroxybutynin/atomoxetine)",
  "indication": "Obstructive sleep apnea",
  "domain": "statistics",
  "type": "SCIENTIFIC_UNCERTAINTY",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-07-10",
  "headline": "SynAIRgy responder secondary analysis depends on intercurrent-event strategy",
  "detail": "At 26 weeks, SynAIRgy AHI ≥50% responder rate was 25.8% versus 19.8% placebo (treatment-policy p=0.182); on-treatment estimate was 39.6% versus 22.3% (p<0.0001).",
  "fdaRelevance": "The analysis strategy changes inference on a clinically interpretable secondary endpoint; requires assessment of adherence, estimands and multiplicity.",
  "counterpoint": "The prespecified AHI primary endpoints were significant in both pivotal studies, and LunAIRo responder analyses were also positive.",
  "remainingQuestion": "How are treatment discontinuation and missing observations handled across co-primary and key secondary analyses?",
  "sourceTitle": "Apnimed July 2026 IPO S-1, responder/estimand analyses",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1745648/000119312526300909/apni-20260710.htm"
},
{
  "id": "axsm-axs12-identity",
  "relatedNcts": [
    "NCT05059223",
    "NCT05113745"
  ],
  "company": "Axsome Therapeutics",
  "drug": "AXS-12 (reboxetine)",
  "indication": "Cataplexy in narcolepsy",
  "domain": "timing",
  "type": "REVIEW_STATUS",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-07-15",
  "headline": "FDA accepted AXS-12 NDA for narcolepsy cataplexy, May 1 2027 PDUFA",
  "detail": "Axsome's July 15 SEC exhibit confirms an accepted NDA for AXS-12, FDA target date May 1, 2027, and no advisory committee currently planned. Both FOCUS NCT IDs pertain to the AXS-12 narcolepsy program.",
  "fdaRelevance": "Validates the current product and indication review cycle rather than conflating it with approved AXS-05 or other Axsome candidates.",
  "counterpoint": "FDA filing acceptance and absence of planned advisory committee do not establish approval readiness.",
  "remainingQuestion": "How robust are SYMPHONY and ENCORE efficacy and long-term safety data, including cataplexy attack frequency and rebound effects?",
  "sourceTitle": "Axsome July 15 2026 SEC 8-K exhibit, AXS-12 FDA acceptance",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1579428/000119312526304039/axsm-ex99_1.htm"
},
{
  "id": "blte-dragon",
  "relatedNcts": [
    "NCT05244304"
  ],
  "company": "Belite Bio",
  "drug": "Tinlarebant",
  "indication": "Stargardt disease type 1",
  "domain": "statistics",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SPONSOR_RELEASE",
  "published": "2025-12-12",
  "headline": "DRAGON lesion-growth endpoint positive; additional post-hoc model reported",
  "detail": "Sponsor reports 35.7% reduction in retinal atrophic-lesion growth with prespecified MMRM unstructured covariance (p=0.0033). A separate post-hoc autoregressive MMRM yielded 35.4% and p<0.0001; these are analytically distinct.",
  "fdaRelevance": "The prespecified result supports anatomical benefit; distinguish the alternative post-hoc analysis and examine visual-function relevance.",
  "counterpoint": "FDA granted priority review with a Feb 12 2027 goal; ocular adverse effects such as xanthopsia and delayed dark adaptation remain relevant.",
  "remainingQuestion": "Does the lesion-growth effect translate to preserved vision/function in the intended population and are ocular adverse effects manageable?",
  "sourceTitle": "Belite Bio Phase 3 DRAGON positive topline results",
  "sourceUrl": "https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite"
},
{
  "id": "cldx-embarq",
  "relatedNcts": [
    "NCT06445023",
    "NCT06455202"
  ],
  "company": "Celldex Therapeutics",
  "drug": "Barzolvolimab",
  "indication": "Chronic spontaneous urticaria",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-05",
  "headline": "Both EMBARQ-CSU Phase 3 studies met Week 12 UAS7 primary endpoints",
  "detail": "Celldex SEC filing reports for the 150 mg dose Week 12 LS mean UAS7 change of -20.2 in each study versus -10.7 and -11.4 placebo, respectively (p<0.00001); all key secondary endpoints reportedly met.",
  "fdaRelevance": "Consistent placebo-controlled pivotal efficacy across two studies supports a future BLA, but the company still plans to file in 2027.",
  "counterpoint": "No FDA-accepted BLA or assigned PDUFA date has yet been shown for these study IDs, and 52-week treatment/safety data require review.",
  "remainingQuestion": "Are long-term safety, immunologic issues and durability sufficient for the proposed population and dosing intervals?",
  "sourceTitle": "Celldex November 2026 Form 10-Q EMBARQ trial tables",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm"
},
{
  "id": "cytk-maple-cycle",
  "relatedNcts": [
    "NCT05767346"
  ],
  "company": "Cytokinetics",
  "drug": "Aficamten (MYQORZO)",
  "indication": "Obstructive hypertrophic cardiomyopathy",
  "domain": "timing",
  "type": "SCIENTIFIC_UNCERTAINTY",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-04",
  "headline": "MAPLE-HCM is in an already approved oHCM indication; recorded Nov 14 goal needs verification",
  "detail": "Cytokinetics' September 2026 Form 10-Q confirms FDA approved MYQORZO for symptomatic obstructive HCM in December 2025 and it was commercially available in 2026. Separate non-obstructive HCM sNDA filing was still planned for Q4 2026.",
  "fdaRelevance": "Do not predict a fresh oHCM approval/CRL against an already approved product or assume November 14 2026 belongs to this trial.",
  "counterpoint": "Other supplemental regulatory cycles could exist, but the exact NDA number, indication and source of the FOCUS date must be demonstrated.",
  "remainingQuestion": "Which exact current FDA application has a November 14 target, and is this NCT actually pivotal for that review cycle?",
  "sourceTitle": "Cytokinetics November 2026 Form 10-Q, approved MYQORZO and future sNDA",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm"
},
{
  "id": "cytk-acacia-safety",
  "relatedNcts": [
    "NCT06081894"
  ],
  "company": "Cytokinetics",
  "drug": "Aficamten",
  "indication": "Symptomatic non-obstructive hypertrophic cardiomyopathy",
  "domain": "safety",
  "type": "SCIENTIFIC_UNCERTAINTY",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-04",
  "headline": "ACACIA-HCM showed heart-failure serious-adverse-event imbalance despite positive endpoints",
  "detail": "Cytokinetics reports LVEF <50% in 10% aficamten versus 1% placebo and heart-failure serious adverse events in 4.7% of aficamten recipients versus 1.2% of placebo recipients; dual endpoints were met.",
  "fdaRelevance": "Potential clinical benefit-risk and REMS/labeling scrutiny for a proposed non-obstructive HCM indication.",
  "counterpoint": "The company reports statistically significant improvements in both dual primary endpoints and key secondary measures; no FDA deficiency is confirmed.",
  "remainingQuestion": "How did investigators adjudicate heart-failure cases, reversible LVEF reduction, discontinuation, monitoring and dose-titration safety?",
  "sourceTitle": "Cytokinetics November 2026 SEC quarterly clinical safety disclosures",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm"
},
{
  "id": "imnm-ringside-efficacy",
  "relatedNcts": [
    "NCT04871282"
  ],
  "company": "Immunome",
  "drug": "Varegacestat",
  "indication": "Progressing desmoid tumors",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SPONSOR_RELEASE",
  "published": "2026-10-26",
  "headline": "RINGSIDE confirmed response 56% vs 9% placebo; PFS HR 0.16",
  "detail": "At ESMO 2026, sponsor reported 56% versus 9% independently assessed confirmed objective responses, and PFS hazard ratio 0.16 (95% CI 0.071–0.375; p<0.0001); common adverse effects included diarrhea, fatigue, rash and nausea.",
  "fdaRelevance": "Large tumor and progression effects support efficacy, while toxicity and patient-reported benefit inform FDA benefit-risk.",
  "counterpoint": "Strong Phase 3 results do not establish manufacturing, inspections or FDA-acceptable proposed labeling.",
  "remainingQuestion": "Are longer-term adverse effects, reproductive risks, secondary malignancies and quality-of-life tradeoffs adequately characterized?",
  "sourceTitle": "Immunome ESMO 2026 RINGSIDE clinical results",
  "sourceUrl": "https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/"
},
{
  "id": "mltx-vela2-primary",
  "relatedNcts": [
    "NCT06411379"
  ],
  "company": "MoonLake Immunotherapeutics",
  "drug": "Sonelokimab",
  "indication": "Hidradenitis suppurativa",
  "domain": "statistics",
  "type": "SCIENTIFIC_UNCERTAINTY",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-04",
  "headline": "VELA-2 prespecified composite primary HiSCR75 missed significance (p=0.053)",
  "detail": "MoonLake reports Week 16 VELA-2 HiSCR75 placebo-adjusted difference of 9 percentage points with prespecified composite-strategy p=0.053; alternative treatment-policy strategy showed p=0.033.",
  "fdaRelevance": "A prespecified multiplicity-controlled primary failure is a substantive statistical uncertainty for reliance on two similarly designed pivotal studies.",
  "counterpoint": "VELA-1's primary was positive and a second prespecified treatment-policy strategy produced significant results in VELA-2.",
  "remainingQuestion": "Which estimand and missing/intercurrent-event treatment will FDA judge adequate for substantial evidence of efficacy?",
  "sourceTitle": "MoonLake November 4 2026 Q3 SEC business update",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1821586/000182158626000013/moonlake-pressreleasexq320.htm"
},
{
  "id": "mltx-vela1",
  "relatedNcts": [
    "NCT06411899"
  ],
  "company": "MoonLake Immunotherapeutics",
  "drug": "Sonelokimab",
  "indication": "Hidradenitis suppurativa",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SPONSOR_RELEASE",
  "published": "2025-09-28",
  "headline": "VELA-1 Week 16 HiSCR75 significantly improved over placebo",
  "detail": "MoonLake reports VELA-1 Week 16 HiSCR75 rates 34.8% sonelokimab versus 17.5% placebo, a 17.3-point difference; company stated significance in both prespecified analysis strategies.",
  "fdaRelevance": "One pivotal trial supports efficacy, but the discordant companion VELA-2 composite analysis requires integrated interpretation.",
  "counterpoint": "The more stringent HiSCR75 endpoint differs from some historical HS comparator programs, limiting cross-trial superiority claims.",
  "remainingQuestion": "What are the complete efficacy, safety, infection and immunogenicity findings across the full VELA program?",
  "sourceTitle": "MoonLake September 28 2025 Phase 3 VELA primary report",
  "sourceUrl": "https://www.globenewswire.com/news-release/2025/9/28/3157370/0/en/moonlake-immunotherapeutics-reports-on-week-16-results-of-the-vela-phase-3-hidradenitis-suppurativa-program-with-the-nanobody-sonelokimab.html"
},
{
  "id": "mltx-filing",
  "relatedNcts": [
    "NCT06411379",
    "NCT06411899"
  ],
  "company": "MoonLake Immunotherapeutics",
  "drug": "Sonelokimab",
  "indication": "Hidradenitis suppurativa",
  "domain": "timing",
  "type": "REVIEW_STATUS",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-04",
  "headline": "BLA submitted September 30; FDA filing acceptance and review goal were still pending",
  "detail": "The company stated its sonelokimab BLA was submitted September 30, 2026 and it expected FDA filing acceptance within roughly 60 days, with review timeline to follow; no approved PDUFA date was confirmed in the filing.",
  "fdaRelevance": "Forecasting a PDUFA action date before FDA accepts the BLA is premature; filing status and statistical concern must both be tracked.",
  "counterpoint": "The filing contains multiple Phase 2/3 studies, including VELA and MIRA, that may strengthen the integrated record.",
  "remainingQuestion": "Has FDA formally accepted the BLA, set a review goal, or requested additional analyses?",
  "sourceTitle": "MoonLake November 4 2026 SEC company update",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1821586/000182158626000013/moonlake-pressreleasexq320.htm"
},
{
  "id": "mlys-launch-hypertension",
  "relatedNcts": [
    "NCT06153693"
  ],
  "company": "Mineralys Therapeutics",
  "drug": "Lorundrostat",
  "indication": "Uncontrolled or resistant hypertension",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-04",
  "headline": "Launch-HTN additional analyses show meaningful blood-pressure reductions",
  "detail": "Company reports that 46% on 50 mg achieved office SBP <130 mmHg at Week 12; more than two-thirds had SBP reduction ≥10 mmHg; the NDA review continued toward December 22, 2026.",
  "fdaRelevance": "Objective blood-pressure lowering supports efficacy; aldosterone pathway risks, electrolytes, renal function and integrated safety require full review.",
  "counterpoint": "Goal attainment is an additional descriptive result; the prespecified primary comparison and hyperkalemia/renal monitoring must be separately verified.",
  "remainingQuestion": "What are placebo-adjusted primary effects, hyperkalemia rates, discontinuation and renal-function safety by baseline CKD status?",
  "sourceTitle": "Mineralys November 4 2026 SEC Q3 results release",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm"
},
{
  "id": "phvs-rapide3",
  "relatedNcts": [
    "NCT06343779"
  ],
  "company": "Pharvaris",
  "drug": "Deucrictibant immediate release",
  "indication": "On-demand hereditary angioedema attacks",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SPONSOR_RELEASE",
  "published": "2025-12-11",
  "headline": "RAPIDe-3 reported time to onset of relief 1.28 h vs over 12 h",
  "detail": "Pharvaris reports faster median time to symptom relief (1.28 h vs >12 h, p<0.0001) and shorter time to end of progression (17.47 vs 228.67 minutes, p<0.0001) compared with placebo.",
  "fdaRelevance": "Acute symptom time-to-relief is highly clinically relevant; robust event adjudication, rescue and recurrence after dosing need assessment.",
  "counterpoint": "The sponsor-reported efficacy effect does not establish FDA acceptance of integrated safety or final product quality.",
  "remainingQuestion": "Were attack-level correlations and repeated attacks handled correctly, and is rescue-medication use captured without bias?",
  "sourceTitle": "Pharvaris RAPIDe-3 top-line results announcement",
  "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study"
},
{
  "id": "phvs-chapter3",
  "relatedNcts": [
    "NCT06669754"
  ],
  "company": "Pharvaris",
  "drug": "Deucrictibant extended release",
  "indication": "Hereditary angioedema prophylaxis",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-09-08",
  "headline": "CHAPTER-3 prevention study reported 83% HAE attack-rate reduction",
  "detail": "In 85 randomized participants (55 treated, 30 placebo), sponsor reported a mean monthly HAE attack-rate reduction of 83% versus placebo (p<0.0001); NDA filing was planned for first half 2027.",
  "fdaRelevance": "Strong preventive effect potentially supports a separate prophylaxis application; do not attach the on-demand April 2027 PDUFA date to this study.",
  "counterpoint": "Sample size and heterogeneous HAE subtypes, including normal C1 inhibitor, require population-specific precision and safety analysis.",
  "remainingQuestion": "Are confidence intervals, subtype interactions, long-term tolerability and a distinct FDA application cycle adequately established?",
  "sourceTitle": "Pharvaris September 8 2026 CHAPTER-3 SEC exhibit",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1830487/000119312526384339/phvs-ex99_1.htm"
},
{
  "id": "prax-ulix-regulatory",
  "relatedNcts": [
    "NCT06087276"
  ],
  "company": "Praxis Precision Medicines",
  "drug": "Ulixacaltamide",
  "indication": "Essential tremor",
  "domain": "inspections",
  "type": "REVIEW_STATUS",
  "evidence": "SPONSOR_RELEASE",
  "published": "2026-08-06",
  "headline": "Sponsor reported favorable FDA mid-cycle feedback and BIMO inspection",
  "detail": "Praxis said FDA identified no major safety or efficacy concerns at mid-cycle to date, did not plan an advisory committee meeting, and BIMO inspections concluded without Form FDA 483 observations. PDUFA goal Jan 29, 2027.",
  "fdaRelevance": "A favorable interim disclosure lowers the concern for known specific inspection deficiencies, but does not confirm final review outcome or CMC completion.",
  "counterpoint": "The company statement is not the full FDA review; manufacturing inspections and final labeling may remain nonpublic.",
  "remainingQuestion": "Are both ESSENTIAL3 pivotal studies, exposure-adjusted adverse events and product-quality readiness acceptable?",
  "sourceTitle": "Praxis August 6 2026 regulatory and operations update",
  "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-provides-corporate-update-and-20"
},
{
  "id": "srpt-essence-failure",
  "relatedNcts": [
    "NCT02500381"
  ],
  "company": "Sarepta Therapeutics",
  "drug": "Golodirsen / casimersen (VYONDYS 53 / AMONDYS 45)",
  "indication": "Duchenne muscular dystrophy",
  "domain": "endpoint",
  "type": "SCIENTIFIC_UNCERTAINTY",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-05",
  "headline": "ESSENCE confirmatory trial missed primary endpoint; sNDAs seek traditional approval",
  "detail": "Sarepta September 2026 Form 10-Q states the November 2025 ESSENCE topline primary endpoint did not reach statistical significance. FDA accepted supplemental NDAs in June 2026 to convert accelerated approvals, with Feb 28 2027 goal.",
  "fdaRelevance": "Direct regulatory risk to verification of clinical benefit; potential outcomes include denial of conversion, label adjustments or an accelerated approval reassessment, rather than a simple first-time approval/CRL dichotomy.",
  "counterpoint": "Both medicines remain approved under accelerated approval and the applications include other published and real-world evidence.",
  "remainingQuestion": "What are the prespecified ESSENCE outcome, treatment effect, confidence intervals, subgroup findings and FDA's standard for adequate confirmation?",
  "sourceTitle": "Sarepta November 5 2026 Form 10-Q ESSENCE result and sNDA risk",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm"
},
{
  "id": "urgn-utopia",
  "relatedNcts": [
    "NCT06331299"
  ],
  "company": "UroGen Pharma",
  "drug": "UGN-103 (mitomycin intravesical)",
  "indication": "Recurrent low-grade intermediate-risk non-muscle-invasive bladder cancer",
  "domain": "design",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SPONSOR_RELEASE",
  "published": "2026-08-25",
  "headline": "UTOPIA single-arm CR 77.8% and conditional 6-month response durability 94.5%",
  "detail": "Sponsor reports 3-month complete response 77.8% (95% CI 68.3–85.5%) and 6-month duration of response by Kaplan-Meier 94.5% (95% CI 86.1–97.9%) among eligible responders; separate-trial ZUSDURI results are not randomized comparisons.",
  "fdaRelevance": "The FDA-agreed single-arm filing strategy and existing mitomycin formulation precedent matter, but cross-trial equivalence is not demonstrated.",
  "counterpoint": "FDA accepted the application with a June 14 2027 goal and a prior approved related product supports the clinical framework.",
  "remainingQuestion": "What do FDA correspondence, selection bias, disease surveillance, durability beyond 6 months and product/CMC changes show?",
  "sourceTitle": "UroGen UGN-103 NDA submission and UTOPIA evidence release",
  "sourceUrl": "https://urogen.gcs-web.com/news-releases/news-release-details/urogen-submits-nda-ugn-103-investigational-treatment-recurrent"
},
{
  "id": "vera-origin3",
  "relatedNcts": [
    "NCT04716231"
  ],
  "company": "Vera Therapeutics",
  "drug": "Atacicept (TRUTAKNA)",
  "indication": "IgA nephropathy",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "SEC_COMPANY_DISCLOSURE",
  "published": "2026-11-05",
  "headline": "ORIGIN 3 final analysis supports sustained kidney-function protection",
  "detail": "Sponsor reports Week-52 eGFR treatment difference +5.6 mL/min/1.73m² (95% CI 3.7–7.5, p<0.0001), two-year annualized eGFR slope difference +5.0 (95% CI 3.6–6.5), composite kidney disease progression HR 0.24.",
  "fdaRelevance": "Provides kidney-function outcomes supporting conversion from accelerated to full approval; duration, clinical endpoint definitions and integrated safety require review.",
  "counterpoint": "Product was already FDA accelerated-approved in July 2026 for proteinuria reduction; a new approval forecast must address the supplemental BLA specifically.",
  "remainingQuestion": "Do longer-term safety, infections/immunoglobulin effects and renal endpoint sensitivity analyses support full approval?",
  "sourceTitle": "Vera November 2026 SEC 10-Q ORIGIN 3 efficacy analysis",
  "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1831828/000119312526449826/vera-20260930.htm"
},
{
  "id": "vera-approval-cycle",
  "relatedNcts": [
    "NCT04716231"
  ],
  "company": "Vera Therapeutics",
  "drug": "Atacicept (TRUTAKNA)",
  "indication": "IgA nephropathy",
  "domain": "timing",
  "type": "REVIEW_STATUS",
  "evidence": "SPONSOR_RELEASE",
  "published": "2026-11-05",
  "headline": "Accelerated approval already granted July 7; full-approval sBLA submitted Nov 3",
  "detail": "Vera announced FDA accelerated approval on July 7 2026 and completion of sBLA filing November 3 2026 for full approval based on ORIGIN 3 final efficacy outcomes. No accepted sBLA PDUFA date was stated.",
  "fdaRelevance": "Separates existing approved product from future supplemental full-approval review and prevents fabricated PDUFA dates.",
  "counterpoint": "A submitted sBLA still requires filing acceptance and review; previous accelerated approval does not guarantee traditional approval.",
  "remainingQuestion": "When does FDA accept the sBLA and what review goal and confirmatory-benefit objections apply?",
  "sourceTitle": "Vera November 5 2026 corporate update",
  "sourceUrl": "https://veratherapeutics.gcs-web.com/news-releases/news-release-details/vera-therapeutics-provides-business-update-and-reports-third-3"
},
{
  "id": "zbio-indigo",
  "relatedNcts": [
    "NCT05662241"
  ],
  "company": "Zenas BioPharma",
  "drug": "Obexelimab",
  "indication": "IgG4-related disease",
  "domain": "endpoint",
  "type": "EFFICACY_EVIDENCE",
  "evidence": "PEER_REVIEWED",
  "published": "2026-06-17",
  "headline": "INDIGO peer-reviewed flare-prevention benefit HR 0.44 with fewer steroid rescue doses",
  "detail": "NEJM reports 194 randomized; first disease flare HR 0.44 (95% CI 0.28–0.71, p<0.001); complete remission 37.1% vs 19.6% (p=0.005). Serious AEs 10.3% on obexelimab versus 18.6% placebo in the trial.",
  "fdaRelevance": "Strong disease-flare efficacy and reduced corticosteroid exposure, balanced against immune modulation, infection and generalizability to target organ subtypes.",
  "counterpoint": "Not all long-term immunologic risks can be ruled out from 52 weeks; FDA accepted BLA with May 27 2027 goal, not an approval commitment.",
  "remainingQuestion": "Were flare criteria uniform across organs, and is long-term infection/immune surveillance sufficient?",
  "sourceTitle": "NEJM, Obexelimab for Treatment of IgG4-Related Disease",
  "sourceUrl": "https://www.nejm.org/doi/full/10.1056/NEJMoa2601337"
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
