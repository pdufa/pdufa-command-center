const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
export default function ScientificSafetyExposureEvidence({value}:{value:unknown}){
 const level=object(value)?value["8"]:null;
 if(!object(level)||level.level!==8||level.score!==null||level.fdaPrediction!=="ABSTAIN"||level.scientificValidation!=="NOT_VERIFIED"||typeof level.status!=="string"||!object(level.criteria)||!Object.values(level.criteria).every(x=>typeof x==="string"))return null;
 const effect=object(level.calculations)?level.calculations.exposureAdjustedRates:null;
 const valid=object(effect)&&effect.fdaPrediction==="ABSTAIN"&&effect.scientificValidation==="NOT_VERIFIED"&&
  ["PERSON_YEARS","PERSON_MONTHS"].includes(String(effect.exposureUnit))&&Array.isArray(effect.arms)&&effect.arms.every(arm=>object(arm)&&typeof arm.label==="string"&&typeof arm.eventsPer100PersonTimeUnits==="number"&&Number.isFinite(arm.eventsPer100PersonTimeUnits)&&arm.eventsPer100PersonTimeUnits>=0);
 return <section aria-label="Level 8 safety exposure evidence">
  <h3>Level 8 · Safety and tolerability</h3>
  <p>{level.status} · Scientific validation NOT_VERIFIED · FDA prediction ABSTAIN</p>
  <ul>{Object.entries(level.criteria).map(([name,status])=><li key={name}>{name}: {String(status)}</li>)}</ul>
  {valid&&object(effect)&&Array.isArray(effect.arms)?<>
   <ul>{effect.arms.map((arm,index)=><li key={index}>{String(arm.label)}: {Number(arm.eventsPer100PersonTimeUnits).toFixed(3)} events per 100 {String(effect.exposureUnit)}.</li>)}</ul>
   <p>Event rates are not percentages of patients. Exposure comparability, causality, clinical relevance and count-model assumptions require separate review. No FDA probability or validated whole-level assessment is implied.</p>
  </>:<p>No reviewed exposure-rate calculation is available. Person-time cannot be inferred from enrollment.</p>}
 </section>;
}
