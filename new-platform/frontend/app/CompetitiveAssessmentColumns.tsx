"use client";
import { COMPETITIVE_STRATEGIES } from "../lib/competitive-strategies";
import {
  COMPETITIVE_ASSESSMENT_COLUMNS, verifiedCompetitiveFact,
  type CompetitiveAssessment, type CompetitiveColumnId, type ResearchEvidence,
} from "../lib/competitive-assessment";
import { calculateTherapyCosts, type TherapyCostComparison } from "../lib/post-phase3-population";

export type CommercialReviewRow = {
  nctId:string; ticker:string; company:string; drug:string|null; indication:string|null;
  sourceUrl:string; reasons:string[];
  therapyCostComparison?: TherapyCostComparison|null;
  commercialAssessment?: CompetitiveAssessment|null;
};
const extraColumns = COMPETITIVE_ASSESSMENT_COLUMNS.slice(4);
type ExtraId = (typeof extraColumns)[number]["id"];
const columnById = (key: CompetitiveColumnId) => COMPETITIVE_ASSESSMENT_COLUMNS.find(column=>column.id===key)!;
const money = (v:number) => v.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0});
const formatMetric = (value:ResearchEvidence, key:string) => {
  if (typeof value.value === "number") {
    if (key==="adoption") return value.value.toFixed(1)+"% of eligible U.S. patients (12 mo)";
    return value.value.toLocaleString("en-US");
  }
  return value.value;
};
function ResearchProvenance({fact}:{fact:ResearchEvidence}) {
  return <div className="competitive-provenance">
    <p><strong>Conclusion:</strong> {fact.reason}</p>
    <p><strong>Method:</strong> {fact.method}</p>
    <p><strong>Assessment:</strong> {fact.status==="MODELED"?"MODELED SCENARIO — not observed":"SOURCE-VERIFIED FACT"} · Confidence: {fact.confidence}</p>
    <p><strong>Source date:</strong> {fact.sourceDate} · <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Supporting source ↗</a></p>
  </div>;
}
function ColumnCell({row,column}:{row:CommercialReviewRow;column:typeof extraColumns[number]}) {
  const {id,purpose,evidence} = column;
  const identity={nctId:row.nctId,ticker:row.ticker,indication:row.indication};
  const dossier=row.commercialAssessment;
  if(id==="competitiveStrategy")return <td><details className="competitive-strategy-cell">
    <summary>Ranked priorities 1–10<small>Not trial-scored</small></summary>
    <p><strong>Purpose:</strong> {purpose}</p>
    <p><strong>Reason:</strong> No comparator-specific, independently verified advantage ranking is available for this trial. The list below is a default review order, not a claim that the proposed therapy wins any category.</p>
    <ol>{COMPETITIVE_STRATEGIES.map(item=><li key={item.id}>
      <strong>{item.rank}. {item.label}</strong>
      <p>{item.potentialBenefit}</p><small>Evidence needed: {item.evidenceRequired}</small>
    </li>)}</ol>
    <p>FDA approval probability is a separate assessment.</p>
  </details></td>;

  if(id==="competitorCount"){
    const approved=verifiedCompetitiveFact(dossier,identity,"approvedCompetitors");
    const late=verifiedCompetitiveFact(dossier,identity,"lateStageCompetitors");
    return <td><details className="competitive-research-cell">
      <summary>{approved&&late
        ? (Number(approved.value)+Number(late.value)).toLocaleString("en-US")+" comparable options"
        : approved||late ? "Partially assessed" : "Not assessed"}
      </summary>
      <p><strong>Purpose:</strong> {purpose}</p>
      <p><strong>Approved comparators:</strong> {approved?formatMetric(approved,"approvedCompetitors"):"Not assessed"}</p>
      {approved&&<ResearchProvenance fact={approved}/>}
      <p><strong>Late-stage comparators:</strong> {late?formatMetric(late,"lateStageCompetitors"):"Not assessed"}</p>
      {late&&<ResearchProvenance fact={late}/>}
      <p><strong>Reason:</strong> {approved&&late
        ?"Both comparator categories have separate evidence; avoid duplicated products and differing eligible populations."
        :"No complete, dated, indication-matched competitor inventory has been verified. Zero must never be inferred from missing research."}</p>
      <p><strong>Evidence required:</strong> {evidence}</p>
    </details></td>;
  }

  if(id==="costDifference"){
    const calculated=calculateTherapyCosts(row.therapyCostComparison);
    const comparable=calculated.costDifferenceUsd!==null;
    return <td><details className="competitive-research-cell">
      <summary>{comparable ? money(calculated.costDifferenceUsd!) : "Not assessed"}
        {comparable&&<small>Proposed minus current / 12 mo</small>}</summary>
      <p><strong>Purpose:</strong> {purpose}</p>
      <p><strong>Reason:</strong> {comparable
        ? "Both regimens have dated source-backed totals and matching price bases. Negative difference indicates lower first-year proposed treatment cost; this is not an insurance copayment."
        : "A first-year cost advantage cannot be calculated until the current and proposed regimens have comparable dated cost evidence."}</p>
      <p><strong>Current 12-month cost:</strong> {calculated.currentUsd!==null?money(calculated.currentUsd):"Not assessed"}</p>
      <p><strong>Proposed 12-month cost:</strong> {calculated.proposedUsd!==null?money(calculated.proposedUsd):"Not assessed"}</p>
      {(["current","proposed"] as const).map(kind=>{
        const record=row.therapyCostComparison?.[kind];
        return <p key={kind}><strong>{kind==="current"?"Current":"Proposed"} source:</strong>{" "}
          {record?.sourceUrl?.startsWith("https://") && record?.sourceDate && record.evidenceStatus
            ? <a href={record.sourceUrl} target="_blank" rel="noopener noreferrer">{record.sourceDate} · {record.priceBasis||"Unknown basis"} ↗</a>
            : "Not verified"}</p>;
      })}
      <p><strong>Evidence required:</strong> {evidence}</p>
    </details></td>;
  }

  if(id==="evidence"){
    const evidenceFields=dossier?.fields || {};
    const verifiedEntries=Object.entries(evidenceFields).filter(([key])=>
      verifiedCompetitiveFact(dossier,identity,key as keyof CompetitiveAssessment["fields"]));
    return <td><details className="competitive-research-cell">
      <summary>{verifiedEntries.length ? verifiedEntries.length+" assessed fields" : "Commercial evidence pending"}</summary>
      <p><strong>Purpose:</strong> {purpose}</p>
      <p><strong>Reason:</strong> {verifiedEntries.length
        ?"The listed competitive metrics have dated evidence. Review each individual metric for its limitations and confidence."
        :"The exact trial has an NCT source, but no complete validated, trial-specific commercial assessment is attached."}</p>
      <p><strong>Source study:</strong> <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId} ↗</a></p>
      <p><strong>Eligibility review remains pending:</strong></p>
      <ul>{row.reasons.map((reason,i)=><li key={i}>{reason}</li>)}</ul>
      <p><strong>Evidence required:</strong> {evidence}</p>
    </details></td>;
  }

  const factKey=(id==="adoption"?"adoption":id) as keyof CompetitiveAssessment["fields"];
  const fact=verifiedCompetitiveFact(dossier,identity,factKey);
  const reason:Record<string,string>={
    eligibleUsPatients:"Total disease prevalence and clinical trial enrollment do not establish label-eligible U.S. treatment population.",
    standardOfCare:"Trial comparator arms alone may not represent the current U.S. standard of care.",
    clinicalBenefit:"A positive trial result is not proof of superiority to marketed alternatives without clinically comparable endpoints.",
    safetyAdvantage:"Trial adverse events need comparable follow-up and exposure before a safety advantage can be claimed.",
    unmetNeed:"A serious disease does not itself establish how many eligible patients remain inadequately treated.",
    convenience:"Comparative dosing and monitoring requirements have not been verified.",
    payerAccess:"Payer coverage and reimbursement for an unapproved therapy must not be presumed.",
    adoption:"No defensible forecast is available without eligible U.S. population, uptake assumptions and documented source methods.",
    verdict:"A reasoned competitive conclusion is withheld until patient benefit, comparators, access, adoption and uncertainties are supported. This is not an FDA decision.",
  };
  return <td><details className="competitive-research-cell">
    <summary>{fact ? formatMetric(fact,id):id==="verdict"?"ABSTAIN — not assessed":"Not assessed"}
      {fact?.status==="MODELED"&&<small>Modeled, not observed</small>}</summary>
    <p><strong>Purpose:</strong> {purpose}</p>
    {fact
      ? <ResearchProvenance fact={fact}/>
      : <p><strong>Reason:</strong> {reason[id]||"No eligible, source-backed assessment is available for this exact trial."}</p>}
    <p><strong>Evidence required:</strong> {evidence}</p>
    <p><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">Exact trial registry ↗</a> (not sufficient by itself to prove commercial advantage).</p>
  </details></td>;
}

export function CompetitiveColumnPurposes(){
  return <details className="competitive-purpose-guide">
    <summary>Column purposes — exact wording and evidence requirements ({COMPETITIVE_ASSESSMENT_COLUMNS.length})</summary>
    <ol>{COMPETITIVE_ASSESSMENT_COLUMNS.map(column=><li key={column.id}>
      <strong>{column.label}</strong><p>{column.purpose}</p>
      <small>To assess: {column.evidence}</small>
    </li>)}</ol>
  </details>;
}
export function CompetitiveAssessmentHeaders(){
  return <>{extraColumns.map(column=><th key={column.id} title={column.purpose} scope="col">{column.label}</th>)}</>;
}
export function CompetitiveAssessmentCells({row}:{row:CommercialReviewRow}){
  return <>{extraColumns.map(column=><ColumnCell key={column.id} row={row} column={column}/>)}</>;
}
