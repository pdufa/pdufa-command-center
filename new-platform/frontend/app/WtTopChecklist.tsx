"use client";
import {useState} from "react";
import type {Candidate} from "./Workspace";
import WtTradingSections from "./WtTradingSections";

export type TrackedWtProgram={programId:string;ticker:string;drug:string;record?:Candidate};

export default function WtTopChecklist({programs}:{programs:TrackedWtProgram[]}){
 const [choice,setChoice]=useState("");
 const active=programs.find(x=>x.programId===choice);
 return <section className="panel wt-checklist-primary" aria-label="WT main Entry Stay Exit checklists">
   <div className="sectionhead">
     <div>
       <h3>WT — ENTRY / STAY / EXIT CHECKLISTS</h3>
       <p className="subtle">Three original-style checkbox areas are always available here.
         Every box starts unchecked. These research selections do not submit orders or
         modify the GEM / GEM JR scanning rules.</p>
     </div>
     <span className="counter">26 indicators · 0 selected initially</span>
   </div>
   <label className="wt-checklist-program-picker">
     <strong>PROGRAM FOR ALPACA NUMBERS</strong>
     <select aria-label="Choose WT program for Alpaca indicators"
       value={active?.programId||""}
       onChange={e=>setChoice(e.target.value)}>
       <option value="">Choose a WT program to display its Alpaca readings</option>
       {programs.map(p=><option key={p.programId} value={p.programId}>
         {p.ticker} · {p.drug||"Drug not recorded"} · {p.programId}
       </option>)}
     </select>
   </label>
   {programs.length===0&&<p className="subtle small" role="status">
     No exact programs are saved in your WT Watchlist or Trading Research yet.
     The checkboxes are visible below regardless. Use W/T on a GEM, GEM JR,
     or PIPELINE program to make its Alpaca market data available here.
   </p>}
   <WtTradingSections key={active?.programId||"NO_PROGRAM_SELECTED"}
     programId={active?.programId||""}
     ticker={active?.ticker||""}
     record={active?.record}
     tech={active?.record?.technical}
     autoFetch={Boolean(active)}
   />
 </section>;
}
