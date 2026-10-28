# FDA action date vs first observed public outcome announcements

**Pilot research snapshot:** 2026-10-28. **Status:** public outcome
announcement *leads only*, not validated FDA review-cycle training labels.

This extends the two actual signed FDA action-letter examples in
`hop_first_real_fda_action_letter_samples.md` with a separate public
announcement chronology. A letter's printed/signature/action date, a
publisher's dated release timestamp, and the day FDA made its original PDF
public are **three distinct clocks**. No missing clock is imputed.

## Three dated source observations

| FDA historical case | Signed FDA action | Publisher source-reported public announcement | Scope |
| --- | --- | --- | --- |
| NDA 213973, ripretinib **APPROVED** | 2020-05-15 | **FDA** release syndicated via PRNewswire, 2020-05-15 15:44 EDT | QINLOCK approval in 4th-line GIST; original submission/review cycle not named in release |
| Same ripretinib case | 2020-05-15 | **Deciphera** company release, 2020-05-15 16:05 EDT | Same product/indication and decision, a distinct publisher origin |
| BLA 761303/Original 1, odronextamab **CRL** | 2024-03-22 | **Regeneron** company release, 2024-03-25 07:00 EDT | Two odronextamab CRLs in FL and DLBCL; release does **not** identify which BLA Original unit corresponds to which indication |

Publisher primary/source pages:

- https://www.prnewswire.com/news-releases/fda-approves-first-drug-for-fourth-line-treatment-of-advanced-gastrointestinal-stromal-tumors-301060275.html (FDA text, syndicated).
- https://www.deciphera.com/news/fda-grants-full-approval-deciphera-pharmaceuticals-qinlocktm-ripretinib-treatment-fourth-line (issuer).
- https://investor.regeneron.com/news-releases/news-release-details/regeneron-provides-update-biologics-license-application (issuer).

The two ripretinib sources are two distinct publishing origins, not
independent model outcomes. Regeneron and its syndicated copies represent
one originating announcement. Do not count syndication as independent
corroboration.

## Exact label / research trust boundary

The research module is `hop_fda_public_disclosure_clock.py`. The source
metadata lives in
`app/research_sources/hop_fda_public_outcome_disclosure_leads.json`.

- All source publication timestamps are **as reported on the publisher
  pages inspected in 2026**. The original release bytes and a historical
  archive proving that exact timestamp were not captured.
- These establish that the selected public pages **report** the outcome
  and publication time. They do not prove there was no earlier release.
- The exact Original unit is not spelled out in these announcements.
  Retrospectively matching an FDA letter to a press release is useful
  research, **not** independently adjudicated public review-cycle labeling.
- The first public availability of the **original FDA letters** is unknown.
  In particular, the archive hosting a 2024 CRL in 2026 must not be treated
  as a 2024 publicly available decision document.
- Day-level forecasting must not train on a decision announced on the
  forecast day without independently verified earlier intraday cutoff;
  the existing backtester excludes same-day labels.
- A publication timestamp in a newer collected source is not an observed
  predecision feature. Research collected 2026-10-28 is invisible under an
  earlier-as-of research audit until explicit point-in-time validation.
- Exact reviewed application/cycle history, complete eligible population
  and independent reviewer adjudication remain unresolved. No approval
  probabilities can be generated.

## Read-only combined research endpoint

`GET /api/internal/hop/public-outcome-disclosures`

Requires `x-pdufa-internal-key`. No PostgreSQL dependency or writes. It
returns two historical FDA action letter observations, three publisher page
observations, their **separate clocks**, missing-evidence blockers and a
hard-coded `INSUFFICIENT_EVIDENCE` decision status.

The response intentionally retains:

- `independentModelEligibleCycles: 0`
- `independentHistoricalBacktests: 0`
- `accuracy: null`
- `approvalProbability: null`
- `trainingAuthorized: false`
- `tradeAuthorized: false`

The public-source module can also be run in offline tests without database
access. Tests reject future dates, impossible release-before-action chronology,
counterfeit domains, artificial Original unit attestations, duplicates,
contradictory outcome labels, false unique-publisher counts, and public
release times silently used as verified review-cycle labels.

## Next steps

1. Preserve original source bytes and cryptographic hashes from
   controlled HTTPS retrieval. FDA PDF hash validation is distinct
   from matching a publisher page's release date.
2. Establish exact NDA/BLA Original or supplement/review-cycle identities
   and separately prove when the matching decision label became public.
3. Build a **consecutive** FDA application denominator, including CRLs,
   approvals and unresolved outcomes. Prespecify sampling rules.
4. Freeze strictly earlier features and reserve an independent,
   program-disjoint historical holdout cohort.
5. Only then calculate genuine out-of-time accuracy, calibration,
   Brier score and approved/CRL predictive performance.

**Software tests can verify this chronology's logic. They cannot certify
historical FDA forecasting performance.**
