# PR #1200 scientific development verification — 2026-11-14

Development only. No merge, deployment, production-data mutation, trading activation,
owner signoff or validated FDA forecast. This report supersedes the **status claims**
of older research reports, not their frozen evidence or histories. Governance is
`AGENTS.md` and `infra/assessment/sole-owner-levels1-20.json`: the owner may review
all levels; outside reviewers and source attestors are not required.

## What changed

Reviewed branch commits through `227347a`. Fixed strict date handling at the saved
registry boundary: complete timezone-aware database timestamps are accepted and
normalized to UTC; malformed date prefixes, naive external timestamps and invalid
offsets are rejected. Publication and scientific review dates remain strict dates.
The earlier CI date-object failures were already repaired before `227347a`.

The packaged FOCUS roster initially failed its equality regression. Reused the
already-published main-branch frontend snapshot and its existing backend copy,
with an assertion that all 32 NCT/company identities were unchanged. No list or
spreadsheet membership changed. This avoids reverting the newer snapshot.

Saved registry eligibility, indication, design, enrollment and endpoint metadata
now populate distinct per-level inventories. Each observation carries exact NCT,
source URL, publication date, actual retrieval time and an allowlisted summary
hash. That hash is explicitly **not an original-document authentication hash**.
Metadata is AVAILABLE_NOT_REVIEWED, never an invented scientific judgment.

Reviewed source-workspace evidence retains reviewer identity, source verification
method/actor/date, rationale and excerpt. Optional retrieval receipts are retained;
when supplied they must fall between publication and source verification, before
review and cutoff. Legacy reviews without receipts explicitly say NOT_RECORDED;
no retrieval date is backfilled. Conflicting reviews are rejected. Official study,
API and protocol/SAP CDN URLs must identify the correct exact ASCII NCT.

New Level 3 and Level 4 descriptive calculations consume only accepted reviewed
binary-event records with retrieval provenance, common endpoint, population and
time window, distinct arm labels and valid integer event counts/denominators.
They report arm event rates, absolute risk difference and risk ratio. Zero
comparator events produce an undefined ratio, without an invented continuity
correction. No interval, multiplicity adjustment, clinical significance, composite
score, exposure-adjusted rate or FDA probability is inferred. These are transparent
arithmetic operations, not validated whole-level assessments.

New history entries retain all six scientific contracts and evidence inventories,
including descriptive calculations. Evidence changes append versions rather than
rewrite existing entries. Older entries retain their original compact schema.
POOL, FOCUS and PAST exact-program intake displays now expose Levels 2–6 criterion
states and source/review provenance alongside Level 1, with malformed responses
failing closed. PAST outcome linkage stays unverified where only ticker/date match;
no outcome records enter scientific calculations.

## Level status and exact next work

| Level | Implemented capability | Scientific completion blocker / next action |
|---|---|---|
| 1 | Exact identity, phase/status, UTC chronology, inventory and provenance | Intake only. Review original source discrepancies and record actual owner conclusions; metadata is not source/clinical validation. |
| 2 | Five design criteria, original document URL checks, registry design/eligibility/enrollment observations, reviewed evidence contract | Original protocol/version/amendment adjudication, execution-versus-plan bias assessment and sample-size rationale remain unreviewed; complete original-document extraction and owner review. |
| 3 | Five statistical/efficacy criteria; gated binary contrasts and provenance | SAP estimand, population, missing-data and multiplicity adjudication and indication-appropriate uncertainty methods remain incomplete. Review source-linked counts before any real-trial contrast is presented as reviewed science. |
| 4 | Five safety criteria; gated AE/SAE/discontinuation binary contrasts | Source-reviewed real safety counts, exposure windows, event definitions, follow-up and clinical benefit-risk judgments are missing. Counts alone cannot establish drug causation or benefit-risk. |
| 5 | Five indication-specific criteria and indication/population inventory | Implement and document disease/subtype/setting-specific comparators, outcome interpretation and meaningfulness rules from applicable sources; record actual owner judgments. No generic weighted replacement. |
| 6 | Five regulatory criteria and phase-aware dossier expectations | Verified trial–indication–application–review-cycle linkage, original agency communications, CMC/inspection and labeling evidence are missing. Do not map by company alone; unavailable/nonpublic material remains unknown. |

All six scientific statuses remain NOT_VERIFIED. Scientific scores remain null /
NOT_VALIDATED. FDA predictions remain ABSTAIN. A reviewed-criterion completeness
flag never changes those statuses. Legacy assessment-runtime v2 source-audit level
numbers have different meanings from these six scientific contracts; existing
versioned results are preserved and must not be relabeled or compared as the same
scientific model. Unified execution/version migration is still required before
claiming the live workbench runs these scientific engines.

## Real evidence counts and local execution

The preserved source-research manifest covers **32 unique real trials**: registry
32; original protocol/SAP documents across 12; posted registry results 12; indexed
journal records across 15; retrieved public full texts across 10; exact-NCT FDA
label leads 2. These are documentary availability counts, not validated claims.
No new source collection is represented as an owner review.

Freshly fetched NCT04576949 through the existing official registry collector.
Stored the real summary and source material in an isolated, in-memory SQLite
FullTrialRecord; executed the existing candidate service; saved and retrieved all
six contracts and one history record. Receipt:
`reports/scientific-levels1-6/pr1200-local-registry-persistence-20261114.json`.
No production database or source-workspace file was written.

