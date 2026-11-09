# ACACIA-HCM: new institutional manuscript route and five-barrier follow-up

This requested Revision 37 follow-up appends to the later verified R48 checkpoint `f93a49a7ea895954d09bf17a24a7f54378524f6b`. It does not restart or replace Revisions 37–48, their 29-trial captures, or the R47 parallel research tracks.

The [structured reviewer packet](./reviewer-barrier-packet.json) records six bounded factual handoffs to existing exact assessment/method positions. Three new public DOI metadata lookups returned HTTP 200; their [receipts](./metadata-retrieval-receipts.json) distinguish fetched-response hashes from retained filtered-metadata hashes. Crossref and Europe PMC did not expose a new primary supplement. OpenAlex supplied a new institutional manuscript location. Aarhus exposed only the DOI; the inspected NYU bibliography page exposed same-trial secondary publications, not a primary supplement.

The [original University of Glasgow repository](https://eprints.gla.ac.uk/394996/) verifies the title, DOI and accepted-version link. Its [33-page accepted manuscript](https://eprints.gla.ac.uk/394996/1/394996.pdf) was obtained through a normal public request: **620,808 bytes**, SHA-256 **`20a804bd113bb40231aec4da466864be0834f78b86c926c8142cc6a0afc67866`**. Printed pages 7, 11 and 13 were visually examined. Exact provenance is in the [manuscript receipt](./accepted-manuscript-receipt.json).

The original repository states **CC BY-NC-ND**, contradicting OpenAlex's CC BY-SA/source-name mapping. Original repository rights govern. The PDF and full article text were kept only in a temporary research workspace, not imported into the product, repository or training corpus. This packet contains metadata, hashes, limited factual findings and external citations. The manuscript is an original investigator report, not the final publisher version, locked SAP, CSR/ISS, or an independently adjudicated review in this installation.

Publication, acceptance and deposit dates have different meanings. The repository lists acceptance July 16, article publication August 28, deposit October 29, a September 15 datestamp, and an October 30 modification. These do not verify when the full accepted manuscript first became public. A historical model must not assume this full text was available at acceptance or at the article's publication date.

| Barrier | Classification | Evidence boundary |
| --- | --- | --- |
| Locked SAP and amendment chronology | PARTIALLY VERIFIED | A new author-reported lock date and primary missingness narrative are available; final approved SAP and complete amendment/lock audit remain inaccessible. |
| CONSORT and analysis populations | PARTIALLY VERIFIED | A new original population-accounting statement supports an exposure distinction; complete disposition and endpoint analysis sets remain unverified. |
| HF 11/1 versus 12/3 | PARTIALLY VERIFIED | Primary manuscript supports the treatment-period claim; matched sponsor cases, definitions and observation windows remain unresolved. |
| Interruption denominators | PARTIALLY VERIFIED | Primary manuscript supplies a distinct protocol-interruption claim; the secondary claim remains preserved pending reconciliation. |
| Authorized independent review | REVIEW PENDING | No reviewer enrollment, authorization, signed phase review or clinical grade was created. |

Subgates distinguish authenticated documentary statements (**VERIFIED**) from still unavailable original documents (**ACCESS RESTRICTED**) and clinical/statistical adjudication (**REVIEW PENDING**). None means failed clinical evidence. The exact bounded findings, page locators, calculations and outstanding requirements are recorded once in the structured reviewer packet.

R46's existing current attachment index has no ACACIA entry, although 12 other NCTs have protocol/SAP metadata. That index was reused without another retrieval and is not proof of external document absence. Earlier NEJM 403 requests, challenged PMC supplement requests, recovered registry versions and successful all-29 source captures were not repeated. No private inquiry, restricted-data request, proxy or challenge bypass was attempted.

Coverage remains **18 existing source leads, 782 unmapped positions, 0 official method grades, 0 qualified phase signoffs and 0 independently completed assessments**. The manuscript adds source-backed preparation; it does not turn an automated documentary check into an independent scientific test. APPROVAL / CRL / REVIEW_DELAY remain **ABSTAIN**, certainty **NOT_VALIDATED**, accuracy **NOT_CALIBRATED**.

Run local packet validation:

```sh
python docs/medical-review-pilot-20261108/revision37-source-reconciliation/verify_source_packet.py
```
