# Independent SCIENCE 40 dossier — research-only readiness

This work is a **structural evidence-readiness contract**, not a validated FDA prediction engine. It preserves the proposed [40-question, eight-layer SCIENCE catalog](https://github.com/pdufa/pdufa-command-center/pull/497) in the current backend, without merging the old 11-file draft or changing GEM JR/GEM/WT FS/FA presets or the 21 legacy list scores. The catalog is labeled `RESEARCH_ONLY_NOT_CERTIFIED`.

## Research layers

1. Clinical efficacy (S01–S05)
2. Statistical integrity (S06–S10)
3. Trial design (S11–S15)
4. Safety (S16–S20)
5. Reproducibility (S21–S25)
6. Regulatory pathway (S26–S30)
7. Manufacturing and quality (S31–S35)
8. External validity and comparators (S36–S40)

The planned investigation-depth framework is **1–20**. Passing all 40 question slots is insufficient for a structurally complete dossier until every depth level has an independently reviewed record. This does not establish actual scientific validity: a qualified independent reviewer must inspect each underlying document and clinical context.

## Evidence trust boundary

- Existing scanner or API claims such as `review_status: VERIFIED` **are not evidence of independent adjudication**.
- Submitted source observations are categorized `SOURCE_REPORTED_UNADJUDICATED` only after syntax, ISO-date, provenance metadata, document SHA-256, interpretation, depth, and cutoff checks. Incorrect/future-dated input is `REJECTED`; absent input is `NOT_SUBMITTED`.
- The separate `science_40_adjudication_register.json` is **currently empty for all real cases**. The API does not accept independent certifications from callers.
- A slot can count `INDEPENDENTLY_REVIEWED` only when a server-side independent reviewer signoff for the **same exact program and question** matches the source URL, document digest, publication date, finding digest, interpretation, and review date. The signoff metadata is necessary but **not sufficient** to prove the review's correctness; reviewers must actually examine the original documents.
- The readiness result is `RELUCTANT` until **40/40** independently attested assessments and **all 20** depth levels have evidence. If such proof is achieved, `READY_FOR_ANALYSIS` describes *structural evidence availability only*. `independentScientificConclusion` and `approvalProbability` remain null, and trading remains disabled.
- Any sources consumed after the as-of cutoff are excluded. Unresolved contradictions remain separately listed.

## Existing eligibility gate

SCIENCE 40 only runs **after** the existing independently checked public Phase 3 results + PDUFA date gate. An otherwise discovered Pipeline trial is still visible but blocked until those prerequisites pass. The existing `science` investigation remains unchanged and is returned alongside a separate `science40` object, protecting established assessments and dashboard consumers.

### First real PEAK trial (COGT, NCT05208047)

Sources published before 27 October 2026:

- 28 May 2026, issuer reports FDA NDA acceptance / 30 November PDUFA date: https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-fda-acceptance-new-drug-0
- 30 May 2026, issuer reports PEAK efficacy and safety results: https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-announces-detailed-clinical-data-peak-phase-3

**Current independently certified SCIENCE outcome: 0/40, coverage 0%, RELUCTANT; no clinical PASS/FAIL or FDA approval probability.** These issuer disclosures may guide what documents to collect; they are **not** yet individually reviewed and independently adjudicated across the 40 questions.

The legacy first-trial research abstention remains in [draft PR #498](https://github.com/pdufa/pdufa-command-center/pull/498) and has not been merged.

## PEAK source-reported research leads (not independent SCIENCE)

The read-only case dossier now surfaces **10 question-linked issuer source leads**
for S01–S05 (efficacy), S17–S19 (safety and exposure), and S26/S30
(regulatory pathway). Source dates are May 28 and May 30, 2026;
the leads were indexed on October 27, 2026 and are excluded from
any earlier point-in-time snapshot.

From the detailed May 30 issuer announcement:

- Reported median PFS 16.5 versus 9.2 months (hazard ratio 0.50,
  95% CI 0.39–0.65, p<0.0001).
- Reported PFS2 HR 0.57 (95% CI 0.41–0.78), as well as claims about
  KIT subgroup consistency.
- Reported grade 3+ ALT/AST elevations 10.8% versus 1.4% and
  treatment-related discontinuation 7.4% versus 3.8%.
- Reported mean duration of combination treatment 21.4 months is
  **not** equivalent to independently verified efficacy durability
  or long-term safety.

The May 28 issuer release reports NDA acceptance, Priority Review,
and a November 30 target. It does not provide an independently
examined FDA receipt letter.

Each lead has an explicit `originalSourceHashAvailable: false` and
`independentlyReviewed: false`. No original source bytes, SAP,
clinical study report or independent FDA correspondence was
authenticated for these leads. The leads are useful **tasks for
evidence collection**, not completed 40/40 questions, and are not
counted toward source submissions or independent readiness.
All ten records remain `NOT_SUBMITTED` for adjudication and the case
remains **0/40, RELUCTANT**, without probability or trading.

## Tests

```sh
pip install -r new-platform/backend/requirements.txt
PYTHONPATH=new-platform/backend pytest -q new-platform/backend/tests/test_science_40_dossier.py
PYTHONPATH=new-platform/backend pytest -q new-platform/backend/tests
```

New tests prove the separate catalog's 40 sequential IDs, 8 layers and 20-depth coverage, first-case 0/40 abstention, forged verification rejecting promotion, future/stale/invalid sources failing closed, isolated synthetic signoff matching, other-program evidence cannot transfer, challenges remain visible, and no PDUFA estimate or trading authorization. The synthetic 40/40 test demonstrates only schema mechanics, **not clinical accuracy or a complete real dossier**.

## Next dependencies

1. Acquire and preserve licensed/access-permitted primary protocols, SAP, full Phase 3 clinical study reports, adverse-event breakdown, public FDA correspondence, and original CMC/inspection evidence when available.
2. Maintain source hashes and timestamps, independent source-level reviewer records, conflict resolution and document specificity for each question.
3. Validate historical FDA review-cycle outcomes and cohort selection before OUTCOME can estimate approval likelihood.
4. Only after evidence correctness and backtesting may MAIN show independent readiness alongside an appropriate uncertainty-based decision.
