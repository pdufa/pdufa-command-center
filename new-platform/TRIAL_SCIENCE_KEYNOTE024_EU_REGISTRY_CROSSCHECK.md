# KEYNOTE-024 EudraCT 2014 endpoint-design corroboration

**Trial:** NCT02142738 / MK-3475-024 / EudraCT 2014-000323-25.

**Review-only finding:** The Dutch entry in the **EU Clinical Trials Register** documents
an early, regulator-hosted source for the KEYNOTE-024 study plan. Its first
record entry and Dutch competent-authority authorization dates are both
**June 19, 2014**. This is NOT proof that all currently displayed trial
endpoints and analysis rules were frozen on that date.

Primary source (specific subsections):
https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL

| Register subsection | Currently displayed design | Original 2016 publication |
|---|---|---|
| A.2 / A.4.1 / A.5.4 | EudraCT 2014-000323-25, MK-3475-024, KEYNOTE 24 | Same study identity; NCI lists both identifiers |
| E.2 / E.5.1 | Primary PFS per RECIST 1.1, blinded central review | Corresponds to original KEYNOTE-024 primary endpoint |
| E.5.1.1 | PFS analysis at ~175 PFS events, anticipated ~20 months after study start | 2016 paper describes ~175 planned; reported 189 at May 9, 2016 cutoff |
| E.5.1.1 | PFS analysis may be delayed for up to 2 months or until the target OS count, if below 110 deaths | 2016 report observes 108 interim deaths; requires the actual signed DMC decision chronology before asserting a deviation |
| E.5.2 / E.5.2.1 | OS, ORR secondary; planned OS assessments ~110 and ~170 deaths | 2016 paper describes planned ~110/170; observed original interim OS deaths 108 |
| E.8.1 / E.8.7 | Open-label randomized trial with monitoring committee | Corresponds to the original published description |

Other primary study identity and early-design corroboration:
- [NCI KEYNOTE-024 trial listing](https://www.cancer.gov/research/participate/clinical-trials-search/v?id=NCT02142738) confirms both NCT02142738 and EudraCT 2014-000323-25 and protocol MK-3475-024.
- [2015 ASCO/JCO study-in-progress TPS8103](https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103) documents PFS by central review, OS, ORR, crossover and randomization, dated May 20, 2015.
- [2016 NEJM original trial](https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774) describes planned interim testing and the 2016 result.
- [Registry-linked 2017 Japan-only protocol/SAP](https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf) does NOT authenticate the pre-interim effective original version.

## Evidence classification and limitations

- **EU regulator-hosted** does not mean an independent study: the application/registry data are sponsor supplied.
- First entry date **2014-06-19** and authority authorization date are explicit. The public page does **not** supply reliable individual field revision histories. Do **not** claim the 175 / 110 / 170 thresholds have been independently authenticated as the signed 2014 or May 2016 effective SAP solely from the current record.
- The approximately 175-event PFS target and approximately 110-death OS target differ from realized 189 and 108 events respectively; **this is not itself evidence of a protocol deviation**. Actual monitoring committee decisions, protocol amendments, alpha spending, calendar/time rules and data freezes require dated verification.
- The 2014 EU trial record, 2015 trial-design abstract, 2016 NEJM report and NCI study listing provide **cross-source agreement** for broad design, but are not independent efficacy replication.
- The EU record does **not** verify one-sided alpha spending, prospective multiplicity hierarchy, or the complete signed original protocol/SAP.
- Do not lift an input/safety/FDA criterion or issue an automated scientific success grade on this basis.

## Implementation contract

`keynote024_eu_protocol_crosscheck` consumes validated existing 2016
interim design, publication and blocked readiness. The optional protected pilot
response `europeanRegistryCrosscheck` includes:
- exact EudraCT/NCI study identity and dated-record provenance
- six source section mappings to the published endpoint/design description
- original observed vs approximate targets with timing uncertainty
- explicit **false** flags for per-field revision verification, pre-interim signed SAP, independent efficacy replication, recomputed alpha, safety adjudication and any readiness change.

No live web fetch or database write occurs in this route. The frontend
strictly validates every source URL, registered number, endpoint count and
uncertainty flag before display. It denies a purported SAP-authenticated or
new FDA-probability payload, and avoids pooling any registry safety counts.

**Input Readiness: FAIL; Reluctance: HIGH; scientific score: NULL; FDA approval probability: NULL.**

The next genuinely grade-affecting step remains obtaining and authenticating
the original signed 2016 or earlier protocol/SAP versions and amendment
history, plus independent analysis of alpha, censoring, safety and population.
