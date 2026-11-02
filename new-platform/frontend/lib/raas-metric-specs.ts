/** RAAS research metric catalog, version 1; specification only, not a validated return predictor.
 * Evidence is linked to exact program identity and assessment date. Missing is NEVER a zero score.
 */
export type RaasStage="pre"|"post";
export type RaasMetric={
 readonly id:string;readonly name:string;readonly requiredEvidence:string;
 readonly scoreRule:string;readonly criticalRisk:string;readonly relatedFieldIds:readonly string[];
};
export type RaasCategory={readonly id:string;readonly name:string;readonly weight:number;readonly metrics:readonly RaasMetric[]};
export type RaasAnchor={readonly points:0|25|50|75|100;readonly label:string;readonly definition:string};
export const RAAS_SPEC_VERSION="2026-11-02-foundation-v1";
export const RAAS_PROVISIONAL_ANCHORS:readonly RaasAnchor[]=[
 {points:0,label:"Materially adverse",definition:"Verified evidence meets a precommitted material-deficiency threshold, never simply missing data."},
 {points:25,label:"Unfavorable",definition:"Verified finding is meaningfully below a disease-, timing-, or market-specific reference benchmark."},
 {points:50,label:"Mixed or neutral",definition:"Verified evidence supports an actual intermediate result; unknown does not receive a 50."},
 {points:75,label:"Favorable",definition:"Verified finding exceeds the relevant precommitted benchmark under sensitivity testing."},
 {points:100,label:"Exceptional",definition:"Exceptional and reliable performance against a precommitted benchmark, with strong uncertainty controls."}
];
export const RAAS_METRIC_CATALOG:Readonly<Record<RaasStage,readonly RaasCategory[]>>={
  "pre": [
    {
      "id": "group-1",
      "name": "Scientific success case",
      "weight": 25,
      "metrics": [
        {
          "id": "pre-1-1",
          "name": "Earlier randomized human efficacy and treatment effect",
          "requiredEvidence": "Randomized Phase 1/2 report, control-arm data, effect sizes, confidence intervals, clinical relevance benchmarks.",
          "scoreRule": "Higher if human benefit is larger, reliable, clinically meaningful and reproducible.",
          "criticalRisk": "Bias, weak control, excessive dropout or exploratory-only positive signals.",
          "relatedFieldIds": [
            "clinicalBenefit",
            "magnitude",
            "meaningfulBenefit"
          ]
        },
        {
          "id": "pre-1-2",
          "name": "Pivotal endpoint alignment, trial power and design",
          "requiredEvidence": "Pivotal protocol and statistical analysis plan, primary endpoint, comparator, power assumptions and sample size.",
          "scoreRule": "Higher for adequate power under conservative effects, validated endpoint and prespecified analysis.",
          "criticalRisk": "Endpoint mismatch, multiplicity or underpowered pivotal design.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-1-3",
          "name": "Mechanism, target engagement and dose response",
          "requiredEvidence": "Human PK/PD, exposure response, target engagement and supported pivotal-dose selection.",
          "scoreRule": "Higher for mechanistic coherence at tolerable clinically attained drug exposure.",
          "criticalRisk": "Unverified human target activity or dose-limiting toxicity.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-1-4",
          "name": "Safety signals and reproducibility",
          "requiredEvidence": "Earlier trial arm-level serious events, tolerability, discontinuation and independent efficacy replication.",
          "scoreRule": "Higher for acceptable tolerability and consistent benefit across independent evidence.",
          "criticalRisk": "Unresolved serious toxicity or nonreplicated signal.",
          "relatedFieldIds": [
            "safetyAdvantage",
            "seriousAes",
            "discontinuation"
          ]
        },
        {
          "id": "pre-1-5",
          "name": "Arguments for and against a successful readout",
          "requiredEvidence": "Negative/neutral trials, alternative explanations, baseline imbalance, placebo patterns and trial amendments.",
          "scoreRule": "Higher if credible counterhypotheses are tested and the treatment effect remains defensible.",
          "criticalRisk": "Plausible unaddressed explanation that could negate Phase 3 efficacy.",
          "relatedFieldIds": [
            "clinicalBenefit",
            "bestSubgroup"
          ]
        }
      ]
    },
    {
      "id": "group-2",
      "name": "Valuation and remaining upside",
      "weight": 25,
      "metrics": [
        {
          "id": "pre-2-1",
          "name": "Current equity value and enterprise value",
          "requiredEvidence": "Dated stock price, diluted shares, cash, debt, SEC filings and enterprise-value reconciliation.",
          "scoreRule": "Higher if risk-adjusted intrinsic equity value exceeds present fully diluted valuation.",
          "criticalRisk": "Unsupported capitalization, stale price or undisclosed obligations.",
          "relatedFieldIds": [
            "valuationImpact"
          ]
        },
        {
          "id": "pre-2-2",
          "name": "Bull, base and bear prices at the TOP exit date",
          "requiredEvidence": "Dated feasible entry and pre-readout exit, explicit bull/base/bear equity value, dilution assumptions.",
          "scoreRule": "Higher if remaining pre-readout upside is robust under conservative exit scenarios.",
          "criticalRisk": "Post-readout gains mistakenly used for a pre-readout exit valuation.",
          "relatedFieldIds": [
            "valuationImpact",
            "shareholderRisk"
          ]
        },
        {
          "id": "pre-2-3",
          "name": "Success expectations implied by today's valuation",
          "requiredEvidence": "Current market cap, asset-level rNPV, modeled outcome probabilities and valuation sensitivity.",
          "scoreRule": "Higher where market-implied expectations materially understate defensible scientific value.",
          "criticalRisk": "Mispricing claimed without asset valuation or plausible probability calibration.",
          "relatedFieldIds": [
            "valuationImpact"
          ]
        },
        {
          "id": "pre-2-4",
          "name": "Probability-weighted remaining return",
          "requiredEvidence": "Scenario exit prices, probabilities totaling 100%, uncertainty bounds, execution costs and historical event calibration.",
          "scoreRule": "Higher for robust positive probability-weighted return, not just a high bull price.",
          "criticalRisk": "Uncalibrated probabilities, missing bear tails or optimistic hindsight.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "pre-2-5",
          "name": "Commercial value without double counting trial results",
          "requiredEvidence": "Patient eligibility, net price, uptake, product cash flows, rights and overlap among NCTs.",
          "scoreRule": "Higher for incremental asset value supported by realistic adoption and costs.",
          "criticalRisk": "Double-counted trials, indications, licensing rights or revenues.",
          "relatedFieldIds": [
            "peakAnnualSales",
            "eligibleUsPatients",
            "licensingValue"
          ]
        }
      ]
    },
    {
      "id": "group-3",
      "name": "Downside protection",
      "weight": 20,
      "metrics": [
        {
          "id": "pre-3-1",
          "name": "Serious clinical failure and early negative-news scenarios",
          "requiredEvidence": "Comparable negative clinical events, timing uncertainty and pre-readout severe-loss scenarios.",
          "scoreRule": "Higher when early-negative-event losses and tail risk are manageable.",
          "criticalRisk": "Assuming surprise early results cannot occur before planned exit.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "pre-3-2",
          "name": "Cash runway beyond the catalyst",
          "requiredEvidence": "Latest quarterly balance sheet, cash burn, debt maturities and estimated milestone spending.",
          "scoreRule": "Higher for conservative runway beyond the intended catalyst and follow-on financing needs.",
          "criticalRisk": "Likely forced financing or solvency risk before exit.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-3-3",
          "name": "Financing and fully diluted share count",
          "requiredEvidence": "Latest SEC ATM/shelf, warrants, convertibles and fully diluted share reconciliation.",
          "scoreRule": "Higher when dilution risk is modest and already reflected per share.",
          "criticalRisk": "Material financing risk omitted from exit-value scenarios.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "pre-3-4",
          "name": "Concentration in the trial drug versus other assets",
          "requiredEvidence": "Segment and asset valuations, other pipeline programs, existing sales, cash and debt.",
          "scoreRule": "Higher if independent assets cushion failure of the trial drug.",
          "criticalRisk": "Nearly all equity value depends on the one unproven program.",
          "relatedFieldIds": [
            "valuationImpact"
          ]
        },
        {
          "id": "pre-3-5",
          "name": "Modeled severe-loss exposure",
          "requiredEvidence": "Combined severe clinical, liquidity, financing and market-shock scenarios, with loss quantiles.",
          "scoreRule": "Higher when stressed losses and expected shortfall remain acceptable.",
          "criticalRisk": "Assuming stop losses eliminate event gaps.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        }
      ]
    },
    {
      "id": "group-4",
      "name": "Readout and exit timing",
      "weight": 15,
      "metrics": [
        {
          "id": "pre-4-1",
          "name": "Source-verified prospective readout window",
          "requiredEvidence": "Most recent sponsor guidance with a future readout window, trial enrollment and dated amendments.",
          "scoreRule": "Higher for corroborated current windows enabling planned exit buffers.",
          "criticalRisk": "Historical source check incorrectly treated as future readout date.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-4-2",
          "name": "Expected trading days remaining",
          "requiredEvidence": "Verified readout range, current market calendar, planned entry and last feasible exit session.",
          "scoreRule": "Higher when a realistic period remains for repricing after costs.",
          "criticalRisk": "Past or nonverified window used as actionable timing.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-4-3",
          "name": "Early readout and delayed announcement risk",
          "requiredEvidence": "Recruitment, data-lock guidance, protocol updates and sponsor scheduling history.",
          "scoreRule": "Higher when early or late readout uncertainty is narrow and modeled.",
          "criticalRisk": "Strategy relies on a speculative exact release day.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-4-4",
          "name": "Entry and planned pre-readout exit",
          "requiredEvidence": "Timestamped entry signal, intended exit buffer and historical bid/ask execution basis.",
          "scoreRule": "Higher when both entry and exit are feasible and fixed before outcomes.",
          "criticalRisk": "Backtest uses future data or a post-readout exit.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-4-5",
          "name": "Other near-term corporate catalysts",
          "requiredEvidence": "Issuer releases, SEC deadlines, other financing and peer clinical catalyst schedules.",
          "scoreRule": "Higher when competing catalysts are known and their risks modeled.",
          "criticalRisk": "Unmodeled offering or adverse peer result before exit.",
          "relatedFieldIds": []
        }
      ]
    },
    {
      "id": "group-5",
      "name": "Medical and peer advantage",
      "weight": 10,
      "metrics": [
        {
          "id": "pre-5-1",
          "name": "Patient-important benefit and unmet need",
          "requiredEvidence": "Disease burden, current standard of care, meaningful difference benchmarks and patient outcomes.",
          "scoreRule": "Higher when credible benefit changes patients' survival, functioning, symptoms or quality of life.",
          "criticalRisk": "Statistical endpoint difference lacks patient-important meaning.",
          "relatedFieldIds": [
            "unmetNeed",
            "meaningfulBenefit",
            "qualityOfLife"
          ]
        },
        {
          "id": "pre-5-2",
          "name": "Same-indication treatment alternatives",
          "requiredEvidence": "Approved labels, guidelines, comparable trial populations and comparator evidence.",
          "scoreRule": "Higher if treatment alternatives leave clear unmet need in the same indication and line.",
          "criticalRisk": "Cross-disease or unmatched endpoints used as superiority proof.",
          "relatedFieldIds": [
            "closestCompetitor",
            "headToHead"
          ]
        },
        {
          "id": "pre-5-3",
          "name": "Evidence-supported competitive differentiation",
          "requiredEvidence": "Matched efficacy, safety, treatment burden and head-to-head evidence where available.",
          "scoreRule": "Higher when differentiating benefit is supported by fair medical comparison.",
          "criticalRisk": "Unsourced or incompatible indirect superiority claim.",
          "relatedFieldIds": [
            "safetyAdvantage",
            "competitiveStrategy"
          ]
        },
        {
          "id": "pre-5-4",
          "name": "Eligible patient population and likely adoption",
          "requiredEvidence": "Source-supported eligible patient pool, line restrictions, biomarker rules and adoption scenarios.",
          "scoreRule": "Higher for credible reachable patients rather than total disease prevalence.",
          "criticalRisk": "Ineligible patients or unconstrained adoption inflate market size.",
          "relatedFieldIds": [
            "eligibleUsPatients",
            "adoption"
          ]
        },
        {
          "id": "pre-5-5",
          "name": "Important safety and treatment-convenience contrasts",
          "requiredEvidence": "Exposure-aligned adverse events, discontinuation, route/frequency, monitoring and adherence evidence.",
          "scoreRule": "Higher for clinically supported safety and convenience relative to alternatives.",
          "criticalRisk": "Key treatment burdens or toxicity undermine the intended population.",
          "relatedFieldIds": [
            "safetyAdvantage",
            "convenience"
          ]
        }
      ]
    },
    {
      "id": "group-6",
      "name": "Liquidity and execution",
      "weight": 5,
      "metrics": [
        {
          "id": "pre-6-1",
          "name": "Daily trading volume and bid-ask spread",
          "requiredEvidence": "Dated daily volumes, bid/ask spread, market depth and intended position size.",
          "scoreRule": "Higher when intended entry and exit can be executed with low expected impact.",
          "criticalRisk": "Thin volume or spread consumes projected upside.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-6-2",
          "name": "Share float, volatility and event-gap risk",
          "requiredEvidence": "Float, realized volatility, historical biotech event gaps and size-sensitive risk.",
          "scoreRule": "Higher for controlled volatility and event loss relative to the modeled return.",
          "criticalRisk": "Overnight gap assumed stoppable by a stop-loss.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-6-3",
          "name": "Slippage and trading-window assumptions",
          "requiredEvidence": "Quoted/effective spreads, trade size, market impact and price-window assumptions.",
          "scoreRule": "Higher when expected appreciation remains favorable after realistic trading friction.",
          "criticalRisk": "Expected alpha disappears with slippage.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-6-4",
          "name": "Position sizing and concentration risk",
          "requiredEvidence": "Portfolio allocation policy, trial overlap, issuer exposure and planned loss budgets.",
          "scoreRule": "Higher for sized positions that respect specified stress-loss budget.",
          "criticalRisk": "Oversized single-issuer exposure.",
          "relatedFieldIds": []
        },
        {
          "id": "pre-6-5",
          "name": "Correlated portfolio and catalyst exposure",
          "requiredEvidence": "Portfolio biotech positions, shared mechanism/catalyst correlations and market-shock stress tests.",
          "scoreRule": "Higher where correlated-event losses remain within portfolio risk limits.",
          "criticalRisk": "Several highly correlated trials mistakenly treated as diversification.",
          "relatedFieldIds": []
        }
      ]
    }
  ],
  "post": [
    {
      "id": "group-1",
      "name": "Actual Phase 3 clinical benefit",
      "weight": 25,
      "metrics": [
        {
          "id": "post-1-1",
          "name": "Primary endpoint and treatment effect size",
          "requiredEvidence": "Full Phase 3 protocol, SAP, arm-level endpoint effect, confidence interval and comparator.",
          "scoreRule": "Higher for large, clinically meaningful prespecified effects with reliable controls.",
          "criticalRisk": "Only a p-value or promotional topline without treatment effect.",
          "relatedFieldIds": [
            "clinicalBenefit",
            "magnitude"
          ]
        },
        {
          "id": "post-1-2",
          "name": "Clinical importance and patient-reported outcomes",
          "requiredEvidence": "Patient-important functional/symptom/survival outcomes, responder definitions and QoL instruments.",
          "scoreRule": "Higher for demonstrated meaningful improvement in how patients feel, function or survive.",
          "criticalRisk": "Significant but clinically trivial endpoint change.",
          "relatedFieldIds": [
            "meaningfulBenefit",
            "qualityOfLife",
            "survivalBenefit"
          ]
        },
        {
          "id": "post-1-3",
          "name": "Confidence intervals, multiplicity and missing-data sensitivity",
          "requiredEvidence": "Multiplicity-adjusted tests, confidence intervals, missing-data and sensitivity analyses.",
          "scoreRule": "Higher when results persist under reasonable conservative analyses.",
          "criticalRisk": "Endpoint switching, uncorrected multiplicity or fragile missing-data assumptions.",
          "relatedFieldIds": [
            "clinicalBenefit",
            "magnitude"
          ]
        },
        {
          "id": "post-1-4",
          "name": "Replication, durability and subgroup reliability",
          "requiredEvidence": "Independent pivotal results, longitudinal follow-up, prespecified subgroup interactions.",
          "scoreRule": "Higher for replicated, durable results rather than post-hoc selected subgroups.",
          "criticalRisk": "Nonreplicable benefit or effect lost during follow-up.",
          "relatedFieldIds": [
            "durability",
            "bestSubgroup"
          ]
        },
        {
          "id": "post-1-5",
          "name": "Safety, tolerability and matched medical peer comparison",
          "requiredEvidence": "Complete safety and discontinuation tables with relevant comparator labels and exposure.",
          "scoreRule": "Higher for favorable net benefit-risk and qualified peer comparisons.",
          "criticalRisk": "Serious toxicity overwhelms patient benefit.",
          "relatedFieldIds": [
            "safetyAdvantage",
            "seriousAes",
            "discontinuation"
          ]
        }
      ]
    },
    {
      "id": "group-2",
      "name": "Remaining valuation upside",
      "weight": 25,
      "metrics": [
        {
          "id": "post-2-1",
          "name": "Current post-readout enterprise and equity valuation",
          "requiredEvidence": "Dated post-readout stock price, enterprise value, diluted shares, net cash and liabilities.",
          "scoreRule": "Higher when residual risk-adjusted asset value is favorable relative to the post-results stock price.",
          "criticalRisk": "Pre-results price used to claim remaining upside.",
          "relatedFieldIds": [
            "valuationImpact"
          ]
        },
        {
          "id": "post-2-2",
          "name": "Bull, base and bear values at the BOTTOM exit date",
          "requiredEvidence": "Exact PDUFA action target, minus-three-day exit, plausible scenarios and diluted equity forecasts.",
          "scoreRule": "Higher for favorable exit-date upside under realistic bear/base/bull scenarios.",
          "criticalRisk": "FDA decision gains included despite pre-decision exit.",
          "relatedFieldIds": [
            "valuationImpact",
            "shareholderRisk"
          ]
        },
        {
          "id": "post-2-3",
          "name": "Value already reflected in stock price after the readout",
          "requiredEvidence": "Post-readout market price, asset rNPV, peer data, approval expectations and implied valuation.",
          "scoreRule": "Higher when strong disclosed trial results are still undervalued.",
          "criticalRisk": "Treats already announced results as unrecognized future news.",
          "relatedFieldIds": [
            "valuationImpact"
          ]
        },
        {
          "id": "post-2-4",
          "name": "Probability-weighted remaining return",
          "requiredEvidence": "Regulatory, financing and sentiment scenarios with calibrated probabilities and feasible exit prices.",
          "scoreRule": "Higher for robust favorable probability-weighted appreciation before cutoff.",
          "criticalRisk": "Arbitrary approval probability substituted for stock-return scenarios.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "post-2-5",
          "name": "Projected dilution and other company assets",
          "requiredEvidence": "Fully diluted shares, future offerings, debt, royalties, shared assets and retained cash.",
          "scoreRule": "Higher for durable per-share value after financing and asset attribution.",
          "criticalRisk": "Double-counted assets or omission of large future dilution.",
          "relatedFieldIds": [
            "valuationImpact",
            "licensingValue"
          ]
        }
      ]
    },
    {
      "id": "group-3",
      "name": "FDA, safety and manufacturing risk",
      "weight": 20,
      "metrics": [
        {
          "id": "post-3-1",
          "name": "FDA submission and application acceptance status",
          "requiredEvidence": "Exact NDA/BLA submission and FDA acceptance source for named indication and program.",
          "scoreRule": "Higher when review progression is independently verified with fewer outstanding uncertainties.",
          "criticalRisk": "A successful Phase 3 readout mistaken for an accepted filing.",
          "relatedFieldIds": []
        },
        {
          "id": "post-3-2",
          "name": "Scientific adequacy of the pivotal evidence",
          "requiredEvidence": "All pivotal results, statistical adequacy, FDA guidance and disclosed regulatory feedback.",
          "scoreRule": "Higher if the total evidence package supports the requested label and indication.",
          "criticalRisk": "Material deficiency in pivotal proof or required confirmation.",
          "relatedFieldIds": [
            "clinicalBenefit",
            "magnitude"
          ]
        },
        {
          "id": "post-3-3",
          "name": "Benefit-risk, indication and labeling questions",
          "requiredEvidence": "Safety tables, relevant FDA labels, risk management and subgroup restriction evidence.",
          "scoreRule": "Higher where net benefit supports a useful treatment label with manageable risk.",
          "criticalRisk": "Serious safety concern or label likely excludes modeled patients.",
          "relatedFieldIds": [
            "safetyAdvantage",
            "seriousAes"
          ]
        },
        {
          "id": "post-3-4",
          "name": "CMC, facilities and quality issues",
          "requiredEvidence": "Public CMC disclosures, manufacturing validation, facility inspections and supplier quality information.",
          "scoreRule": "Higher with corroborated readiness and no material unresolved deficiencies.",
          "criticalRisk": "Known CMC or facility issue capable of delaying action.",
          "relatedFieldIds": []
        },
        {
          "id": "post-3-5",
          "name": "Verified PDUFA date and unresolved review risks",
          "requiredEvidence": "Source-verified accepted application and PDUFA target, dated review developments and changes.",
          "scoreRule": "Higher when the exact-program target is verified and review risks are explicitly assessed.",
          "criticalRisk": "Invented, outdated or wrong-program PDUFA date.",
          "relatedFieldIds": []
        }
      ]
    },
    {
      "id": "group-4",
      "name": "Downside and financing",
      "weight": 15,
      "metrics": [
        {
          "id": "post-4-1",
          "name": "Regulatory delay and adverse-decision scenarios",
          "requiredEvidence": "Early review events and analogous adverse-news scenarios before scheduled exit.",
          "scoreRule": "Higher when credible pre-cutoff regulatory shock losses are controlled.",
          "criticalRisk": "Assumes all agency setbacks occur only on target action day.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "post-4-2",
          "name": "Cash runway, debt and convertible securities",
          "requiredEvidence": "Latest cash, burn, debt, convertibles, covenants and launch readiness spending.",
          "scoreRule": "Higher for runway covering the target and post-decision needs.",
          "criticalRisk": "Pre-PDUFA liquidity shortfall.",
          "relatedFieldIds": []
        },
        {
          "id": "post-4-3",
          "name": "Financing and future dilution risk",
          "requiredEvidence": "SEC shelf/ATM, anticipated offerings, options, warrants and dilution waterfall.",
          "scoreRule": "Higher for small, fully incorporated financing uncertainty.",
          "criticalRisk": "Nominal upside ignores likely offering.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "post-4-4",
          "name": "Severe-loss exposure before the planned exit",
          "requiredEvidence": "Early regulatory, safety, manufacturing and liquidity joint tail scenarios.",
          "scoreRule": "Higher for smaller severe-loss exposure and expected shortfall before cutoff.",
          "criticalRisk": "Price gap and event tail risk omitted.",
          "relatedFieldIds": [
            "shareholderRisk"
          ]
        },
        {
          "id": "post-4-5",
          "name": "Sensitivity to lower modeled commercial value",
          "requiredEvidence": "Conservative net price, eligible patients, adoption, margin, competition and discount rate sensitivities.",
          "scoreRule": "Higher when downside remains contained under realistic commercial stress.",
          "criticalRisk": "Value collapses under minor reductions in price or uptake.",
          "relatedFieldIds": [
            "adoption",
            "treatmentPrice",
            "peakAnnualSales"
          ]
        }
      ]
    },
    {
      "id": "group-5",
      "name": "Patients, payers and competition",
      "weight": 10,
      "metrics": [
        {
          "id": "post-5-1",
          "name": "Evidence-supported eligible patient population",
          "requiredEvidence": "Indication-specific epidemiology, trial inclusion criteria, label, line of therapy and geography.",
          "scoreRule": "Higher for a credible eligible treated patient population rather than prevalence.",
          "criticalRisk": "Patients modeled are ineligible for the proposed label.",
          "relatedFieldIds": [
            "eligibleUsPatients",
            "internationalPatients"
          ]
        },
        {
          "id": "post-5-2",
          "name": "Clinical advantage against relevant alternatives",
          "requiredEvidence": "Approved competitor labels, matched patient groups/endpoints and comparative clinical reports.",
          "scoreRule": "Higher for meaningful, defensible clinical differentiation in the same indication.",
          "criticalRisk": "Unmatched across-trial efficacy comparison.",
          "relatedFieldIds": [
            "closestCompetitor",
            "headToHead"
          ]
        },
        {
          "id": "post-5-3",
          "name": "Reimbursement, insurer restrictions and coverage assumptions",
          "requiredEvidence": "Public coverage policies of comparable drugs, payer restrictions and value/cost evidence.",
          "scoreRule": "Higher for credible reimbursement after restrictions and net economics.",
          "criticalRisk": "Universal access assumed before payer evidence.",
          "relatedFieldIds": [
            "payerAccess",
            "valuePerOutcome"
          ]
        },
        {
          "id": "post-5-4",
          "name": "Net pricing, uptake and market penetration",
          "requiredEvidence": "Comparable net pricing, duration, adoption, persistence, switching and revenue ramp.",
          "scoreRule": "Higher for realistic net revenue after discounts and competition.",
          "criticalRisk": "Gross list price or implausible penetration treated as revenue.",
          "relatedFieldIds": [
            "treatmentPrice",
            "adoption"
          ]
        },
        {
          "id": "post-5-5",
          "name": "Peak sales, exclusivity and competitive threats",
          "requiredEvidence": "Cash-flow forecasts, exclusivity/expiry, competing pipeline, regional and licensing rights.",
          "scoreRule": "Higher for defensible product lifetime revenue under competition.",
          "criticalRisk": "Peak-sales assumptions ignore patent expiry or license costs.",
          "relatedFieldIds": [
            "peakAnnualSales",
            "exclusivity",
            "competitivePipelineThreat"
          ]
        }
      ]
    },
    {
      "id": "group-6",
      "name": "PDUFA timing and execution",
      "weight": 5,
      "metrics": [
        {
          "id": "post-6-1",
          "name": "Confirmed exact-program PDUFA target",
          "requiredEvidence": "Accepted FDA application and exact product/indication action date from dated public source.",
          "scoreRule": "Higher if a future source-verified PDUFA target supports strategy eligibility.",
          "criticalRisk": "Unconfirmed or different-product date.",
          "relatedFieldIds": []
        },
        {
          "id": "post-6-2",
          "name": "Planned exit three calendar days before that target",
          "requiredEvidence": "Confirmed date, US market session calendar and conservative sell cutoff three calendar days before.",
          "scoreRule": "Higher for feasible and correctly calculated plan before the cutoff.",
          "criticalRisk": "Cutoff occurs after change in PDUFA target or nontrading day.",
          "relatedFieldIds": []
        },
        {
          "id": "post-6-3",
          "name": "Unexpected early action and adverse-news risk",
          "requiredEvidence": "Early action precedents, current review disclosure and adverse news sensitivity.",
          "scoreRule": "Higher when early decisions and safety/CMC announcements are included in risk scenarios.",
          "criticalRisk": "Assumes FDA cannot act before its target.",
          "relatedFieldIds": []
        },
        {
          "id": "post-6-4",
          "name": "Trading spreads, liquidity and timing",
          "requiredEvidence": "Dated spreads, volume, market depth, position size, event volatility and slippage.",
          "scoreRule": "Higher where a position can exit before cutoff with low costs.",
          "criticalRisk": "Thin market makes modeled exit price unrealistic.",
          "relatedFieldIds": []
        },
        {
          "id": "post-6-5",
          "name": "Other milestones occurring before the exit",
          "requiredEvidence": "Issuer milestones, SEC deadlines, competitor events and financing announcements before cutoff.",
          "scoreRule": "Higher when all material near-term catalysts are identified and stress tested.",
          "criticalRisk": "Large other catalyst ignored.",
          "relatedFieldIds": []
        }
      ]
    }
  ]
};
