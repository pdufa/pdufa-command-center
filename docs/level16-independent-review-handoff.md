# Level 1–6 independent clinical reviewer handoff — research only

> **ARCHIVED EXTERNAL-REVIEW DESIGN — NOT AN ACTIVE REQUIREMENT (owner decision, November 13, 2026).**
> All outside clinical, statistical, source-attestation, challenger, regulatory,
> qualification and multi-person adjudication gates described below were
> **withdrawn for owner assessments at Levels 1–20**. The owner alone checks
> and accepts results. The former five-person/A01–A14 reviewer scheme and
> its old synthetic tests are historical/disabled engineering, not owner
> work blockers. Use `AGENTS.md` (top directive),
> `infra/assessment/sole-owner-levels1-20.json` and
> `docs/level16-sole-owner-operation.md` for active policy.
> Existing security, evidence honesty, cutoff and deployment controls remain.
> No external review has been falsely recorded as completed.


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


## Next case: ORCA-3 replication study (NCT05206370) — source-reported clinical facts

The second same-indication clinical case is **ORCA-3**, also from Achieve
Life Sciences, but with a **different exact NCT, trial population, protocol,
SAP and original 2025 study report**. Research must never silently replace
ORCA-2 evidence with ORCA-3 or pool the two studies as if one randomized trial.

Original source: [Rigotti et al, JAMA Internal Medicine, published online
April 21, 2025, doi:10.1001/jamainternmed.2025.0628,
PMID 40257755](https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700/),
Results / Tables 2–3 / Limitations. These are public reported facts; neither
the journal nor ClinicalTrials.gov data has yet been independently authenticated
as original evidence by the approved verifier.

Study source description: 792 randomized in three groups (6-week cytisinicline
263; 12-week cytisinicline 264; placebo 265), 20 sites, double blind,
behavioral support in all arms, 628 completing week-24 follow-up. The treated
safety population is **785**, not 792 (523 in the combined cytisinicline
arms, 262 placebo). Missing smoking outcomes counted as smoking.

| Publication Table 2 outcome | Cytisinicline | Placebo | Table 2 reported OR, 95% CI |
| --- | --- | --- | --- |
| PRIMARY 6-week course, weeks 3–6 | 39/263 (14.8%) | 16/265 (6.0%) | 2.9 (1.5–5.6) |
| PRIMARY 12-week course, weeks 9–12 | 80/264 (30.3%) | 25/265 (9.4%) | 4.4 (2.6–7.3) |
| SECONDARY 6-week course, weeks 3–24 | 18/263 (6.8%) | 3/265 (1.1%) | 6.3 (1.9–34.6), per Table 2 |
| SECONDARY 12-week course, weeks 9–24 | 54/264 (20.5%) | 11/265 (4.2%) | 5.8 (2.9–12.5), per Table 2 |

**Original-article source discrepancy:** The article's narrative reports
lower CI bound **1.8** for the 6-week secondary outcome and upper CI bound
**12.4** for the 12-week secondary outcome, while the HTML Table 2 displays
**1.9** and **12.5**, respectively. The research ledger records *both* and
requires original publisher/source resolution; it does not call either value
a confirmed analysis error or assume clinical/fda materiality.

The publication records 16/523 serious treatment-emergent adverse events
in the two cytisinicline arms versus 8/262 placebo; 9/523 versus 3/262
discontinuations for adverse events; and four deaths in the cytisinicline
arms. The investigators determined none of the serious adverse events
treatment-related and considered the deaths unrelated or unlikely related.
These attribution statements are **not proof of absence of risk**.
A qualified reviewer must examine the actual case-level evidence and the
comparative population/exposure context.

Limitations include low representation of non-White participants, exclusion
of smokers using fewer than 10 cigarettes/day, selected psychiatric and
cardiovascular exclusions, relatively intensive behavioral support, and
only 24 weeks of abstinence and 12 weeks of treatment-related safety
observation.

Dedicated sources and checks:

```powershell
python scripts/medical/level16_orca3_publication_review.py
python -m unittest discover -s tests -p "test_level16_orca3_publication_review.py" -v
python scripts/medical/level16_review_handoff.py --nct NCT05206370 --format markdown
```

The original article's supplemental **protocol and SAP** are linked in the
public PMC article. Their dated versions and complete amendments have not
been independently reconciled in this clinical research case. Genuine source
verification, separate statistics review, disease-relevance review,
independent challenge and adjudication remain blocked by the existing A01–A14
owner authorization requirements.

