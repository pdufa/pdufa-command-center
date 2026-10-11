# PRE PHASE 3 / Step 7: source review and entry gate rules

**Status:** Research automation is implemented. Any trade signal still requires verified, exact-event human review. The monitor is not an automated issuer-filing adjudicator or a real-time quote terminal.

## Independent data channels

1. **Clinical registry:** `data/phase_pipeline.csv`, `data/phase3_announcements.csv`, `data/phase3_primary_pvalues.csv`. These establish registry status, reported primary p-values, and whether effect-size/CI fields are present for an exact ticker + NCT. Results being posted, p below 0.05, and trial completion are NOT Phase 3 success determinations.
2. **Pre-readout trial design:** `data/pre_readout_protocols.csv` contributes six recorded inputs (primary endpoint, timeframe, allocation, masking, comparator, sample size). The existing `pre_readout_score.candidate_queue` + `assess` rubric provides a **source-dated, uncalibrated clinical research score /100** only when properly documented in `data/phase3_pre_readout_evidence.csv`. Coverage /6 is not statistical or clinical quality. Neither research score is FDA approval probability.
3. **SEC second financing:** `data/second_financing_status.csv` supplies the historical transactions, but the eligibility gate requires exact event identity, ordered **post-readout** closings, two SEC archive document URLs, documented financing review within 30 days, a successful SEC-source check within 2 days, and explicit reviewer attestation. The source's text must actually establish closing (not merely filing, registration or announcement). `SOURCE_BLOCKED_RETAINED` or any partial/failed SEC check always blocks it. Historical closing alone never qualifies for entry.
4. **Market:** `data/step7_market_status.csv` stores approximately 35 EOD close/volume rows per financing-watchlist ticker, alongside time and source. The source-reported EOD feed is not exchange certified. The market gate computes the past ten closing-price range (max/min - 1) and five-session mean volume versus the preceding twenty sessions. **Research heuristic only:** close-price range <= 15%; volume ratio 0.50-1.25; >=31 bars and >=10 sessions after the documented readout; quote within five calendar days and source check within two days. A reviewer must independently assess chart, stabilization and issuer mapping.
5. **ENTRY READY:** `step7_entry.evaluate_entry` requires eight independent gates with all valid exact-event, NCT, source/date, and reviewer evidence. Verdict `ENTRY READY — ATTESTED EVIDENCE / NOT INDEPENDENTLY AUDITED` explicitly means a reviewer supplied and attested the primary links; the engine has not re-read, fact-checked, or audited every issuer/SEC document. Otherwise `REVIEW`; past/decided PDUFA events are `EXCLUDED`.

## Eight hard gates

- Exact issuer / drug / NCT / source and current reviewer identity
- Actual Phase 3 primary endpoint met, as independently interpreted and attested
- Meaningful effect size and confidence interval with clinical relevance review
- No major unresolved safety concern
- Two ordered, source-confirmed post-readout financing closures, current SEC check
- No unresolved ATM / secondary dilution with a separate recent SEC review
- Base stability supported by dated price history **and** manual chart review
- Normalized volume supported by dated price history **and** manual volume review

## How to complete missing inputs without fabricating PASS

Open **PDUFA → PRE PHASE 3** and download the *PRE-READOUT CLINICAL SCORING EVIDENCE TEMPLATE* for the trial-design rubric, and the *BLANK 8-GATE EVIDENCE REVIEW TEMPLATE* for event-level review. Review and populate the matching CSVs at `data/phase3_pre_readout_evidence.csv` and `data/step7_entry_evidence.csv`. Keep trial and event keys exact. An absence of entries is normal and means no event is eligible; it is not a negative clinical trial outcome.

The Streamlit **RELOAD SAVED SOURCE FILES** button reloads repository-managed data after it is deployed; it does not contact the SEC or automatically sign an attestation. Daily GitHub Actions collect registry, market and source snapshots separately.

