# Level 1–6 independent clinical reviewer handoff — research only

This is a continuation of draft PR #1181 and issue #1179. The original source
collection, 192 preliminary worksheets, six-level reviewer permissions,
append-only database events and staged research preview already exist.
**No new identities, reviewers, production changes, credentials, FDA predictions
or clinical approvals were created here.**

## Purpose

`scripts/medical/level16_review_handoff.py` turns the current published
**research-coverage** snapshot into a separate list of specific tasks for
authorized clinical reviewers. It does **not** authenticate any original source
or permit reviewers to sign, change a database, certify a clinical finding or
produce an FDA probability.

The script refuses to operate if the exact FOCUS roster or provisional
application cycle crosswalk mismatches the current frozen evidence cohort,
if a review or prediction status has been promoted without independent evidence,
or if the ORCA-2 source chronology asserts a verified SAP-lock relationship.

Input:
- `reports/scientific-levels1-6/scientific-coverage-20261114.json`
- `new-platform/frontend/data/p3PostDataActive.json` (legacy filename only)
- `new-platform/backend/app/data/focus_application_snapshot.json`
- `reports/scientific-levels1-6/orca2-statistical-chronology-20261114.json`

The script reads only already committed research metadata and the unreviewed,
fixed ORCA-2 statistical chronology. It cannot access external services,
change live trial membership, unlock the staging reviewer app or run any
source-validation/medical signoff process.

## Run on a reviewed checkout, offline

To inspect the first ORCA-2 handoff as Markdown:

```powershell
python scripts/medical/level16_review_handoff.py --nct NCT04576949 --format markdown
```

To generate the complete 32-trial / 192-level handoff in a private folder,
redirect standard output:

```powershell
python scripts/medical/level16_review_handoff.py --format json > focus-level1-6-review-handoff.json
```

The target file is a **local output**; do not commit private reviewer notes
or patient-level information.

## Review queue model

Every trial carries distinct source collection, unverified application
mapping, research-only phase, evidence questions and four mandatory independent
review stages:

1. Authorized source verifier checks exact original source ownership,
   actual bytes, dates, versions, amendments and cutoff.
2. Separately authorized clinician or statistician examines the
   phase-appropriate clinical evidence, methods, conflicting sources and
   limitations.
3. Independent challenger documents and resolves objections to the
   proposed interpretation.
4. Separate adjudicator reviews prior history and signs the final
   decision only after the approved protected infrastructure is available.

All these steps are **pending**. Collected registry data, full text or an
original SAP remains `COLLECTED_UNREVIEWED`, not authenticated or
scientifically reviewed. An absent public protocol/SAP or posted-results record
is recorded as `NOT_COLLECTED_AVAILABILITY_UNRESOLVED`, never automatically as
a trial failure, unpublished result or statistical deficiency.

Earlier-only phases do not require future pivotal Phase 3 results/SAP. A
registry-listed combined Phase 2/3 study instead receives
`MIXED_PHASE2_PHASE3_REQUIRES_APPLICABILITY_REVIEW`; this unreviewed label
does not independently certify the study's current phase.

The review order is **ORCA-2 first**, followed by breadth of already collected
document categories. This is a logistics queue, **not a ranking of trial
quality, FDA approval chances or patient benefit**.

## ORCA-2 first review packet

ORCA-2 `NCT04576949` has a complete public-source chronology comparison:
a March 8, 2021 protocol containing Hochberg, a registry primary-completion
date of December 23, 2021, a March 25, 2022 SAP describing Bonferroni sizing
simulations and Hochberg primary testing, and the later trial publication.

The *actual* database-lock/unblinding timestamps, signed final SAP date,
earlier amendments and independent statistical interpretation are still missing.
Therefore Level 5 remains `NOT_ADJUDICATED`. No claim of an improper post-hoc
change, consistent finalized estimand, FDA approval probability or independent
review is made.

## Validation and live-activation blockers

```powershell
python -m unittest discover -s tests -p "test_level16_review_handoff.py" -v
python -m unittest discover -s tests -p "test_level16_orca2_statistical_timeline.py" -v
python scripts/audit_raas_retirement.py --check
```

Dedicated CI runs the new handoff and existing phase-first regressions on
Windows and Linux alongside disposable PostgreSQL checks. Passing tests verify
**only software behavior**.

The owner approval package A01–A14, real individual identity administrator,
five genuinely identity-proofed authorized persons, source-attestation
authority, lawfully accessible originals, independent scientific reviews,
protected staging approval and verified application links remain outstanding.
The three unverified crosswalk exceptions stay visible. Do not merge/deploy
this draft to satisfy a review-readiness test.


## Fourth slice — connect review questions to the offline FOCUS preview

The review handoff now can be displayed beside the existing preliminary
research within the original, **offline-only** FOCUS preview. The renderer
checks that all 32 exact NCTs match, the 192 levels are in order, provisional
application-cycle status has not changed and every source authentication,
clinical review, independent challenge, score and FDA prediction is still
unreviewed/null. Handoff text is HTML-escaped; this does not create an
authorized reviewer session.

