# First-trial prediction research and historical FDA recovery — October 27, 2026

Development only: `pdufa/pdufa-command-center`, branch
`feature/decision-workstream-20261026`, existing draft PR #498.
The latest priority is one real current trial before population-wide processing.
The existing SCIENCE, OUTCOME, MAIN, DECISION, HOP ingestion, and pilot components
were reused. This report supersedes earlier same-day counts where stated.

## First selected trial: actual status

| Item | Observed result |
| --- | --- |
| Current program | COGT PEAK, bezuclastinib plus sunitinib, advanced GIST after imatinib |
| Trial / protocol | NCT05208047 / CGT9486-21-301 |
| Exact application key | `APPLICATION\|COGT\|BEZUCLASTINIB_GIST_20261130` |
| Target | November 30, 2026, sponsor reported; current FDA application/cycle not independently reconciled |
| Saved record | `PEAK-NCT05208047-20261027-research-001` |
| Evidence cutoff | October 27, 2026, 23:19:59 UTC |
| Preliminary outcome / processing status | **INDETERMINATE / INCOMPLETE** |
| Evidence observations | 9 source texts examined, 2 unavailable sources, 8 unverified publication dates |
| Findings / comparisons | 9 cited qualitative findings / 3 selected historical contexts |
| Scientific assessment execution | **0/40 assessments; 0/20 reviewed levels; 0/8 represented layers** |
| Independently adjudicated eligible historical cycles | **0** |
| Numerical approval/nonapproval probability / confidence | Unavailable / unavailable |
| Full end-to-end cases completed / saved research abstentions | **0 / 1** |
| Additional trials queued | **0**; controlled batch processing remains disabled |

The saved record is real case research, not a simulated prediction. The new
reusable evaluator validates identity, citation availability, chronology,
supporting/opposing finding references, optional existing SCIENCE dossier
association, and duration consistency. Its present method is an evidence audit
that abstains. It is not a trained or validated PASS/FAIL classifier. Completing
the whole historical database is not required for this case; the immediate
obstacles are the case-specific scientific and source requirements below.

### Source findings and limitations

Issuer disclosures report PEAK PFS HR 0.50 (95% CI 0.39–0.65), medians
16.5 versus 9.2 months, and a response benefit. SEC-hosted issuer material
describes 413 randomized participants (204/209), with a different safety
population of 204/208. Supporting findings concern randomized design and
reported efficacy. Opposing/uncertain findings include hepatic laboratory
toxicity, treatment discontinuation, immature overall survival, and the
difference between filing acceptance and approval. These clinical quantities
are not FDA approval probabilities. Sponsor/SEC hosting does not establish
independent scientific or FDA endorsement.

The three historical contexts are sunitinib in GIST (NDA021938), regorafenib
GRID (application number unresolved), and ripretinib INVICTUS (NDA213973).
Original FDA letter text or official indication records support the described
approval claims. Differences in treatment line, placebo versus active control,
mechanism, endpoint and patient population remain explicit. The sunitinib TTP
endpoint is not renamed PFS, and its separate RCC application/accelerated
approval is not attributed to GIST. The retrospective ripretinib review is
context for the 2026 case, not a predecision feature for a 2020 backtest.

These deliberately selected methodology examples are **excluded from independent
validation**. Complete cycle histories, original retained documents and
publication chronology have not been independently adjudicated. An FDA source
text observation is not the same thing as an eligible verified training label.

All exact citations, publication-date missingness, source access status,
limitations and findings are saved in
`new-platform/frontend/data/peak-pilot-run-20261027.json`. The computed result,
input SHA-256, evaluation timestamp and limited evaluator timing are saved in
`research/first-trial/peak-pilot-evaluation-20261027.json`.
The dashboard's **FIRST TRIAL ASSESSMENT** link opens `/prediction-pilot`, which
renders that actual saved input through the evaluator. Source provenance,
historical comparisons and the preserved earlier manual preview use collapsed
details. Viewing the record starts no fetch, job, scan, database write or trade.

