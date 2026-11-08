# MAIN-aligned Analyze Now canary — implementation and acceptance

This additive branch is based on current MAIN, not on the older conflicting all-in-one draft. It retains the 29 exact-NCT FOCUS roster, the existing POOL and FOCUS Google Sheets, and source provenance. P3, P3 POST-DATA, RAAS, GEM and GEM JR remain retired as active workspaces or analysis inputs. A trial's Phase 3 evidence is still valid science.

## Installed in code
- One opt-in 12-stage source collection worker, with stop/resume and immutable exact-NCT source and revision records.
- Explicit user-initiated Analyze Now proxy, authenticated with the existing session and strict same-origin UUID request; one default eligible canary `NCT06081894`.
- Read-only saved history even after an NCT leaves FOCUS.
- Read-only backend `/api/internal/medical-canary-preflight` under the existing internal key, reporting actual preview flag and persistent storage readiness without disclosing secrets or starting jobs.
- Separate FDA approval, CRL and review-delay decisions all `ABSTAIN` with null probabilities; certainty `NOT_VALIDATED` with null rating until real independent review and calibration.

## Verified deployment blockers (November 7, 2026, Pacific)

- **Wrong Render source branch:** the existing isolated service `pdufa-medical-intelligence-preview` (`srv-dbntrkpsrm7s73aec3lg`) still tracks `feature/deep-medical-intelligence-preview-20261107`, not this feature branch `feature/main-aligned-analyze-now-canary-20261107`. A READY Vercel preview of this PR cannot make the old Render backend run this PR's routes. In the Render service's **Settings → Build & Deploy**, select the tested canary branch and deploy the exact checked commit, then verify the service's reported branch and deployment SHA. Its auto-deploy is off. Do not repurpose the production backend.
- **Database not connected:** the isolated Render PostgreSQL database `dpg-dbnts20u01pc73do32qg-a` is available, but the Render service logs report `sqlite`, `postgres_required: True`, and `persistent database ready: False`. Set `DATABASE_URL` using the database's **Internal Database URL**, exclusively in the isolated service's secret Environment settings; do not paste or commit it. Keep `PDUFA_REQUIRE_POSTGRES=true`.
- **Canary still gated:** leave `PDUFA_MEDICAL_PREVIEW_ENABLED=false` until that branch and database are configured. Once configured, set the flag `true` in the **isolated** backend only and redeploy. Read the authenticated `/api/internal/medical-canary-preflight`: both `persistentStorageReady` and `sourceWorkerReady` must be `true`. An HTTP 200 from `/health` alone is not enough.
- **Front-end preview pairing:** use Vercel's preview environment for the same tested branch, with the isolated `PDUFA_API_BASE_URL` and `PDUFA_INTERNAL_API_KEY` configured securely and branch-scoped. Never copy live production secrets.
- **No bulk activation:** keep `PDUFA_ANALYZE_NOW_ALL_ENABLED` unset/false; only `NCT06081894` is eligible until a real saved 12-stage canary survives reload, stop/resume, restart and immutable-history review.
- The Render free database currently expires December 8, 2026; replace or upgrade it before relying on it for permanent analysis history.

These external requirements are **not** complete because the code compiled or simulated PostgreSQL readiness in tests.

## Release boundary and existing preview environment
This is a feature-branch integration and **not** authorization for an automatic production release, running bulk analysis, copying spreadsheets, or assigning scientific grades. Backend routes and table initialization are off unless `PDUFA_MEDICAL_PREVIEW_ENABLED=true` is explicitly configured on the isolated preview service. Persistent research runs require working PostgreSQL; in-memory/ephemeral fallback does not count.

1. Verify all frontend/backend/retirement tests and the exact-commit Vercel preview.
2. Verify the isolated preview Render backend has a working **Internal Database URL** in the secret environment setting `DATABASE_URL`, with `PDUFA_REQUIRE_POSTGRES=true`. Do not expose or paste credentials.
3. Bind this branch's Vercel preview to that isolated backend using preview-scoped `PDUFA_API_BASE_URL` and `PDUFA_INTERNAL_API_KEY`. Match the same key securely on Render; never copy production credentials into the preview.
4. Activate `PDUFA_MEDICAL_PREVIEW_ENABLED=true` **on the isolated backend only**, verify authenticated preflight gives `persistentStorageReady: true` and `sourceWorkerReady: true`, and verify `/health` reports `storage_kind: postgresql`.
5. Sign in to branch preview, open `/analyze-now?nct=NCT06081894`, click once, and verify 12 saved stage dispositions and immutable history survive reload, stop/resume and service restart.
6. Confirm missing clinical/CMC documentation remains a gap and approval/CRL/delay/independent certainty remain ABSTAIN/null. Only after genuine canary validation consider other 28 FOCUS trials, optionally setting `PDUFA_ANALYZE_NOW_ALL_ENABLED=true` on **both isolated backend and matching Vercel preview**.

## Not installed or certified
Live database connection, real canary completion, historical out-of-sample calibration, FDA/SEC/PubMed monitoring, Telegram delivery, independent specialist signoff and production rollout are **not** claimed by a passing code test or a READY preview. The former free Render PostgreSQL preview expires December 8, 2026; evaluate durable storage before retaining long-lived research.
