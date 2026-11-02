/** Evidence-backed rating-input audit for Step 5.
 * It reports what is source-supported, NEVER a clinical superiority grade,
 * trading prediction or a comparable investment rank.
 * Do not equate a source count with positive benefit or greater stock upside.
 */
import {BENEFIT_GROUPS,benefitForTrial,type BenefitFeed,type BenefitFact} from "./benefit-assessments";
import {competitiveReadiness,type CompetitiveResearchTrial} from "./tools-competitive-readiness";
import type {RegistrySourceRow} from "./registry-benefit-coverage";

export type RatingGroupKey="M"|"A"|"B"|"C"|"D"|"E";
export type RatingIngredientKey="VER"|"MOD"|"MISS"|"CRIT"|"ER"|"FDA"|
 "CL"|"SAF"|"COMP"|"POP"|"ACCESS"|"REV"|"VAL"|"CASH"|"MOM"|"FLOW"|"CAT"|
 "APP"|"READY"|"GRADE";
export type EvidenceLink={field:string;status:BenefitFact["status"];url:string;date:string};
export type RatingAuditCell={
  label:string;explanation:string;kind:"count"|"coverage"|"status"|"unscored";
  links:EvidenceLink[];
};
export type RatingAudit={
  group:Record<RatingGroupKey,RatingAuditCell>;
  ingredient:Record<RatingIngredientKey,RatingAuditCell>;
  eligibleForInvestmentRanking:false;
  sourceRecordPresent:boolean;
  evidenceFeedAvailable:boolean;
  verifiedFields:number;modeledFields:number;missingFields:number;totalFields:number;
};
const allFields=[...new Set(BENEFIT_GROUPS.flatMap(group=>group.fields.map(field=>field.id)))];
const groupFields=(...numbers:number[])=>[...new Set(
  BENEFIT_GROUPS.filter(g=>numbers.includes(g.number)).flatMap(g=>g.fields.map(f=>f.id))
)];
const keys={
 CL:groupFields(3,4,5),SAF:groupFields(8),COMP:groupFields(6),
 POP:groupFields(1,2,13),ACCESS:groupFields(9,10,11,12),
 REV:groupFields(14,15,16),VAL:groupFields(19,20)
} as const;
const input=(label:string,explanation:string,kind:RatingAuditCell["kind"]="status",links:EvidenceLink[]=[]):RatingAuditCell=>
 ({label,explanation,kind,links});
const noScore=(why:string)=>input("N/A",why,"unscored");
const factLinks=(facts:Record<string,BenefitFact>,fields:readonly string[]):EvidenceLink[]=>fields.flatMap(field=>{
  const fact=facts[field];return fact?[{field,status:fact.status,url:fact.sourceUrl,date:fact.sourceDate}]:[];
});
/** A source receipt requires exact NCT+ticker+therapy+indication, and a
 * server-validated fact. A missing feed is NOT counted as zero evidence. */
