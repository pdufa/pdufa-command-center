# MAIN — ACACIA-HCM original protocol source review, revision 5

**Observed:** 2026-11-08 UTC  
**Exact trial:** NCT06081894; EU CT 2023-505797-15-00; Cytokinetics protocol CY 6033; aficamten for symptomatic nonobstructive hypertrophic cardiomyopathy (nHCM).  
**Source provenance:** Official CTIS public document-download interface, original public file `D1_2023-505797-15-00_Protocol_FP`, original source version displayed in the PDF as **Amendment 04 dated October 28, 2025**.  
**Artifact:** [GitHub Actions source capture and original PDF](https://github.com/pdufa/pdufa-command-center/actions/runs/42525291355/artifacts/13634488398). The source capture used an exact CTIS identifier and a signed CTIS publication-engine S3 delivery link restricted to an allowlisted host; the presigned URL was never retained.  
**SHA-256 of PDF bytes:** `853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8`; **701,086 bytes**; **90 PDF pages**; machine-readable text extracted from the public PDF by pinned `pypdf==5.9.0`. This is an authentic source-retrieval and text-extraction record, **not independent human protocol review or visual proof that all tables/figures were interpreted correctly.**

This is an **additive revision** to the earlier [EU CTIS protocol discovery](./eu-ctis-phase-protocol-discovery-revision4-20261108.md), [safety analysis](./source-reconciliation-revision3-20261108.md), and immutable [first source receipt manifest](./receipts.json). It updates only the public protocol's retrieval status; it does not rewrite earlier original receipts, author clinical phase verification, enter method grades, authorize a regulator prediction, or change saved live evidence.

## Original protocol: extracted methodological facts and their limits

| Assessment / source section | Source evidence from Amendment 04 | Remaining verification |
| --- | --- | --- |
| 4.1 Randomization, blinding, comparator | Original title and protocol identity confirm the Phase 3 randomized, double-blind, aficamten-versus-placebo design for nHCM. | Clinical protocol text does not establish actual concealment compliance, deviations, or blinded site-monitoring performance. |
| 4.2 / 5.1 Primary endpoint identity and estimands | In its statistical section the protocol identifies the **two co-primary differences in mean change from baseline to week 36**: KCCQ clinical summary score (KCCQ-CSS) and peak oxygen uptake (pVO₂). It describes primary estimands in the nHCM population despite postrandomization intercurrent events. | Reconcile the exact final analysis language, protocol versions, endpoint charter and FDA acceptability with final signed SAP. |
| 4.3 Planned analysis population | Original section 9.3 defines a **full analysis set (FAS)** containing all randomized participants. The safety analysis set is those randomized who received ≥1 dose, with treatment assignment described in the protocol. | Verify final SAP/CSR analyses actually used these definitions, participant flow and how intercurrent events or treatment switching were handled. |
| 4.3 Missing data and sensitivity analyses | Original statistical section states that the SAP contains fuller missing-data and sensitivity methods. | **Not resolved:** The *final locked SAP itself* has **not** been retrieved, authenticated, or reviewed. This is a critical boundary: the protocol is not the full statistical audit. |
| 4.4 Sample-size/power expectations | Original section 9.2 plans approximately **500 participants randomized 1:1**, allowing about **10% missingness**, with roughly **90% power for each co-primary endpoint**. An example design target is a **5-point placebo-adjusted KCCQ-CSS difference**. The later publication reports **517 randomized** and a **3-point KCCQ-CSS difference** (95% CI 0.5–5.5). | The 5-point design assumption is **not automatically an FDA minimum clinically important difference or passing threshold**. Separately scrutinize the observed 3-point effect, clinical meaningfulness and sensitivity results before any grade. |
| 4.2 / 5.2 Multiplicity | Original section 9.4.1.1 describes **familywise two-sided alpha 0.05 controlled through a prespecified graphical multiplicity procedure**. Amendment 04's summary discusses a change to a graphical approach with alpha recycling. | Compare the exact graph/hypothesis hierarchy and final SAP with the sponsor's simplified public description of parallel 0.025 testing. These are **not presumed contradictory** without the full graph, version history and test results. |
| 5.3 Safety | The protocol specifies dose adjustment, monitoring, and safety follow-up procedures; it does not replace the later blinded adverse-event line listings. | Revision 3's serious heart-failure adverse-event count discrepancy (11/1 in secondary full text vs 12/3 in later sponsor disclosures) and treatment-interruption percentage mismatch remain **unresolved**. |
| 8.1–8.2 Integrated review | Primary source provides a method-planning benchmark for efficacy/safety and regulatory review. | Missing independent data adjudication, original final SAP, complete safety definitions, and authorized clinical review. FDA and review certainty remain withheld. |

## New exact-source evidence status

- **EU/ClinicalTrials.gov identity crosswalk:** source-matched for Phase III protocol CY 6033, exact EU and NCT records; different regional versus global status scopes preserved.
- **Published original Phase III protocol Amendment 04:** **RETRIEVED**, PDF identity checked, content machine-readable, hash/size/pages logged; **not independently clinically signed off**.
- **Signed final statistical analysis plan (SAP):** **NOT OBTAINED**. The protocol's own statistical section points to a separate detailed SAP. The public CTIS 133-document listing checked did not expose a document title explicitly containing “SAP,” “statistical analysis,” or “analysis plan.” Absence from the indexed titles alone is not proof that no SAP exists publicly or in another repository.
- **Complete original primary publication + supplementary appendix:** previously indexed; the journal's direct file-download path was not accessible in the prior research attempts. These were not substituted with the EU protocol.
- **Regulatory outcome:** As of the November 4 disclosure, nHCM sNDA filing was expected rather than publicly demonstrated as accepted for review; no nHCM PDUFA date or approval event inferred.

## Gated next work

1. Locate and authenticate the **final signed SAP**, including the dated graphical multiplicity diagram, all statistical hypotheses, estimands, missing-data and sensitivity specifications.
2. Compare Amendment 04's sample-size, endpoints and planned hypothesis graph to **the final SAP and dated preceding amendments**. Preserve protocol assumptions distinct from observed outcomes.
3. Reconcile original primary/supplemental results and all safety counting windows, including the 11/1-versus-12/3 HF SAE reports, all-cause SAEs, and treatment interruptions.
4. Request an authorized **independent scientific/clinical reviewer** to verify exact trial phase and original evidence. Append review events only through the existing auditable phase-first ledger after authorization. Do not generate grades or FDA probabilities from a research source alone.

**Controlled counters unchanged:** original 29/29 source research runs retained; independent phase verifications **0/29**; scientifically scored method positions **0/23,200** (pilot **0/800**); independently signed reviews **0**; FDA approval / CRL / delay **ABSTAIN**; certainty **NOT_VALIDATED**. Production, POOL/FOCUS roster and prior evidence history are unchanged.
