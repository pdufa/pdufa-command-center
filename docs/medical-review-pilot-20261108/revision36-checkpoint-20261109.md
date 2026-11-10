# MAIN Revision 36: recovered original history and verified review interface

PR [#965](https://github.com/pdufa/pdufa-command-center/pull/965) remains **DRAFT** on `feature/medical-stage4-verified-method-matrix-20261108`, based on `feature/medical-stage4-queue-live-audit-20261108`. Revision 35 checkpoint `13b3dae5cd8bfb003430e03f56bff58caf1da70c` was fast-forwarded without resetting completed work. Earlier unfinished local files were preserved separately before that fast-forward. No FOCUS/POOL membership or historical scientific events were modified.

## Evidence obtained

Four original ClinicalTrials.gov study responses and the official version index are retained with exact URLs, UTC retrieval receipts, byte lengths and SHA-256 digests in [the original-history packet](./revision36-original-history/README.md). Standard public browser navigation succeeded after earlier direct API attempts were denied; those failure receipts remain preserved. Offline replay rejects cross-NCT, wrong-version/date and digest mismatches, keeps complete endpoint text, and does not repeat denied network requests.

| Original version | Submitted | Public posting | Primary endpoints | Enrollment |
| --- | --- | --- | ---: | --- |
| v26 | January 11, 2025 | January 14, 2025 | 1 | 420 estimated |
| v27 | May 15, 2025 | May 20, 2025 | 2 | 500 estimated |
| v29 | January 29, 2026 | February 2, 2026 | 2 | 500 estimated |
| v30 | August 3, 2026 | August 5, 2026 | 2 | 500 estimated |

KCCQ-CSS is primary in all four. pVO2 becomes an additional primary in v27 and remains primary in v29/v30. The change is original documentary evidence, not an adjudication of prespecification or post hoc conduct. Estimated enrollment does not establish the randomized or treated population and does not resolve 516 versus 517. Temporal analyses must use the public posting date rather than assuming the earlier submission date was public.

The preserved CTIS Amendment04 protocol was rehashed and its page66 multiplicity graph visually transcribed into the [prioritized reviewer packet](./revision36-protocol-safety/reviewer-packet.json). This reexamines an existing original; it does not collect a new protocol or authenticate the final SAP. Protocol page67 defers missing-data/sensitivity detail to the SAP. A new October11 sponsor dosing/safety deck supplies additional reporting-window questions, but exact PDF bytes could not be captured: direct403 and ordinary-browser200/no-download receipts remain explicit. Its hash and visual verification remain unclaimed.

The [November9 regulatory recheck](./revision36-regulatory-source-check.json) found a new original sponsor disclosure still describing the nonobstructive-HCM sNDA as plannedQ4. The November14 MAPLE-HCM action date and original NDA219083 approval concern obstructive HCM. They do not establish ACACIA nHCM FDA filing or acceptance. Original web text was examined; uncaptured exact-byte hashes remain null.

## Work and grading boundaries

| Item | Before | After | Remaining |
| --- | ---: | ---: | --- |
| Existing trial source packets | 29 | 29 | No new source-packet completion claimed |
| Pilot source-audit receipts | 800 | 800 | Clinical examination is separate |
| Pilot source-mapped research leads | 18 | 18 | 782 positions not source mapped |
| Documentary checklists / numeric research calculations | 3 / 2 | 3 / 2 | 13 other source leads; no new scored checklist claimed |
| Qualified phase signoffs | 0 | 0 | 29 exact trials require authorized review |
| Independently completed assessments | 0 | 0 | 40 pilot; 1,160 across29 trials |
| Official individual method grades | 0 | 0 | 800 pilot; 23,200 across29 trials |
| Validated FDA forecasts | 0 | 0 | Outcome-specific evidence/calibration gates unmet |
| Validated accuracy | 0 | 0 | Frozen historical labels and untouched temporal validation required |

Recovered originals enrich existing method handoffs4.2:L1,4.4:L1,8.2:L1; protocol/safety notes remain mapped to their existing exact assessment positions. No methodology slot, retrieved source, automated source receipt, or provisional research score is promoted to an independently reviewed scientific test. All grade recommendations requiring missing primary evidence remain unassigned. APPROVAL/CRL/REVIEW_DELAY: **ABSTAIN**; certainty **NOT_VALIDATED**; accuracy **NOT_CALIBRATED**.

The next scientific blockers are the final dated locked SAP and protocol/amendment/data-lock chronology; original CONSORT and analysis-set accounting; matched definitions, populations and reporting windows for HF11/1 versus12/3; and denominators underlying14(2.7%) interruptions. The HFSA deck's before-week12 clue does not reconcile its cases with the secondary report. Authorized independent clinical/statistical adjudication remains required after documents are acquired. No restricted-data request, external message, or clinical signoff was initiated.

## Components and observed verification

- `scripts/medical/acacia_ctg_historical_versions.py` and the bounded public-browser adapter preserve/reconcile original bytes and exact study identity. The existing Actions workflow replays preserved sources offline; CI success is not a fresh source retrieval.
- `PilotOriginalHistoryEvidence.tsx` and its source-linked data expand the existing PhaseIII review queue. The existing installation monitor records stable Revision36 task IDs, traceable acceptance evidence and an active-source-task locator. Existing live-ledger tasks and histories remain separate.
- `hop_forecast_metrics.py` adds pointwise Wilson95 intervals for observed event rates in fixed calibration bins. These assume independent rows, exclude label/model uncertainty, are not simultaneous intervals or an ECE confidence interval, and cannot release FDA probabilities.
- The inactive vault authorization guard now rejects malformed non-ASCII keys with401 before any storage access. Four GET/POST raw-header cases also retain503 while the feature is disabled. No role, flag, grant, database firewall or credential was changed.

[Authenticated CI run42628975006](https://github.com/pdufa/pdufa-command-center/actions/runs/42628975006) passed normal protected dashboard login, anonymous401 and origin/input errors, all40assessments/800methods, source citations/history, 18-lead CSV and unchanged ledger snapshot. [Sanitized readback records](./revision36-verification/authenticated-readback-summary.json) show0grades,0historical clinical events and800source-audit positions; snapshotSHA256 `c5833e1315f64c19c2b5b1f857534b6eff6dbdda69189637e5f8275cf28e9dad`. Frontend PostgreSQL-ready projection validation passed; no SQLite fallback was used for live acceptance.

[Local browser acceptance](./revision36-verification/local-browser-receipt.json) passed17checks at390px and1440px, including four expandable originals, visible digests, no page overflow, no browser runtime errors and the active-task focus behavior. This used ephemeral local application test credentials, not a reviewer identity or live database. The remote authenticated run used the existing protected CI test secret without disclosing it.

Local regression: **1,373 backend passed,8 skipped,6 existing warnings**; **150 frontend test files passed,0failed**; **41 ACACIA source tests passed**; **20 retirement-policy tests passed**,248entrypoints audited with0violations; TypeScript and production build passed. Eight local skips require unconfigured external PostgreSQL role/vault acceptance fixtures. Sandbox-specific child-process/stdout and TestClient socket restrictions were diagnosed and the checks rerun successfully with permitted execution. A missing declared cryptography dependency was installed locally without changing requirements. No outstanding implementation test failures remain.

Verified frontend deployment: [`dpl_ARC5XDy19zhsmLX5qLCKc9YHZzSj`](https://pdufa-new-dashboard-ljnrkkg3e-pdufa.vercel.app), commit `013f81b40344a3f485b777925f1cfd53f1f94c8d`, READY plus authenticated operational acceptance. Earlier runtime observation: isolated Render `srv-dbntrkpsrm7s73aec3lg`, deployment `dep-dbogvaoqr7gs73ava440`, commit `7c35253f8f6fa58714738c3619336380fb974d03`, auto-deployOFF. The subsequent [guarded release](./revision36-verification/release-receipt.json) passed all gates: Render deployment `dep-dbot3n8u01pc738b6bq0` is LIVE at `d580b966a4f28d64f1878a9a5e9f6f5713e181b3`, finished14:01:20UTC. Startup and health confirmed PostgreSQLREADY,29sourcepackets/348stages,23,200positions,0grades and retained source revision2/historyCount2. Post-rollout run42630127667 read all800methods with the identical matrixSHA256. Vault route404 confirms it remains uninstalled. The old backend observation above remains part of the preserved pre-rollout receipt.

Automatic approval review rejected moving the existing Vercel feature alias because a hosted-routing change lacked explicit authorization. The alias was not changed or bypassed. The verified unique preview provides the safe access path. Production operations, clinical reviewer writes and vault activation were not performed.

Final monitor preview: [dpl_FsYVRRjmgo5rXaqH7uqzJ9hPsioh](https://pdufa-new-dashboard-2rz1u59ty-pdufa.vercel.app), frontend commit `62ba6bd5fd632d556a81149189214e4f60dda87c`. [Run42631538008](https://github.com/pdufa/pdufa-command-center/actions/runs/42631538008) passed normal authenticated40×20readback and now also requires the actual Render deploymentID/commit in the installed checkpoint. [FullCI42631538010](https://github.com/pdufa/pdufa-command-center/actions/runs/42631538010) passed backend,frontend andretirement on codecommit `bf2fb5de0b2550b64301ce8bef2db917b71ed0e1`. The frontend Git tree is exactly `f6ad2a52606d9f5164f7c4f2eb9de94cd0be71f2` in both commits; only acceptance tooling changed afterward. See [finalpreviewreceipt](./revision36-verification/final-preview-receipt.json). The closing repository commit adds receipts/documentation only. Active scientific task remains `r36.source-reconciliation`; no background clinical grading or numerical FDA forecasting is running.
