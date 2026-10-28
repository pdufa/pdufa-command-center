/** FDA CRL evidence is a review-cycle nonapproval, not a permanent drug failure. */
export type CrlEvidenceInput={applicationNumber:string;letterDate:string;letterType:string;sourceUrl:string;deficiencyCategories:string[];sourceReviewed:boolean};
export type CrlEvidenceReview={status:"NOT_READY"|"READY_FOR_INDEPENDENT_REVIEW";applicationNumber:string;decision:"NONAPPROVAL_THIS_REVIEW_CYCLE"|null;deficiencyCategories:string[];issues:string[]};
export function assessCrlEvidence(input:CrlEvidenceInput,asOf:string):CrlEvidenceReview{
 const issues:string[]=[];const date=Date.parse(input.letterDate),cutoff=Date.parse(asOf);
 if(!/^(NDA|BLA)\d{6}$/i.test(input.applicationNumber))issues.push("Invalid NDA/BLA application number");
 if(!Number.isFinite(date)||!Number.isFinite(cutoff)||date>=cutoff)issues.push("CRL is not verified as pre-cutoff evidence");
 if(input.letterType.trim().toUpperCase()!=="COMPLETE RESPONSE")issues.push("Document is not classified as a complete response letter");
 let sourceOk=false;try{const u=new URL(input.sourceUrl);sourceOk=u.protocol==="https:"&&Boolean(u.hostname)&&/(^|\.)fda\.gov$/.test(u.hostname);}catch{}
 if(!sourceOk)issues.push("Original FDA source URL required");
 if(!input.sourceReviewed)issues.push("Original CRL has not been independently reviewed");
 if(!input.deficiencyCategories.length||input.deficiencyCategories.some(x=>!x.trim()))issues.push("CRL deficiencies have not been categorized");
 return {status:issues.length?"NOT_READY":"READY_FOR_INDEPENDENT_REVIEW",applicationNumber:input.applicationNumber,decision:issues.length?null:"NONAPPROVAL_THIS_REVIEW_CYCLE",deficiencyCategories:input.deficiencyCategories,issues};
}
