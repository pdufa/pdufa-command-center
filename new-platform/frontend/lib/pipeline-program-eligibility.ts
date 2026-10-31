/** Current prospective eligibility is separate from historical research membership. */
export type ProgramIdentity={nctId:string;ticker:string;drug:string;indication:string;sponsor:string};
type Fact<T>={value:T;identity:ProgramIdentity;status:"VERIFIED";sourceUrl:string;publishedAt:string;verifiedAt:string;validUntil:string};
export type ProgramEligibilityEvidence={
 listing?:Fact<{public:boolean;exchangeCountry:string}>;
 marketCap?:Fact<{usd:number}>;
 identity?:Fact<{reconciled:boolean}>;
 pivotal?:Fact<{phase:3;pivotal:boolean;finalReadout:boolean;completed:boolean;publicResultsRelease:string}>;
 fda?:Fact<{relevant:boolean;pdufaDate:string|null}>;
};
const keys=["nctId","ticker","drug","indication","sponsor"] as const;
const day=(s:string)=>{if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return null;const t=Date.parse(s+"T00:00:00Z");return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===s?t/86400000:null;};
export function programEligibility(identity:ProgramIdentity,evidence:ProgramEligibilityEvidence|undefined,today:string){
 const reasons:string[]=[];let rejected=false;const now=day(today);
 if(now===null||!/^NCT\d{8}$/.test(identity.nctId)||keys.some(k=>!identity[k]?.trim()))reasons.push("EXACT_PROGRAM_IDENTITY_MISSING");
 function fact<T>(name:keyof ProgramEligibilityEvidence):T|null{
  const f=evidence?.[name] as Fact<T>|undefined;
  if(!f||f.status!=="VERIFIED"||!f.identity||keys.some(k=>f.identity[k]!==identity[k])||!/^https:\/\/[^\s]+$/.test(f.sourceUrl)
   ||!Number.isFinite(Date.parse(f.verifiedAt))||!Number.isFinite(Date.parse(f.publishedAt))||!Number.isFinite(Date.parse(f.validUntil))
   ||Date.parse(f.publishedAt)>Date.parse(f.verifiedAt)||Date.parse(f.verifiedAt)>Date.parse(today+"T23:59:59Z")
   ||Date.parse(f.validUntil)<Date.parse(today+"T00:00:00Z")){reasons.push(name.toUpperCase()+"_CURRENT_VERIFIED_EVIDENCE_MISSING");return null;}
  return f.value;
 }
 const listing=fact<{public:boolean;exchangeCountry:string}>("listing");
 if(listing&&(listing.public!==true||listing.exchangeCountry!=="US")){rejected=true;reasons.push("PUBLIC_US_LISTING_REQUIRED");}
 const cap=fact<{usd:number}>("marketCap");
 if(cap&&(!Number.isFinite(cap.usd)||cap.usd<300000000||cap.usd>10000000000)){rejected=true;reasons.push("CURRENT_CAP_OUTSIDE_300M_10B");}
 const match=fact<{reconciled:boolean}>("identity");if(match&&match.reconciled!==true)reasons.push("SPONSOR_DRUG_INDICATION_RECONCILIATION_MISSING");
 const phase=fact<{phase:number;pivotal:boolean;finalReadout:boolean;completed:boolean;publicResultsRelease:string}>("pivotal");
 const release=phase?day(phase.publicResultsRelease):null;
 if(phase&&(phase.phase!==3||phase.pivotal!==true||!(phase.completed===true||phase.finalReadout===true)||release===null||now===null||release>now))reasons.push("PUBLIC_FINAL_PIVOTAL_RESULTS_REQUIRED");
 const fda=fact<{relevant:boolean;pdufaDate:string|null}>("fda");
 if(fda&&fda.relevant!==true){rejected=true;reasons.push("US_FDA_RELEVANCE_REQUIRED");}
 const action=fda?.pdufaDate?day(fda.pdufaDate):null;
 let researchWindow:"ACTIVE"|"CUTOFF_REACHED"|"DATES_UNVERIFIED"="DATES_UNVERIFIED";
 if(release!==null&&action!==null&&now!==null&&release<=now&&release<action-3){researchWindow=now<action-3?"ACTIVE":"CUTOFF_REACHED";}
 if(researchWindow!=="ACTIVE")reasons.push(researchWindow);
 return {status:rejected?"REJECTED":reasons.length?"NEEDS_REVIEW":"QUALIFIED",researchWindow,reasons};
}
