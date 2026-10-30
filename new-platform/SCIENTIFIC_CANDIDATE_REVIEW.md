# Scientific candidate review, Task 3

The 228-candidate cohort is frozen to the October 30, 2026 archive evidence screen.
The worker checks every archived record in a read-only snapshot against the
immutable manifest, selects that same cohort, and logs its exact IDs. Regulatory
identifier candidates are extracted verbatim from secondary-ID fields across
the entire archive. The earlier count of three was a trial count, not a guarantee
of three distinct identifiers. Every actual identifier is retained with its raw
field and associated NCT ID.

Fresh ClinicalTrials.gov full records are retrieved in exact-ID batches of40.
Receipt URLs, HTTP statuses, timestamps and raw batch-response SHA-256 hashes are
stored. Each live study has a separate canonical JSON fingerprint. A failed
fetch never counts as an independent check. A fresh registry check establishes
what the registry reports; it is not independent adjudication of clinical validity.

The dossier covers the20 requested fields. Primary outcomes, numeric arm results,
primary-endpoint analyses, effect estimates/intervals, p-values and SAE populations
are retained. Secondary analyses are never substituted for primary analyses.
Significance, multiplicity, analysis populations and clinical meaningfulness require
further review and are not inferred from a p-value alone. Missing information is
explicit, including uncertainty and archive/live sponsor conflicts.

An openFDA exact ingredient-name search is attempted per trial's first named
active intervention. It records candidate applications and source receipts only.
It cannot establish the trial's FDA pathway, approved indication, special
designation, submission, or PDUFA date. No search hit is not evidence that no
application exists. Sponsor disclosures and FDA trial-specific documents remain
unverified unless separately reviewed and cited. Curated regulatory reconciliations
are versioned with the evidence file; unverified identifiers stay UNRESOLVED.

READY means sufficient evidence for intake review under the existing framework,
not completed science. RELUCTANT means core primary evidence exists with material
scientific/regulatory uncertainty. NOT READY identifies critical evidence gaps or
identity conflicts. Reasons are stored per trial. These are evidence-readiness
labels, never PASS/CRL/EXTENSION or FDA approval-probability predictions.

The existing science40 catalog remains authoritative:20 investigation levels,
eight subject layers and40 assessments. Dossiers include its existing catalog
reference and handoff state; this worker performs zero framework assessments and
does not activate the existing gate or authorize investigations/trades. Full
scientific investigations completed remains0 until that independent work exists.

New tables scientific_review_runs, scientific_candidate_dossiers, and
regulatory_identifier_reconciliations store append-only review metadata. Run IDs
include the review version and curated-evidence hash. PostgreSQL advisory locks
prevent overlap. All228 dossiers and their final counts commit atomically, and
each dossier has a canonical checksum. A later retry after unavailable sources
requires an explicit review-version/evidence revision; earlier reports stay intact.
Only metadata is written. Archive payloads, checksums, manifests, list membership,
FS/FA restrictions, scans/schedules and trading controls are unchanged.

Authenticated read-only APIs: GET /api/scientific-candidates and GET
/api/scientific-candidates/{nct_id}. The dashboard fetches persisted results on
expansion and each dossier on demand. Summary counters reconcile to actual
persisted rows and classifications; unavailable values render as unverified.

Runtime logs: PDUFA_CANDIDATE_SOURCE_PROGRESS, PDUFA_CANDIDATE_IDENTIFIERS,
PDUFA_CANDIDATE_REGISTRY_BATCH, PDUFA_CANDIDATE_REVIEW_PROGRESS,
PDUFA_REGULATORY_RECONCILIATION_RESULT, PDUFA_CANDIDATE_REVIEW_RESULT,
PDUFA_CANDIDATE_HTTP_SELFTEST. Failure logs identify the phase and error type,
without credentials. The authenticated loopback HTTP selftest reads the persisted
list and a dossier and reconciles all228 counts.
