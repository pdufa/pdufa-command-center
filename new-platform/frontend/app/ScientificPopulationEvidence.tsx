const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
/** Exact program/NCT identity is enforced by the parent loader. No new execution endpoint. */
export default function ScientificPopulationEvidence({value}:{value:unknown}){
 const level=object(value)?value["7"]:null;
 if(!object(level)||level.level!==7||level.score!==null||level.fdaPrediction!=="ABSTAIN"||level.scientificValidation!=="NOT_VERIFIED"||typeof level.status!=="string"||!object(level.criteria)||!Object.values(level.criteria).every(x=>typeof x==="string"))return null;
 const calculations=object(level.calculations)?level.calculations:{};
 const effect=calculations.treatmentSubgroupInteraction;
 const estimate=object(effect)&&effect.fdaPrediction==="ABSTAIN"&&effect.scientificValidation==="NOT_VERIFIED"&&typeof effect.ratioOfRiskRatios==="number"&&Number.isFinite(effect.ratioOfRiskRatios)&&effect.ratioOfRiskRatios>0?effect.ratioOfRiskRatios:null;
 const interval=object(effect)&&object(effect.nominal95Interval)?effect.nominal95Interval:null;
 const bounds=interval&&typeof interval.lower==="number"&&Number.isFinite(interval.lower)&&typeof interval.upper==="number"&&Number.isFinite(interval.upper)&&interval.lower>0&&interval.upper>=interval.lower?interval:null;
 return <section aria-label="Level 7 population and subgroup evidence">
  <h3>Level 7 · Population and subgroup validity</h3>
  <p>{level.status} · Scientific validation NOT_VERIFIED · FDA prediction ABSTAIN</p>
  <ul>{Object.entries(level.criteria).map(([name,status])=><li key={name}>{name}: {String(status)}</li>)}</ul>
  {estimate!==null&&<p>Descriptive ratio of subgroup risk ratios: {estimate.toFixed(3)}.
   {bounds&&` Nominal 95% interval: ${Number(bounds.lower).toFixed(3)}–${Number(bounds.upper).toFixed(3)}.`}
   {" "}Unadjusted for multiplicity. Prespecification and clinical relevance require separate source review. This is not an FDA probability or a validated whole-level assessment.</p>}
  {estimate===null&&<p>No reviewed, estimable subgroup interaction is available. Registry population metadata does not establish generalizability.</p>}
 </section>;
}
