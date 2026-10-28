# HOP prespecified family-disjoint FDA walk-forward research evaluation

The original historical backtester prevented reusing a **single exact FDA
application** between training and testing, but related drug programs can
appear under different NDA/BLA application numbers, indications, sponsors,
supplements, or product aliases. Historical metrics can be artificially
optimistic when earlier decisions about the same program inform a supposedly
unseen later regulatory case.

This increment adds a **strict optional program-heldout evaluation** to
`app.hop_backtest.walk_forward_backtest`. It does not change the legacy
research API or existing metric calculations.

## Frozen inputs

Pass:

- `program_group_by_application`: a complete canonical dictionary mapping
  **every** source application ID to an unambiguous program-family ID, including
  excluded/nonbinary/source-quarantined records.
- `heldout_program_groups`: an explicit set or frozenset of groups selected
  **before** fitting, a nonempty proper subset of the known groups.
- Continue providing chronological decision, public-outcome and
  predecision-feature clocks as before.

All group names must be canonical uppercase IDs (digits, underscores,
periods, colons, dashes permitted). Missing or extra application IDs,
unknown heldouts, malformed family names and all-heldout/no-training
configurations fail before model scoring.

**A caller-provided map is only a declaration of grouping, not proof it
captures every molecular, sponsor, asset, indication or regulatory
relationship.** A qualified independent source audit remains necessary.

## Prediction safety

1. Remove **all** records from **every** heldout program family from
   **every** training pool, including earlier approvals and CRLs from a
   related application. This prevents past same-program decisions from
   leaking into the forecast features.
2. Evaluate heldout program groups only. Unselected programs and
   ineligible/duplicated records are excluded and counted separately.
3. Within a fold, the **earliest eligible** submission from a program
   is the only eligible test member. After a program has been considered
   in one fold—including an abstention—it cannot contribute a later,
   possibly easier, application or cycle to a future fold.
4. Recompute each candidate training dataset based on strictly earlier
   public labels and feature cutoffs. Do not reveal hidden test labels to
   the scoring callback.
5. The returned `family_holdout_audit` states the declared holdout
   groups, observed test-family groups and mandatory **false**
   `mappingIndependentlyAdjudicated` and
   `realFdaOutcomeCohortVerified` flags. A split that is internally
   disjoint on supplied IDs is **not** an independently validated FDA
   forecasting experiment.

## Synthetic regression demonstration

```python
rows = [
    OutcomeObservation(... application_id="TRAIN_1" ...),
    OutcomeObservation(... application_id="RELATED_1" ...),
    OutcomeObservation(... application_id="RELATED_2" ...),
]
folds = walk_forward_backtest(
    rows,
    cutoffs,
    score_fn,
    min_train=1,
    program_group_by_application={
        "TRAIN_1": "CONTROL_FAMILY",
        "RELATED_1": "STUDY_FAMILY",
        "RELATED_2": "STUDY_FAMILY",
    },
    heldout_program_groups={"STUDY_FAMILY"},
)
```

The example is illustrative, not an FDA source dataset. Unit tests use
synthetic labels to prove that `RELATED_1` cannot enter the training
dataset for `RELATED_2`, same-family repeats cannot inflate test cases,
abstentions do not cherry-pick a later trial, and malformed grouping
cannot bypass the gate.

## Limits remaining under the PDUFA MASTER DIRECTIVE

- This software has **0 independently verified historical model-eligible FDA
  cycles** and **0 genuinely independent real FDA backtests**.
- No actual FDA PASS/FAIL approval probability, Brier score, calibration
  accuracy or family-disjoint model skill is demonstrated by synthetic tests.
- The historical FDA approved-survivor appendix, selectively published
  CRL archive, and two independently fingerprinted FDA PDFs remain
  **research sources only**, not an unbiased or complete training cohort.
- Before claiming independent validation: construct a prespecified complete
  original NDA/BLA review-cycle roster, independently adjudicate public
  label clocks and predecision features, **audit all program-family group
  aliases and related assets**, freeze a totally untouched evaluation period,
  and compare against simpler predictive baselines.

No scheduling, database writes, checklist/FS/FA membership changes,
spreadsheets or broker trades are authorized by this increment.
