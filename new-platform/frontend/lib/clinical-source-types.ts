/** Minimal retired-feed compatibility for shared registry/clinical views.
 * No 1–20 survey catalog, questions, data loading, or background collection.
 */
export type BenefitFact={
  value:string|number;status:"VERIFIED"|"MODELED";sourceUrl:string;
  sourceDate:string;method:string;confidence:"HIGH"|"MODERATE"|"LOW"
};
export type BenefitRecord={
  nctId:string;ticker:string;drug:string;indication:string;
  facts:Record<string,BenefitFact>;
};
export type BenefitFeed={schemaVersion:1;sourceAsOf:string|null;records:BenefitRecord[]};
/** Explicitly no survey groups remain installed. */
export const BENEFIT_GROUPS:readonly {number:number;fields:readonly {id:string;label:string}[]}[]=[];
export function benefitForTrial(
  _feed:BenefitFeed|null,
  _trial:{nctId:string;ticker:string;drug:string|null;indication:string|null}
):BenefitRecord|null{return null;}
