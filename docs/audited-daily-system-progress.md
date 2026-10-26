# Daily SCIENCE / OUTCOME / MAIN progress reporting

Run `python -m unittest tests.test_audited_daily_progress` and
`python scripts/audited_daily_progress.py yesterday.json today.json`.

Each daily JSON snapshot must contain `as_of` and exactly three keys under
`systems`: `SCIENCE`, `OUTCOME`, `MAIN`. Each system is either `null`
(not verified) or an object with integer `completed`, integer `total`,
HTTPS `evidence_uri`, and a stable `scope` naming the audited population.

Example **schema only, not measured progress**:
```json
{"as_of":"2026-10-26","systems":{"SCIENCE":null,"OUTCOME":null,"MAIN":null}}
```

Report the measured percentage only for a defensible, complete denominator.
Daily percentage-point change is shown only when yesterday and today have
the **same scope and denominator on adjacent calendar dates**. Otherwise report BASELINE_ONLY and no
change. Do not silently treat missing observations as zero or rebase to
a different denominator. A change in audited scope requires a new baseline.

SCIENCE numerator: fully source-verified 40-investigation units for a
predeclared exact-trial cohort; denominator: 40 times the cohort size.
Existing P/J/G seven-category heuristics are **not** SCIENCE-40.

OUTCOME numerator: independently certified, point-in-time, model-eligible
FDA review cycles in a predeclared complete application cohort; denominator:
all review cycles in that cohort. Selected CRL or approval samples do not
qualify as a complete denominator. Historical research timeline coverage,
such as 17/20, is a **separate metric**, not OUTCOME completion or accuracy.

MAIN numerator: individually accepted production requirements from a frozen,
versioned acceptance inventory; denominator: all requirements in that inventory.
Do not equate 741 source-linked trials with 741 fully qualified trials.

Prediction accuracy is **never** derived from completion. Report it only
from independently held-out labeled decisions with the model version,
sample size, uncertainty, and metric (e.g. Brier score) shown.

The script is an auditable comparison utility. It does not schedule or collect
source observations. The dashboard integration is described below.

## First MAIN dashboard baseline — October 26, 2026

The dashboard now validates a versioned **MAIN / Core Platform** inventory:
8 sections, 31 applicable code/deployment/runtime/evidence gates, and the original
one excluded N/A gate. This is the Core Platform checklist population, not the
39-task spreadsheet, the full 59-gate installation checklist, or a measure of
engineering effort. SCIENCE and OUTCOME retain null completion measurements.

`mainAcceptanceInventory.json` pins every gate identity to the original merged
checklist commit. `mainDailyEvidenceSnapshots.json` records every gate's status,
source, Pacific date and observation time. `mainProductionDeploymentEvidence.json`
records sanitized authenticated Vercel deployment metadata (and may contain a
list when additional dated deployment observations are collected).

The first baseline has **1/31 verified gates (3.23%)**, **6/31 code/deployment
signals**, **5/31 partial**, and **19/31 unverified**. The sole accepted gate is
the Core Platform production frontend deployment: project
`prj_7VRIuXH3FzUseTmXkzLDYQbEAd5l`, deployment
`dpl_C5AzDtzWZhL1ym9cF1DJhB9RW4uT`, production alias
`pdufa-new-dashboard.vercel.app`, commit
`dbf786766a3f5c39f65c44c452a01422a431df1f`, state READY.
This provider record proves deployment, not full runtime acceptance or FDA data
validity. **0/8 whole sections are fully accepted; 30/31 gates remain open.**

The validator refuses missing/duplicated/reassigned gates, changed exclusions,
preview/wrong-project deployment proof, mismatched commit or alias, proof reused
for another gate, future observations, and duplicate or incorrectly ordered
Pacific dates. Invalid input withholds the entire daily measurement. Saved
observations are reviewed records; validation of their consistency does not
cryptographically authenticate an external provider.

The first observation establishes a baseline only. It does not invent yesterday's
value. Daily percentage-point change requires adjacent dates with the same
inventory; gaps or scope changes establish a new baseline. ETA requires eight
actual comparable daily measurements spanning seven days, positive progress and
no regressions; two distant endpoints are insufficient. No initial ETA is shown.
This dated baseline does not automatically refresh, create a recurring job, or
change the existing 8 PM Pacific scans. Additional accepted gate types require
their own complete evidence contracts; a deployment proof cannot certify them.

## Technical acceptance correction — scope v2

MAIN final acceptance follows the October 25 technical-installation policy, independently of completing SCIENCE investigations or validating OUTCOME probabilities. Ten prerequisite components combine Core Platform (excluding its final acceptance row) and Production Automation. Their readiness is evaluated from actual code/deployment/runtime/evidence states. Missing technical proof still blocks acceptance; successful research cannot compensate for it.

The daily Core Platform inventory retains all 31 gate identities and the original N/A exclusion. Its scope is now `MAIN/core-platform-gates/v2`, with the immutable technical-policy source attached. The earlier v1 snapshot is preserved in Git history at commit `8cc349ec5ed0b1958e98751d69938c26cc86d6c2`. The correction changes no gate status or completion count: 1/31 verified, 30 open, 0/8 accepted sections. It starts a new baseline, and comparisons against v1 or the former mixed-policy October 25 graph are withheld.

The separately displayed 10-component technical prerequisite count is not the 31-gate daily denominator. It neither certifies FDA source completeness nor creates calibrated probabilities. Original source-health gaps, full runtime verification, and backup/restore requirements remain open until their own evidence is established.
