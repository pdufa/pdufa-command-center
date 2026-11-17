/** Read-only presentation of unvalidated scientific Levels 9–20.
 * The parent loader verifies exact NCT and program identity. This component
 * refuses non-null scores or non-abstaining FDA output, and does not execute.
 */
const object=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==="object"&&!Array.isArray(v);
const methodKeys:Record<number,string>={
  9:"benefitHarmContextComparison",
  10:"standardOfCareContext",
  11:"therapeuticContext",
  12:"replicationCandidates",
  13:"filingContext",
  14:"designationContext",
  15:"precedentContext",
  16:"manufacturingContext",
  17:"disclosureContext",
  18:"challengeContext",
  19:"prospectiveIntegrity",
  20:"outcomeChronology",
};
const numbers=Array.from({length:12},(_,i)=>i+9);
type EvidenceLevel={
 level:number; name:string; status:string; criteria:Record<string,string>;
 score:null;fdaPrediction:"ABSTAIN";scientificValidation:"NOT_VERIFIED";
 methodStatus:string;reviewedCount?:number;[key:string]:unknown;
};
function safeText(v:unknown):v is string{return typeof v==="string"&&v.length>0&&v.length<=240;}
export function validAdvancedScientificLevels(value:unknown):value is Record<string,EvidenceLevel>{
 if(!object(value))return false;
 return numbers.every(n=>{
  const entry=value[String(n)];
  if(!object(entry))return false;
  const criteria=entry.criteria;
  return entry.level===n&&safeText(entry.name)&&safeText(entry.status)&&
   entry.score===null&&entry.fdaPrediction==="ABSTAIN"&&entry.scientificValidation==="NOT_VERIFIED"&&
   safeText(entry.methodStatus)&&entry.methodStatus.startsWith("PARTIAL_")&&
   object(criteria)&&Object.entries(criteria).length>0&&Object.entries(criteria).length<=20&&
   Object.entries(criteria).every(([key,val])=>safeText(key)&&safeText(val))&&
   (entry.reviewedCount===undefined||(Number.isSafeInteger(entry.reviewedCount)&&
    Number(entry.reviewedCount)>=0&&Number(entry.reviewedCount)<=20));
 });
}
function safeMethodStatus(level:EvidenceLevel,n:number):string|null{
 const method=level[methodKeys[n]];
 if(!object(method)||method.score!==null||method.fdaPrediction!=="ABSTAIN"||
    method.scientificValidation!=="NOT_VERIFIED"||!safeText(method.status))
    return null;
 return method.status;
}
export default function ScientificAdvancedLevelsEvidence({value}:{value:unknown}){
 if(!validAdvancedScientificLevels(value))
  return <p>Levels 9–20 source-review contracts unavailable or unverified. No scientific completion or FDA prediction is implied.</p>;
 return <section aria-label="Scientific evidence Levels 9 through 20">
  <h3>Scientific research · Levels 9–20</h3>
  <p>Development-only, partial methods. All scientific scores are NOT_VALIDATED and FDA predictions ABSTAIN. Source-review coverage does not establish clinical validity, official FDA certification, blind forecasting, or owner acceptance.</p>
  {numbers.map(n=>{
   const entry=value[String(n)];
   const method=safeMethodStatus(entry,n);
   return <details key={n}>
    <summary>Level {n}: {entry.name} · {entry.status} · Partial research only</summary>
    <p>Method: {entry.methodStatus}. {method?("Source-bounded method status: "+method+"."):"No accepted method calculation available."} No validated whole-level result.</p>
    {typeof entry.reviewedCount==="number"&&<p>Accepted source-review records: {entry.reviewedCount}. This is coverage, not scientific approval.</p>}
    <ul>{Object.entries(entry.criteria).map(([criterion,state])=>
     <li key={criterion}><strong>{criterion}</strong>: {state}</li>)}</ul>
    {n===19&&<p>Freeze digests are not proof of genuinely blind, immutable, prospective prediction or calibration.</p>}
    {n===20&&<p>Official postdecision outcomes must remain separate from forecasts; reported action dates are not prospective accuracy.</p>}
   </details>;
  })}
 </section>;
}
