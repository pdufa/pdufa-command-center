/** FDA APPLICATION / REVIEW CYCLE IDENTITY MAP — read-only, dated source-linked reconstruction.
 * A single trial may support multiple applications and multiple trials may support one application.
 * State is sponsor/document-reported, NOT a confirmed FDA adjudication or recommendation.
 */ 
export type ApplicationCycle = {
 id:string; ticker:string; drug:string; indication:string; ncts:readonly string[];
 applicationType:string;
 stage:"PLANNED"|"PRIOR_CRL_RESUBMISSION_PLANNED"|"SUBMITTED_PENDING_ACCEPTANCE"|"UNDER_REVIEW"|"SUPPLEMENT_UNDER_REVIEW"|"APPROVED_ALREADY";
 reportedGoal:string|null; sourceDate:string; sourceUrl:string; criticalQuestion:string;
};
export const APPLICATION_CYCLES:readonly ApplicationCycle[]=[
  {
    "id": "abvx-uc",
    "ticker": "ABVX",
    "drug": "Obefazimod",
    "indication": "Ulcerative colitis",
    "ncts": [
      "NCT05507203",
      "NCT05507216"
    ],
    "applicationType": "NDA",
    "stage": "PLANNED",
    "reportedGoal": null,
    "sourceDate": "2026-06-01",
    "sourceUrl": "https://abivax.gcs-web.com/news-releases/news-release-details/abivax-announces-landmark-phase-3-abtect-maintenance-trial",
    "criticalQuestion": "Which dose and ABTECT induction/maintenance analyses are in the proposed NDA, and does FDA agree on the full safety package?"
  },
  {
    "id": "achv-cytisinicline",
    "ticker": "ACHV",
    "drug": "Cytisinicline",
    "indication": "Nicotine dependence / smoking cessation",
    "ncts": [
      "NCT04576949",
      "NCT05206370"
    ],
    "applicationType": "NDA",
    "stage": "PRIOR_CRL_RESUBMISSION_PLANNED",
    "reportedGoal": null,
    "sourceDate": "2026-08-11",
    "sourceUrl": "https://ir.achievelifesciences.com/sec-filings/all-sec-filings/content/0001193125-26-344624/achv-20260630.htm",
    "criticalQuestion": "Has replacement manufacturing facility validation and labeling resolved the June 2026 CRL deficiencies?"
  },
  {
    "id": "apmd-ad109",
    "ticker": "APMD",
    "drug": "AD109 (aroxybutynin + atomoxetine)",
    "indication": "Obstructive sleep apnea",
    "ncts": [
      "NCT05811247",
      "NCT05813275"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-02-28",
    "sourceDate": "2026-07-14",
    "sourceUrl": "https://ir.apnimed.com/news-releases/news-release-details/apnimed-announces-fda-acceptance-new-drug-application-ad109",
    "criticalQuestion": "Do dual pivotal AHI effects and intercurrent-event sensitivity outweigh cardiovascular, anticholinergic and adherence concerns?"
  },
  {
    "id": "axsm-axs12",
    "ticker": "AXSM",
    "drug": "AXS-12 (reboxetine)",
    "indication": "Cataplexy in narcolepsy",
    "ncts": [
      "NCT05059223",
      "NCT05113745"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-05-01",
    "sourceDate": "2026-07-15",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1579428/000119312526304039/axsm-ex99_1.htm",
    "criticalQuestion": "Are cataplexy efficacy, long-term safety and relapse findings acceptable for the accepted NDA?"
  },
  {
    "id": "blte-stargardt",
    "ticker": "BLTE",
    "drug": "Tinlarebant",
    "indication": "Stargardt disease type 1",
    "ncts": [
      "NCT05244304"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-02-12",
    "sourceDate": "2026-08-11",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1889109/000110465926094040/tm2622827d1_ex99-1.htm",
    "criticalQuestion": "Is imaging-based retinal lesion-growth benefit sufficiently clinically meaningful and robust, with tolerable ocular adverse effects?"
  },
  {
    "id": "capr-deramiocel",
    "ticker": "CAPR",
    "drug": "Deramiocel",
    "indication": "Duchenne muscular dystrophy",
    "ncts": [
      "NCT05126758"
    ],
    "applicationType": "BLA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2026-11-22",
    "sourceDate": "2026-08-24",
    "sourceUrl": "https://www.capricor.com/investors/news-events/press-releases/detail/354/capricor-therapeutics-announces-extension-of-pdufa-target",
    "criticalQuestion": "Have FDA's documented efficacy/statistical objections and inspection observations been resolved for the refined proposed indication?"
  },
  {
    "id": "cldx-barzolvolimab",
    "ticker": "CLDX",
    "drug": "Barzolvolimab",
    "indication": "Chronic spontaneous urticaria",
    "ncts": [
      "NCT06445023",
      "NCT06455202"
    ],
    "applicationType": "BLA",
    "stage": "PLANNED",
    "reportedGoal": null,
    "sourceDate": "2026-11-05",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/744218/000110465926123322/cldx-20260930x10q.htm",
    "criticalQuestion": "Will durable response, immunologic safety, 52-week follow-up and CMC support the 2027 BLA filing?"
  },
  {
    "id": "cogt-gist",
    "ticker": "COGT",
    "drug": "Bezuclastinib + sunitinib",
    "indication": "GIST after prior imatinib",
    "ncts": [
      "NCT05208047"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2026-11-30",
    "sourceDate": "2026-11-05",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1622229/000119312526449926/cogt-ex99_1.htm",
    "criticalQuestion": "Do safety, mutational subgroup consistency, and manufacturing support approval despite strong PEAK progression-free-survival results?"
  },
  {
    "id": "cort-relacorilant",
    "ticker": "CORT",
    "drug": "Relacorilant",
    "indication": "Cushing syndrome / hypercortisolism",
    "ncts": [
      "NCT03697109",
      "NCT04308590"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2026-12-17",
    "sourceDate": "2026-11-03",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1088856/000162828026069501/cort-20260930.htm",
    "criticalQuestion": "Does FDA's requested global statistical analysis directly cure the prior efficacy CRL?"
  },
  {
    "id": "cytk-aficamten-ohcm",
    "ticker": "CYTK",
    "drug": "MYQORZO (aficamten)",
    "indication": "Obstructive HCM",
    "ncts": [
      "NCT05767346"
    ],
    "applicationType": "NDA",
    "stage": "APPROVED_ALREADY",
    "reportedGoal": null,
    "sourceDate": "2026-11-04",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm",
    "criticalQuestion": "Reconcile FOCUS's recorded November 14 2026 PDUFA event: the oHCM product was approved in December 2025."
  },
  {
    "id": "cytk-aficamten-nhcm",
    "ticker": "CYTK",
    "drug": "Aficamten",
    "indication": "Non-obstructive HCM",
    "ncts": [
      "NCT06081894"
    ],
    "applicationType": "sNDA",
    "stage": "PLANNED",
    "reportedGoal": null,
    "sourceDate": "2026-11-04",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1061983/000119312526447408/cytk-20260930.htm",
    "criticalQuestion": "Will FDA accept a non-obstructive indication despite LVEF reductions and heart-failure event imbalance?"
  },
  {
    "id": "imnm-desmoid",
    "ticker": "IMNM",
    "drug": "Varegacestat",
    "indication": "Progressing desmoid tumors",
    "ncts": [
      "NCT04871282"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-04-28",
    "sourceDate": "2026-08-11",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1472012/000119312526344577/imnm-ex99_1.htm",
    "criticalQuestion": "Do durable PFS benefit and clinical symptom improvement outweigh long-term gamma-secretase inhibitor risks?"
  },
  {
    "id": "mltx-sonelokimab",
    "ticker": "MLTX",
    "drug": "Sonelokimab",
    "indication": "Hidradenitis suppurativa",
    "ncts": [
      "NCT06411379",
      "NCT06411899"
    ],
    "applicationType": "BLA",
    "stage": "SUBMITTED_PENDING_ACCEPTANCE",
    "reportedGoal": null,
    "sourceDate": "2026-11-04",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1821586/000182158626000013/moonlake-pressreleasexq320.htm",
    "criticalQuestion": "Can the application reconcile VELA-2's composite primary p=0.053 and demonstrate consistent FDA-acceptable evidence?"
  },
  {
    "id": "mlys-lorundrostat",
    "ticker": "MLYS",
    "drug": "Lorundrostat",
    "indication": "Resistant or uncontrolled hypertension",
    "ncts": [
      "NCT06153693"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2026-12-22",
    "sourceDate": "2026-11-04",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm",
    "criticalQuestion": "Are clinical blood-pressure effects and aldosterone-related hyperkalemia/renal safety acceptable?"
  },
  {
    "id": "phvs-ondemand",
    "ticker": "PHVS",
    "drug": "Deucrictibant immediate-release",
    "indication": "On-demand hereditary angioedema attacks",
    "ncts": [
      "NCT06343779"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-04-23",
    "sourceDate": "2026-10-08",
    "sourceUrl": "https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-fda-acceptance-new-drug-application",
    "criticalQuestion": "Are repeat-attack efficacy, rescue-medication handling, safety and immediate-release CMC adequate?"
  },
  {
    "id": "phvs-prophylaxis",
    "ticker": "PHVS",
    "drug": "Deucrictibant extended-release",
    "indication": "Prophylaxis of hereditary angioedema attacks",
    "ncts": [
      "NCT06669754"
    ],
    "applicationType": "NDA",
    "stage": "PLANNED",
    "reportedGoal": null,
    "sourceDate": "2026-09-08",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1830487/000119312526384339/phvs-ex99_1.htm",
    "criticalQuestion": "Is the small randomized prevention trial and HAE subtype evidence adequate for a distinct prophylaxis NDA?"
  },
  {
    "id": "prax-ulixacaltamide",
    "ticker": "PRAX",
    "drug": "Ulixacaltamide",
    "indication": "Essential tremor",
    "ncts": [
      "NCT06087276"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-01-29",
    "sourceDate": "2026-08-06",
    "sourceUrl": "https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-provides-corporate-update-and-20",
    "criticalQuestion": "Do pivotal efficacy, adverse effects, CMC and final inspection findings align with favorable mid-cycle feedback?"
  },
  {
    "id": "srpt-casimersen",
    "ticker": "SRPT",
    "drug": "AMONDYS 45 (casimersen)",
    "indication": "DMD mutation amenable to exon 45 skipping",
    "ncts": [
      "NCT02500381"
    ],
    "applicationType": "sNDA",
    "stage": "SUPPLEMENT_UNDER_REVIEW",
    "reportedGoal": "2027-02-28",
    "sourceDate": "2026-11-05",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm",
    "criticalQuestion": "Can total evidence verify benefit for traditional approval despite failed ESSENCE confirmatory primary endpoint?"
  },
  {
    "id": "srpt-golodirsen",
    "ticker": "SRPT",
    "drug": "VYONDYS 53 (golodirsen)",
    "indication": "DMD mutation amenable to exon 53 skipping",
    "ncts": [
      "NCT02500381"
    ],
    "applicationType": "sNDA",
    "stage": "SUPPLEMENT_UNDER_REVIEW",
    "reportedGoal": "2027-02-28",
    "sourceDate": "2026-11-05",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/873303/000119312526449721/srpt-20260930.htm",
    "criticalQuestion": "What consequences follow from failed ESSENCE significance for this separately reviewed exon-skipping product?"
  },
  {
    "id": "svra-molgramostim",
    "ticker": "SVRA",
    "drug": "Molgramostim inhalation solution",
    "indication": "Autoimmune pulmonary alveolar proteinosis",
    "ncts": [
      "NCT04544293"
    ],
    "applicationType": "BLA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2026-11-22",
    "sourceDate": "2026-04-15",
    "sourceUrl": "https://investors.savarapharma.com/news/news-details/2026/Savara-Announces-the-U-S--Food--Drug-Administration-FDA-Has-Extended-the-Review-Period-for-the-Molgramostim-Inhalation-Solution-Molgramostim-Biologics-License-Application-BLA-in-Autoimmune-Pulmonary-Alveolar-Proteinosis-Autoimmune-PAP/default.aspx",
    "criticalQuestion": "Does longer-term disease/function benefit support approval after the already confirmed major-amendment extension?"
  },
  {
    "id": "urgn-ugn103",
    "ticker": "URGN",
    "drug": "UGN-103 (mitomycin)",
    "indication": "Recurrent low-grade intermediate-risk NMIBC",
    "ncts": [
      "NCT06331299"
    ],
    "applicationType": "NDA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-06-14",
    "sourceDate": "2026-11-04",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1668243/000143774926034769/ex_1036873.htm",
    "criticalQuestion": "Does the single-arm response, durability and novel formulation provide adequate efficacy and quality evidence?"
  },
  {
    "id": "vera-trutakna",
    "ticker": "VERA",
    "drug": "TRUTAKNA (atacicept)",
    "indication": "IgA nephropathy",
    "ncts": [
      "NCT04716231"
    ],
    "applicationType": "sBLA",
    "stage": "SUBMITTED_PENDING_ACCEPTANCE",
    "reportedGoal": null,
    "sourceDate": "2026-11-05",
    "sourceUrl": "https://veratherapeutics.gcs-web.com/news-releases/news-release-details/vera-therapeutics-provides-business-update-and-reports-third-3",
    "criticalQuestion": "For an already accelerated-approved product, is the confirmatory ORIGIN 3 evidence sufficient for full approval?"
  },
  {
    "id": "zbio-obexelimab",
    "ticker": "ZBIO",
    "drug": "Obexelimab",
    "indication": "IgG4-related disease",
    "ncts": [
      "NCT05662241"
    ],
    "applicationType": "BLA",
    "stage": "UNDER_REVIEW",
    "reportedGoal": "2027-05-27",
    "sourceDate": "2026-11-05",
    "sourceUrl": "https://www.sec.gov/Archives/edgar/data/1953926/000110465926123040/zbio-20260930x10q.htm",
    "criticalQuestion": "Does flare reduction remain persuasive across organ systems and does long-term immunologic safety support approval?"
  }
] as const;
export function applicationsForNct(nct:string):ApplicationCycle[]{
 return /^NCT\d{8}$/.test(nct)?APPLICATION_CYCLES.filter(x=>x.ncts.includes(nct)):[];
}
export const CYCLE_COUNTS={
 total:APPLICATION_CYCLES.length,
 underReview:APPLICATION_CYCLES.filter(x=>x.stage==="UNDER_REVIEW"||x.stage==="SUPPLEMENT_UNDER_REVIEW").length,
 planned:APPLICATION_CYCLES.filter(x=>x.stage==="PLANNED").length,
 pendingAcceptance:APPLICATION_CYCLES.filter(x=>x.stage==="SUBMITTED_PENDING_ACCEPTANCE").length,
 priorCrlPlannedResubmission:APPLICATION_CYCLES.filter(x=>x.stage==="PRIOR_CRL_RESUBMISSION_PLANNED").length,
 alreadyApproved:APPLICATION_CYCLES.filter(x=>x.stage==="APPROVED_ALREADY").length
};
