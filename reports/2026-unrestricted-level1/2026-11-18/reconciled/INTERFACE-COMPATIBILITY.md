# Interface compatibility

**Offline research mapping validated. Production integration remains unverified.** The projector accepts existing eligible POOL and FOCUS trial IDs. This branch adds no application callers or production data writes.

| Interface | Research projection | Remaining integration constraint |
| --- | --- | --- |
| PAST | Application-cycle event key, verified outcome, decision date, outcome-aware status and nullable blind prediction | The current Level 4 queue expects a cutoff and joins displayed outcomes by ticker and date. A production research view needs an exact application-cycle join. |
| POOL | Exact NCT joins to the caller's eligible POOL set | The caller supplies current market-cap screening, stage and eligibility. |
| FOCUS | Exact NCT joins to the caller's existing FOCUS set, with distinct application cycles retained | Trial documentation-readiness scores are separate from qualitative FDA assessments. |
| ASSESSMENTS | Level 1, separately typed forecast and retrospective result, cutoffs, versions and nullable confidence percentage | The existing scientific runtime expects exact-NCT reports and calibrated FDA metric fields. An application-cycle research type is still required. |

Contract tests exercise all four projections, exact NCT matching, empty membership, preserved outcomes, confidence null handling, abstentions and sorting. [Offline projector](../../../../scripts/project_2026_level1_contracts.py) · [Tests](../../../../tests/test_2026_unrestricted_level1_audit.py)

The offline join found four trial links across three application cycles in the frontend's 32-trial FOCUS roster. The backend and frontend snapshots list the same 32 NCT IDs. Their as-of dates differ, November 14 in the backend package and November 17 in the frontend, so the packaged-roster equality regression fails. Updating those production input snapshots requires an independent publication decision.
