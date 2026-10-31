/** Default commercial-adoption priorities, not scored therapy-specific advantages.
 * Actual priorities require an indication-specific comparator and cited evidence.
 * This assessment is separate from the FDA PASS / CRL / EXTENSION forecast.
 */
export type CompetitiveStrategy = Readonly<{
  rank: number;
  id: string;
  label: string;
  potentialBenefit: string;
  evidenceRequired: string;
}>;

export const COMPETITIVE_STRATEGIES: readonly CompetitiveStrategy[] = [
  { rank: 1, id: "efficacy", label: "Superior clinical efficacy",
    potentialBenefit: "Meaningfully better patient outcomes than the relevant standard of care.",
    evidenceRequired: "Comparable, patient-relevant endpoints; head-to-head trials when available; effect size and uncertainty." },
  { rank: 2, id: "safety", label: "Safety and tolerability",
    potentialBenefit: "Fewer important adverse events, contraindications, or treatment discontinuations.",
    evidenceRequired: "Comparable adverse-event rates, discontinuations, monitoring requirements, and approved labeling." },
  { rank: 3, id: "unmet-need", label: "Unmet medical need",
    potentialBenefit: "Helps patients who have few effective options or an inadequately treated condition.",
    evidenceRequired: "Guidelines, treated/untreated population estimates, treatment gaps, and precisely eligible patients." },
  { rank: 4, id: "access", label: "Insurance coverage and reimbursement",
    potentialBenefit: "Reduces formulary, prior-authorization, and out-of-pocket access barriers.",
    evidenceRequired: "Payer coverage criteria, formulary tier, eligibility restrictions, and patient cost-sharing." },
  { rank: 5, id: "cost", label: "Competitive treatment cost",
    potentialBenefit: "Improves value compared with the current regimen and total cost of care.",
    evidenceRequired: "Like-for-like annual regimen costs, administration/monitoring costs, net price caveats, and outcomes." },
  { rank: 6, id: "administration", label: "Easier administration",
    potentialBenefit: "Reduces dosing burden, visits, monitoring, or barriers to adherence.",
    evidenceRequired: "Dosing schedule, route, site of care, persistence, and patient-reported burden." },
  { rank: 7, id: "prescribing", label: "Physician and guideline adoption",
    potentialBenefit: "Builds evidence-based support for prescribing in the appropriate population.",
    evidenceRequired: "Current clinical guidelines, prescribing evidence, specialist uptake, and real-world outcomes." },
  { rank: 8, id: "switching", label: "Switching advantage",
    potentialBenefit: "Makes an appropriate transition from existing therapy practical and beneficial.",
    evidenceRequired: "Switching trials, washout and sequencing constraints, clinical equivalence, and patient preferences." },
  { rank: 9, id: "supply", label: "Manufacturing and distribution readiness",
    potentialBenefit: "Provides reliable commercial availability where patients need treatment.",
    evidenceRequired: "Manufacturing readiness, cold chain, site capacity, shortage history, and distribution coverage." },
  { rank: 10, id: "differentiation", label: "Market differentiation and exclusivity",
    potentialBenefit: "Sustains a distinct commercial position against existing and incoming competitors.",
    evidenceRequired: "Exact indication/label, competitors and launches, regulatory exclusivity, patents, and licensing rights." },
] as const;
