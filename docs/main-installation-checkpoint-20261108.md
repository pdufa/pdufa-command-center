# MAIN continuation checkpoint — November 8, 2026

Continue PR [#965](https://github.com/pdufa/pdufa-command-center/pull/965), branch
`feature/medical-stage4-verified-method-matrix-20261108`, from verified original
head `a8bef64a759c4215e77db2d7b1d0d00d0ac3e2a0`. Parent:
`feature/medical-stage4-queue-live-audit-20261108`,
`54cfb466ad745b71c1d4706821a464599220fb40`. This is an additive development
checkpoint, not a release or clinical signoff.

## Repository and live evidence

Both packaged FOCUS rosters contain the same 29 unique ordered exact NCTs.
Backend roster SHA-256:
`ab505f993262491d7ab313eaedadb3f82c01321f14ab603ea65a1cea3f4fedff`.
The catalog contains 8 layers, 5 assessments per layer and 20 methods per
assessment: 800 investigation positions per trial; 23,200 across the roster.
Positions, source stages and research checks are not independently graded tests.

Read-only Render verification used the explicitly authorized My Workspace
(`tea-db967i3l550s73cadem0`), service `srv-dbntrkpsrm7s73aec3lg`.
Live deploy `dep-dboc20uc6qcc73d7u4vg` runs
`e1e756efdfb1bff6961971bb26a9418dc0e5e7c3`, finished at 18:36:27 UTC.
Automatic deployment is off. Startup receipts at 18:36:21–25 UTC report:

- 29/29 completed source trials, 348 saved stages; restart readback PASS with
  12 stages, revision 2, history count 2.
- 29/29 triage snapshots and registry reconciliations.
- 0 human-verified phases and 0 scientific review events.
- Review queue: 1 phase-reconciliation trial, 12 trials with posted primary
  results requiring review, 16 without posted primary results; 45 registered
  primary definitions and 16 posted primary measures.
- No clinical signoff, outcomes ABSTAIN, certainty NOT_VALIDATED.

Fresh unauthenticated probes returned `/health` HTTP 200 (PostgreSQL READY,
production scans disabled) and the protected assessment coverage HTTP 401.
The explicit gap-event count was not available from safe receipts and remains
unverified. Startup observations are dated evidence, not a fresh database census.

The initial Vercel deployment `dpl_2hhU7VcW1aRrd2sjSfjaTikezp3c` is READY at
original PR head `a8bef64…`. Its assessment page returned HTTP 200; protected
installation-progress returned HTTP 401 without an application session.
A frontend build does not establish an authenticated frontend-to-ledger flow.
The Render backend predates PR #965; current additions are not operationally
verified on that service. No remote configuration or database was changed.

## Implemented continuation

- Exact parsed source URL matching and exact-NCT registry identity checks;
  source-prefix matches cannot authenticate evidence.
- Per-method historical revisions, retractions, phase history and recorded gaps
  in the read-only matrix, with current-phase counts kept separate.
- Versioned 0–5 rubric and 0–100 normalization disclosure. The rubric is pending
  authorized clinical validation; historical events are not retroactively
  certified, and no automatic scoring is enabled. The existing writer enforces
  provenance, not the complete independent-review authorization workflow.
- Database accident guards for assessment roster/phase/review/gap tables:
  UPDATE/DELETE/TRUNCATE rejected in PostgreSQL; UPDATE/DELETE in isolated
  SQLite tests. Owners can alter schema; these are not tamper-proof against an
  administrator. Production/source-run tables and privileges are unchanged.
- Selected-trial expandable assessment/method/citation/gap/history UI with
  strict payload, current-phase and snapshot-consistency validation.
- Session-protected GET proxies use only explicit
  `PDUFA_MEDICAL_REVIEW_API_BASE_URL`; no ordinary production API fallback.
  Matrix uses the scoped medical internal key when configured. Monitoring uses
  the existing internal key required by that read-only endpoint. Credentials
  stay server-side; redirects are rejected and responses are not cached.
- Seven stable medical installation task IDs with observed counts, actual
  current task, dependency explanations and freshness/expiry definitions.
  Existing installation tasks and unrelated completion evidence are retained.
- Existing bootstrap CI extended to the installation branch, including the
  permanent-retirement guard. No retired workflows were started.

## Pilot and controlled gate

[Source pilot](medical-review-pilot-20261108/README.md): NCT06081894, ACACIA-HCM.
Four original responses preserve the full registry, three NLM publication
records, one PMC full text, and original sponsor disclosures with SHA-256
receipts. Findings separate favorable reported efficacy, adverse safety counts,
methodological limitations, missing documents and unresolved source differences.
Protocol/SAP and full primary report access remain blocked; prior-phase history,
application-specific FDA records and authorized independent review remain open.
No packet was imported into the live ledger; no phase signoff or grade was
created. No expansion beyond this pilot is authorized by these source receipts.

## Validation

Local final backend command:
`PYTHONPATH=new-platform/backend .venv/bin/python -m pytest -q new-platform/backend/tests`
with the optional dedicated loopback PostgreSQL test URL supplied privately:
**1,247 passed, 3 skipped**, 6 existing warnings. The PostgreSQL 17 contract
exercised all 12 table/operation mutation guards, repeated initialization and
seeding, unchanged history after failed DML, and an appended retraction.
No remote database was used. Without the optional local PostgreSQL connection,
that contract skips rather than pretending PostgreSQL was tested.

Frontend: `npm test` **126 passed / 0 failed** test files; final focused matrix,
monitoring and auth tests pass. `npm run typecheck` and `npm run build` pass.
Chromium with backend-generated ungraded fixture data verified 40 assessment
sections, 20 methods on expansion, history/collapse, and no page errors. This
is local UI verification, not live evidence adjudication or deployed integration.
The real backend payload contract also passes strict frontend validation.

`python scripts/audit_raas_retirement.py --check` passes with zero active
retired dependencies; retirement guard unit tests: **20 passed**.
`python docs/medical-review-pilot-20261108/verify_receipts.py` passes all original
byte digests, exact NCT/DOI/PMID linkage and extracted sponsor-object checks.

Resolved failures: initial dependency-install race; sandbox-local TestClient
socket hang (same tests pass outside sandbox); one stale frontend assertion
expecting the superseded unscoped authentication dependency. Backend scoped
authentication was preserved. Unrelated backend deprecation/return-value warnings
remain warnings, not scientific acceptance evidence.

## Current task and remaining release gates

| Stable task ID | Completed observation | Remaining / dependency | State |
| --- | --- | --- | --- |
| medical.sources | 29/29 attached source runs in dated live receipts | Protocol/SAP, source history and missing original evidence remain separate work | Source collection verified at receipt time |
| medical.phase-verification | 0/29 human phase verifications in live receipts | 29 current-phase reviews; original evidence and authorized reviewers | ACTIVE |
| medical.prior-phase-review | None independently established by this checkpoint | Exact prior-trial links, original records and completed-phase adjudication | UNKNOWN |
| medical.method-review | 0 scientific review events in live receipts | 23,200 potential positions remain ungraded; exclusions require review | BLOCKED on phase/source/independent review gates |
| medical.clinical-review | No signoff claimed | Authorized multidisciplinary review and signoff workflow | BLOCKED |
| medical.fda-forecast | Approval, CRL and delay remain separate ABSTAIN outcomes | Independent assessment and outcome-specific historical calibration | BLOCKED |
| medical.certainty | NOT_VALIDATED | Independent out-of-sample reliability validation | BLOCKED |

Next safe release action: review this draft, validate the isolated deployment's
schema-owner privileges and explicit review-backend configuration, then verify
its authenticated read-only matrix and monitoring against the retained ledger.
Do not merge unfinished drafts or promote to production. Next scientific action:
obtain the primary report/protocol/SAP and an authorized independent review for
the single pilot, then validate its append-only revision history before expanding.
