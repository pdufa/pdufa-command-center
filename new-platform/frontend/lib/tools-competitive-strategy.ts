/** Competitive-strategy investigation for post–Phase 3 trial candidates.
 * Uses the existing twenty-assessment source fields, not new unreviewed scores.
 * A displayed field requires the exact NCT + ticker + drug + indication match.
 */
export const COMPETITIVE_STRATEGY_TOPICS=[
  {key:"SOC",name:"Current competition",
    monitor:"Approved drugs, current standard of care, closest substitutes, treatment line and patient subgroup.",
    rank:"Competitive positioning within the same indication, line and patient population.",
    fields:["closestCompetitor","competitorCount","standardOfCare"]},
  {key:"MED",name:"Medical advantage",
    monitor:"Matched efficacy endpoints, direct head-to-head outcomes, survival, tolerability and treatment convenience.",
    rank:"Size, clinical meaning and strength of directly comparable benefit and safety evidence.",
    fields:["headToHead","clinicalBenefit","survivalBenefit","safetyAdvantage","convenience"]},
  {key:"PIPE",name:"Pipeline threats",
    monitor:"Rival Phase 3 results, FDA filings, PDUFA dates, label expansions and new market entrants.",
    rank:"Threat severity, timing, likelihood and relevance to the same patient population.",
    fields:["competitivePipelineThreat"]},
  {key:"COMM",name:"Commercial position",
    monitor:"Payer access, expected net treatment price, adoption, switching and uptake assumptions.",
    rank:"Ability to convert differentiated benefit into reimbursed, sustainable uptake.",
    fields:["payerAccess","treatmentPrice","adoption","switchingPool"]},
  {key:"MOAT",name:"Competitive moat",
    monitor:"Patent and regulatory exclusivity, litigation, commercial rights and partner dependencies.",
    rank:"Evidence-backed durability of advantage after competitor entry.",
    fields:["exclusivity","licensingValue"]},
  {key:"STOCK",name:"Stock implications",
    monitor:"Competition-sensitive valuation, market expectations, dilution, rival catalysts and shareholder risk.",
    rank:"Potential risk-adjusted appreciation not yet reflected in the current valuation.",
    fields:["competitiveStrategy","valuationImpact","shareholderRisk"]}
] as const;

/** A confirmed outcome requires a matched, sourced comparator and defensible
 * ranking method; topic coverage alone is never a stock-return rating. */
