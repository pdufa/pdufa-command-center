/** Disease-specific scientific context; never by itself a claim of regulatory deficiency. */
export type ConditionDossier={
  id:string;
  ncts:readonly string[];
  indication:string;
  mechanism:string;
  naturalHistory:string;
  patientOutcomes:string;
  trialInterpretation:string;
  failureFirstQuestions:readonly string[];
  sourceTitle:string;
  sourceUrl:string;
};
export const CONDITION_DOSSIERS:readonly ConditionDossier[]=[
 {
  id:"dmd",ncts:["NCT05126758"],indication:"Duchenne muscular dystrophy",
  mechanism:"Dystrophin deficiency causes progressive skeletal and cardiac muscle damage. Later-stage patients commonly lose upper-limb function and develop cardiac dysfunction.",
  naturalHistory:"Progression varies with age, baseline functional abilities and ambulation; FDA's briefing describes slow, heterogeneous changes in LVEF and measurement variability.",
  patientOutcomes:"Preservation of upper-limb activities, respiratory and cardiac function, independence and survival.",
  trialInterpretation:"PUL 2.0 directly measures arm function, while cardiac imaging evaluates a different treatment claim. A trial not requiring cardiomyopathy at baseline may not fully represent a cardiomyopathy-labeled population.",
  failureFirstQuestions:[
   "Does the proposed indication match the population and clinical endpoints actually studied?",
   "Would results remain persuasive using prespecified analysis plans and credible missing-data methods?",
   "Are one-year changes clinically meaningful relative to disease stage and natural-history decline?",
   "Are cardiac outcomes sufficiently robust given LVEF variability and baseline status?"
  ],
  sourceTitle:"FDA deramiocel July 2026 advisory briefing, disease and trial sections",
  sourceUrl:"https://www.fda.gov/media/193912/download"
 },
 {
  id:"cushing",ncts:["NCT03697109","NCT04308590"],indication:"Cushing syndrome / endogenous hypercortisolism",
  mechanism:"Chronic excess cortisol exposure affects blood pressure, glucose regulation, body composition, bone and cardiovascular function; manifestations vary by patient.",
  naturalHistory:"Symptoms overlap with common conditions, can be heterogeneous, and may be difficult to attribute to a treatment without appropriate diagnosis and controlled comparisons.",
  patientOutcomes:"Sustained improvement in hypertension, glycemic control, weight/body composition, complications and quality of life.",
  trialInterpretation:"A randomized-withdrawal design can demonstrate maintenance of response in selected responders, but the generalizability of enriched patients to the broad target population requires assessment.",
  failureFirstQuestions:[
   "Do the original endpoints and the FDA-requested multicomponent statistical test establish effect across heterogeneous manifestations?",
   "Were selection, responder enrichment, multiplicity and alternative analyses handled rigorously?",
   "Does the resubmission directly resolve the December 2025 efficacy CRL?",
   "Are improvements durable, clinically important and representative of the intended patient population?"
  ],
  sourceTitle:"NIDDK — Cushing syndrome disease description and complications",
  sourceUrl:"https://www.niddk.nih.gov/health-information/endocrine-diseases/cushings-syndrome"
 },
 {
  id:"apap",ncts:["NCT04544293"],indication:"Autoimmune pulmonary alveolar proteinosis",
  mechanism:"Autoantibodies to GM-CSF impair alveolar macrophage function and surfactant clearance, allowing material to accumulate in the lungs and interfere with gas exchange.",
  naturalHistory:"Disease severity and physiology vary. Diffusing capacity and respiratory symptoms need not change identically over time.",
  patientOutcomes:"Better oxygen transfer, respiratory quality of life, exercise capacity, daily functioning and avoidance of pulmonary complications.",
  trialInterpretation:"DLCO is a physiological gas-transfer measure; its improvement should be interpreted alongside patient-reported outcomes, exercise performance, duration, and effect size.",
  failureFirstQuestions:[
   "Does an improvement in DLCO translate into meaningful, sustained patient benefit?",
   "What does the non-significant Week-48 SGRQ total result imply for durability of quality-of-life benefit?",
   "Does the treated study population represent the proposed labeled severity and diagnostic subtype?",
   "Has the major-amendment extension been fully resolved without new disclosed application deficiencies?"
  ],
  sourceTitle:"NCBI Bookshelf — Pulmonary alveolar proteinosis pathology",
  sourceUrl:"https://www.ncbi.nlm.nih.gov/sites/books/NBK482308/"
 },
 {
  id:"gist",ncts:["NCT05208047"],indication:"Gastrointestinal stromal tumor following prior imatinib",
  mechanism:"Many GISTs depend on activating KIT or PDGFRA alterations. Treatment selection and resistance vary by genotype, and tyrosine kinase inhibitors are a central therapy.",
  naturalHistory:"Metastatic or recurrent disease requires sequential systemic therapy. Mutation subtypes may respond differently, and progression is clinically consequential.",
  patientOutcomes:"Delayed tumor progression, quality of life, symptom control, treatment tolerability and ultimately survival.",
  trialInterpretation:"PEAK compares combination therapy against active standard-of-care sunitinib after prior imatinib; its reported PFS advantage is stronger comparative evidence than cross-study contrasts.",
  failureFirstQuestions:[
   "Are benefits consistent across relevant KIT/PDGFRA genotypes and previous treatment histories?",
   "Do safety and tolerability allow patients to receive the combination long enough to sustain benefit?",
   "Are PFS assessments robust, independently reviewed and clinically meaningful?",
   "Do survival and subsequent-treatment data raise any offsetting concerns despite favorable PFS?"
  ],
  sourceTitle:"National Cancer Institute — GIST Treatment (PDQ), kinase variants and sequential TKIs",
  sourceUrl:"https://www.cancer.gov/types/soft-tissue-sarcoma/hp/gist-treatment-pdq"
 }
];
export function conditionForNct(nct:string):ConditionDossier|null{
  if(!/^NCT\d{8}$/.test(nct))return null;
  return CONDITION_DOSSIERS.find(d=>d.ncts.includes(nct))||null;
}
