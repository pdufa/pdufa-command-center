# Historical outcome intake milestone — 2026-10-28

## Actual audit baseline

GitHub main and Render's latest live deployment both remain at
`7a88764c6a5d798b917d3b1cdcfe8a07964343e2`. Render service
`pdufa-hop-readonly-review` reports deployment
`dep-dbgnvknlk1mc7392bml0` live, branch main, automatic deployment off and
health path `/health`. This is control-plane metadata, not a successful workload
probe. The current environment is running and connected, but has no custom
source/Render host grants or internal API-key binding.

The direct `/health` attempt failed at the proxy: curl exit **56**, `CONNECT
tunnel failed, response 403`, application HTTP status **000**. No application
response was received. Render lists `pdufa-new-staging-db` available; its external
IP allowlist is empty. The read-only SQL probe was rejected by the hosted
connector before connection. Database query health is **not verified**; this is
an access restriction, not evidence of a database outage. No access settings
were changed.

Repository audit found:

| Component | Implemented on main | Actual validation/operation limit |
| --- | --- | --- |
| SCIENCE | Eight layers, 40 questions, 20 depths; ten dated PEAK leads | **0/40 certified assessments, 0/20 certified depths**; source leads are unadjudicated |
| Deep research | Source/date gates, authenticated batch and published-discovery previews | Read-only integration seam; current main returns empty OUTCOME/MAIN research results |
| Pipeline | Published exact-trial identity/stage reconciliation | Current feed freshness and durable automatic early-development research history are not established here |
| GEM JR/GEM | Saved ACTIVE exact-identity memberships and source-linked funding checks | Existing periods, restrictions and FS/FA associations preserved |
| WT | Published Pipeline trial lookup and separate technical data | Clinical/financing eligibility is not copied across programs by ticker |
| OUTCOME/HOP | Source audits, identity/page review queues, intake, cohort and backtest utilities | No connected training data or independently validated prediction model |
| MAIN | Separate system/research status | Combined PEAK research view is in unmerged PR #507 |

Committed source indexes contain **458 published letter records** and **29,416
approved-registry application records**, all quarantined. Those inventories are
not a complete decision-cycle denominator. The page worksheet has **zero
independently verified page ranges/action dates/review cycles**. One staged
outcome remains model-ineligible. Existing retrospective development-match
files are not blind historical validation and were not promoted or rewritten.

PR #507 (PEAK research register/dashboard) and PR #508 (public-label clocks and
blinded walk-forward evaluation) remain open, unmerged and undeployed. This
increment starts separately from the same verified main baseline; it does not
merge either draft wholesale.

## Completed engineering increment

The legacy JSON parser required outcome `evidence_as_of` before action, while
the comparator required it on/after action and separately required predecision
features. It could never produce a temporally usable comparator record.

The parser now reuses the existing 15-field CSV metadata contract, preserves
exact canonical application/cycle identity, drug/sponsor/source metadata and
separate feature/outcome clocks. It supports a fixed replay cutoff and rejects
repeated JSON keys. Old single-clock records explicitly require source review;
no archived dates, review cycles or provenance are inferred or migrated.

CSV intake now reconciles every parseable application/cycle claim and nonempty
local case ID before row-quality filtering. Invalid conflicting claims cannot
disappear and leave a sibling apparently unique. Rejections retain logical
record numbers and combined reasons. Descriptive comparisons likewise exclude
all duplicate cycle claims, require exact identity and exclude same-day outcome
availability at date-only prediction cutoffs. Intake never sets independent
adjudication, enables training or creates a probability.

The existing PR safety workflow includes these parser/comparator regressions.
No live scanner schedule, API, database schema, spreadsheet, membership, FS/FA,
broker or trading behavior is changed. Test-created SQLite files and logs remain
local ignored artifacts.

## Verification

| Check | Observed result |
| --- | --- |
| Complete backend suite | **649 passed**, five dependency/Pandas warnings, no failures |
| Intake/comparator/staging subset (included above) | **98 passed** |
| Related root OUTCOME regressions | **103 passed plus 12 subtests** |
| Cross-format integration | JSON/CSV preserve identical identity, source metadata and distinct clocks; neither self-certifies |
| Adversarial software regressions | Invalid conflicting rows in either order, identity aliases, repeated JSON keys, source spoofing, malformed clocks and client-supplied adjudication flags |
| Code review | Found silent duplicate-JSON-key overwrite; fixed and covered by four regressions |

These are software checks using explicitly fictitious fixtures. They establish
no FDA outcome truth or empirical predictive accuracy. GitHub commit/PR checks
are reported on the PR after publication; this local record does not predeclare
their result.

## Measurable scientific status and remaining work

- **Independently verified model-eligible FDA decision cycles: 0.**
- **SCIENCE independently certified: 0/40; certified depths: 0/20.**
- **Independent real historical cases backtested: 0.**
- **Accuracy, balanced accuracy, sensitivity/specificity, Brier score, log loss,
  AUROC, calibration and confidence intervals: not measured.**
- **Prediction coverage: no validated real forecasts; no empirical coverage
  rate or covered-case accuracy is available.**
- **OUTCOME: not validated, approval/nonapproval probabilities unavailable.**
- **MAIN: current deployed baseline remains unchanged; insufficient evidence
  remains the appropriate prediction status.**

Next dataset work requires exact independently adjudicated action/cycle
identities; original source bytes and publication chronology; source-supported
PDUFA target revisions; explicit delay/withdrawal/refuse-to-file/unresolved event
histories; frozen predecision feature provenance; an exact representative cohort
roster; related-program independence and an untouched final evaluation cohort.
Only then can baselines, calibration, adversarial forecasting improvements and
independent performance be measured.

For live verification, configure scoped source/Render access and securely bind
the internal key through supported environment configuration. Use an authorized
read-only database connection from an approved network. The hosted Render MCP
connector reports that it has no stable outbound IP to allowlist; no global
database allow rule is proposed. Reviewed offline evidence is an alternative
for source intake. Deployment and production activation still require separate
authorization.
