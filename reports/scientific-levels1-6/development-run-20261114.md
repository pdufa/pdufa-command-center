# Levels 1–6 evidence preparation — 2026-11-14

Engineering delivery only. No live identity provider, staging activation, deployment, production migration, scientific signoff or FDA forecast.

Baseline reconciled against commit `9c0f733454a2ee95f8eb370424c1ded73c62e9d5` and draft PR #1181: 137 applicable tests; 32 registry packets; two pilot PDFs; 12 registry result packets; 23 protocol/SAP leads across 12 trials; 37 publication links/36 unique PMIDs; preliminary observations for all 32 trials; zero authenticated sources and zero adjudicated assessments. Existing 34 original files matched retained digests. Previous research snapshots were preserved.

This run refreshed 32 exact-NCT registry packets at a 2026-11-14 current-source cutoff, retrieved all 23 registered protocol/SAP PDFs, 36 PubMed records and 12 public full texts (five other full-text endpoints failed), and searched public FDA labels for all 32 NCTs. Two labels contained exact NCT text: NCT02500381 and NCT04716231. For unmapped trials, drug-context FDA searches and 12 original public label/letter PDFs were collected; no application cycle was independently verified. These are research observations, not authenticated originals or qualified assessments.

The 33 MB combined NCT04716231 PDF was separately bounded to 40 MiB and stored in private research quarantine after one transient 503 response. It was not ingested into staging; the standard collector remains limited to 16 MiB. All raw originals, full texts, extracted document text and acquisition manifests remain outside Git with restricted file permissions. Only public metadata, receipts, bounded factual observations and preliminary worksheets are committed.

| Level | Engineering | Current clinical evidence coverage | Scientific status |
|---|---|---|---|
| 1 | Existing provenance/authentication boundaries reused; new receipt/report safeguards tested | Registry 32/32; protocol/SAP PDFs across 12/32 | Zero independent source authentications |
| 2 | Phase-first identity/crosswalk controls retained | Registry phase, status, indication and population for 32/32, unreviewed | Current source reconciliation outstanding; 29 trials/23 cycles remain provisional |
| 3 | Separate results observations and conservative abstention | Posted registry results 12/32; dated indexed journal records across 15/32; public full texts across 10/32 | No independently established efficacy conclusions; endpoint disagreements remain explicit |
| 4 | Protocol receipts/versions and design questions integrated | Original registered protocols 12/32; registry designs 32/32 | Amendment completeness and actual execution unverified |
| 5 | Original SAP receipts, statistical questions and cutoff checks | SAPs 12/32 | Prespecification, timing, multiplicity, populations and analyses need biostatistical review |
| 6 | Disease-specific endpoint questions and limitations for all 32 | Registered endpoints 32/32; four trials have additional bounded report observations | Endpoint importance and benefit/risk not independently adjudicated |

There are 192 separate preliminary worksheets. All 32 trials await additional evidence and independent review. Registry coverage is not evidence completeness. The 35 records with exact publication dates by cutoff are indexing/collection records; one design-paper date was imprecise and excluded from dated coverage. Publication links may describe background, prior phases, protocols or secondary analyses. Verified primary trial-report count remains zero pending source/reviewer verification. No trial/application crosswalk changes were made, including NCT05031780, NCT06747468 and NCT06553768.

Deliverables:

- `focus-source-research-20261114.json`: per-trial/per-level evidence, factual observations, research interpretation, reasons, contradictions, risks, missing/not-yet-expected evidence and review requirements.
- `scientific-coverage-20261114.json` and `.md`: source-kind coverage; all 32 records.
- `all-nct-research-readiness-20261114.md`: six-level readiness for every NCT.
- `first-clinical-case-preparation-20261114.md`: ORCA-2 first-review candidate and unresolved SAP timing question.
- `unmapped-application-research-20261114.json`: FDA drug context and uncertainty; no invented mappings.
- `owner-approval-resolution-20261114.json` and `docs/level16-owner-approval-resolution-20261114.md`: all A01–A14 decisions, checks, options/costs, missing real-world information and minimum owner actions. None approved.
- Offline preview shows escaped preliminary research interpretations, source observations, limitations and review requirements. Production remains unmounted.

Validation: 161 distinct applicable tests passed (95 existing non-database, 24 new coverage/research safeguards, 42 existing PostgreSQL/integration/recovery tests). A first local restore invocation failed because a container name was supplied; the unchanged isolation guard requires a hexadecimal container ID. Rerunning with the actual dedicated container ID passed. No safeguard was weakened. Retirement audit passed with zero active dependencies. Windows/Linux/PostgreSQL and broader backend/frontend CI are checked on the delivered commit and linked in PR #1181; local test success alone is not a CI result.

Read-only report reproduction:

```bash
python scripts/medical/level16_scientific_coverage.py --research reports/scientific-levels1-6/focus-source-research-20261114.json --output /tmp/level16-coverage-new.json
```

The output path must not already exist. The report cannot authorize reviewers, authenticate sources, create review events or update predictions.

Exact next action: owner names the real identity administrator, source-attestation authority and five qualified, distinct people, and approves the isolated infrastructure/policy/budget decisions in A01–A14. Qualify an actual provider token/session contract and protected browser access, then perform isolated acceptance/restore checks before any explicitly authorized release. First real source verification should use the ORCA-2 package, including original SAP versions and database-lock/unblinding timing; clinician review, independent challenge and separate adjudication follow. Until then live access stays disabled and authenticated/adjudicated counts remain zero.