Generate the complete handoff locally, then render it in the existing
read-only preview workflow:

```powershell
python scripts/medical/level16_review_handoff.py --format json > focus-level1-6-review-handoff.json

python scripts/medical/render_level16_focus_preview.py --report levels1-6-readiness.json --review-handoff focus-level1-6-review-handoff.json --output focus-level1-6-review.html
```

The readiness input is generated separately by the existing
`phase_first_levels_1_6.py` command against an available registry
checkpoint. If there is no current checkpoint, do not invent one and do not
claim an updated readiness display. Optionally include
`--preliminary-research reports/scientific-levels1-6/focus-source-research-20261114.json`
only on a checkout with the actual source snapshot present.

The preview refuses handoffs with altered NCT membership, corrupted level
count, incompatible provisional application status, claimed authenticated
sources/reviewers, fake independent review or numerical predictions.
This tests safe presentation of **unreviewed** work, not medical validity
or a production website.

## Fifth slice — populate preview from the 32 original registry receipts

The earlier offline preview can use an empty registry checkpoint, incorrectly
showing UNRESOLVED phase and BLOCKED_ON_REGISTRY_SOURCE even when the dated
source-research bundle contains all 32 original registries. The new
`scripts/medical/level16_offline_research_preview.py` uses the existing
`level16_research_preparation.readiness_report()` function to load the actual
captured but UNREVIEWED registry fields, preliminary worksheets, and review
handoff into a single read-only page.

It validates the exact 32 NCTs, frozen source cutoff, all 32 source receipts,
captured digests, phase and ticker consistency with the evidence-coverage
snapshot, provisional application relationships and six levels per trial.
No authentication, clinical adjudication or FDA forecast is inferred.

Run from the working repository checkout, specifying an existing parent
directory **outside** the Git repository, with a new target filename:

```powershell
python scripts/medical/level16_offline_research_preview.py --output C:\PDUFA-Research\focus-level1-6-preview.html
```

The output is an offline HTML file; the command does not download clinical
evidence or change reviewer records, scans, workspaces or production. It never
overwrites an existing file. The stdout JSON receipt reports 32 captured
registry sources and zero authenticated sources, completed reviews or FDA
forecasts. The original bytes remain outside the repository.

```powershell
python -m unittest discover -s tests -p "test_level16_offline_research_preview.py" -v
python scripts/audit_raas_retirement.py --check
```

These checks establish only the consistency of unreviewed public-source
metadata. Real phase verification, current-status updates, approvals A01–A14,
independent scientific review and staging activation remain separate gates.

## Sixth engineering slice — trigger reassessment when original registry evidence changes

Before activating evidence-driven reassessment, the read-only tool
`scripts/medical/level16_registry_change_triage.py` compares **two complete,
dated and explicitly unreviewed** FOCUS research snapshots. It verifies the
same 32 exact NCTs, 29 provisional mappings, 23 provisional application
cycles, saved receipt cutoff dates and source digests. It never updates a
database, publishes a prediction or automatically carries forward old
scientific signoffs.

A new original registry SHA-256 value creates a review trigger for **all six**
levels, even if the selected public fields appear unchanged. Changes to
trial phase, status, indication, endpoints, results, design, population,
listed documents or contradictions are separately reported with the
affected levels. A registry posted-version rollback also requires review.
Only source-receipt metadata are compared; the tool does not independently
retrieve or authenticate the source bytes. An unchanged comparison does
**not** mean existing research remains current or scientifically approved.

Example comparison of a frozen snapshot against itself (no changes expected):

```powershell
python scripts/medical/level16_registry_change_triage.py --baseline reports/scientific-levels1-6/focus-source-research-20261114.json --candidate reports/scientific-levels1-6/focus-source-research-20261114.json > focus-evidence-change-triage.json
```

For actual new source activity, use a separately captured immutable candidate
snapshot as `--candidate`; retain the baseline untouched. Only source
receipts with an equal or later evidence cutoff and nondecreasing retrieval
time are accepted. Original-document availability/contents, peer-reviewed
trial reports, sponsor disclosures and FDA application relationships still
require separate reconciliation. This tool is not a background monitor or
automated reassessment scheduler.

```powershell
python -m unittest discover -s tests -p "test_level16_registry_change_triage.py" -v
python scripts/audit_raas_retirement.py --check
```

Tests cover 32-trial invariants, changed registry hashes, changed phases
and status, version rollback, snapshot cutoff, metadata mismatch under an
unchanged digest, false source authentication, forged FDA outcomes and
absence of network/production writes. These are software checks only.

## Seventh engineering slice — change triage connected to manual reviewer worklist

The offline-only command `scripts/medical/level16_change_review_worklist.py`
now joins the **existing** registry-change detector to the frozen 32-trial,
192-level unsigned scientific handoff. It recomputes the handoff from
committed source snapshots and checks the packet digest, before accepting a
separately captured *unreviewed* candidate research snapshot.

