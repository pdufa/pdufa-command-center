# Interface compatibility

**Offline research mapping validated. Production integration remains unverified.** The projector accepts existing eligible POOL and FOCUS trial IDs. This branch adds no application callers or production data writes.

| Interface | Research projection | Remaining integration constraint |
| --- | --- | --- |
| PAST | Application-cycle event key, verified outcome, decision date, outcome-aware status and nullable blind prediction | The current Level 4 queue expects a cutoff and joins displayed outcomes by ticker and date. A production research view needs an exact application-cycle join. |
| POOL | Exact NCT joins to the caller's eligible POOL set | The caller supplies current market-cap screening, stage and eligibility. |
| FOCUS | Exact NCT joins to the caller's existing FOCUS set, with distinct application cycles retained | Trial documentation-readiness scores are separate from qualitative FDA assessments. |
| ASSESSMENTS | Level 1, separately typed forecast and retrospective result, cutoffs, versions and nullable confidence percentage | The existing scientific runtime expects exact-NCT reports and calibrated FDA metric fields. An application-cycle research type is still required. |

Contract tests exercise all four projections, exact NCT matching, empty membership, preserved outcomes, confidence null handling, abstentions and sorting. [Offline projector](../../../../scripts/project_2026_level1_contracts.py) · [Tests](../../../../tests/test_2026_unrestricted_level1_audit.py)

The frontend and backend development copies now contain the same 32 NCTs and identical November 17 roster metadata. The older November 14 research input was archived for reproducibility. The backend equality regression passes on the development branch.

## Deployed read-only verification

On November 18, 2026, the deployed PAST, POOL, FOCUS and ASSESSMENTS page routes returned HTTP 200 HTML. Their live data contracts remained protected. GET requests to the deployed POOL scope-funnel endpoint and the PAST, FOCUS and ASSESSMENTS runtime endpoints returned HTTP 401 JSON. The public frontend OpenAPI path returned 404. The configured backend OpenAPI probe did not return a response within 15 seconds. This verified route availability and authentication behavior. An authorized read-only owner session or redacted production schema export is needed to compare live payload fields and nullability. The development branch retains the offline mappings because the deployed checks established no compatible payload change.

The checkout and deployed paths use distinct semantics. PAST has a historical queue and saved assessments; POOL serves a screened trial funnel; FOCUS joins exact NCTs and owner-saved reports; ASSESSMENTS serves authenticated, versioned readouts. The Level 1 workbook is application-cycle research across market caps. The four route shells do not establish compatibility with that workbook.

This recheck used repository schemas and fixtures. Approved authenticated production access was unavailable, so live payload compatibility remains UNVERIFIED.
