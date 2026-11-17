# KEYNOTE-522 — 2019 pre-decision independent conference-source lead

**DISCOVERY_ONLY** — not a frozen point-in-time source or blind prediction.

A distinct, earlier publication has been identified for acquisition and source cross-check:

- Schmid et al., KEYNOTE-522 Phase III neoadjuvant pembrolizumab + chemotherapy versus placebo + chemotherapy, followed by adjuvant treatment.
- ESMO 2019 late-breaking abstract LBA8_PR, *Annals of Oncology* 2019;30(suppl 5):v853–v854.
- Source URL: https://www.annalsofoncology.org/article/S0923-7534%2819%2960363-7/fulltext
- Publication year: 2019, before 2020 NEJM publication and before 2021-07-26 FDA decision.
- This is an independent publication **date**, not an independently authenticated archived copy. Retrieval in 2026 does not make it a 2019 frozen snapshot.
- Source is a conference abstract, not a full peer-reviewed trial report. Do not replace the 2020 NEJM primary report with it.
- The 2021 ESMO abstract at https://www.annalsofoncology.org/article/S0923-7534%2821%2902063-9/fulltext is dated September 2021, **after** the 2021-07-26 FDA decision; explicitly exclude it from a July 2021 pre-decision evidence package.
- Also exclude the 2022 NEJM mature EFS report DOI 10.1056/NEJMoa2112651 and the 2024 overall-survival paper DOI 10.1056/NEJMoa2409932.

## Collection and eligibility steps
1. Retrieve the exact 2019 abstract bytes from the publisher or a legitimate repository; hash and record retrieval timestamp and content type.
2. Cross-check trial identifier NCT03036488, treatment schema, pCR endpoint, population and data cutoff against the 2020 NEJM paper.
3. Independently establish the archive timestamp if a historical frozen copy exists.
4. Keep FDA outcome documents and post-July-2021 results in an isolated outcome partition.
5. Maintain `blind_eligible=false` and `accuracy_evaluated=false` until historical integrity and evaluation gates pass.

The existence of this 2019 source broadens the potential pre-decision research evidence base; it does not validate a model score.