export function auditTrialRatings(
  row:CompetitiveResearchTrial,today:string,feed:BenefitFeed|null,
  feedUnavailable=false,registry:RegistrySourceRow|null=null
):RatingAudit{
  const matched=benefitForTrial(feed,row);
  const facts=matched?.facts||{};
  const observed=factLinks(facts,allFields);
  const verified=observed.filter(x=>x.status==="VERIFIED").length;
  const modeled=observed.filter(x=>x.status==="MODELED").length;
  const missing=allFields.length-verified-modeled;
  const readiness=competitiveReadiness(row,today,feed);
  const absent=feedUnavailable?"Research feed unavailable; evidence completeness cannot be established.":
    "Research data not recorded for this exact trial; missing is not a failed outcome.";
  const coverage=(fields:readonly string[],name:string):RatingAuditCell=>{
    const found=factLinks(facts,fields);
    const good=found.filter(x=>x.status==="VERIFIED").length;
    const modeled=found.filter(x=>x.status==="MODELED").length;
    return found.length?input(good+"/"+fields.length+" verified",
      name+": "+good+" source-verified, "+modeled+" modeled, "+
      (fields.length-good-modeled)+" missing. Evidence coverage only, NOT a score or positive outcome.",
      "coverage",found):noScore(name+": "+absent);
  };
  // Registry measures are independently source-recorded *observations*.
  // Do not count them as efficacy, safety superiority, head-to-head findings,
  // a public sponsor readout date or verified commercial differentiation.
  const registryLink=registry?.resultsPosted?{
    field:"ClinicalTrials.gov posted results (not comparative superiority)" as const,
    status:"VERIFIED" as const,
    url:"https://clinicaltrials.gov/study/"+row.nctId,
    date:registry.retrievedAt.slice(0,10)
  }:null;
  const clinical=coverage(keys.CL,"Medical and clinical benefit");
  const safety=coverage(keys.SAF,"Safety");
  const primary=registry?.resultsPosted&&registry.measuredPrimary&&!registry.truncated;
  const serious=registry?.resultsPosted&&registry.measuredSeriousEvents&&!registry.truncated;
  const clinicalInput:RatingAuditCell=clinical.kind!=="unscored"?{
    ...clinical,
    explanation:clinical.explanation+(primary?
      " ClinicalTrials.gov also has measured primary outcomes; interpreting efficacy still requires trial-specific review.":""),
    links:registryLink&&primary?[...clinical.links,registryLink]:clinical.links
  }:primary&&registryLink?input("Registry data",
    registry.primaryOutcomeCount+" primary outcome(s) recorded in ClinicalTrials.gov as of "+
    registry.retrievedAt.slice(0,10)+". Measurements are available but have NOT been clinically adjudicated; no comparative advantage is established.",
    "coverage",[registryLink]):clinical;
  const safetyInput:RatingAuditCell=safety.kind!=="unscored"?{
    ...safety,
    explanation:safety.explanation+(serious?
      " Registry serious-adverse-event counts are available, not comparative safety superiority.":""),
    links:registryLink&&serious?[...safety.links,registryLink]:safety.links
  }:serious&&registryLink?input("Registry AEs",
    registry.seriousEventTerms+" serious-adverse-event term(s) recorded; counts require comparable exposure and adjudication. NOT a safety advantage.",
    "coverage",[registryLink]):safety;
  const unsupported=(name:string)=>noScore(name+": no validated source-linked rating inputs are mapped yet.");
  const critical=[
    !/^NCT\d{8}$/.test(row.nctId)||!row.ticker.trim()||!row.drug.trim()||!row.indication.trim()
      ?"Exact NCT, company, drug and indication identity incomplete":null,
    readiness.status==="NO_VERIFIED_PUBLIC_READOUT"?"Public Phase 3 results release not verified":null,
    readiness.status==="PDUFA_DATE_UNVERIFIED"?"Exact-program PDUFA date not verified":null,
    readiness.status==="PDUFA_CUTOFF_REACHED"?"PDUFA-minus-three-day cutoff reached":null,
  ].filter((v):v is string=>!!v);
  const ingredients:Record<RatingIngredientKey,RatingAuditCell>={
    VER:input(feedUnavailable?"Unavailable":String(verified),
      feedUnavailable?absent:verified+" verified source fields for an exact-matched research identity.","count",
      observed.filter(x=>x.status==="VERIFIED")),
    MOD:input(feedUnavailable?"Unavailable":String(modeled),
      feedUnavailable?absent:modeled+" modeled fields; modeled values are not verified trial results.","count",
      observed.filter(x=>x.status==="MODELED")),
    MISS:input(feedUnavailable?"Unavailable":String(missing),
      feedUnavailable?absent:missing+" of "+allFields.length+" supporting research fields lack valid evidence.","count"),
    CRIT:input(String(critical.length)+" gaps",critical.length?critical.join("; "):
      "No readout or date-gate gaps observed; independent pivotal, market-cap and commercial-rights checks remain outstanding.","status"),
    ER:input(feedUnavailable?"Unavailable":verified+"/"+allFields.length,
      feedUnavailable?absent:verified+" verified, "+modeled+" modeled and "+missing+
        " missing research fields. This measures source coverage, not scientific strength.","coverage",observed),
    FDA:input(readiness.daysToPdufa===null?"Date unknown":readiness.daysToPdufa+" days",
      readiness.daysToPdufa===null?"No exact-program PDUFA date verified; FDA decision readiness is not assessed.":
      "Source-recorded days to PDUFA, not an FDA decision readiness score.","status",
      row.timeline?.pdufaTarget?[{field:"pdufaTarget",status:"VERIFIED",
        url:row.timeline.pdufaTarget.sourceUrl,date:row.timeline.pdufaTarget.date}]:[]),
    CL:clinicalInput,SAF:safetyInput,
    COMP:coverage(keys.COMP,"Competitor-specific differentiation"),
    POP:coverage(keys.POP,"Patient opportunity"),ACCESS:coverage(keys.ACCESS,"Commercial access"),
    REV:coverage(keys.REV,"Revenue opportunity"),VAL:coverage(keys.VAL,"Valuation and shareholder risk"),
    CASH:unsupported("Financial strength"),MOM:unsupported("Stock momentum"),
    FLOW:unsupported("Ownership and trading"),
    CAT:input(readiness.daysToPdufa===null?"N/A":"PDUFA dated",
      "A verified FDA target date is one catalyst input, not a complete catalyst strength rating.",
      readiness.daysToPdufa===null?"unscored":"status",
      row.timeline?.pdufaTarget?[{field:"pdufaTarget",status:"VERIFIED",
        url:row.timeline.pdufaTarget.sourceUrl,date:row.timeline.pdufaTarget.date}]:[]),
    APP:unsupported("Appreciation potential"),
    READY:input(readiness.status==="RESEARCH_WINDOW_OPEN"?
       (readiness.verifiedTopics===6?"Evidence review":"Partial research"):
       "Not qualified",readiness.reasons.join("; ")+"; readiness does not establish expected stock appreciation.","status"),
    GRADE:unsupported("Final stock opportunity grade")
  };
  const groupCoverage=(ingredientKeys:readonly RatingIngredientKey[],groupName:string)=>{
    const count=ingredientKeys.filter(k=>ingredients[k].kind!=="unscored").length;
    return count?input(count+"/"+ingredientKeys.length+" inputs",
      groupName+": "+count+" component(s) have source coverage or a timeline status. "+
      "Do not interpret this as a clinical or investment score.","coverage",
      ingredientKeys.flatMap(k=>ingredients[k].links)):noScore(groupName+
      ": no verified outcome ratings have been produced.");
  };
  const groups:Record<RatingGroupKey,RatingAuditCell>={
    M:input(feedUnavailable?"Unavailable":verified+"/"+allFields.length,
      "Source evidence audit: "+verified+" verified, "+modeled+" modeled, "+missing+" missing, "+
      critical.length+" critical timing/identity gaps. Not a completeness-adjusted performance score.","coverage",
      observed),
    A:input(readiness.status==="RESEARCH_WINDOW_OPEN"?"Window open":"Needs review",
      "Evidence coverage and FDA target status only. This does not measure probability of FDA approval.","status",
      [...ingredients.ER.links,...ingredients.FDA.links]),
    B:groupCoverage(["CL","SAF","COMP"],"Medical"),
    C:groupCoverage(["POP","ACCESS","REV"],"Commercial"),
    D:groupCoverage(["VAL","CASH","MOM","FLOW","CAT"],"Stock"),
    E:noScore("Final rating: no validated comparative opportunity model or audited stock-return estimates.")
  };
  return {group:groups,ingredient:ingredients,eligibleForInvestmentRanking:false,
    sourceRecordPresent:!!matched,evidenceFeedAvailable:!feedUnavailable,
    verifiedFields:verified,modeledFields:modeled,missingFields:missing,totalFields:allFields.length};
}
