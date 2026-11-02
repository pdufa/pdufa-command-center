"use client";
import type {ReadoutRow} from "../lib/phase3-public-readout";
import type {readoutResearchCoverage} from "../lib/phase3-readout-sort";
import css from "./TrialRaasDisclosure.module.css";

type Stage="pre"|"post";
type ResearchStatus="idle"|"loading"|"ready"|"unavailable";
type Coverage=ReturnType<typeof readoutResearchCoverage>;
type Ingredient={name:string;weight:number;factors:readonly string[]};
const TOP:readonly Ingredient[]=[
 {name:"Scientific success case",weight:25,factors:["Earlier randomized human efficacy and treatment effect","Pivotal endpoint alignment, trial power and design","Mechanism, target engagement and dose response","Safety signals and reproducibility","Arguments for and against a successful readout"]},
 {name:"Valuation and remaining upside",weight:25,factors:["Current equity value and enterprise value","Bull, base and bear prices at the TOP exit date","Success expectations implied by today's valuation","Probability-weighted remaining return","Commercial value without double counting trial results"]},
 {name:"Downside protection",weight:20,factors:["Serious clinical failure and early negative-news scenarios","Cash runway beyond the catalyst","Financing and fully diluted share count","Concentration in the trial drug versus other assets","Modeled severe-loss exposure"]},
 {name:"Readout and exit timing",weight:15,factors:["Source-verified prospective readout window","Expected trading days remaining","Early readout and delayed announcement risk","Entry and planned pre-readout exit","Other near-term corporate catalysts"]},
 {name:"Medical and peer advantage",weight:10,factors:["Patient-important benefit and unmet need","Same-indication treatment alternatives","Evidence-supported competitive differentiation","Eligible patient population and likely adoption","Important safety and treatment-convenience contrasts"]},
 {name:"Liquidity and execution",weight:5,factors:["Daily trading volume and bid-ask spread","Share float, volatility and event-gap risk","Slippage and trading-window assumptions","Position sizing and concentration risk"]}
];
const BOTTOM:readonly Ingredient[]=[
 {name:"Actual Phase 3 clinical benefit",weight:25,factors:["Primary endpoint and treatment effect size","Clinical importance and patient-reported outcomes","Confidence intervals, multiplicity and missing-data sensitivity","Replication, durability and subgroup reliability","Safety, tolerability and matched medical peer comparison"]},
 {name:"Remaining valuation upside",weight:25,factors:["Current post-readout enterprise and equity valuation","Bull, base and bear values at the BOTTOM exit date","Value already reflected in stock price after the readout","Probability-weighted remaining return","Projected dilution and other company assets"]},
 {name:"FDA, safety and manufacturing risk",weight:20,factors:["FDA submission and application acceptance status","Scientific adequacy of the pivotal evidence","Benefit-risk, indication and labeling questions","CMC, facilities and quality issues","Verified PDUFA date and unresolved review risks"]},
 {name:"Downside and financing",weight:15,factors:["Regulatory delay and adverse-decision scenarios","Cash runway, debt and convertible securities","Financing and future dilution risk","Severe-loss exposure before the planned exit","Sensitivity to lower modeled commercial value"]},
 {name:"Patients, payers and competition",weight:10,factors:["Evidence-supported eligible patient population","Clinical advantage against relevant alternatives","Reimbursement, insurer restrictions and coverage assumptions","Net pricing, uptake and market penetration","Peak sales, exclusivity and competitive threats"]},
 {name:"PDUFA timing and execution",weight:5,factors:["Confirmed exact-program PDUFA target","Planned exit three calendar days before that target","Unexpected early action and adverse-news risk","Trading spreads, liquidity and timing","Other milestones occurring before the exit"]}
];
export default function TrialRaasDisclosure({row,bucket,researchStatus,coverage,onResearchRequest}:{
  row:ReadoutRow;bucket:Stage;researchStatus:ResearchStatus;
  coverage:Coverage;onResearchRequest:()=>void;
}){
 const isTop=bucket==="pre";
 const label=isTop?"TOP-RAAS":"BOTTOM-RAAS";
 const groups=isTop?TOP:BOTTOM;
 return <details className={css.raas} data-raas-phase={bucket} data-raas-trial={row.nctId}>
   <summary className={css.summary} onClick={onResearchRequest}
     aria-label={label+" · "+row.ticker+" "+row.nctId+" · expand or collapse proposed score ingredients"}>
     <span className={css.summaryText}><strong>{label}</strong>
       <small>— / 100 · Not scored</small></span>
     <span className={css.chevron} aria-hidden="true">▸</span>
   </summary>
   <div className={css.panel}>
     <p className={css.disclaimer}><strong>Proposed risk-adjusted appreciation score.</strong> No numeric grade is calculated until the phase-specific methodology, current prices, event dates and evidence are verified and validated. Missing inputs are not zeros.</p>
     <div className={css.snapshots} aria-label={label+" score snapshots"}>
       <div><strong>ENTRY</strong><span>— / 100</span><small>{isTop?"Pre-readout signal":"Post-readout signal"}</small></div>
       <div><strong>CURRENT</strong><span>— / 100</span><small>Reassessed as evidence changes</small></div>
       <div><strong>EXIT</strong><span>— / 100</span><small>{isTop?"Before public Phase 3 data":"PDUFA − 3 days if verified"}</small></div>
     </div>
     <p className={css.hint}>Select any ingredient group to expand its components <strong>to the right</strong>. Every group starts retracted.</p>
     <div className={css.factors} aria-label={label+" six weighted ingredients"}>
       {groups.map((group,i)=><details key={group.name} className={css.factor} data-raas-factor={i+1}>
         <summary className={css.factorSummary}>
           <span className={css.factorName}><strong>{i+1}. {group.name}</strong><small>Weight {group.weight}% · grade unassigned</small></span>
           <span className={css.factorChevron} aria-hidden="true">▸</span>
         </summary>
         <div className={css.factorBody}>
           <strong>Underlying assessments</strong>
           <ol>{group.factors.map(item=><li key={item}>{item}</li>)}</ol>
         </div>
       </details>)}
     </div>
     <div className={css.coverage} role="status">
       {researchStatus==="loading"?"Loading source-backed research inputs…":
        researchStatus==="unavailable"?"Research feed unavailable; no score inferred.":
        coverage?coverage.verified+" verified research inputs recorded; evidence coverage is not a RAAS score.":
        "Research inputs not yet assessed. The category weights do not establish trial success or upside."}
     </div>
     <p className={css.disclaimer}>{isTop?
       "TOP source-check evidence is historical; it does not verify a future readout date or that results remain unreleased.":
       "A positive Phase 3 readout does not establish FDA filing acceptance or an actionable PDUFA date."}</p>
   </div>
 </details>;
}