- Real trials with available evidence in the preserved manifest: **32**.
- Fresh real-trial local persistence executions in this development run: **1**.
- Trials with completed verified scientific evidence reviews demonstrated: **0**.
- Trials with completed validated six-level assessments demonstrated: **0**.
- Validated/calibrated FDA predictive models demonstrated: **0** (ABSTAIN).

Automated exact identity/chronology checks are distinct from scientific evidence
review. No production-wide count was queried or inferred from these local counts.

## Historical protection and remaining integration

Source receipt chronology, strict cutoff tests and the existing immutable runtime
snapshot tests remain required. Current saved registry data cannot reconstruct an
earlier snapshot. A post-cutoff source, retrieval, verification or review is
ineligible. Existing outcome exposure remains disclosed; hiding known outcomes
cannot create genuinely blind calibration cases. Keep outcomes in a separate
comparison step after prediction persistence.

The candidate service currently assesses at its current source date; it does not
expose a historical scientific execution API. The older runtime's blind source
isolation remains separate. Next integration must bind these new scientific
contracts to immutable point-in-time inputs and owner-authorized execution, with
semantic engine versions and full current/blind persistence tests. Do not claim
these additions activated production or finished application/outcome linkage.

## Extension through Level 20

Levels 7–20 are **unimplemented**, not implicitly complete because governance
covers them. Do not choose permanent scientific meanings from UI labels alone.
For each future level, define its question, scientific method, phase/indication
applicability, evidence contract, limitations and acceptance examples first.
Suggested capabilities to allocate in an owner-approved level specification:

| Proposed capability family (no completed level assignment) | Sources and implementation dependencies | Validation gate |
|---|---|---|
| Replication, external validity and subgroups | Independent trial records, populations, interaction estimates, indication dossiers | Correct cohorts, heterogeneity, prespecified versus exploratory findings |
| Durability, patient benefit and comparative care | Long-term follow-up, patient-reported outcomes, disease guidelines and contemporaneous comparators | Indication-specific interpretation and source-reviewed thresholds |
| Clinical pharmacology and dose/exposure | PK/PD, exposure-response, interactions, special populations | Appropriate units, model assumptions, population applicability |
| Manufacturing, inspections and regulatory cycle | Exact application IDs, official public review files, original communications and dated labels | No company-only linkage; private/unavailable facts stay unknown |
| Evidence synthesis and decision uncertainty | Versioned accepted findings, contradiction ledger, transparent synthesis rules | No arbitrary composite or copied legacy score |
| Prospective prediction and outcome/timing evaluation | Frozen outcome-unexposed cohorts, separate adjudicated outcomes, model artifacts | Out-of-sample calibration, proper uncertainty, leakage tests and model-specific abstention |
| Ongoing surveillance and reassessment | Verified new source versions, idempotent event keys, immutable history | No reassessment from unverified news; preserve prior predictions and provenance |

Implement shared source/review receipts, per-indication methods, execution jobs,
immutable input/output versions, authentication and UI history before adding new
numbered buttons. Retain owner-only review governance through Level 20. Missing
outside people is not a blocker; missing factual evidence and unimplemented
scientific methods are.

## Verification results

- Full backend: **1,336 passed, 2 skipped**, plus 28 passing subtests.
- Frontend: **162 test files passed**, zero failures.
- TypeScript `tsc --noEmit`: passed.
- Next.js production build: passed locally; no deployment invoked.
- Additional repository integration regressions: **27 passed**.
- Permanent retirement audit: passed, zero active retired dependencies.
- Live official-registry fetch plus isolated local save/readback: passed for
  NCT04576949; all six contracts retained, zero scientific reviews invented.

Initial local backend failure was the snapshot mismatch; repaired while retaining
all trial identities. Intermediate new-test failures exposed missing persisted
contracts, a UI fixture assertion formatting dependency and a TypeScript narrowing
error; all repaired without deleting or relaxing tests. Older failed Actions run
43633071223 had three date-object cutoff regressions already fixed by the supplied
branch commits; the `227347a` Actions checks passed. New push checks must still be
reported from the actual delivered commit, not inferred from these older runs.

Vercel automatic Git deployment is explicitly disabled **only for this development
branch** in its frontend `vercel.json`, per the published branch-specific
`git.deploymentEnabled` setting. Existing cron schedules and other branches are
unchanged. This allows draft-PR CI without requesting a preview or production
release. No platform project setting or production configuration was mutated.

A broad legacy repository-root pytest invocation also encountered **34 collection
errors** from missing legacy dependencies (including Streamlit, requests, Jinja2,
Google/JWT packages) and the removed `collect_focus_survey_evidence` module. It is
not a passing whole-repository suite. The retired survey engine was not restored.
The active FastAPI suite and the explicitly relevant repository integration tests
were run separately with their actual results above. No test was removed,
skipped newly, or weakened to hide that legacy collection limitation.

Delivered-commit CI additionally detected a stale generated package in Linux and
Windows phase-first checks (run 43635201787). Regenerated it with the unchanged
exporter: only `rosterAsOf` changed from November 13 to November 14; retained
source digests and clinical observations did not change. Export reproducibility
and all **5 exporter regressions passed** before the corrective commit.
