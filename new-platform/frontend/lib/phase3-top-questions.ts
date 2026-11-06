/** Source-linked, pre-readout analytical predictions; never issuer/registry results.
 * Questions 3–30 are intentionally unassigned until the 30-question framework
 * is confirmed. A missing assessment is not a PASS or a FAIL.
 */
export const PHASE3_QUESTION_COUNT=30;
export type Phase3Answer={number:number;heading:string;question:string;prediction:"PASS"|"FAIL"|"UNCERTAIN";summary:string;reason:string;asOf:string;evidenceCutoff:string;sources:readonly {label:string;url:string}[]};
const izar2:readonly Phase3Answer[]=[
 {number:1,heading:"Primary endpoint efficacy",question:"Will the trial achieve its primary efficacy objective?",
  prediction:"PASS",summary:"Predict sonelokimab will outperform placebo on ACR50 at Week 16 in IZAR-2.",
  reason:"The predecessor ARGO Phase 2b trial reported Week 12 ACR50 of 46.3% (60 mg induction) and 46.5% (120 mg induction), versus 20.0% for placebo. IZAR-2 enrolls a more treatment-experienced anti-TNF inadequate-response population, so that effect is not guaranteed to reproduce.",
  asOf:"2026-11-05",evidenceCutoff:"2023-11-05 Phase 2 report, available before IZAR-2 Phase 3 entry",
  sources:[{label:"ARGO results (SEC, 2023)",url:"https://www.sec.gov/Archives/edgar/data/1821586/000162828023036888/mltx-20231105.htm"},
   {label:"IZAR-2 trial registry",url:"https://clinicaltrials.gov/study/NCT06641089"}]},
 {number:2,heading:"Statistical reliability",question:"Is the prior clinical evidence statistically strong enough to predict a positive Phase 3 primary endpoint?",
  prediction:"PASS",summary:"Predict statistical superiority to placebo on the Week 16 ACR50 endpoint.",
  reason:"ARGO's induction groups achieved statistically significant placebo-adjusted ACR50 differences (60 mg: P=0.012; 120 mg: P=0.009), whereas the non-induction 60 mg arm did not (P=0.086). Phase 2 groups were small and only about 17% had previous biologic exposure; the outcome of IZAR-2 remains unknown.",
  asOf:"2026-11-05",evidenceCutoff:"2023–2024 ARGO analyses, before IZAR-2 Phase 3 entry",
  sources:[{label:"ARGO results (Annals of the Rheumatic Diseases, 2024)",url:"https://ard.bmj.com/content/83/Suppl_1/154"},
   {label:"IZAR-2 trial registry",url:"https://clinicaltrials.gov/study/NCT06641089"}]}
];
const PREDICTIONS:Readonly<Record<string,readonly Phase3Answer[]>>={"NCT06641089":izar2};
export type Phase3QuestionSlot={number:number;heading:string;answer:Phase3Answer|null};
export function phase3QuestionSlots(nctId:string):Phase3QuestionSlot[]{
 const known=PREDICTIONS[nctId]||[];
 const byNumber=new Map(known.map(answer=>[answer.number,answer] as const));
 return Array.from({length:PHASE3_QUESTION_COUNT},(_,i)=>{
  const number=i+1,answer=byNumber.get(number)||null;
  return {number,heading:answer?.heading||(
   number===1?"Primary endpoint efficacy":number===2?"Statistical reliability":
   "Heading not yet defined"),answer};
 });
}
export function phase3AnalysisCsvHeaders():string[]{
 return phase3QuestionSlots("").map(q=>"Q"+q.number+" — "+q.heading+" (pre-readout prediction)");
}
export function phase3AnalysisCsvValues(nctId:string):string[]{
 return phase3QuestionSlots(nctId).map(q=>q.answer?
  q.answer.prediction+" — predicted, NOT a reported result; "+q.answer.summary:"");
}
export function phase3CompletedQuestions(nctId:string):number{
 return phase3QuestionSlots(nctId).filter(x=>x.answer).length;
}
