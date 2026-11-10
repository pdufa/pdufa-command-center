# MAIN Revision 29 — original document metadata intake precheck

**Exact pilot:** ACACIA-HCM / NCT06081894 / CY 6033.  
**Branch:** `feature/medical-stage4-verified-method-matrix-20261108`, draft PR #965 only.  
**Document snapshot:** existing research handoff as of November 8, 2026.

## What this stage actually installs

An authenticated, **stateless original-document metadata precheck** is now accessible from the draft PREDICTIONS page. It allows a researcher to choose one of the six previously defined original-evidence requests, enter the source document title, exact version/date, HTTPS source link and purported SHA-256, and check that the metadata has the expected shape and is mapped to the correct Phase III scientific methods.

The interface offers optional **browser-local SHA-256** calculation for a user-selected authorized/public original document up to 25 MB. The browser reads the selected bytes locally; **only SHA-256 and explicit metadata** are sent to the isolated preview for a transient format check. File bytes, file name and any patient content are not uploaded, saved or transmitted. The user is explicitly warned not to select patient-level or confidential files.

**This is a precheck, not completed ingestion.** A submitted hash is not authenticated by the server from original document bytes. An allowlisted URL is not fetched or proof of ownership, quality or relevance. No evidence object is persisted. On refresh, user-entered metadata is not available for further study. The response says `METADATA_FORMAT_CHECKED_ONLY` or `REJECTED_METADATA` and lists five remaining human review tasks.

## Installed controls

- `new-platform/frontend/lib/acacia-evidence-intake-precheck.ts`: six exact request-to-document type mappings, strict NCT, title, version, actual ISO date, SHA-256 syntax and fixed HTTPS original-source host allowlist; links accepted metadata to the request's original method positions. Wrong NCT, wrong type, unknown source, query tokens, IP or local host, credential-bearing URL, malformed claimed digest, dates or unexpected keys fail closed.
- `new-platform/frontend/app/api/predictions/medical-evidence-intake-precheck/route.ts`: dashboard-cookie session required, **same-origin POST required**, exact NCT query, JSON-only small payload (12 KB), private no-store. There are **no** GET, file upload, PDF parsing, external fetch, DB writes, reviewer permissions, mail sends or change actions.
- `new-platform/frontend/app/predictions/assessment/PilotEvidenceIntakePrecheck.tsx`: iPhone-friendly interactive form, optional browser-local digest, strict status display and all five outstanding independent source/medical review gates.
- `new-platform/frontend/app/predictions/assessment/PilotPredictionWorkup.tsx`: renders new stage immediately below the six original-source acquisition requirements, maintaining the 18-source research worklist, two quantitative scientific methods, the documentary research checks and the existing 800-position clinical ledger.
- `new-platform/frontend/tests/acacia-evidence-intake-precheck.test.cjs`: validates every mapped request, source-hash gate, wrong trial, malformed date, unsafe URL, extra/unexpected PHI fields, no grade/signoff/forecast/persistence, and URL/CSRF/byte-cap safeguards.
- `new-platform/backend/scripts/verify_medical_preview.py`: authenticated live HTTP acceptance of the actual browser-visible form and synthetic metadata POST. Tests a valid exact source *format* candidate, rejects cross-origin POST, rejects private-IP sources and wrong NCT, and independently confirms zero historical medical review events.

## What remains deliberately NOT installed

1. Permanent encrypted original document storage with source access control, versioning, owner rights, backups and retention requirements.
2. Independent confirmation that claimed SHA-256 matches original, authorized source bytes (the optional client-local digest is not server-side authenticity proof).
3. Trusted verification of original source issuer, exact trial/indication, protocol/version effective date, complete original SAP, clinical missingness/sensitivity and safety event datasets.
4. Multi-party, independently qualified medical reviewer signoff with append-only source/assessment clinical events; existing independent-grade ledger remains unchanged.
5. FDA decision model and independent outcome calibration.

The source packet continues to report **0/800 independently authorized clinical scores**, no reviewer signoff, FDA `ABSTAIN`, accuracy `NOT_CALIBRATED`. No medical scientific findings were changed merely because document metadata passed a precheck. This must never be represented as ingestion into a validated clinical evidence repository.

**Production boundary:** Draft Vercel preview only, PR #965 remains draft; no isolated Render medical service redeploy, no production scoring deployment, no reviewer credential changes. Default-branch nightly public-source monitor is separate.
