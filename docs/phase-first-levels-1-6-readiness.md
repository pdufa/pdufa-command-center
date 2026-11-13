# Phase-first scientific Levels 1–6 — evidence readiness only

This is the **first isolated engineering slice** for #1179. It is **not** a medical assessment, a site release, a verified current FOCUS scan, or an FDA outcome prediction.

## Reused inputs

- Current 32 exact-NCT FOCUS roster (as of 2026-11-13): `new-platform/frontend/data/p3PostDataActive.json`. This legacy filename remains an internal source artifact, not an active P3 workspace.
- Existing application crosswalk: `new-platform/backend/app/data/focus_application_snapshot.json`, with 29/32 FOCUS NCTs mapped to 23 **provisional** cycle IDs. Three newly added exact NCTs are explicitly **NOT_MAPPED_APPLICATION_CYCLE**, never silently excluded or assigned guessed FDA applications. The unreviewed cycle IDs and indication labels remain leads only.
- The existing `scripts/medical/level4_registry_extraction.py` source checkpoint, now with an additional read-only `studyOverallStatus` field for future captures.
- Existing 20-level names: `new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json`; only Levels 1–6 are read.

No legacy score model is imported. This does not touch POOL/FOCUS membership, FDA outcomes, assessment history, production or the separate automatic coder.

## Run offline, against an existing checkpoint

```powershell
python scripts/medical/phase_first_levels_1_6.py --checkpoint path/to/level4-checkpoint.json > levels1-6-readiness.json
```

The process performs **no network calls**, database writes or predictions, and only emits JSON to standard output. Its report is provenance-gated: an exact-NCT/source-location mismatch, invalid SHA-256 metadata, duplicate FOCUS trial or mismatched candidate application identity stops processing. A SHA-256 string is a source-receipt attribute, **not** proof the underlying source was independently reviewed.

Each exact-NCT trial returns six separate Level readiness records:

| Level | Original scientific objective | This first slice |
| --- | --- | --- |
| 1 | Source identity and provenance | Registry-source capture/identity check; independent provenance review still required |
| 2 | Registry and phase verification | Captured phase and trial status are explicitly *unreviewed*; absent status unresolved |
| 3 | Clinical results evidence | Phase 1/2 does not automatically require future pivotal readout; registered endpoints are not results |
| 4 | Trial design and protocol investigation | Captured design attributes are not scientific judgments; single-arm/open-label applicability must be reviewed |
| 5 | Statistical analysis and multiplicity | Original SAP/multiplicity evidence is required for potential pivotal Phase 3; future pivotal SAP not imposed on earlier phases |
| 6 | Endpoint clinical relevance | Indication leads and registered outcomes need independent specialty/contextual review |

All scores, probabilities, FDA outcome/timing judgments and scientific conclusions remain **null**. Every level is **NOT_ADJUDICATED**. Real phase-specific assessment code, original-document review, independent scientific signoff, validated assessment outputs, FOCUS UI integration and runtime verification remain future engineering/review tasks.

For a Phase 4 or `NA` registry category the pivotal requirements remain subject to applicability/manual review; Phase 4 is never automatically treated as an upcoming FDA approval trial.

## Tests and acceptance boundaries

```powershell
python -m unittest discover -s tests -p "test_phase_first_levels_1_6.py" -v
python -m unittest discover -s tests -p "test_level4_registry_extraction.py" -v
python scripts/audit_raas_retirement.py --check
```

The isolated workflow `.github/workflows/phase-first-levels1-6-tests.yml` runs these on Windows and Ubuntu. This test receipt verifies **software structure**, never actual clinical validity.

**Next slice:** independently verified trial phase/status and indication provenance; source-specific clinical evidence requests and phase-specific reviewer workflow; staging integration after acceptance. Preserve distinct approvals, CRLs, extensions and abstentions and ensure postdecision historical outcomes are not laundered as predictions.


## Second engineering slice — source-submission review queue and offline preview

A separate fail-closed source intake is implemented in
`scripts/medical/level16_source_submissions.py`. It accepts bounded
source metadata for **Levels 1–6** only and attaches each lead to its exact
NCT and (optionally) its *provisional* application-cycle ID.

A submission contains `submissionId`, `nct`, `level`, `sourceKind`,
`sourceUrl`, `sourceDate`, `accessedDate`, `documentSha256`,
`locator`, `claim`, `role` (SUPPORTS/CHALLENGES/CONTEXT), and
`submittedBy`; `candidateApplicationCycleId` is optional. The enclosing
object requires `schemaVersion: 1`, `kind:
FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS`, `cutoffDate`, and `records`.

