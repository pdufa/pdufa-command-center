# PEAK SCIENCE → OUTCOME → MAIN progress — October 28, 2026 Pacific

Review: [PR #507](https://github.com/pdufa/pdufa-command-center/pull/507),
`feature/peak-science-outcome-20261028`, based directly on main `7a88764c`.
Implementation: `b70177a2`. No unrelated draft branch was merged. Earlier scanner
work remains preserved separately; it is not a dependency of this change.

## Implemented and locally verified

The existing eight-domain, 40-question, 20-depth SCIENCE catalog and empty
independent adjudication register are reused unchanged. The server-maintained
`peak_research_register.json` adds a complete question-by-question **research
inventory**, with exact PEAK identity, source references/locations, observations,
interpretations, missing documents, uncertainties and review requirements.
The loader excludes this October 28 inventory from earlier cutoffs and prevents
cross-trial reuse, forged document hashes, claimed signoff or training eligibility.

| PEAK measurement | Actual result |
| --- | --- |
| Trial / treatment | NCT05208047; bezuclastinib plus sunitinib; GIST after imatinib |
| Existing curated SCIENCE source leads | **10**, unchanged |
| Question research records | **40**, across eight existing domains |
| Questions with unadjudicated source observations | **27**; this is not 27 completed scientific assessments |
| Independently certified SCIENCE assessments | **0/40** |
| Independently reviewed investigation-depth levels | **0/20** |
| Missing/unverified required document families | **12**: 11 MISSING, one UNVERIFIED; exact individual file count is unknown |
| Original source bytes retained / original source hashes | **0 / unavailable** |
| Selected historical source contexts | **3**: two approval-letter examples, one issuer-reported CRL example |
| Independently adjudicated historical review cycles | **0** |
| Research readiness / decision readiness | **RELUCTANT / ABSTAIN** |
| Prediction validation / approval probability / confidence | **NOT VALIDATED / unavailable / unavailable** |
| Automatic scheduling / sheet writes / trading | **Disabled** |

The existing batch now returns OUTCOME and MAIN summaries instead of empty
values. Scientific completeness, historical comparison quality, regulatory
uncertainty and model validation remain separate. Even structural SCIENCE
readiness cannot produce a probability without model validation.

The existing Pipeline dashboard includes a collapsed PEAK research panel. It
loads only when expanded, through an authenticated read-only proxy. It shows
actual counts, the timeline and source basis, all 40 research records, critical
concerns, missing document families and selected historical contexts. Bad source
identity or attempted prediction/certification promotion withholds the display.
It uses existing HOP service configuration and no new credential values.

## Source investigation and limits

The SEC-filed November 10, 2025 issuer presentation supplies locations for
trial design, randomized and safety populations, PFS/ORR and safety tables.
The NCI official trial catalog supplies multipart design and eligibility context.
Earlier observed May 28/30, 2026 issuer disclosures remain explicitly labeled;
fresh requests were partly restricted/403. No original document bytes were
downloaded and no text-transcription digest is presented as a PDF/HTML hash.
Unknown original publication dates remain null, distinct from printed document
dates and the October 28 observation/index date.

Notable research concerns include hepatic laboratory toxicity, treatment-related
discontinuation, open-label treatment versus blinded central endpoint review,
crossover/estimands, missing sensitivity analyses and absent CMC/inspection
evidence. The register distinguishes apparent discrepancies from different
populations: planned Part 2 enrollment versus actual randomized enrollment,
and 413 randomized versus 412 safety participants. The sponsor's never-dosed
control explanation is recorded without inventing independent adjudication.

Required original protocol/amendments, pre-unblinding SAP, full clinical report,
reproduction package, safety narratives, DDI reports, original FDA correspondence,
CMC/process/stability records, inspection evidence and complete historical cycle
records were not obtained. ClinicalTrials.gov API and candidate public protocol/
SAP locators were inaccessible through the research tool. ASCO access returned
403. Candidate locators are not proof that a document exists or is unavailable
worldwide. A third-party CTIS index is a discovery lead, not an acquired original
protocol. Missing documents are unknowns, not adverse scientific conclusions.

Historical context includes FDA sunitinib **NDA021938** for GIST (separate from
the RCC application in the same letter), FDA ripretinib **NDA213973** in a later
treatment line, and issuer-reported poziotinib nonapproval in **NDA215643**.
The FDA/Federal Register meeting notice supports that last application identity;
the SEC-filed issuer disclosure reports CRL receipt on November 25, 2022. That
receipt report is not substituted for the original FDA action date or CRL.
Poziotinib is a different-disease regulatory-risk example, not a close GIST
efficacy match. Review cycles remain null. All examples are excluded from
training/validation; no representative denominator or historical accuracy is claimed.

## Tests and reproducible local result

| Check | Result |
| --- | --- |
| Entire backend suite | **610 passed**, five dependency/Pandas warnings |
| Entire frontend suite | **391 passed**, no failures/skips |
| TypeScript without incremental cache | Passed |
| Next.js production build | Passed locally; not a deployment |
| Local authenticated PEAK view / real-case batch | **HTTP 200 / 200** |
| Local unauthorized PEAK view | **HTTP 401** |
| Local real-case sheet preview | One preview row; **writtenToSheet=false** |
| Storage isolation of new read | Test rejects any attempted database connection; none occurs |
| Identity/cutoff/false-signoff/model-promotion regressions | Passed |

The local verification summary and implementation commit are preserved in
`research/peak-science-20261028/local-verification.json`. Full local responses
remain in ignored `work/peak-science-20261028/local-api-response.json` and are
excluded from proposed publication. These are local ASGI and
UI software checks using the real source case, not a live deployment result or
validated prediction accuracy. Synthetic negative tests validate trust boundaries
only. The old tests expecting empty OUTCOME/MAIN were updated to require
abstention. An initial npm cache ENOENT was resolved using a writable `/tmp`
cache; subsequent install, TypeScript, tests and build passed.

All four GitHub workflow runs completed successfully for `b70177a2`:
Command Center CI (including backend/frontend jobs), Next.js checks, WT UI
checks and isolated recovery rehearsal. Draft PR #507 contains that implementation.
Automatic approval review rejected a later command attempting to commit/push the
full local response archive, citing potentially sensitive research data and
authorization for this new branch. The rejected command made no commit or push.
The governing master directive subsequently authorized ordinary development and
reviewable PRs. The safer counts-only summary and this report were pushed in
`3c95e058`; all four workflow runs also passed at that commit. The full response
remains local and ignored, and its publication is not proposed. No merge or
deployment occurred.

## Deployment and live-access blocker

Render control-plane inspection confirmed service `pdufa-hop-readonly-review`
deployment **dep-dbgnvknlk1mc7392bml0** is live at **7a88764c**. This confirms
deployment metadata, not current API content or a deployment of this PR.
The supplied baseline reports PostgreSQL READY; Render lists the staging database
available. Independent SQL access through the hosted connector is blocked by its
existing empty external IP allowlist; this does not establish a database outage.
No allowlist was changed. This feature adds no schema, migration, DB writes,
backup operation or storage fallback.

This managed environment has no secure `PDUFA_INTERNAL_API_KEY` binding and does
not permit the Render host. The provided smoke runner exits **2 before submission**
for missing credentials; the direct health probe returns **HTTP 403**. Therefore
authenticated live batch, published-discovery preview, eligibility, SCIENCE 40 and
sheet-preview contents were **not independently rerun here**. The new route and
dashboard are not claimed deployed or remotely verified. No merge or deployment
was performed and production scheduling/sheet/trading settings were unchanged.

To unblock live tests, configure the internal key through the managed secret UI
and authorize `pdufa-hop-readonly-review.onrender.com` in the supported network
configuration; never paste credentials into chat or bypass TLS/proxy controls.
Then rerun the authenticated read-only checks, verify database health and preview
contents, and obtain appropriate deployment authorization for this reviewed change.

## Outstanding scientific work

Acquire the missing originals and preserve actual bytes/timestamps; complete the
20-depth investigations with source-specific evidence; obtain actual authorized
independent review for the 40 questions; reconcile application/cycle/indication
and predecision chronology for relevant approvals/nonapprovals; establish a
representative cohort, frozen predictions and independent out-of-sample calibration.
Until then PEAK remains **RELUCTANT / ABSTAIN**, without a validated probability,
independent favorable conclusion, BUY/PASS/FAIL recommendation or trading readiness.
