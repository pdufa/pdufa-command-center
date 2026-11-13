# PDUFA cumulative scored assessments — completion contract (Levels 4–20)

## User requirement

**Not** "engineering level's code passed tests" = "PDUFA level assessment complete". Instead **each level** must evaluate *every* current FOCUS trial using only evidence applicable at that trial's verified phase and FDA application stage, produce a traceable 0–100 research score **where the evidence supports scoring**, explain every score, document unknown/unpublished items, and preserve version history and independent review.

This PR is an **engineering scoring foundation**, not a completed, independently validated set of 32 PDUFA assessments, not an FDA approval probability model, and not installed/deployed to the user's Windows PC or assessment website.

## What is implemented

- `automation/focus-assessment-roster-snapshot-20261112.json`: **32 exact NCT trial IDs**, ticker, company, registry status and dated FOCUS data from connected Google Sheet. This is a **dated source snapshot**, not proof of current FOCUS membership or current trial phase. Previous `CLINICAL_FIVE` preliminary scores are explicitly identified and **never promoted into Level 4–20 PDUFA scores**.
- `scripts/pdufa_cumulative_level_assessments.py`: cumulative, versioned **17-stage assessment implementation** (Levels 4–20), driven by the existing scientific level manifest. Level 6 adds separate **efficacy, safety, trial quality, benefit–risk and manufacturing/CMC** domains to the existing clinical/preclinical/regulatory integration fields.
- Strict **phase-first evidence**: trial phase must have a dated, hash-labelled ClinicalTrials.gov receipt with the exact NCT. Claims that an application has been filed/under review need a separate original source; a registry phase alone cannot prove FDA application status.
- Per-criterion **research rubric 0–100** requires source URL, SHA-256 digest, publication/retrieval dates not exceeding the assessment cutoff, and a meaningful explanatory reason. Sources are **claimed/recorded**, **not independently audited** by this code. Human independent adjudication remains essential.
- Unknown, missing and unpublished evidence remains **not scored**: never zero-filled or treated as proof of negative efficacy. Phase-specific `NOT_YET_EXPECTED` only for narrowly defined prefiling application/CMC cases. Other arbitrary applicability exemptions are rejected until reviewed.
- For each trial and each level: individual criterion contributions, cumulative evidence source list, gaps, provisional score **only if all phase-applicable criteria have source-backed ratings**, evidence counts, stage and reason, and separate review/validation status. **All output probabilities remain null**.
- Blinding: named final FDA outcomes forbidden in input; all cited evidence must have a publication date at or before the freeze date; validation of historic source capture before that time must still be independently verified.
- `automation/assessment-level-acceptance-contract.json`: explicit **assessment deliverable** for each FOCUS trial and every level, separate from engineering workflow completion and distinct from scientific review.
- A new GitHub workflow and offline tests cover real 32×17 coverage, no fake scores, date leakage, source/phase mismatch, explicit missing evidence and case-by-case synthetic Level 4–6 score calculation.

## How to run the read-only preview

```bash
python scripts/pdufa_cumulative_level_assessments.py --output assessment-readiness.json
```

Without independently sourced criterion ratings, this produces **544 assessment coverage records, all transparently unscored**. It never publishes changes to the website or updates the Google Sheet. That is correct for the current inputs.

When reviewed, phase-verified original evidence and explicit per-criterion ratings are available:

```bash
python scripts/pdufa_cumulative_level_assessments.py \
  --evidence /secure/reviewed-phase-and-scientific-evidence.json \
  --output /secure/assessments-2026-11-12.json
```

Evidence JSON input:

```json
{
  "schema_version": 1,
  "as_of": "2026-11-12",
  "trials": [
    {
      "nct": "NCT00000000",
      "phase": "PHASE3",
      "phase_source": {"url": "https://clinicaltrials.gov/study/NCT00000000",
                       "sha256": "64 lowercase hex digest",
                       "published_on": "2026-11-01",
                       "retrieved_at_utc": "2026-11-12T00:00:00Z"},
      "application_stage": "PRE_APPLICATION",
      "evidence": {
        "trial_design": {"status": "UNKNOWN", "reason": "Not yet adjudicated"},
        "manufacturing_cmc": {"status": "NOT_YET_EXPECTED"}
      }
    }
  ]
}
```

The example is a **schema illustration only**, not an actual clinical trial or a score.

## What is still required for *actual Level 6 PDUFA scores*

1. Refresh and reconcile **current canonical FOCUS** 32 trial IDs and drug/application identities; verify actual trial phase and FDA review cycle for each.
2. Retrieve and verify *phase-appropriate* original clinical, preclinical and regulatory evidence; source receipt hashes must be computed and checked, not simply asserted in input. Classify unpublic vs not yet expected vs truly missing.
3. Define and independently scientifically review the Level 4–20 scoring rubric **and weights**. Current numerical aggregation uses explicitly **unvalidated equal weighting** as an engineering pilot, **not** an externally validated FDA approval model.
4. Populate true evidence-based criterion ratings with reasons (do not recycle old five-component research scores), then run all 32 trials through each level with cutoff protections.
5. Have independent scientific/code reviewers adjudicate scored output and any unscorable explanations. Track immutable per-level scoring versions and historical-outcome-blind backtesting.
6. Integrate reviewed results into the Assessments page and Windows worker/installer through separate reviewed PRs, with regression CI and approved deployment. Current PR does not modify running PC or website.

## Completion and progress display

Separate clearly: `engineering implementation/code tests`, `phase-specific evidence coverage`, `provisional research scores`, `complete reviewed scientific assessments`, `validated FDA approval predictions`, and `deployment/installation`.

No level may be called **scientifically complete** merely because it passes CI or emits a numeric research score. Do not force a made-up score for a trial whose crucial evidence is genuinely unavailable; show an **explicit reviewed unscorable reason**.
