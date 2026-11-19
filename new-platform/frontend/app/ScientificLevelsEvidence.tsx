/** Scientific review contracts; registry observations never become validated scores. */
type Observation={state:string;observation:unknown;provenance?:{source:string;sourceDate:string;retrievedAt:string;documentType:string;inputSha256:string}|null};
type Level={level:number;name:string;status:string;criteria:Record<string,string>;score:null;scientificValidation:"NOT_VERIFIED";fdaPrediction:"ABSTAIN";descriptiveCalculations?:Record<string,unknown>;registryEvidenceInventory?:Record<string,Observation>;acceptedEvidence?:Record<string,{reviewerId:string;reviewedAt:string;rationale:string;evidenceExcerpt:string;source:string}>};
const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
function validInventory(x:unknown):boolean{
 return x===undefined||(object(x)&&Object.values(x).every(item=>{
  if(!object(item)||typeof item.state!=="string")return false;
  const provenance=item.provenance;
  return provenance===null||provenance===undefined||(object(provenance)&&["source","sourceDate","retrievedAt","documentType","inputSha256"].every(k=>typeof provenance[k]==="string"));
 }));
}
function validReviews(x:unknown):boolean{
 return x===undefined||(object(x)&&Object.values(x).every(item=>object(item)&&["reviewerId","reviewedAt","rationale","evidenceExcerpt","source"].every(k=>typeof item[k]==="string")));
}
function DescriptiveEffect({value}:{value:unknown}){
 if(!object(value))return null;
 if(value.status!=="DESCRIPTIVE_CALCULATION_NOT_VALIDATED_ASSESSMENT")return <p>Descriptive calculation unavailable; reviewed measurements incomplete or rejected.</p>;
 const difference=value.absoluteRiskDifference,ratio=value.riskRatio;
 if(typeof difference!=="number"||!Number.isFinite(difference)||Math.abs(difference)>1||
  (ratio!==null&&(typeof ratio!=="number"||!Number.isFinite(ratio)||ratio<0))||
  value.scientificValidation!=="NOT_VERIFIED"||value.fdaPrediction!=="ABSTAIN")return null;
 return <p>Descriptive event-rate difference: {(difference*100).toFixed(2)} percentage points. Risk ratio: {ratio===null?"undefined (zero comparator events)":ratio.toFixed(3)}. No confidence interval or clinical significance inferred. This is not an FDA probability or a validated assessment score.</p>;
}
export function validScientificLevels(value:unknown):value is Record<string,Level>{
 if(!value||typeof value!=="object"||Array.isArray(value))return false;
 const data=value as Record<string,Level>;
 return [2,3,4,5,6].every(n=>{
  const x=data[String(n)];
  return x?.level===n&&typeof x.name==="string"&&typeof x.status==="string"&&x.score===null&&x.scientificValidation==="NOT_VERIFIED"&&x.fdaPrediction==="ABSTAIN"&&!!x.criteria&&typeof x.criteria==="object"&&!Array.isArray(x.criteria)&&Object.values(x.criteria).every(s=>typeof s==="string")&&validInventory(x.registryEvidenceInventory)&&validReviews(x.acceptedEvidence);
 });
}
export default function ScientificLevelsEvidence({value,selectedLevel}:{value:unknown;selectedLevel?:number}){
 if(!validScientificLevels(value))return <p>Levels 2–6 evidence contracts unavailable or not verified.</p>;
 return <section aria-label="Scientific evidence Levels 2 through 6">
  <h3>Scientific evidence · Levels 2–6</h3>
  <p>Source collection is not scientific validation. Scores NOT_VALIDATED; FDA prediction ABSTAIN.</p>
  {[2,3,4,5,6].filter(n=>selectedLevel===undefined||selectedLevel===n).map(n=>{const level=value[String(n)];return <details key={n} open={selectedLevel===n||undefined}>
   <summary>Level {n}: {level.name} · {level.status}</summary>
   <ul>{Object.entries(level.criteria).map(([criterion,state])=>{
    const observation=level.registryEvidenceInventory?.[criterion];
    const review=level.acceptedEvidence?.[criterion];
    return <li key={criterion}><strong>{criterion}: {state}</strong>
     {observation&&<p>Saved registry inventory: {observation.state}. Metadata requires scientific review.</p>}
     {observation?.provenance&&<p>Source: {observation.provenance.source} · Published {observation.provenance.sourceDate} · Retrieved {observation.provenance.retrievedAt} · {observation.provenance.documentType} · Input SHA-256 {observation.provenance.inputSha256}</p>}
     {review&&<blockquote>{review.evidenceExcerpt}<p>Reviewer {review.reviewerId} · {review.reviewedAt} · {review.rationale} · {review.source}</p></blockquote>}
     {object(level.descriptiveCalculations)&&<DescriptiveEffect value={level.descriptiveCalculations[criterion]}/>}
    </li>;
   })}</ul>
  </details>;})}
 </section>;
}
