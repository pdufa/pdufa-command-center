# Main installation — GOAL nightly source-ledger conflict parity

**Scope: GOAL evidence display only; no scans, trading, restrictions or credentials changed.**

## Concrete production-data defect

The main branch's October 25 Pacific nightly source ledger has **1,121**
total findings, broken down as:

| Source finding status | Number |
|---|---:|
| Verified | 995 |
| Unresolved | 21 |
| **Conflicted** | **2** |
| Unavailable | 93 |
| Not applicable | 10 |
| **Total** | **1,121** |

The previous GOAL validator added verified + unresolved + unavailable + not
applicable and required the sum to equal 1,121. **It omitted conflicted**.
The actual 995 + 21 + 93 + 10 = 1,119 mismatch therefore made the
**entire GOAL source evidence panel unavailable**, even though the source
report provided a valid separate conflict category. By contrast, the
production SYSTEM STATUS tracker correctly displayed the two conflicts.

A second GOAL validator accepted only `TICKER|PROGRAM` source evidence
identities, but the **two SEC filings-inventory conflicts** are properly
identified as `REGISTRY:QNCX` and `REGISTRY:TBPH`. This rejected the
entire 23-item required evidence worklist.

## Targeted changes

- GOAL source coverage now accounts for `findings_conflicted` as a
  **separate** integer, keeping 21 unresolved and 2 conflicted. Legacy
  historical audits which legitimately omit the conflict field remain
  valid only if all their other counts reconcile. Invalid or fabricated
  values and false full-coverage claims fail closed.
- The GOAL source panel displays a separate **Conflicted** card on desktop
  and mobile. A conflicted record **never becomes verified** by being
  displayed.
- The required worklist accepts the exact `REGISTRY:TICKER` identity
  **only** for SEC / FILINGS_INVENTORY / CONFLICT. Wrong tickers, other
  claim types, forged identities and fake success statuses still fail.
- Regression tests load the **actual committed October 25 source report
  and dated RESULTS record** and verify all **23 distinct** required
  issues: 2 SEC registry identity conflicts, 20 additional SEC
  review-required findings, and 1 FINANCIAL review-required finding.
  The two conflicts remain open and the $300M–$10B qualified Pipeline
  population is not inferred from this source ledger.

## Boundaries

The GOAL evidence view is read-only and continues to require the source
report's exact nightly run ID and GitHub Actions URL to match the dated
RESULTS record. No standalone run, stale report, source-family mismatch,
unverified count or content mutation is treated as a current source audit.
Scientific source coverage remains **PARTIAL** with SEC and FINANCIAL
families missing. No GEM JR/GEM FS/FA presets, WT, nightly workflows,
production database or trading functions are touched.

This fixes the **visibility of real remaining installation blockers**;
it does not resolve the two SEC identity conflicts or the 21 other
required evidence gaps. End-to-end deployment and runtime acceptance
remain separate proof gates.
