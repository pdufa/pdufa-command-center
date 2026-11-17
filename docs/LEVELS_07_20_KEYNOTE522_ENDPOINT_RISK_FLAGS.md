# KEYNOTE-522 original article: endpoint-specific extraction and risk flags

**Discovery-only research note.** Source published 2020-02-26, before 2021-07-26 FDA decision. The original article was accessible for reading at https://www.nejm.org/doi/full/10.1056/NEJMoa1910549 and the original PDF text was discoverable at https://www.nejm.org/doi/pdf/10.1056/NEJMoa1910549?articleTools=true . This note does **not** assert downloaded PDF bytes, an original-document SHA-256, or a pre-decision frozen snapshot.

## Primary endpoint: pathological complete response (pCR)
- Definition: ypT0/Tis ypN0 (no invasive tumor in breast and negative nodes at surgery).
- Primary pCR analysis cohort: first **602** randomized participants, **401** assigned pembrolizumab + chemotherapy and **201** assigned placebo + chemotherapy.
- pCR: **260/401 = 64.8%** (95% CI 59.9–69.5) vs **103/201 = 51.2%** (95% CI 44.1–58.3).
- Estimated difference: **13.6 percentage points** (95% CI 5.4–21.8), **p < 0.001**.
- pCR data cutoff: **2018-09-24**.
- Alternate pCR definition ypT0 ypN0: 240/401 (59.9%) vs 91/201 (45.3%).
- Alternate pCR definition ypT0/Tis: 275/401 (68.6%) vs 108/201 (53.7%).

## Early event-free survival (EFS) observations
- Full randomized population: **784** vs **390**, total **1,174**; this is NOT the pCR analysis denominator.
- Median follow-up **15.5 months**.
- Early EFS events **58/784** vs **46/390**; hazard ratio **0.63** (95% CI 0.43–0.93).
- Reported **104 events of 327 expected at final analysis**; the paper explicitly notes immature survival follow-up.
- At 18 months, estimated event-free proportion **91.3%** (95% CI 88.8–93.3) vs **85.3%** (95% CI 80.3–89.1).
- These figures must NOT be labeled mature EFS results, final overall survival, or a final confirmatory endpoint.

## Subgroup and safety details
- PD-L1-positive pCR: **230/334 = 68.9%** vs **90/164 = 54.9%**.
- PD-L1-negative pCR: **29/64 = 45.3%** vs **10/33 = 30.3%**; small subgroup, avoid claiming subgroup-specific significance.
- Grade >=3 treatment-related adverse events: **78.0%** vs **73.0%**.
- Treatment-related deaths: **3** vs **1**.
- Trial did not include adjuvant capecitabine; neoadjuvant vs adjuvant contribution was not separable by trial design.
- Survival maturity and long-term safety were explicit limitations.

## Model handling / no leakage
- Store per-endpoint denominators and analysis dates, not a single undifferentiated trial N.
- Label the 2020 EFS data **immature** and record final planned event count.
- Flag exploratory/small PD-L1-negative subgroup and safety burden.
- Do not incorporate the 2022 NEJM EFS report (DOI 10.1056/NEJMoa2112651) into a 2021 pre-decision assessment.
- No retrospective prediction or confidence % is assigned here.
- Publication timing establishes public availability in 2020, but does not independently prove a historically captured, immutable snapshot.

Source: Schmid et al., *N Engl J Med* 2020;382:810–821. DOI: 10.1056/NEJMoa1910549.
