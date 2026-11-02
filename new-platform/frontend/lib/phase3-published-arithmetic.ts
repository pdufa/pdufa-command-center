/** Recalculation of published (rounded) placebo-arm arithmetic for two EXACT
 * Phase 3 EMBARQ studies. This is independent arithmetic on sponsor numbers,
 * NOT independent clinical adjudication, a confidence interval, an adjusted
 * odds ratio, an NNT, or a calibrated FDA outcome probability.
 */
import type {BenefitRecord} from "./benefit-assessments";

const release="https://celldex.gcs-web.com/news-releases/news-release-details/celldex-announces-positive-results-phase-3-embarq-csu1-and";
const filedCopy="https://www.sec.gov/Archives/edgar/data/744218/000110465926109465/tm2625892d1_ex99-1.htm";
type Response={active:number;placebo:number};
type RawArm={
 nctId:string;trial:string;totalRandomized:number;
 primary:{active:number;placebo:number};
 week12:Response;week24:Response;
};
const ARMS:readonly RawArm[]=[
 {nctId:"NCT06445023",trial:"EMBARQ-CSU1",totalRandomized:963,
  primary:{active:-20.2,placebo:-10.7},
  week12:{active:42.4,placebo:9.3},week24:{active:49.0,placebo:15.4}},
 {nctId:"NCT06455202",trial:"EMBARQ-CSU2",totalRandomized:976,
  primary:{active:-20.2,placebo:-11.4},
  week12:{active:45.7,placebo:12.6},week24:{active:54.0,placebo:17.6}}
];
export type Phase3ArithmeticCheck={
 nctId:string;trial:string;
 regimen:"150 mg every 4 weeks";
 uas7ExtraReduction:number;
 week12ExtraResponsePp:number;
 week24ExtraResponsePp:number;
 totalRandomized:number;
 issuerUrl:string;filedCopyUrl:string;
 limitations:string[];
};
const oneDecimal=(n:number)=>Math.round((n+Number.EPSILON)*10)/10;
const str=(n:number)=>n.toFixed(1);
export function checkPhase3PublishedArithmetic(record:BenefitRecord|null):Phase3ArithmeticCheck|null{
 if(!record||record.ticker!=="CLDX"||record.drug!=="barzolvolimab"||
  record.indication!=="chronic spontaneous urticaria")return null;
 const raw=ARMS.find(r=>r.nctId===record.nctId);
 if(!raw)return null;
 const facts=record.facts;
 const required=["clinicalBenefit","magnitude","responseRemission","durability"] as const;
 for(const key of required){
  const f=facts[key];
  if(!f||f.status!=="VERIFIED"||f.sourceUrl!==release||
    f.sourceDate!=="2026-09-22"||f.confidence==="LOW")return null;
 }
 const extra=oneDecimal(raw.primary.placebo-raw.primary.active);
 const strings=[
  [facts.clinicalBenefit.value,`${raw.trial} Week 12 UAS7 LS mean change: barzolvolimab 150 mg Q4W ${str(raw.primary.active)} vs placebo ${str(raw.primary.placebo)}`],
  [facts.magnitude.value,`placebo-adjusted LS mean reduction ${str(extra)} points`],
  [facts.responseRemission.value,`150 mg Q4W ${str(raw.week12.active)}% vs placebo ${str(raw.week12.placebo)}%`],
  [facts.durability.value,`Week 12 ${str(raw.week12.active)}% (placebo ${str(raw.week12.placebo)}%); Week 24 ${str(raw.week24.active)}% (placebo ${str(raw.week24.placebo)}%)`]
 ];
 if(strings.some(([actual,expected])=>typeof actual!=="string"||!actual.includes(expected)))return null;
 return {
  nctId:raw.nctId,trial:raw.trial,regimen:"150 mg every 4 weeks",
  uas7ExtraReduction:extra,
  week12ExtraResponsePp:oneDecimal(raw.week12.active-raw.week12.placebo),
  week24ExtraResponsePp:oneDecimal(raw.week24.active-raw.week24.placebo),
  totalRandomized:raw.totalRandomized,
  issuerUrl:release,filedCopyUrl:filedCopy,
  limitations:[
   "Calculated from sponsor-published rounded treatment-arm numbers; no patient-level dataset was accessed.",
   "The SEC exhibit reproduces the issuer's release; it is independent filing retrieval, not independent clinical validation.",
   "Total randomized trial N is reported, but per-arm analyzed denominators and covariance are not supplied here. No NNT, CI, adjusted p-value or pooled cross-trial effect was calculated.",
   "Week 12 and Week 24 response proportions are separate snapshots, not a within-person continuous-response or retention estimate.",
   "No comparator-aligned numerical SAE or discontinuation rates are available in the pinned topline release; no comparative safety grade.",
   "No observed benefit or derived number here establishes an accepted BLA, PDUFA target, FDA approval probability, CRL or extension."
  ]
 };
}
