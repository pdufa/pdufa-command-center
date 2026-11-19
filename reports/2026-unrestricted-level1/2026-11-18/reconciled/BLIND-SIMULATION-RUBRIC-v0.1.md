# Level 1 historical reconstruction — fixed scoring rule v0.1

**Status:** Retrospective simulation protocol. Not a prospectively validated predictor.  
**Scope:** 2026 FDA application review cycles with dated pre-action clinical evidence.  
**Outcome isolation:** Reviewers preparing prediction packets must not see FDA action letters, action dates, actual outcomes, or outcome-aware assessments. Reviewers may see the PDUFA target and evidence published by the cutoff.

## Fixed decision rubric (written before any new simulation predictions in this protocol)

Assign 0–2 points to each of five categories using only a dated, auditable predecision source:

1. **Efficacy:** 0 = negative/missing prespecified endpoint; 1 = positive but uncontrolled or uncertain clinical benefit; 2 = convincing positive prespecified endpoint with meaningful effect.
2. **Design/analysis:** 0 = known major methodological concern or serious protocol deviations; 1 = uncontrolled/external comparison or incomplete analysis verification; 2 = adequate control and prespecified robust statistical plan.
3. **Safety:** 0 = major unresolved attributable toxicity; 1 = serious events or limited characterization but no established prohibitive signal; 2 = well characterized acceptable benefit-risk.
4. **Regulatory readiness:** 0 = documented unresolved major FDA/CMC concern; 1 = accepted application with material prior deficiency or unresolved readiness; 2 = no documented major blocker and adequately supported filing.
5. **Evidence completeness:** 0 = essential trial/source evidence missing; 1 = important verification gaps; 2 = independently verified endpoint, statistics, safety and regulatory evidence.

**Classification:** 0–3 = CRL risk / do not predict approval; 4–6 = INDETERMINATE; 7–10 = APPROVAL LEAN. Missing evidence cannot be treated as favorable. No numerical confidence percentage is permitted without separate out-of-sample calibration. For each assessment, retain five component scores, source URLs, source publication dates, cutoff, rationale and version.

**Important limits:** A single-arm pivotal trial does not automatically imply rejection. The rubric is a reproducible heuristic, not a proven FDA approval probability model. Historical scoring after the action date is a retrospective evidence-restricted simulation, never a genuinely pre-action frozen forecast. Accuracy must be labeled accordingly. FDA outcome data is consulted only in a separate evaluation pass after predictions are saved.

## Ebvallo candidate input facts (predecision, not yet independently scored)

- ALLELE trial **NCT03394365**, single-arm open-label Phase 3.
- 2025 conference abstract: **38/75 ORR (50.7%, 95% CI 38.9–62.4)**; 21/75 complete responses, median duration of response 23 months.
- Treatment-emergent serious adverse events in 65.4% HCT and 61.2% SOT; fatal treatment-emergent adverse events 19.2% HCT and 18.4% SOT, with none reported treatment-related in that abstract.
- 2025 resubmission accepted for priority review with January 10, 2026 target.
- **Unresolved for scoring:** independent review of protocol deviations, prespecified endpoint analysis, external-control construction, and resubmission remediation. Do not use any post-action FDA assessment to resolve these gaps.

Sources published before action:
- https://www.icml.ch/dam/jcr%3A3acc2325-b2d6-4035-9393-6c896c7f7318/18-ICML_AbstractBook_Oral%2520presentations_HON_v43_S3_FullPDF%2520copy.pdf
- https://www.pierrefabrepharmaceuticals.com/sites/default/files/press/20241207_PR_ASH_2024_tabelecleucel_ALLELE_results_safety_efficacy_durability.pdf
- https://www.sec.gov/Archives/edgar/data/1604464/000095017025106533/atra-ex99_1.htm

**No FDA outcome or accuracy result is included in this document.**
