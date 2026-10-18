"use client";
import type {Candidate} from "./Workspace";
import {GEM_CLINICAL_FILTERS,GEM_TRADING_FILTERS,gemMatchesCheckedFilters,
        type GemCriterion} from "../lib/gem-qualification-checks";

type Stage="GEM"|"GEM_JR";
export default function GemQualificationCheckboxes({
  stage,records,checked,onCheckedChange
}:{
  stage:Stage; records:Candidate[]; checked:string[];
  onCheckedChange:(key:string,value:boolean)=>void;
}){
  const filtered=records.filter(r=>gemMatchesCheckedFilters(r,checked)).length;
  const group=(title:string,items:readonly GemCriterion[])=><div className="gem-real-checkbox-grid">
    {items.map(c=><label className={"gem-real-check"+(checked.includes(c.key)?" gem-real-check-active":"")}
       key={c.key} title={c.help}>
      <input type="checkbox"
        checked={checked.includes(c.key)}
        onChange={event=>onCheckedChange(c.key,event.target.checked)}
        aria-label={c.label}/>
      <span>{c.label}</span>
    </label>)}
  </div>;
  return <section className="gem-real-checkbox-panel"
    aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checkbox filters"}>
    <div className="gem-real-checkbox-head">
      <strong>QUALIFICATION CHECKBOXES — {stage==="GEM"?"GEM":"GEM JR"}</strong>
      <button type="button" className="secondary" onClick={()=>
        checked.forEach(key=>onCheckedChange(key,false))}
        disabled={!checked.length}>CLEAR ALL</button>
    </div>
    <p className="subtle small">Select any combination. Every checked item must pass
      for a trial to appear. Missing evidence never counts as PASS.
      These are display filters only—clinical eligibility and scanning rules do not change.</p>
    <div className="gem-real-checkbox-group">
      <h4>CLINICAL / FINANCING / FDA</h4>
      {group("Clinical",GEM_CLINICAL_FILTERS)}
    </div>
    <details className="gem-real-trading-group" open>
      <summary>TRADING — OPTIONAL CHECKBOXES ({GEM_TRADING_FILTERS.length})</summary>
      {group("Trading",GEM_TRADING_FILTERS)}
    </details>
    <p className="gem-real-checkbox-count" role="status" aria-live="polite">
      <strong>{filtered} / {records.length}</strong> matching programs ·
      {checked.length} combined criteria selected
    </p>
  </section>;
}
