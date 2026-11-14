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
