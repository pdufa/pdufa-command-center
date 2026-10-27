# Navigation and startup test migration

The active dashboard is Next.js with a FastAPI backend. The root Streamlit `app.py`, its widget keys, radio options, keyed tabs, `session_state` routing and CPython file-watcher import wrapper are retired. Restoring that application would exercise an unsupported product surface.

Four existing pytest modules retain 22 current product entry points and execute the actual supported-app suites through `tests/supported_dashboard_checks.py`. The bridge requires successful test discovery and a zero exit status. Each referenced frontend suite runs in a separate Node process once per pytest process; multiple Python entry points do not represent additional independent frontend assertions. Failures are not converted into skips.

| Legacy test file | Retained supported-app coverage |
| --- | --- |
| `test_navigation_merge.py` | Rendered safe fallback for old bookmarks; exactly one published SCANS panel; retained historical model CSV and independence metadata; HOP source/model boundaries. |
| `test_pipeline_ui_smoke.py` | Bounded Pipeline paging and full-universe search; intersected phase/date/cap/search filters; distinct GEM JR/GEM checklists; permanent program WT labels; restriction/preset isolation; missing/dates/source-aware candidate scores; preserved plan CSV. |
| `test_startup_import_race.py` | FastAPI source work requires explicit startup opt-in; Next.js GET recovery is bounded to one retry; permanent authorization/conflict errors do not retry; writes are prohibited; failed sources cannot become qualified/trade-ready evidence. |
| `test_four_pdufa_score_tabs.py` | Real React candidate-details rendering for all three seven-category ranking models, actual zero versus missing evidence, exact candidate identity, dated citations and complete-score ordering; separate GEM qualification and financing/trial boundaries. |

The additional `retired-navigation-migration.test.cjs` renders the current Workspace and exercises old/unknown section queries, supported trial-sheet deep links, SCANS, switching GEM stages and WT, and the supported research-only HOP screen. It verifies all navigation requests remain GET requests, exact WT program labels survive section changes, and historical ticker-only navigation state is not promoted or rewritten.

Some old UI assumptions intentionally no longer apply. Current Pipeline filtering treats cleared selections as the full published universe, rather than the old Streamlit empty-results gate. Controls now live on the current restrictions/workspace surfaces; exact Streamlit dataframe column positions are not an API. A read-only HOP page now exists and must withhold unsupported predictions, so the old blanket assertion that no prediction screen may exist has been replaced by those evidence boundaries. Python hot-reload eviction mechanics are not part of Next.js startup; bounded recovery and authorization are verified at the supported HTTP/startup boundaries instead.

No scientific scores, FDA outcomes, source datasets, scan schedules, restrictions, FS/FA associations, trading permissions or production settings are modified by this migration. Synthetic rendering and HTTP fixtures verify software behavior only, not prediction accuracy.

Verification: the 22 migrated pytest cases passed; the five new frontend tests passed. Additional existing frontend and backend assertions execute inside the bridge, with their output retained when a failure occurs.
