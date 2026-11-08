/** Clinically specialized, disease-specific evidence review lenses.
 * Inspired by the kinds of questions a relevant clinical subspecialist would ask,
 * NOT authored or signed off by a licensed medical professional.
 * Source questions are unreviewed until their linked trial/clinical evidence is adjudicated.
 */ 
export type ClinicalSpecialtyProfile={
 id:string;specialty:string;mechanism:string;clinicalContext:string;
 meaningfulOutcomes:string;subgroups:string;seriousRisks:string;coreChallenge:string;
};
export type ClinicalSpecialtyAxis={id:number;name:string;clinicalQuestion:string};
export const CLINICAL_SPECIALTY_PROFILES:readonly ClinicalSpecialtyProfile[]=[
  {
    "id": "neuromuscular",
    "specialty": "Neuromuscular medicine / pediatric neurology",
    "mechanism": "Dystrophinopathy and motor-function trajectory",
    "clinicalContext": "Longitudinal stage of DMD, ambulatory status, upper-limb reserve, cardiomyopathy and respiratory weakness",
    "meaningfulOutcomes": "PUL 2.0 changes relative to natural progression and patient-important hand/arm tasks; distinguish cardiac LVEF claim from upper-limb effect",
    "subgroups": "Age, steroid exposure, ambulatory status, genotype, baseline cardiac function and ventilation",
    "seriousRisks": "Loss of independently valued functions, cardiac deterioration, ventilatory decline and treatment-related infusion burden",
    "coreChallenge": "Are the responder population and prespecified PUL effects clinically meaningful for the precise proposed indication?"
  },
  {
    "id": "endocrinology",
    "specialty": "Endocrinology / pituitary-adrenal disease",
    "mechanism": "Cortisol excess and multisystem organ injury",
    "clinicalContext": "Biochemical etiology, degree and duration of cortisol exposure, comorbidity burden and reversibility of complications",
    "meaningfulOutcomes": "Blood pressure, glycemia, body weight, quality of life and biochemical control as distinct outcomes; consider withdrawal-enriched trial inference",
    "subgroups": "Etiology, adrenal tumor status, diabetes, cardiovascular risk and baseline hypertension",
    "seriousRisks": "Adrenal insufficiency, medication interactions, persistence of comorbidities and recurrence",
    "coreChallenge": "Does the total treatment effect improve clinically important hypercortisolism manifestations beyond selected responders?"
  },
  {
    "id": "gastroenterology",
    "specialty": "Gastroenterology / inflammatory bowel disease",
    "mechanism": "Immune-mediated intestinal inflammation",
    "clinicalContext": "Disease extent, endoscopy/histology, steroid exposure, baseline severity and previous biologic failures",
    "meaningfulOutcomes": "Clinical remission defined by stool frequency, rectal bleeding, endoscopy and durable steroid-free outcomes",
    "subgroups": "Prior JAK/biologic exposure, disease location, extraintestinal manifestations and dosing",
    "seriousRisks": "Serious infections, thrombotic risks where mechanism-relevant, adverse-event withdrawals and maintenance failures",
    "coreChallenge": "Does the selected dose deliver durable, clinically important remission in refractory disease with acceptable risk?"
  },
  {
    "id": "surgical-oncology",
    "specialty": "Sarcoma medical oncology / gastrointestinal tumor oncology",
    "mechanism": "KIT/PDGFRA-driven gastrointestinal stromal tumors or desmoid biology",
    "clinicalContext": "Genotype, progression kinetics, metastatic burden, prior-line failure and symptoms",
    "meaningfulOutcomes": "PFS, objective response, symptom relief, survival maturity and radiographic adjudication",
    "subgroups": "KIT exon mutations, PDGFRA variants, secondary resistance mutations and organ involvement",
    "seriousRisks": "Liver injury, dose intensity, treatment discontinuation and quality-of-life tradeoffs",
    "coreChallenge": "Is the magnitude of progression control worth the added toxicity compared with the active standard treatment?"
  },
  {
    "id": "pulmonology",
    "specialty": "Pulmonology / rare interstitial lung disease",
    "mechanism": "Surfactant accumulation with impaired alveolar macrophage function",
    "clinicalContext": "DLCO impairment, hypoxemia, exercise tolerance, radiographic severity and autoimmune PAP diagnosis",
    "meaningfulOutcomes": "Meaningful change in gas transfer, breathlessness, exercise function, patient-reported outcomes and durability",
    "subgroups": "Baseline diffusion deficit, oxygen need, infection burden and mild versus severe disease",
    "seriousRisks": "Inhaled-drug tolerability, infections, immunogenicity and inadequate functional response",
    "coreChallenge": "Does the physiological improvement translate into sustained, patient-important respiratory benefit?"
  },
  {
    "id": "sleep-medicine",
    "specialty": "Sleep medicine / pulmonary medicine",
    "mechanism": "Sleep-disordered breathing and upper-airway obstruction",
    "clinicalContext": "Baseline apnea-hypopnea index, obesity, sleepiness, hypoxia and cardiometabolic comorbidities",
    "meaningfulOutcomes": "AHI treatment-policy and on-treatment estimands, oxygen desaturation and symptom/function improvement",
    "subgroups": "OSA severity, BMI, CPAP tolerance, adherence and comorbid hypertension",
    "seriousRisks": "Anticholinergic toxicity, cardiovascular effects, insomnia and dropout-related bias",
    "coreChallenge": "Does AHI improvement represent a durable, real-world benefit for patients who actually take the drug?"
  },
  {
    "id": "addiction",
    "specialty": "Addiction medicine / tobacco treatment",
    "mechanism": "Nicotine dependence and relapse biology",
    "clinicalContext": "Nicotine exposure, withdrawal severity, quit history, psychiatric comorbidity and cessation support",
    "meaningfulOutcomes": "Biochemically validated sustained abstinence, relapse and real-world quit rates",
    "subgroups": "Baseline dependence, smoking patterns, mental health and concurrent behavioral therapy",
    "seriousRisks": "Neuropsychiatric effects, discontinuation, adherence and medication availability",
    "coreChallenge": "Do sustained verified cessation outcomes outweigh safety risk, and are manufacturing blockers independently resolved?"
  },
  {
    "id": "neurology-sleep",
    "specialty": "Neurology / sleep disorders",
    "mechanism": "Narcolepsy and cataplexy neurophysiology",
    "clinicalContext": "Cataplexy phenomenology, baseline episode counts, comorbid sleepiness and functional impairment",
    "meaningfulOutcomes": "Attack-frequency change, responder thresholds, daytime function and durable control",
    "subgroups": "Narcolepsy type, concomitant stimulants, depression/anxiety and sleep habits",
    "seriousRisks": "Mood changes, cardiovascular effects, sleep disruption and withdrawal/rebound",
    "coreChallenge": "Does cataplexy reduction translate into safer daily activity and reliably improve life beyond selective diary metrics?"
  },
  {
    "id": "retina",
    "specialty": "Retina / inherited retinal disease",
    "mechanism": "Retinal degeneration and Stargardt disease",
    "clinicalContext": "ABCA4 status, age of onset, lesion location, foveal involvement, baseline acuity and disease stage",
    "meaningfulOutcomes": "Atrophic-lesion growth versus visual acuity, reading capacity, night vision and patient-perceived function",
    "subgroups": "Genotype, foveal sparing, lesion burden, age and both-eye correlation",
    "seriousRisks": "Xanthopsia, dark adaptation, vitamin A pathway and longer-term visual function",
    "coreChallenge": "Does slowing a structural retinal lesion demonstrate meaningful preservation of visual function?"
  },
  {
    "id": "allergy-immunology",
    "specialty": "Allergy / clinical immunology",
    "mechanism": "IgE-mediated disease, mast-cell function or immune regulation",
    "clinicalContext": "Biomarkers, phenotype, baseline attacks, prior therapies and treatment resistance",
    "meaningfulOutcomes": "Disease-specific activity score, flare rate, time to relief, steroid sparing and quality of life",
    "subgroups": "Trigger patterns, complement or organ subtype, atopic comorbidity and prior biologic response",
    "seriousRisks": "Infections, immunoglobulin suppression, hypersensitivity and immunogenicity",
    "coreChallenge": "Are reductions in attacks/flares durable, clinically important and supported across the intended immune phenotypes?"
  },
  {
    "id": "cardiology",
    "specialty": "Cardiology / hypertrophic cardiomyopathy",
    "mechanism": "Myocardial contractility, obstruction and heart failure",
    "clinicalContext": "Obstructive versus non-obstructive pathophysiology, NYHA class, LVEF and exercise limitation",
    "meaningfulOutcomes": "Exercise capacity, KCCQ quality of life, gradient reduction, clinical events and preserved systolic function",
    "subgroups": "Baseline ejection fraction, arrhythmias, genetic substrate and background beta blockers",
    "seriousRisks": "Systolic dysfunction, heart-failure hospitalizations, arrhythmias and dose titration",
    "coreChallenge": "Does symptomatic benefit outweigh the risk of reduced contractility in the precise HCM phenotype?"
  },
  {
    "id": "hypertension",
    "specialty": "Cardiology / hypertension and nephrology",
    "mechanism": "Aldosterone-mediated blood pressure dysregulation",
    "clinicalContext": "Resistant versus uncontrolled BP, medication adherence, CKD, obesity and secondary causes",
    "meaningfulOutcomes": "24-hour ambulatory systolic BP, office BP, achieved clinical thresholds and durability",
    "subgroups": "Baseline eGFR, serum potassium, RAAS medications and resistant-hypertension definition",
    "seriousRisks": "Hyperkalemia, renal deterioration, hypotension and concomitant antihypertensives",
    "coreChallenge": "Is BP lowering sustained and clinically relevant with acceptable electrolyte and renal safety in CKD patients?"
  },
  {
    "id": "dermatology",
    "specialty": "Dermatology / inflammatory skin disease",
    "mechanism": "Hidradenitis suppurativa immune inflammation",
    "clinicalContext": "Hurley stage, lesion location, draining tunnels, scarring, pain and relapse",
    "meaningfulOutcomes": "HiSCR75 treatment-policy versus composite estimands, abscess/nodule count, pain and patient function",
    "subgroups": "Baseline tunnels, prior biologic failure, BMI and disease duration",
    "seriousRisks": "Infection, immunogenicity, adverse-event discontinuations and treatment burden",
    "coreChallenge": "Does a marginal primary endpoint across the two pivotal trials reliably improve real-world HS suffering?"
  },
  {
    "id": "neurology-movement",
    "specialty": "Movement disorders neurology",
    "mechanism": "Essential tremor and action tremor disability",
    "clinicalContext": "Action versus rest tremor, dystonia/Parkinson differential, severity and daily activities",
    "meaningfulOutcomes": "Functional activities, standardized tremor scales, clinician ratings and sustained benefit",
    "subgroups": "Baseline severity, alcohol/propranolol or primidone use, age and comorbid neurologic symptoms",
    "seriousRisks": "Sedation, balance, cognitive effects, interaction with background therapy",
    "coreChallenge": "Is the measured tremor improvement large enough to change actual daily function without unacceptable CNS harms?"
  },
  {
    "id": "uro-oncology",
    "specialty": "Urologic oncology",
    "mechanism": "Recurrent low-grade non-muscle-invasive bladder cancer",
    "clinicalContext": "Recurrence frequency, tumor grade, prior resections, disease risk stratification and surveillance burden",
    "meaningfulOutcomes": "Complete response at 3 months, recurrence-free duration and patient-important avoidance of repeated procedures",
    "subgroups": "Prior intravesical therapy, multifocal disease, recurrence density and histologic confirmation",
    "seriousRisks": "Chemical cystitis, dysuria, urinary infections and novel formulation administration",
    "coreChallenge": "Can a single-arm response and durability package support the precise recurrence indication and acceptable safety?"
  },
  {
    "id": "nephrology",
    "specialty": "Nephrology / glomerular disease",
    "mechanism": "IgA nephropathy and progressive glomerular inflammation",
    "clinicalContext": "Proteinuria, eGFR, histologic features, CKD stage, background supportive care",
    "meaningfulOutcomes": "Confirmed eGFR slope, kidney failure outcomes, proteinuria as surrogate and long-term kidney protection",
    "subgroups": "Baseline eGFR, proteinuria severity, immunoglobulin function, regional care patterns",
    "seriousRisks": "Infection, hypogammaglobulinemia, edema and longer-term immunomodulation risk",
    "coreChallenge": "Do confirmatory kidney function outcomes justify full approval beyond proteinuria surrogate improvement?"
  }
] as const;
export const CLINICAL_SPECIALTY_ASSIGNMENTS:Readonly<Record<string,string>>={
  "abvx-uc": "gastroenterology",
  "achv-cytisinicline": "addiction",
  "apmd-ad109": "sleep-medicine",
  "axsm-axs12": "neurology-sleep",
  "blte-stargardt": "retina",
  "capr-deramiocel": "neuromuscular",
  "cldx-barzolvolimab": "allergy-immunology",
  "cogt-gist": "surgical-oncology",
  "cort-relacorilant": "endocrinology",
  "cytk-aficamten-ohcm": "cardiology",
  "cytk-aficamten-nhcm": "cardiology",
  "imnm-desmoid": "surgical-oncology",
  "mltx-sonelokimab": "dermatology",
  "mlys-lorundrostat": "hypertension",
  "phvs-ondemand": "allergy-immunology",
  "phvs-prophylaxis": "allergy-immunology",
  "prax-ulixacaltamide": "neurology-movement",
  "srpt-casimersen": "neuromuscular",
  "srpt-golodirsen": "neuromuscular",
  "svra-molgramostim": "pulmonology",
  "urgn-ugn103": "uro-oncology",
  "vera-trutakna": "nephrology",
  "zbio-obexelimab": "allergy-immunology"
} as const;
export const CLINICAL_SPECIALTY_AXES:readonly ClinicalSpecialtyAxis[]=[
  {
    "id": 1,
    "name": "Clinical phenotype and differential diagnosis",
    "clinicalQuestion": "Does enrollment accurately represent the clinical disease and exclude look-alike conditions?"
  },
  {
    "id": 2,
    "name": "Mechanism and disease-specific plausibility",
    "clinicalQuestion": "Does target engagement connect causally to a change in clinically important disease progression?"
  },
  {
    "id": 3,
    "name": "Clinical treatment algorithm",
    "clinicalQuestion": "Where would this medicine sit relative to existing first-, second-, or later-line treatments?"
  },
  {
    "id": 4,
    "name": "Outcome validity and patient importance",
    "clinicalQuestion": "Does the outcome measure reflect something patients feel, do, avoid, or survive?"
  },
  {
    "id": 5,
    "name": "Subgroup selection and heterogeneity",
    "clinicalQuestion": "Which clinical phenotypes should benefit or be exposed to excess harm?"
  },
  {
    "id": 6,
    "name": "Magnitude and duration of benefit",
    "clinicalQuestion": "Are the absolute treatment differences, confidence intervals and duration meaningful clinically?"
  },
  {
    "id": 7,
    "name": "Serious harms and practical manageability",
    "clinicalQuestion": "Are high-grade toxicity, discontinuations, drug interactions and monitoring burdens acceptable?"
  },
  {
    "id": 8,
    "name": "Alternative explanations and real-world fit",
    "clinicalQuestion": "Can selection, missing data, open-label enrichment or spontaneous disease fluctuation explain the effect?"
  },
  {
    "id": 9,
    "name": "Independent specialty challenge",
    "clinicalQuestion": "How would a skeptical disease specialist rebut the sponsor's strongest clinical claim?"
  },
  {
    "id": 10,
    "name": "FDA benefit-risk translation",
    "clinicalQuestion": "Which clinical deficiencies plausibly change indication, label, REMS, CRL or review timing?"
  }
] as const;
export const CLINICAL_SPECIALTY_STANDARDS=[
  {
    "title": "FDA clinical outcome assessment roadmap",
    "url": "https://www.fda.gov/drugs/drug-development-tool-ddt-qualification-programs/roadmap-patient-focused-outcome-measurement-clinical-trials-text-version"
  },
  {
    "title": "FDA patient-focused clinical outcome assessment guidance (final)",
    "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/patient-focused-drug-development-selecting-developing-or-modifying-fit-purpose-clinical-outcome"
  },
  {
    "title": "FDA/ICH E9(R1) estimands and sensitivity analysis",
    "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/e9r1-statistical-principles-clinical-trials-addendum-estimands-and-sensitivity-analysis-clinical"
  }
] as const;
export function getSpecialtyProfile(cycleId:string):ClinicalSpecialtyProfile|null{
 const specialty=CLINICAL_SPECIALTY_ASSIGNMENTS[cycleId];
 return CLINICAL_SPECIALTY_PROFILES.find(p=>p.id===specialty)||null;
}
export type SpecialistResearchTask={
 id:string;axis:number;status:"NOT_CLINICALLY_ADJUDICATED";
 prompt:string;requiredEvidence:string;potentialFdaConsequence:string;
};
export function getSpecialtyTasks(cycleId:string):SpecialistResearchTask[]{
 const p=getSpecialtyProfile(cycleId);
 if(!p)return [];
 const evidence=[
 p.clinicalContext,p.mechanism,p.meaningfulOutcomes,p.subgroups,p.seriousRisks,
 "Individual primary and secondary outcome tables; full protocol and SAP; medical literature",
 "Time-on-treatment, effect magnitude, confidence intervals and patient-important outcomes",
 "Adjudicated serious events, withdrawal patterns, comparator matching and clinical pathway",
 "Independent competing hypotheses; FDA and sponsor discrepancies; validated clinical guidelines",
 "FDA benefit-risk review, current application-cycle correspondence, integrated clinical evidence"
 ];
 return CLINICAL_SPECIALTY_AXES.map((a,i)=>({
  id:cycleId+":S"+a.id,axis:a.id,status:"NOT_CLINICALLY_ADJUDICATED" as const,
  prompt:a.clinicalQuestion+" Specialist-specific question: "+p.coreChallenge,
  requiredEvidence:evidence[i],
  potentialFdaConsequence:"Assess whether a confirmed issue is relevant to efficacy, safety, labeling, current-cycle CRL, or review timing; do not infer an FDA deficiency from uncertainty alone."
 }));
}
