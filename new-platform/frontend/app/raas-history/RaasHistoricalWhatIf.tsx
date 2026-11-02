"use client";
import {useState} from "react";
import {researchCostReplay} from "../../lib/raas-finance-reconciliation";
import css from "./page.module.css";

type CaseInput={id:string;ticker:string;stage:"pre"|"post";entryPrice:number;exitPrice:number};
export default function RaasHistoricalWhatIf({cases}:{cases:CaseInput[]}){
 const [roundTripBps,setRoundTripBps]=useState(50);
 const [shockPercent,setShockPercent]=useState(-20);
 return <div className={css.whatIf} data-research-simulation="retrospective-cost-and-shock">
   <div className={css.whatIfHeader}>
     <h2>Historical cost &amp; price-shock laboratory</h2>
     <p><strong>Hypothetical only.</strong> Change assumptions to understand trading friction and downside. Results are not investment forecasts, validated fills, model performance, or RAAS metric grades.</p>
   </div>
   <div className={css.whatIfControls}>
     <label htmlFor="raas-hypothetical-costs">Illustrative total round-trip costs: <strong>{roundTripBps} bps ({(roundTripBps/100).toFixed(2)}%)</strong></label>
     <input id="raas-hypothetical-costs" type="range" min="0" max="500" step="25"
       value={roundTripBps} onChange={event=>setRoundTripBps(Number(event.target.value))}/>
     <label htmlFor="raas-hypothetical-price-shock">Independent hypothetical share-price move from entry: <strong>{shockPercent>=0?"+":""}{shockPercent}%</strong></label>
     <input id="raas-hypothetical-price-shock" type="range" min="-80" max="100" step="5"
       value={shockPercent} onChange={event=>setShockPercent(Number(event.target.value))}/>
   </div>
   <div className={css.sandboxTableWrap}>
     <table className={css.sandboxTable}>
       <thead><tr><th>Phase / ticker</th><th>Observed gross</th><th>Historical close less <em>hypothetical</em> costs</th><th>Independent hypothetical shock after costs</th></tr></thead>
       <tbody>{cases.map(c=>{
         const result=researchCostReplay(c.entryPrice,c.exitPrice,roundTripBps,shockPercent);
         if(!result)return <tr key={c.id}><td>{c.ticker}</td><td colSpan={3}>Inputs incomplete</td></tr>;
         return <tr key={c.id}><th scope="row">{c.stage==="pre"?"TOP":"BOTTOM"} · {c.ticker}</th>
           <td>{result.observedGrossPercent>=0?"+":""}{result.observedGrossPercent.toFixed(2)}%</td>
           <td>{result.hypotheticalAfterCostsPercent>=0?"+":""}{result.hypotheticalAfterCostsPercent.toFixed(2)}%</td>
           <td>{result.hypotheticalShockReturnAfterCostsPercent>=0?"+":""}{result.hypotheticalShockReturnAfterCostsPercent.toFixed(2)}% <small>(exit at ${result.hypotheticalShockExitPrice.toFixed(2)} if the shock occurred)</small></td>
         </tr>;
       })}</tbody>
     </table>
   </div>
   <p className={css.whatIfFoot}>This calculator subtracts the chosen cost percentage from a simple gross share-price percentage change. The shock scenario is a separately assumed change from entry, not a fitted price prediction. Dividends, borrow costs, overnight fills, stock splits, ADR conversion, taxes and genuine transaction execution are not reconciled. It never updates historical scores or the approved-grade ledger.</p>
 </div>;
}
