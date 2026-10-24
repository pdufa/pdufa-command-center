# Shared research data setup

Pipeline, GEM JR and GEM continue the earlier saved catalog of **50 data fields**:
35 source fields, 10 calculated fields, and 5 modeled assessments. The earlier
30/15/5 conversation estimate differs from that saved registry. These are research
inputs, not 50 active restrictions. No list selection, threshold, saved preset,
FS/FA association, permanent PDUFA number or qualification rule is changed.

Open **SHARED DATA SETUP** below Source health on Pipeline, GEM JR, GEM or
RESTRICTIONS. Choose a list to see available, stale, review/conflict and missing
counts for every field. Counts are exact programs in the dated source universe,
not a newly qualified candidate list. Open **DETAILS → SHARED RESEARCH FIELDS**
to inspect values, source links, original observation/retrieval dates and formulas.

## Sources and missing fields

| Input | Source | Refresh / limitations |
| --- | --- | --- |
| Trial identity, registered phase/status, completion and results-post dates | Existing ClinicalTrials.gov collectors | Exact NCT match. Completion is not readout; posted results are not success. |
| FDA dates, outcomes and designations | Existing exact-event source-verification/designation ledgers | Unverified claims remain REVIEW; no designation record does not mean none. |
| Cash, operating cash flow, shares and debt | Existing SEC Step 4 parser, extended across Pipeline issuers | 25 due issuers per run, oldest attempted first; current cached GEM data reused. Unique ticker/CIK required. |
| Financing closings | Existing exact-event two-close SEC recheck | Offering announcements and shelf registrations do not prove a closing. |
| Market cap | Existing verified cap ledger | Original retrieval timestamps retained. |
| OHLCV and long chart history | Optional Alpaca historical data API | 25 due tickers per run; split-adjusted daily history. IEX volume is labeled single-exchange. Existing saved provider histories remain labeled and are never combined with Alpaca bars. |
| Company revenue | SEC companyfacts | Reporting period preserved. This is distinct from product sales, which remain in the existing approved-drug sales display. |
| Enrollment, safety and additional primary statistics | Exact-trial detail and endpoint evidence | Enrollment, adjudicated primary-endpoint result, adverse events and comparator effect remain MISSING until their exact-trial collectors/reviews are connected. Existing primary p-value observations are imported. |
| Clinical score, regulatory probability, upside, downside and expected return | Future source-reviewed model inputs | These five modeled fields remain MISSING; research grades are not converted into probabilities, price targets or expected returns. |
| Permanent Program ID | Existing live program registry | Still displayed in the existing program details. The shared snapshot does not reassign IDs; its reserved field remains MISSING until a read-only registry join is connected. |

FINRA short interest and CMS opportunity estimates are **not connected in this
initial 50-field catalog**. No new subscription is required or purchased here.

The shared collector reads existing GitHub Actions SEC contact configuration.
Alpaca collection uses `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`, or the existing
`APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` aliases, if available to Actions. Render
environment values are not automatically shared with Actions. Missing credentials
are reported as NOT CONFIGURED; no keys are displayed or copied into source.

## Automatic operation

The existing overnight sequence runs shared-data collection **after primary
sources and before scoring/repair**. The setup commit runs an initial bounded
refresh. This adds no second clock and no broker operations. Full SEC/Alpaca
universe coverage takes multiple batches and depends on source availability.

Run `python scripts/shared_enrichment.py` to rebuild from saved observations only.
Run `python scripts/collect_shared_enrichment.py --max-tickers 25` for bounded
external collection. Dedicated caches never overwrite canonical qualification,
financing or source-verification ledgers. A failed retrieval retains its old
source date; rebuilding a report never renews source freshness.

The existing field IDs and source/derived/modeled classifications are preserved
from `new-platform/backend/config/enrichment_field_registry.json`. Its draft
connection labels are definitions; actual availability is in the generated index.

Each field's state is OBSERVED, CALCULATED, MODELED, STALE, REVIEW, CONFLICTING or
MISSING. A missing field is never zero or a failed restriction. Calculation
results inherit their input evidence. The API reevaluates retrieval age and date
distances when DETAILS opens. The coverage table is explicitly dated to its
publication. Source file hashes record the input revision.