### Timing: no 45-minute claim

Full evidence-collection, comparison, scientific-review and prediction-generation
durations were not instrumented from the beginning. Their stage/total fields
remain null and the UI displays **Not measured**. A partial remaining-work log
started at 23:15:41.610256 UTC and excludes earlier research; it cannot establish
the full processing duration.

The saved evaluation took **1.6334939999999847 ms** to validate an already
assembled in-memory record and calculate abstention. This excludes evidence
collection and scientific investigation. It does not demonstrate the 45-minute
assessment target or a completed prediction workflow.

### Precise blockers and next eligible work

1. The repository implements the 20-level / eight-layer / 40-assessment contract,
   but the reviewed scientific definitions and evaluation criteria were not
   found. A read-only connected project tracker repeated the requirement without
   those definitions. Supply the existing reviewed protocol/criteria; do not
   invent a replacement taxonomy or mark 40 placeholders complete.
2. Retrieve and independently review PEAK's original protocol/SAP, patient flow,
   censoring, missing-data and multiplicity evidence. The ASCO full text returned
   403 and the ClinicalTrials.gov API was unavailable; its study page exposed
   only a shell. NCI supplies additional official identity context.
3. Reconcile the exact current NDA, review correspondence, CMC/facility evidence,
   and persistent program-registry identity. No fabricated `PDUFA-...` ID was
   assigned and no production registry/database was queried or modified.
4. Independently adjudicate the selected historical application/cycle/action and
   source-publication evidence, and conduct a source-bound scientific challenge.
   Document a justified preliminary classification method before adding PASS/FAIL
   outputs. Numeric probabilities need additional calibration evidence.
5. Re-run an instrumented complete assessment with original stage timings. Only
   after the first case passes all scientific/source/workflow checks should a
   controlled GEM JR → GEM → WT → other eligible Pipeline queue be activated.

## Historical FDA development completed in parallel

Three existing GitHub Actions artifacts were recovered before expiration, pinned
to repository, run, artifact ID, source commit, creation time and ZIP/member
SHA-256. The exact recovered ZIPs and provenance manifest are committed under
`research/fda/recovered-20261027/`. They contain **derived source metadata**, not
original FDA manifest/archive/PDF bytes. Recovered-row digests are explicitly
separate from unreproducible claimed original-row hashes.

`scripts/ingest_hop_recovered_metadata.py` performs a deterministic read-only
audit or creates an explicitly named, new local research SQLite database. It
does not read environment database URLs, fetch network data, overwrite an
existing file, or promote labels. Safe ZIP reads, bounded inputs, pinned
provenance, cross-artifact joins and exclusive no-symlink output are tested.

| Imported observations | Count / range |
| --- | --- |
| Published letters | 458: 445 COMPLETE RESPONSE; 13 other/unclassified |
| Published-letter date strings | 458 parse; March 15, 2002–August 7, 2026 |
| Approved-centric registry applications | 29,416: 23,023 ANDA; 5,908 NDA; 485 BLA |
| Submission observations | 188,890; not assumed distinct review cycles |
| Published submission status codes | AP 187,733; TA 1,155; CR 1; missing 1 |
| Valid submission dates | 188,883; February 9, 1939–October 21, 2026; 7 unknown/invalid |
| Registry applications lacking submission metadata | 2,706 |
| Action-review / PDF-check / worksheet observations | 458 / 458 / 154; overlapping letter worklists, not extra decisions |
| CRL-to-registry linkage candidates | 334 present; 107 not found; 15 unresolved; 2 ambiguous |
| Independently verified eligible PASS / FAIL | **0 / 0** |
| Adjudicated review cycles / usable predecision cases / backtest-eligible decisions | **0 / 0 / 0** |

