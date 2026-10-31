/** Export a *registry-only* evidence intake row for human review in Google Sheets.
 * Fields and order correspond to tab 20 Registry Evidence Intake (A:X).
 * No drug identity, regulatory milestone, therapeutic benefit or eligibility
 * is asserted by an official trial registration alone.
 */
import type { RegistryReview } from "./pipeline-live-registry";
export const REGISTRY_EVIDENCE_HEADERS=[
 "NCT ID","Snapshot Ticker","Snapshot Company","Snapshot Proposed Drug (unverified)",
 "Snapshot Indication (unverified)","Registry Title","Registry Status","Registry Phases",
 "Phase 3 Registered","Registry Completed","Lead Sponsor","Registered Conditions",
 "Registered Interventions","Primary Completion","Last Update Posted","Enrollment",
 "Registry Results Posted","Registry URL","Registry Checked UTC","Therapy Match",
 "Indication Match","Sponsor Name Match","Current Pipeline Qualification",
 "Independent Review Status"
] as const;
export type PinnedRegistryIdentity={nctId:string;ticker:string;company:string};
const canonicalName=(v:string)=>v.trim().replace(/\s+/g," ").toLocaleLowerCase("en-US");
const csvCell=(input:string|number)=>{
 const v=String(input);
 // CSV/Excel formula injection: prefix risky source text with an apostrophe.
 const safe=/^[\s]*[=+@\-]/.test(v)?"'"+v:v;
 return '"'+safe.replaceAll('"','""')+'"';
};
export function registryEvidenceRow(review:RegistryReview,pinned:PinnedRegistryIdentity):(string|number)[]{
 if(!/^NCT\d{8}$/.test(pinned.nctId)||pinned.nctId!==review.nctId
  ||!pinned.ticker.trim()||!pinned.company.trim()
  ||review.qualification!=="NEEDS_REVIEW"
  ||review.sourceUrl!=="https://clinicaltrials.gov/study/"+pinned.nctId
  ||!Number.isFinite(Date.parse(review.verifiedAt))
  ||review.phases.length>20||review.conditions.length>15||review.interventions.length>20)
   throw Error("Registry evidence identity or provenance invalid");
 const sponsorNameOnly=review.leadSponsor&&canonicalName(review.leadSponsor)===canonicalName(pinned.company)
  ?"EXACT_NAME_MATCH_ONLY — RIGHTS NOT VERIFIED":"NEEDS_REVIEW";
 return [
  pinned.nctId,pinned.ticker,pinned.company,"","",
  review.title||"",review.registryStatus||"",review.phases.join("; "),
  review.phase3Registered?"YES — REGISTRY ONLY":"NO / NOT ESTABLISHED",
  review.completedRegistered?"YES — REGISTRY ONLY":"NO",
  review.leadSponsor||"",review.conditions.join("; "),review.interventions.join("; "),
  review.primaryCompletionDate||"",review.lastUpdatePosted||"",
  review.enrollment===null?"":review.enrollment,
  review.resultsPosted?"YES — POSTED":"NOT CONFIRMED",
  review.sourceUrl,review.verifiedAt,"NOT EVALUATED — DRUG NOT VERIFIED",
  "NOT EVALUATED — INDICATION NOT VERIFIED",sponsorNameOnly,
  "NEEDS_REVIEW — NOT QUALIFIED","REVIEW_REQUIRED"
 ];
}
export function renderRegistryEvidenceCsv(review:RegistryReview,pinned:PinnedRegistryIdentity):string {
 const row=registryEvidenceRow(review,pinned);
 if(row.length!==REGISTRY_EVIDENCE_HEADERS.length)throw Error("Evidence schema drift");
 return [REGISTRY_EVIDENCE_HEADERS,row].map(r=>r.map(v=>csvCell(String(v))).join(",")).join("\r\n")+"\r\n";
}