**Crucial trust boundary:** a submitted SHA-256 string or source URL is
**unverified metadata**, not proof that the underlying document bytes have
been accessed or authenticated. Likewise, a string in `submittedBy` is
not an independently authenticated reviewer signature. Caller-supplied
verification, reviewer approval, score or FDA prediction fields are rejected.
Every accepted source lead is marked
`SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED` and every level remains
`NOT_ADJUDICATED`. Even a registry source lead must match the checkpoint's
exact NCT, URL, SHA-256 and captured field locator. No self-attestation can
promote an item into independent scientific review.

### No-source example

Create a local `source-submissions.json` file containing this example.
It is a valid **empty queue**, not actual verified evidence:

```json
{
  "schemaVersion": 1,
  "kind": "FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS",
  "cutoffDate": "2026-11-13",
  "records": []
}
```

### Read-only workflow

```powershell
python scripts/medical/phase_first_levels_1_6.py --checkpoint path/to/level4-checkpoint.json --source-submissions source-submissions.json > levels1-6-readiness.json

python scripts/medical/render_level16_focus_preview.py --report levels1-6-readiness.json --output levels1-6-preview.html
```

The output HTML is **offline-only**, not a deployed route. It displays a
32-NCT (or exact current FOCUS roster count), six-level, expandable review queue and strongly labels all evidence
as unauthenticated and all assessments as unreviewed. All free-text and
source links are escaped/validated. It does not connect to the live FOCUS
site or modify databases, records, memberships, scoring or predictions.

### Tests

```powershell
python -m unittest discover -s tests -p "test_phase_first_levels_1_6.py" -v
python -m unittest discover -s tests -p "test_render_level16_focus_preview.py" -v
python -m unittest discover -s tests -p "test_level4_registry_extraction.py" -v
python scripts/audit_raas_retirement.py --check
```

Windows and Ubuntu CI run the checks with byte-preserving checkout and
UTF-8 decoding so the historical-record hash audit is not invalidated by
Windows line-ending conversion. Do not weaken that audit.

### Still required before functional assessments

- Provenance authentication against actual permitted original source bytes;
  reproducible hashes, publication/access dates and phase-first identity
  verification;
- A separate *authenticated* reviewer workflow with demonstrably independent
  source and clinical reviews, amendment tracking and contradictory evidence;
- Trial/indication-specific clinical analyses and methods for Levels 1–6;
  independent specialist challenge, and FDA application-cycle adjudication;
- Approved frontend integration on an actual protected FOCUS page, runtime
  smoke testing and explicit release approval before deployment;
- Historical point-in-time blind validation before quantitative probability
  forecasts. These submissions and this preview cannot be used to assert
  clinical accuracy, reviewer completion or approval probability.


## Third engineering slice — bounded local byte-consistency receipts

The optional `scripts/medical/level16_local_byte_receipts.py` checks local
**bytes** against the SHA-256 value in an existing, already-validated
submission. This is an offline, read-only operation; it neither downloads
sources nor proves publication origin, clinical relevance, original acquisition,
FDA authenticity or reviewer independence. Do **not** put licensed clinical
records, study reports or patient data into GitHub or CI fixtures.

Provide a private evidence root on the PC, accessible only to the authorized
operator. Then create an optional JSON sidecar, for example:

```json
{
  "schemaVersion": 1,
  "kind": "FOCUS_LEVELS_1_6_LOCAL_BYTE_RECEIPTS",
  "records": [
    {
      "submissionId": "a-submission-id-already-listed-in-source-submissions",
      "relativePath": "trial-research/source.pdf"
    }
  ]
}
```

The source submission itself must already contain the **same** `submissionId`
and the declared lowercase 64-character SHA-256 for the stored original file.
The example is illustrative and does not assert that this source or file exists.

Run the strict local check:

```powershell
python scripts/medical/phase_first_levels_1_6.py --checkpoint path/to/level4-checkpoint.json --source-submissions source-submissions.json --local-byte-receipts local-byte-receipts.json --evidence-root C:\private\pdufa-original-sources > levels1-6-readiness.json

python scripts/medical/render_level16_focus_preview.py --report levels1-6-readiness.json --output levels1-6-preview.html
```

The permitted filenames are relative, slash-separated and bounded; absolute
paths, traversal, symlinks and source files larger than 64 MiB are refused.
The computed hash is compared with the recorded hash, but the byte contents
and absolute local file paths are not copied into the output report. There are
no network calls or writes to source files.

The possible per-submission states are:

- `LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY` — local file contents match
  the *submitted* checksum; **not** independent source authentication
- `LOCAL_DIGEST_MISMATCH` — do not use the claimed document until reconciled
- `LOCAL_FILE_NOT_PRESENT` — a path was specified but no local bytes exist
- `NO_LOCAL_RECEIPT` — no entry was supplied for that submission

