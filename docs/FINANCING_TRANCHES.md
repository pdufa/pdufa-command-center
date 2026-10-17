# Financing agreements, individual tranches, and cash runway

A **single financing agreement** can involve two or more funding tranches. Never
treat installments under the same agreement as two independent post-Phase-3
financings. Conversely, runway should account for each *separately verified*
cash receipt, not just the headline financing commitment.

## Required tranche input

Enter one row per distinct company/program tranche in
`data/financing_tranches.csv`. Use the same `financing_id` for every
disbursement from one agreement and a distinct `tranche_id` for each draw.

| CSV column | What to enter |
| --- | --- |
| `event_key`, `ticker` | Exact drug/indication program and issuing company; no cross-company attribution |
| `financing_id` | Stable ID of the underlying legal financing agreement/transaction |
| `tranche_id` | Unique ID of this particular disbursement under that agreement |
| `tranche_status` | `FUNDED`, `COMMITTED_UNFUNDED`, `CONDITIONAL`, `EXPECTED`, `ANNOUNCED`, `CANCELLED`, or `NOT_APPLICABLE` |
| `funded_date`, `expected_date` | Actual funding date versus anticipated date; never substitute the latter |
| `gross_amount_usd` | Disclosed gross principal/proceeds; useful for diligence, **not** automatically available cash |
| `net_cash_received_usd` | Actual net cash after fees/withholdings; leave blank when not independently established |
| `restricted_cash_usd` | Confirmed restricted portion; use zero only when explicitly supported |
| `source_url`, `source_sha256` | Same-company primary SEC filing/document and content digest |
| `verification_status` | `VERIFIED` only after validating the filing, amount, funding date, restrictions and company identity |
| `notes` | Conditions precedent, covenant issues, fees, dilution, warrants, maturity, repayment, program relevance |

**Company website → Investor Relations → offering and financial announcements**
is a mandatory research avenue for gaps; open and validate the matched SEC
filing before promoting any cash receipt.

## Two different calculations

**Financing #2 gate.** Require two independently verified qualifying financing
transactions after the exact program's Phase 3 readout. Two installments under
one `financing_id` are **one transaction for this gate**, even if the
installments arrive on different dates. A future draw/undrawn line does not
establish a completed financing. Existing `gem_financing_gate.py` retains
the final eligibility decision.

**Runway research.** Start from an independently validated SEC balance-sheet
cash balance and the matching operating cash-flow period. Add only
**verified net unrestricted proceeds** received *after* the balance-sheet
date and on/before the assessment date. Funding already reflected in the
reported cash figure must not be added again. Deduct an estimate of cash burn
since the cash statement, using the historically observed monthly rate:

```
monthly_burn = -operating_cash_flow / number_of_reported_months
estimated_cash_as_of = max(0,
    reported_unrestricted_cash
    + verified_net_post_statement_tranche_receipts
    - monthly_burn * days_elapsed / 30.4375)
research_runway_months = estimated_cash_as_of / monthly_burn
```

This is a **pro-forma research scenario**, not a reported cash balance, a
company forecast, or a new trade-entry gate. The calculation is withheld
when the SEC cash/burn basis fails, when any actual post-statement funded
tranche lacks verified net proceeds, or when tranche identities duplicate.
Announced/committed/conditional/undrawn tranches remain visible, but excluded.

The GEM and GEM JR candidate dashboards expose a
**Financing tranches and funded cash runway · Research only** section,
including agreement IDs, tranche IDs, dates, gross versus net figures,
whether each was added, and the research-only result. It does not overwrite
the strict cash-only runway or financing gate.

## Existing first entry

Dyne's June 16, 2026 $50 million loan draw is entered as **one tranche** under
its 2026 loan-facility agreement, with the issuer SEC document. Because
verified *net unrestricted cash received* and a matched document digest are
not yet in the ledger, this **does not increase runway** and does **not**
constitute a second independent financing.

## Review and validation

Run:

```bash
python -m unittest discover -s tests -p 'test_financing_tranche_runway.py' -v
python -m unittest discover -s tests
```

Never infer current cash from gross agreement capacity, double-count an
underwriter option from the same offering as a separate financing, or mark
an unresolved GEM/PIPELINE/FINANCIAL report complete because a research
calculation returns a number.
