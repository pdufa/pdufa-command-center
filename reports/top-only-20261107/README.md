# TOP-only completion ledger — 7 November 2026

Scope: the 235 exact NCT records in the existing live TOP spreadsheet. Membership is frozen. BOTTOM, Pipeline, global evidence, source models, existing scoring formulas and original score-history datasets are unchanged by this change.

## Results

- 235/235 fresh official registry records; 203 Phase 3 and 32 combined Phase 2/3.
- Registry activity: 113 recruiting, 85 active not recruiting, 22 enrolling by invitation, 15 not yet recruiting.
- 235/235 rows have all 190 fields accounted for (44,650 cells): original/source-backed value or explicit unavailable/unscored status. This does **not** mean 44,650 verified facts.
- 235/235 have all 30 metric dispositions (7,050). The current established clinical model activates five equal-weight factors; the other 25 historical metrics remain archived. No retired metric is silently reactivated.
- 43 supported clinical factor grades; 1,132 active factors remain unscored. Six complete five-factor overall scores; zero complete legacy 30-metric scores. No new numerical grade or retrospective FDA prediction is invented.
- All 235 trials still have source gaps. Question evidence: 2,728 verified, 2,579 missing expected, 383 unverified, 1,125 pending, 235 not yet expected. Pending/later/inapplicable evidence is excluded from the completeness denominator.
- Exact-NCT searches for all 235 and official-source discovery searches for all 108 represented companies are saved. Discovery results are leads, not scientific validation.
- 191 unique candidate documents attempted: 175 directly retrieved, two additional documents available through web fallback, 14 URLs still blocked. Full-text retrieval/identity checking is explicitly distinguished from scientific review. Twelve additional exact-NCT document facts cover design, power, analysis sets, FDA discussions, disposition and component-specific outcomes. Eight earlier reviewed publication readouts are retained. All newly reviewed facts stay separate from existing grades.

## Remaining blockers

`top-blockers.csv` lists the field/question and scoring blocker for every exact TOP NCT. Missing expected evidence is not a claim that no public information exists. Statistical power, dose selection, analysis plans, multiplicity, prior clinical effect size and exact-program regulatory alignment often remain unestablished by reviewed evidence. Unreviewed document leads require interpretation before acceptance; finding a document cannot itself satisfy a numerical rubric. The established scoring model requires dated exact-program primary evidence, a benchmark, uncertainty and an explicit justified grade. A partial mean is never displayed as a complete overall score.

`top-source-access-blockers.csv` records every initially blocked URL and alternate-access result, including the 14 unresolved sources at ArriVent, Candel, Geron, Iovance, Kodiak, Intellia, Ocular Therapeutix, Taysha and X4. Alternative retrieved documents are retained independently; no absent document is counted as a clinical failure.

Some existing TOP records have public findings, including Essential3. Per the user's scope restriction these records remain in TOP; no BOTTOM record is processed, moved or modified. Essential3's parallel and withdrawal components and high discontinuation rates are reported separately. Known outcomes never generate prospective forecasts.

## Reviewable artifacts and website

- `top-190-accounted.csv`: same exact 190 column names/order and 235 unique NCTs.
- `top-question-coverage.csv`: all 30 question availability counts.
- `trial-score-coverage.json`: individual phase/status, factor coverage and supported full scores.
- `coverage.json`: data-driven totals.
- `/api/top-only-completion`: TOP summary; add `nctId=NCT...` for all fields, metric dispositions, source searches, provenance, blockers and append-only snapshot history.
- `/api/top-only-completion?format=csv` and `?format=metrics`: TOP-only exports.
- `/raas-top-bottom`: only the TOP rendering is replaced with collapsed horizontal ingredient cards, score/source filters, sorting, pagination and explicit evidence statuses. BOTTOM uses its original component invocation.

No database migration or original-history rewrite is required. New immutable research fingerprints are appended to a separate TOP-only ledger; identical reruns append nothing. Full testing/deployment receipts are reported with the pull request and execution report.
