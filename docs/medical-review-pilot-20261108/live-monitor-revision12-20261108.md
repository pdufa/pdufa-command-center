# MAIN — Live prediction/research monitoring, revision 12 (2026-11-08)

**Scope:** Preview-only, authenticated, read-only observability. Exact-NCT case ACACIA-HCM `NCT06081894` plus the same monitor on the other FOCUS scientific-matrix pages. **This is live telemetry wiring, not the installation of a calibrated FDA prediction model.**

## Delivered

- New mobile-friendly **MAIN · LIVE SCIENTIFIC REVIEW MONITOR** appears at the top of each trial's scientific matrix, above the existing research summary and installation evidence.
- The original `/api/predictions/medical-matrix?nct=` reads the isolated, authenticated review ledger and checks the exact NCT, 40 assessment summaries, phase-event snapshot and sum of 800 method positions. The display polls this verified API every **15 seconds while visible** and immediately on tab return; a manual **Refresh now** button is available.
- The monitor displays current verified phase, **independently recorded scored methods**, explicit not-applicable exclusions, remaining method positions, last successful fetch and observed changes in phase/review/gap counts. If source reads fail, previous snapshot data are labeled stale and review details are withheld until a successful read.
- Existing `medical_continuous.py` already tracks an **actual, durable 12-stage source-research worker**. New authenticated GET-only proxy `/api/predictions/medical-source-run?nct=` reads `/api/medical-continuous/{exactNct}/runs/latest` from the **explicit isolated medical backend origin**, with strict schema and status validation. No operation is issued to start/stop/resume a worker. If configured and available, the UI shows the real source **run status**, 12-stage completion count, current reported research stage, run timestamps and stage details.
- Its backend key must be the **operational internal key** (`PDUFA_MEDICAL_INTERNAL_API_KEY` or `PDUFA_INTERNAL_API_KEY`) because the upstream source-worker route does not accept the separate review-only key. If no authorized operational key exists in the preview environment, status is **unavailable** rather than guessed. Production fallback is forbidden.
- The live monitor's **FDA Prediction = ABSTAIN** and **Accuracy Rating = NOT CALIBRATED** are shown separately and distinctly from both source-worker progress and independently scored methods. The 12-stage source worker **does not perform or count as any of the 800 scientific-method grades**; a source run's COMPLETE status is not a completed clinical investigation or FDA forecast.
- No real 800-method **scientific prediction-job event producer** exists yet. Hence the corresponding run status is explicitly **NOT OBSERVABLE**, with no made-up current clinical method, ETA or provisional probabilities. To complete full prediction-run streaming, an independently authorized scientific-scoring worker must emit persisted run/method updates and a validated prediction engine must output calibrated forecasts; neither was fabricated here.
- In-flight stale method-detail responses are rejected against the **latest** ledger snapshot, and cached details cleared on genuine phase/review/gap changes. Page visibility prevents wasteful background polling; requests are abortable and protected against overlapping intervals.
- Removed duplicate static prediction/accuracy cards under the real monitor so only a single live header is shown.

## Security, validation and release boundaries

- Route reads require an active signed-in session and an exact NCT in the 29-trial FOCUS queue; no generic/production backend fallback or inherited broad permissions are used.
- The source worker proxy validates run UUID, 12 stages, status, time fields, numeric counts and the backend's `ABSTAIN` / null approval probability; it **omits raw per-stage research documents** from the returned response.
- Regression tests cover polling/reconnect, visibility, idle/unavailable/active distinction, no fictional prediction job, source worker exact-NCT identity, stage sanitizer, stale-read invalidation and numerical review count invariants.
- User-facing preview branch `feature/medical-stage4-verified-method-matrix-20261108`, draft PR #965; Vercel preview only. No production release, backend schema or database mutation, source roster edit, clinical phase signoff or FDA prediction.
- A READY preview and passing CI verify the build/contract but **do not prove a signed-in iPhone browser session or a real running worker was exercised** in this checkpoint. The source status may be `UNAVAILABLE` if operational credentials are not configured in this preview.

## Remaining scientific balance (unchanged)

- 29/29 original FOCUS source packets captured.
- 0/29 independently phase-verified; 0/1,160 completed 40-assessment groups; 0/23,200 independently graded 20-method positions.
- Pilot: 15/800 source-to-method **leads**, not grades; **0/800 independently graded methods**.
- 0/29 validated FDA outcomes; forecast **ABSTAIN**, accuracy **NOT CALIBRATED**.
- Seven high-level ACACIA-HCM unresolved evidence questions; final locked **CY 6033 SAP** still missing.
- **Remaining software feature:** true 800-method scoring-run event producer and calibrated probability engine. A live *read-only status display* is not that producer.