For SEC 403: configure a genuine `SEC_USER_AGENT` in **GitHub → Settings → Secrets and variables → Actions**, such as `ResearchApp your-real-contact@example.com` with the actual contact details (not the literal example). The surveillance and recheck workflows pass this secret to the SEC client. Retry the relevant GitHub Actions recheck. Some cloud-hosted runner IP addresses remain blocked by SEC regardless of user agent; in that case, source access must be resolved or the documents manually inspected in the SEC Financial Analysis page. A human reading a document is an evidence-review path, not an automated SEC verification.

Always read the `SOURCE HEALTH` panel; any stale, blocked or unresolved source gate must remain REVIEW. The FDA/PoA prediction engine stays independent from these trading gates.


## PRE PHASE 3 completion verification (separate from ENTRY READY)

The **PRE PHASE 3 COMPLETION CHECKLIST** at the top of the tab is intentionally independent of the post-readout SEC financing gate. It checks six fresh research feeds (clinical universe, Phase 3 results, Phase 3 primary statistics, Phase 2 primary p intake, protocol design, and market capitalization), active Phase 3 protocol coverage, Phase 2 linked-NCT collector coverage, whether exact-linked Phase 2 PRIMARY observations display in the table, and whether at least one real source-reviewed pre-readout clinical scoring pilot is complete.

The new columns **Linked Phase 2 PRIMARY p**, **Phase 2 PRIMARY evidence count**, **Phase 2 PRIMARY first observed UTC**, and **Phase 2 PRIMARY registry sources** are joined only through the same ticker and an explicitly linked Phase 2 NCT. The source must be exactly the ClinicalTrials.gov study URL; observations and registry publications must predate the research as-of time. No primary p-value being published is **not** a Phase 2 trial failure. A `p=0.0000` is reproduced from source precision and should not be interpreted as a mathematical zero; `p<0.001` retains the published inequality.

A 100-point pre-readout research rubric is **not** a calibrated Phase 3 probability of success. Manual, source-dated issuer status / trial-design / benefit / safety review is still needed. `READY FOR FINAL BROWSER ACCEPTANCE` is a technical checklist milestone, not a declaration that the tab is finished. Only passing real-browser regression checks, zero unresolved source blockers and a separately confirmed completion acceptance review can justify a completion notification.

**Known outstanding issue:** live SEC document access requires the `SEC_USER_AGENT` repository secret; this affects the separate post-readout financing review, not the clinical PRE PHASE 3 completion count.


## Scoring workflow UI: next pilot milestone

The PRE PHASE 3 clinical table presents **Ticker → Pre-readout research score /100 → Score status → Linked Phase 2 PRIMARY p** as its first four columns. A missing score stays empty, with a clearly visible `NOT SCORED` status and a count of successfully source-reviewed scores; it is never displayed as zero or invented from p-value significance or six-field design coverage.

A **NEXT 10 SOURCE-REVIEWED CLINICAL SCORING PILOTS** worklist follows the main table. Its selection rules are prospective active Phase 3/2–3 status, an exact valid NCT and ClinicalTrials.gov source URL, no registry-posted result, and no already-complete clinical score. Candidates with documented linked Phase 2 primary p, fresh protocols, recent registry checks, verified program identity, and an in-range verified market cap are reviewed first. This numerical research *review priority* is **not a clinical rating**.

Download the worklist and the separate **SOURCE-REVIEW SCORING TEMPLATE FOR THESE 10**. For each case, independently investigate the Phase 2 primary endpoint and benefit magnitude, Phase 3 randomization/control/power, safety, regulatory alignment, trial execution, source quality, and whether issuer topline has *actually* been published. Save only sourced analyst decisions through the existing `data/phase3_pre_readout_evidence.csv` review process and run the strict 100-point research rubric; even a completed research score remains **uncalibrated** and is not Phase 3 probability of success. Downloads alone do not save records to GitHub.