For each trial, the JSON output identifies the affected Levels 1–6,
unchanged-versus-new registry evidence, and the exact source-review
questions from the original handoff. A newer source byte digest triggers
all six levels. Phase and endpoint changes remain explicit review reasons.
Absent changes do NOT mean scientific adequacy or completed reviews.

To inspect this research worklist from a local checkout:

```powershell
python scripts/medical/level16_change_review_worklist.py --candidate reports/scientific-levels1-6/focus-source-research-20261114.json > focus-level1-6-change-worklist.json
```

The example compares the frozen baseline against itself and should show
no new changes. To detect real changes, first obtain a *new independent
point-in-time* source snapshot and pass it as `--candidate`.
No active source worker or nightly scan is installed by this feature.

**Trust and security boundaries:** this is an unsigned, offline worklist.
It cannot authenticate source bytes or reviewer identity, modify the
append-only protected review store, invalidate an already approved
scientific conclusion, activate staging, queue a background job,
or produce a score or FDA probability. A human reviewer must determine
how new evidence affects old conclusions. A live, transactional
reassessment workflow remains owner-approval gated (A01–A14).

```powershell
python -m unittest discover -s tests -p "test_level16_change_review_worklist.py" -v
python scripts/audit_raas_retirement.py --check
```

Tests verify all 32 NCTs and 192 levels, ORCA-2 and unmapped trial
handling, phase changes, altered source digests, cutoff/identity
rejections, and no fake signoff, reviewer activation or live writes.


## Published efficacy and safety detail — first ORCA-2 clinical review case

As an independent **research-only** input to clinical Levels 3, 4 and 6,
`reports/scientific-levels1-6/orca2-publication-outcomes-20261114.json`
records exactly attributed primary/secondary efficacy and safety findings
from the [2023 JAMA ORCA-2 article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/)
(PMID 37432430, DOI 10.1001/jama.2023.10042). The associated
`scripts/medical/level16_orca2_publication_review.py` checks the exact
reported comparator, endpoint type, arm denominator, effect, safety report,
study metadata and publication identity against a fixed research-only
source layout. It **does not** reproduce an independently verified statistical
analysis or a source attestation. The publication's embedded protocol and
SAP links and the independent review workflow still require examination.

Original Table 2 of the article reports:

| Endpoint | Cytisinicline | Placebo | Published OR (95% CI) |
| --- | --- | --- | --- |
| Primary, 6 weeks (weeks 3–6) | 68/269 (25.3%) | 12/271 (4.4%) | 8.0 (3.9–16.3) |
| Primary, 12 weeks (weeks 9–12) | 88/270 (32.6%) | 19/271 (7.0%) | 6.3 (3.7–11.6) |
| Secondary, 6-week regimen to week 24 (weeks 3–24) | 24/269 (8.9%) | 7/271 (2.6%) | 3.7 (1.5–10.2) |
| Secondary, 12-week regimen to week 24 (weeks 9–24) | 57/270 (21.1%) | 13/271 (4.8%) | 5.3 (2.8–11.1) |

All rates, odds ratios and confidence intervals are **transcribed as
published**, not invented or recalculated FDA acceptance tests. The 2023
paper reports missing smoking assessments classified as smoking, 810
randomized participants but only 618 (76.3%) completing week 24. The
safety analysis population includes 539 cytisinicline-exposed and 270
placebo-exposed participants (a separate placebo enrollee received no drug).

Importantly, the article reports **18 serious adverse events** among 539
cytisinicline-exposed participants versus **3** among 270 placebo-exposed
participants, and reports **0 events judged treatment-related** by
investigators. These statements have different meanings: the latter is an
investigator attribution, not proof that the observed imbalance is harmless.
A death in the 6-week group, treatment discontinuations due to adverse
events (16 vs 4), and rare-event power limitations require independent
benefit–risk review. No unsupported safety causality judgment is made.

A disease-relevance review must examine the surrogate relationship between
biochemically verified abstinence and subsequent health outcomes, durability
beyond 24 weeks, excluded psychiatric/cardiovascular populations, enrolled
racial diversity, treatment adherence, and intensive behavioral support
relative to usual care. The 2023 paper by itself does not establish a
reduction in mortality or a generalizable comparative advantage over
all licensed smoking cessation treatments.

The original ORCA-2 **statistical chronology** is separate: the public
March 2021 protocol describes Hochberg prior to the registry's primary
completion, but final SAP approval relative to actual database lock or
unblinding remains unverified. Statistical questions and clinical findings
must not be collapsed into a numeric FDA forecast.

### Run the added checks

```powershell
python -m unittest discover -s tests -p "test_level16_orca2_publication_review.py" -v
python scripts/medical/level16_orca2_publication_review.py
python scripts/medical/level16_review_handoff.py --nct NCT04576949 --format markdown
```

When generating an unsigned complete research handoff, the source bundle
now binds the journal-reported outcome metadata as a **fifth** snapshot. This
is source-text transcription and consistency checking, not independent
authentication of the publisher's served original bits or a scientific
review signature. No signed clinical assessments exist in these outputs.