ORCA-3's Levels **3, 4 and 6** research handoff contains the four published
endpoints, reported safety and population, clinical limitations and the
unresolved original-source CI discrepancy, all marked **UNREVIEWED**.
The Level 5 SAP/statistical chronology is **not** presumed to be the same as
ORCA-2's merely because the drug, trial sponsor and primary outcome are similar.
No FDA prediction, score, signed review or blinded retrospective analysis
is generated from either article.


## Third evidence-detailed trial — MAPLE-HCM (NCT05767346), distinct disease and continuous outcome

**Phase-first research only; no source signed, no independent assessment, no score
or FDA prediction.** MAPLE-HCM is Cytokinetics' Phase 3 aficamten-versus-
metoprolol double-blind, double-dummy, **active-comparator** study in
symptomatic obstructive hypertrophic cardiomyopathy. It is NOT SEQUOIA-HCM
and must not inherit another NCT's evidence.

**Original peer-reviewed abstract**:
[NEJM, Garcia-Pavia et al., posted August 30, 2025,
doi:10.1056/NEJMoa2504654](https://www.nejm.org/doi/10.1056/NEJMoa2504654)
(PubMed PMID 40888697). The study reports 175 randomized patients,
88 aficamten and 87 metoprolol, each with matching placebo, treated
over 24 weeks. Its **primary endpoint is a continuous exercise-capacity
measure**, not a binary abstinence or response rate:

| NEJM abstract, week 24 peak oxygen uptake change | Reported value (mL/kg/min) |
| --- | --- |
| Aficamten mean change | +1.1 (95% CI +0.5 to +1.7) |
| Metoprolol mean change | −1.2 (95% CI −1.7 to −0.8) |
| Adjusted between-group difference | +2.3 (95% CI +1.5 to +3.1), P<0.001 |

**Secondary cardiology-society synopsis (not original publisher's full
tables):** [American College of Cardiology trial summary,
posted September 24, 2025; updated November 9,
2025](https://www.acc.org/latest-in-cardiology/clinical-trials/2025/09/23/17/49/maple-hcm).
The ACC reports between-group improvements in NYHA class (+25 percentage
points), KCCQ-CSS (+6.9 points), Valsalva LVOT gradient (−34.9 mm Hg),
NT-proBNP proportional change (ratio 0.19) and left atrial volume index
(−7.0 mL/m²). Its left ventricular mass index comparison was −4.9 g/m²
(95% CI −11.7 to 2.0; P=0.16), **not a reported significant improvement**.
Every estimate retains its **own unit, source role and endpoint type**.

ACC also summarizes serious adverse events in **7/88 aficamten** versus
**6/87 metoprolol** recipients, adverse events requiring dose reduction
in 1 versus 4 participants, and a mean between-arm LVEF change of −4.2
percentage points (95% CI −5.3 to −3.1). One death was reported in the
aficamten arm. These published observations require specialist safety review;
they do not justify asserting causal attribution or long-term safety.

**Original-source gaps requiring review:** exact full NEJM tables and
supplements, registered protocol and SAP version sequence, prespecified
endpoint hierarchy and multiplicity, CPET missingness, dose titration,
withdrawal from previous beta blockers, arrhythmia/LVEF exclusion criteria,
LVEF monitoring and recovery, longer-term durability, adverse-event
case evidence, exact application-cycle mapping, and authenticated source
provenance. Neither the 175-person sample nor 24 weeks establishes
mortality benefit or long-term safety.

The source-separated, unit-aware record is
`reports/scientific-levels1-6/maple-hcm-source-review-20261114.json`.
It is validated by `scripts/medical/level16_maple_hcm_publication_review.py`
and imported into **Levels 3, 4 and 6 only** of
`scripts/medical/level16_review_handoff.py`.
Level 5 original statistical plan is still unreviewed; do not infer one from
other myosin inhibitor studies. The exact 32-NCT cohort and provisional
application crosswalk are unchanged. The offline handoff bundle now hashes
**seven** source metadata snapshots; hash equality means only local research
snapshot consistency.

```powershell
python -m unittest discover -s tests -p "test_level16_maple_hcm_publication_review.py" -v
python scripts/medical/level16_maple_hcm_publication_review.py
python scripts/medical/level16_review_handoff.py --nct NCT05767346 --format markdown
```

No human reviewer, original-source attestor or application-cycle verifier has
been authorized by these commands. No deployment, scoring, clinical
adjudication or FDA prediction should result from running them.


## Fourth evidence-detailed case: Vera ORIGIN 3 IgA nephropathy, NCT04716231

**Public-source research, not independently authenticated or clinically
adjudicated; no FDA approval probability, no retrospective blind assessment.**

The exact NCT is a multi-part record with an earlier Phase 2b portion and a
separate pivotal Phase 3 portion. The Phase 3 publication sequence must not
be merged into Phase 2b data or incorrectly presented as two independent
Phase 3 replication trials. Original protocol, SAP and trial mapping still
require independent reconciliation.

Two *original peer-reviewed research articles on the same Phase 3 trial*
were retrieved:

1. [NEJM original November 6, 2025 interim analysis (DOI:
   10.1056/NEJMoa2510198, PMID 41196369)](https://www.nejm.org/doi/full/10.1056/NEJMoa2510198).
   Its **prespecified week-36 interim primary endpoint** is change in
   24-hour urinary protein-to-creatinine ratio (UPCR), a proteinuria biomarker.
   The evaluated interim cohort was **203** patients (106 atacicept, 97
   placebo). The published relative reduction was **45.7% vs 6.8%**,
   with a *source-reported geometric-mean between-arm contrast* of **41.8
   percentage points** (95% CI 28.9–52.3; P<0.001). That contrast is an
   original reported model result, **not** an arithmetic subtraction of
   45.7% minus 6.8%. Any adverse events were reported in **59.3% vs 50.0%**
   of the interim populations. A biomarker response alone does not prove
   long-term preservation of kidney function or reduction in renal failure.

2. [NEJM original October 22, 2026 final efficacy analysis (DOI:
   10.1056/NEJMoa2610103, PMID 42911181)](https://www.nejm.org/doi/full/10.1056/NEJMoa2610103).
   There were **431 randomized**; **428 treated** (214 each group).
   The reported **prespecified secondary** eGFR change at week 52 was
   −0.11 mL/min/1.73m² with atacicept and −5.69 with placebo, for an
   adjusted between-group difference of **+5.58 mL/min/1.73m²**
   (95% CI 3.68–7.48; P<0.001).
   The reported annualized eGFR slope through week 104 was −0.60 vs
   −5.60 mL/min/1.73m²/year, difference **+5.00**
   (95% CI 3.55–6.45; P<0.001).
   The reported kidney-progression composite occurred in 11 patients
   (5.1%) vs 38 (17.8%), published HR 0.24
   (95% CI 0.12–0.48). This is a **composite**, not a claim of mortality
   reduction. Serious adverse events were **7.0% vs 15.4%**, and one death
   was reported in the placebo group. These results still require
   independent endpoint, censoring, multiplicity, and safety review.

**Do not combine populations:** the original 203-person interim analysis is
not identical to the later randomized 431/treated 428 population; numerical
AE denominators and event rates cannot be silently pooled.

**Critical outcome chronology:** The final eGFR paper appeared
**October 22, 2026**. It is newly published later evidence relative to
the 2025 interim paper and is **not valid input** into any historical blind
backtest or FDA prediction purportedly made before that date. The current
2026-11-14 research packet is openly outcome-exposed; no PDUFA decision or
FDA-approved status is inferred from it.

**Per-level review intent:** Level 1 must authenticate both original
publisher versions, registration, amendments and source receipts. Level 2
must reconcile the multi-part Phase 2b/Phase 3 record and indication-specific
cohort. Level 3 distinguishes the interim **primary UPCR** biomarker from
later **secondary eGFR change, eGFR slope, kidney-progression composite**
and safety. Level 4 reviews comparator/background therapy, allocation,
adherence, missingness and protocol conduct. Level 5 independently verifies
interim/final SAP versions, alpha spending, hierarchy, estimands, censoring,
database lock and unblinding. Level 6 evaluates UPCR as an intermediate
surrogate versus clinically meaningful loss of kidney function, need for
dialysis/transplant, benefits, harms and follow-up.

Machine-readable source and conservative validator:

```powershell
python scripts/medical/level16_origin3_renal_publication.py
python -m unittest discover -s tests -p "test_level16_origin3_renal_publication.py" -v
python scripts/medical/level16_review_handoff.py --nct NCT04716231 --format markdown
```

Only the actual frozen FOCUS NCT NCT04716231 receives this original
kidney evidence; the other 31 trials retain their own independent sources
and initial readiness gates. The unsigned research handoff now binds an
**eighth** fixed metadata source. Passing software tests proves neither
original-source authenticity nor efficacy/safety adjudication. A01–A14
owner decisions, authorized source verification and qualified reviewers
remain outstanding, with all code in draft PR #1181 and no site deployment.
