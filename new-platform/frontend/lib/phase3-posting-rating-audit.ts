/** Evidence-safe display cells for the registry Before/Past tables.
 * Neither the posting snapshot nor its ticker + NCT supplies exact drug,
 * indication, comparative medical outcomes, or validated 20-assessment scores.
 * Never project the main research-feed grades into this table by ticker/NCT alone.
 */
import type {RegistryPostingRow} from "./phase3-registry-posting";
import type {ToolsRatingGroupKey,ToolsRatingIngredientKey} from "./tools-rating-groups";
export type PostingRatingCell={label:string;description:string;sourceUrl?:string};
export type PostingRatingAudit={
  group:Record<ToolsRatingGroupKey,PostingRatingCell>;
  ingredient:Record<ToolsRatingIngredientKey,PostingRatingCell>;
};
export function postingRatingAudit(row:RegistryPostingRow):PostingRatingAudit{
  const posted=row.resultsCount>0;
  const source=row.sourceUrl;
  const cell=(label:string,description:string,sourceUrl?:string):PostingRatingCell=>
    ({label,description,sourceUrl});
  const noScore=(what:string)=>cell("Not assessed",what+
    " has no verified trial-specific medical or commercial rating in this ClinicalTrials.gov results-posting classification.");
  const noPdufa=cell("Not verified",
    "A registry posting is not an FDA application-level PDUFA date or outcome.");
  const inputPending=cell("Not reviewed",
    "This registry-only export does not contain the source-verified 38-question scientific survey results.");
  const medical=noScore("Medical benefit");
  const postedClinical=posted?cell("Review needed",
    "Registry results are posted for this exact NCT; effect sizes, comparators, endpoints and clinical interpretation have not been adjudicated. Posting is NOT efficacy or superiority.",
    source):cell("Not assessed",
    "No results are posted in this dated registry snapshot. Clinical benefit is unknown.",source);
  const evidence=cell(posted?"Results posted":"Not posted",
    "ClinicalTrials.gov results-posting status only; not a company Phase 3 announcement, efficacy score, evidence-quality grade or FDA decision.",
    source);
  const ingredient:PostingRatingAudit["ingredient"]={
    VER:inputPending,MOD:inputPending,
    MISS:cell("38 to review",
      "The linked research framework defines 38 supporting survey questions, but this registry snapshot does not contain completed answers. This is NOT a verified count of failed criteria."),
    CRIT:cell("Gates missing",
      "Exact trial drug, indication, issuer results announcement, PDUFA link and 38 scientific evidence reviews are not reconciled by this table."),
    ER:evidence,FDA:noPdufa,
    CL:postedClinical,
    SAF:posted?cell("Review needed",
      "Registry results are posted, but exposure-aligned adverse-event and discontinuation comparisons have not been clinically adjudicated.",source):medical,
    COMP:noScore("Competitor-specific evidence"),
    POP:noScore("Patient population advantage"),
    ACCESS:noScore("Coverage, access and reimbursement"),
    REV:noScore("Revenue and adoption"),
    VAL:noScore("Company valuation"),
    CASH:noScore("Cash runway"),
    MOM:noScore("Stock momentum"),
    FLOW:noScore("Ownership or trading flow"),
    CAT:noPdufa,
    APP:noScore("Appreciation potential"),
    READY:cell("Not qualified",
      "A registry classification is insufficient to establish post-Phase 3 research readiness, FDA dates, scientific benefit or investability."),
    GRADE:noScore("Final opportunity grade")
  };
  return {group:{
    M:cell("Unassessed","38 individual survey evidence requirements are not completed by the registry export."),
    A:evidence,
    B:cell("Not rated","Clinical outcomes and comparative safety have not been adjudicated; source posting is not an efficacy grade.",posted?source:undefined),
    C:noScore("Commercial opportunity"),
    D:noScore("Stock appreciation"),
    E:noScore("Final assessment")
  },ingredient};
}