The actual isolated database is
`work/phase2-20261027/historical-source-metadata.sqlite3` (121,782,272 bytes).
It passed SQLite `integrity_check` and has zero foreign-key violations.
Its 30,912 generic recovered JSON rows include derived worklists and must not
be described as independent FDA decisions. The database is an ignored local
artifact; the committed inputs, importer and audit make it reproducible.
Drug/indication/trial/PDUFA/source-publication/review-cycle fields remain NULL
where missing. A source `CR` code is not automatically a CRL, and registry
presence does not label an earlier CRL cycle approved.

Backend comparators now deduplicate by explicit application/review cycle,
quarantine conflicting claims before ranking, and preserve distinct cycles
without treating them as independent cases. Frontend forecast diagnostics add
tie-aware AUROC and traceable per-forecast proper-score errors. Single-class
AUROC, abstention coverage without a full universe/policy, and uncertainty
intervals without a dependence-aware plan remain unavailable. Arithmetic tests
are not FDA accuracy validation; no real performance improvement is claimed.

Future bulk collectors have an optional `--retain-originals-dir NEWPATH` that
keeps exact manifest/ZIP bytes and post-acquisition receipts. Defaults and live
workflows were not changed; the flag is not enabled. Direct shell FDA download
still fails at proxy CONNECT with `Tunnel connection failed: 403 Forbidden`.
Use supported host allowlisting or reviewed offline originals. No proxy/TLS or
access-control bypass was attempted.

## Preserved concurrent work and verification

All **84** remote commits from `5edbb9a5` through `2ffbfba0` were integrated
without conflict using a merge on the same development branch (`bc8aefdc`).
They add source staging, reconciliation, review packets, evidence audits and
readiness checks. Existing changes were not overwritten; `dd4f9f65` and
`e5800a07` remain ancestors. Their research-only workflow is preserved as
received; no operational scan schedule was edited or dispatched.

Before integration, full checks passed: **2,549 Python tests**, one existing
opt-in skip, 557 subtests, 13 existing dependency/Pandas warnings; **664 frontend
tests**, TypeScript and the Next.js build. A real-case integrity regression
also reconciles the dashboard input bytes/hash and every stored computed result.
Post-integration verification:

| Check | Result |
| --- | --- |
| Complete default pytest | **2,611 passed, 1 existing skipped; 557 subtests passed**, 13 existing warnings |
| Complete frontend suite | **665 passed, 0 failures, 0 skips** |
| TypeScript without incremental cache | Passed |
| Local Next.js production build | Passed; not a deployment |
| Built page HTTP verification | HTTP 200; actual saved run, abstention, incomplete SCIENCE, source notes and unmeasured timing displayed |
| Saved real-case integrity | Input SHA-256 and every evaluator result match the stored result at its recorded evaluation time |
| Independent implementation review | No material case-data, identity, display or restriction regression found |
| Recovered research SQLite | Integrity `ok`; zero foreign-key violations; exact source counts reconciled |
| Whitespace/source checks | Passed |

Synthetic regression fixtures verify arithmetic and software contracts only.
The real saved-record integrity test verifies reproducibility, not truth or
prediction accuracy. Local HTTP checks do not establish browser interaction,
live dashboard authentication or a remotely deployed version.

The source implementation commits are `bd26a4bd`, `1a97c81a`, `24b96af4`,
`b6e10d4f`, `a6cb26bd`, with remote work preserved by `bc8aefdc`; later report/UI
verification commits are visible in PR #498. Push only the exact feature ref
with a normal fast-forward push; do not force-push concurrent work.

### Development preview access

The connected Vercel deployment listing for project `pdufa-new-dashboard` and the
feature branch returned **403 forbidden: “You don't have permission to list the
deployment.”** No authenticated Vercel CLI is installed. Do not retry unchanged,
disable protection, change production configuration, or request a long-lived
secret. After pushing, inspect GitHub's existing Vercel status/PR comment for
the feature-preview URL and attempt ordinary authorized preview verification.
If access remains blocked, the remote-display milestone stays incomplete.
No manual production deployment is performed.

No existing GEM JR/GEM/WT restriction, FS/FA association, live source dataset,
production configuration/database, trading permission or order was changed.
No main merge/push, production deployment or new paid resource is authorized.
