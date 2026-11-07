# FDA original NDA/BLA submissions ↔ published letter application-ID bridge

**Research snapshot: October 25, 2026 — source identity only, no outcomes verified.**

The new read-only [official FDA collection workflow](https://github.com/pdufa/pdufa-command-center/actions/runs/40247135687) reuses the actual
Drugs@FDA `Applications` / `Submissions` raw tables acquired by the
October 25 source audit, retrieves the exact published CRL archive
advertised in the FDA official manifest, and verifies its source hash against
the previously committed CRL source index.

The aggregate-only report is stored at
`new-platform/backend/app/research_sources/hop_fda_original_letter_bridge_20261025.json`
and in [the short-retention GitHub Actions artifact](https://github.com/pdufa/pdufa-command-center/actions/runs/40247135687/artifacts/12618459836).

## Actual cross-source observations

| FDA published letter / original submission relationship | Count | Meaning |
|---|---:|---|
| All selectively published FDA letter references | **458** | Source documents, not FDA decisions |
| Letter references linked by one clean NDA/BLA application ID to the original-submission inventory | **334** | Application identity link only |
| Published letter references whose NDA/BLA application is absent from that inventory | **107** | Absent in this approval-centric source family; **not** proven unapproved |
| Ambiguous, missing, or unparseable published letter application identities | **17** | Require authoritative identifier review |
| ANDA references separately classified in this selected collection | **0** | Not a measurement of all ANDA correspondence |
| Distinct original-inventory NDA/BLA applications referred to by the 334 linked letter references | **238** | Applications, not cycles |
| Linked application identities with two or more letter references | **63** | Repeat-letter case-review candidates |
| Matched letter references with applications having multiple original submission numbers | **11** | May have complicated submission history |
| Published `/Original N` qualifiers matching a source submission number in text | **7** | Text concordance, not verified cycle identity |
| Published `/Original N` qualifiers absent from that source application submission-number list | **3** | Identity conflict to investigate |

This bridge compares the **6,033** original NDA/BLA submission-history entries
representing **5,973** distinct application IDs from the actual Drugs@FDA
tables with **458** selectively published FDA letter references. The same
counts were obtained directly in the read-only workflow and are now subject
to regression tests. It exports only aggregate counts, source fingerprints and
provenance, not the original FDA table records or per-company predictions.

## Why an application-ID match is not outcome evidence

A published Complete Response Letter may precede later successful approval.
Matching an application to Drugs@FDA today does **not** prove it was approved
during the earlier CRL cycle, and a CRL is not necessarily a final rejection
of the entire application. Conversely, the 107 source-selected letter
references missing from this approved-product original-submission inventory
are **not evidence** of 107 permanently declined applications.

An FDA original submission number is not automatically a review-cycle
number. Even a matching textual `Original 2` qualifier does not establish
the original action date, clinical evidence available before the decision,
or an adjudicated FDA approval/nonapproval event. FDA corrections, rescissions,
supplements, tentative approvals, and other document classes need separate
human regulatory review.

The CRL publication corpus and the approval-centric product archive have
different inclusion mechanisms and **cannot provide a complete NDA/BLA
approval/nonapproval decision denominator**. FDA review-cycle outcome
labels, an observed approval rate, historical model accuracy, and drug-level
approval probabilities all remain unavailable.

## Reproduction and safety

The pull-request-only workflow in
`.github/workflows/hop-drugsfda-original-source-research.yml`
uses these code paths:

- `app/hop_drugsfda_submission_spine.py` for original NDA/BLA submission
  observations, never adjudicated outcomes.
- `app/hop_openfda_snapshot.py` for the selectively published source-letter
  archive, retaining null review-cycle identities.
- `app/hop_fda_original_letter_bridge.py` for the source-ID-only join.
- `scripts/collect_hop_fda_original_letter_bridge.py` for pinned official
  archive retrieval and aggregate-only collection.
- `tests/test_hop_fda_original_letter_bridge.py` for synthetic safety cases
  plus a regression check on the real published audit snapshot.

The collector requires pinned FDA source bytes and source hashes from the
previous audit. It fails if a source archive changes unexpectedly instead
of blending multiple dated source snapshots. It does not write to production
Postgres, alter scans, merge any PR, send orders or emails, or train a model.

**Outstanding work:** obtain independent authenticated original FDA
letter/action reviews; reconcile the 17 ambiguous identities and 107 registry
nonmatches; investigate repeats and original-submission-number disagreements;
and independently reconstruct a complete original NDA/BLA decision
population including never-approved candidates. Then verify predecision
features and run strictly time-forward calibration. Current independent FDA
review-cycle outcomes verified: **0**. Model-eligible records: **0**.
Approval rate, predictive accuracy and approval probability: **null**.