Counters explicitly preserve `originalSourceAuthenticated: 0` and
`independentScientificReviews: 0`, even after a successful byte match.
This third slice does **not** verify that the source URL served the same bytes
at the recorded access date. The document must still be independently
authenticated and reviewed, and source dates and clinical assertions reconciled.

### Additional tests

```powershell
python -m unittest discover -s tests -p "test_level16_local_byte_receipts.py" -v
```

CI covers synthetic byte matching and mismatches, missing files, oversized
files, relative-path confinement, symlink refusal, manifest tampering,
review-status non-promotion, and the 32-NCT FOCUS integration contract.
These are engineering tests, not clinical source-verification receipts.

## Source-verification cases and scientific-review proposals (November 13)

The next bounded engineering slice adds `level16_review_cases.py`. These are
**offline unreviewed queues**, not a permissioned authentication service or
completed scientific assessments. No original sources were authenticated in this
slice, and no real reviewer identity was established. Tests use synthetic data.

The readiness CLI now accepts `--source-cases` and `--review-proposals` JSON,
only with `--source-submissions`. Both documents require exactly `schemaVersion`
(integer 1), `kind`, `cutoffDate` (equal to the validated submission cutoff), and
`records` (at most 2,000). They never accept scores, outcomes, probabilities,
verified flags, or signed-off status. Review dates can follow the evidence
cutoff; such dates do not establish a prospective blind assessment.

Source-case kind: `FOCUS_LEVELS_1_6_SOURCE_CASES`. Each record contains exactly:

- `submissionId`, `nct`, `candidateApplicationCycleId`, `documentSha256`,
  `sourceUrl`, `sourceDate`, `accessedDate`: must match the validated source lead.
- `checks`: exactly `exactNct`, `phase`, `registryStatus`, `indication`,
  `population`, `sourceOwnership`, `publicationDate`, `retrievalDate`,
  `documentVersion`, `protocolVersion`. Every check has `state`, `observation`,
  and `locator`; observations and locators are bounded, nonblank source leads.
- `conflicts` and `limitations`: bounded text lists. Conflicting checks require
  explicit contradictory information. Unknown versions remain MISSING or
  NOT_PUBLICLY_AVAILABLE with explanation; do not invent versions.

Review-proposal kind: `FOCUS_LEVELS_1_6_REVIEW_PROPOSALS`. Each record contains
exactly `proposalId`, `nct`, `level`, `candidateApplicationCycleId`,
`sourceSubmissionIds`, `phaseBasis`, `evidenceState`, `findings`, `reasons`,
`contradictoryEvidence`, `limitations`, `reviewerIdentityClaim`, `reviewDate`,
`challenge`, and `outstandingBlockers`. Findings, reasons and limitations require
nonempty text lists. Every evidence ID must match the exact trial, level and
application candidate (including null for unmapped evidence). A phase basis is
required but remains unverified and cannot override registry phase.

`challenge` has exactly `reviewerIdentityClaim`, `reviewDate`, `findings`, and
`limitations`; all four are null if absent. An included challenge must follow
the first review date and use a different identity claim. Different strings
**do not prove different people or independence**. Both identities and challenge
remain unverified; all proposals still require trusted identity, authenticated
sources, verified phase, and independent scientific adjudication. An AI statement
has the same unreviewed status as any other submitted statement.

Allowed intake evidence/check states are UNREVIEWED, MISSING, CONFLICTING, and
NOT_PUBLICLY_AVAILABLE. NOT_YET_EXPECTED_AT_THIS_PHASE is additionally permitted
only for proposed Levels 3/5 assessments with an exclusively Phase 1/2 basis;
it cannot waive source identity, provenance or phase checks. VERIFIED is
intentionally unavailable until a separate trusted review service exists.

Dossiers flag same-digest submissions as duplicate documents, never independent
corroboration. Different digests at the same URL require variant reconciliation.
A matching local-byte receipt does not remove the authentication blocker.
The offline preview shows dossier blockers/conflicts/limitations and proposed
findings/reasons with explicit UNREVIEWED labels, escaped as text. It continues
to reject review promotion and predictions. This is not protected staging:
authentication, authorization, immutable review storage and runtime integration
are still outstanding. No service, worker, production configuration or history
is changed.

Next implementation: add a separately permissioned reviewer identity and
append-only review-event boundary, with trusted authorization supplied by the
service rather than JSON intake; bind each event to immutable original evidence
bytes and cutoff. Only then implement adjudication transitions and protected
staging integration. Obtain original-source and medical specialist review for
all six levels; keep all 32 trials and the three unmapped exceptions visible.
