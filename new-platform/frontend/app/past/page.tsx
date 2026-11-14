"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import ScientificStepsReadiness from "../ScientificStepsReadiness";
import {ExactTrialIntakeSelector} from "../ExactTrialScientificIntake";
import historical from "../../data/level4BlindAssessmentQueue20261112.json";
import comparisons from "../../data/blindHistoricalComparisons2026.json";

type HistoricalRow={eventKey:string;ticker:string;cutoffDate:string;level4Score:number|null;blindPrediction:string|null;confidence:number|null;status:string};
const rows=historical.historical2026 as HistoricalRow[];
const known=comparisons.records;
export default function PastPage(){
 const [year,setYear]=useState("2026");
 const [search,setSearch]=useState("");
 const [reveal,setReveal]=useState(false);
 const [verifiedNctByEvent,setVerifiedNctByEvent]=useState<Record<string,string>>({});
 const filtered=useMemo(()=>year==="2026"?rows.filter(r=>(r.ticker+" "+r.eventKey).toLowerCase().includes(search.toLowerCase())):[],[year,search]);
 return <main style={{maxWidth:1400,margin:"24px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif"}}>
 <nav style={{display:"flex",gap:14,marginBottom:16}}><Link href="/focus">FOCUS</Link><strong>PAST</strong><Link href="/pool">POOL</Link></nav>
 <h1>PAST — Historical PDUFA trials</h1>
 <ScientificStepsReadiness cohort="PAST"/>
 <p>Year-by-year historical cohort. The 2026 queue is an evidence-freeze research queue, not a verified complete FDA decision census. No missing values are treated as zero or as a negative decision.</p>
 <div style={{display:"flex",gap:12,alignItems:"center",flexWrap:"wrap",marginBottom:16}}>
 <label>Year <select aria-label="PDUFA year" value={year} onChange={e=>setYear(e.target.value)}>{Array.from({length:10},(_,i)=>2026-i).map(y=><option key={y}>{y}</option>)}</select></label>
 <label>Search <input aria-label="Search historical trials" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Ticker or application"/></label>
 <label><input type="checkbox" checked={reveal} onChange={e=>setReveal(e.target.checked)}/> Reveal verified FDA decisions (exclude from blind scoring)</label>
 </div>
 <p><strong>{filtered.length}</strong> queued historical records for {year}. {year!=="2026"?"Historical cohort not imported for this year.":""}</p>
 <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
 <table style={{borderCollapse:"collapse",minWidth:1650,width:"100%",fontSize:13}}>
 <thead style={{background:"#e6f2ea"}}><tr>{["Ticker","NCT / Trial","Company","FDA Special Designations","Market cap ($B)","FDA / PDUFA path","Sources","7 gate checks","PDUFA date (unverified queue date)","Assessment level","Score","Confidence","Blind prediction","FDA Decision Type","FDA Decision"].map(h=><th key={h} style={{textAlign:"left",padding:10,whiteSpace:"nowrap"}}>{h}</th>)}</tr></thead>
 <tbody>{filtered.map((r,i)=>{const name=r.eventKey.split("|")[2]||"Not recorded";const verified=known.find(k=>k.ticker===r.ticker&&k.actualFdaActionDate===r.cutoffDate);
 return <tr key={r.eventKey} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
 <td style={{padding:9,fontWeight:700}}>{r.ticker}</td><td style={{padding:9}}><details><summary>Not linked · enter candidate NCT</summary><label style={{fontSize:12}}>Exact NCT <input aria-label={"Candidate NCT for "+r.eventKey} value={verifiedNctByEvent[r.eventKey]??""} onChange={e=>setVerifiedNctByEvent(prev=>({...prev,[r.eventKey]:e.target.value.toUpperCase()}))} placeholder="NCT12345678" maxLength={11}/></label>{/^NCT\\d{8}$/.test(verifiedNctByEvent[r.eventKey]??"")?<ExactTrialIntakeSelector cohort="PAST" nctId={verifiedNctByEvent[r.eventKey]}/>:<p style={{fontSize:11}}>Historical event-to-NCT linkage remains unverified; no intake displayed.</p>}</details></td><td style={{padding:9}}>Not recorded</td><td style={{padding:9}}>Not verified</td><td style={{padding:9}}>—</td>
 <td style={{padding:9}}>{name}</td><td style={{padding:9}}>Evidence pending</td><td style={{padding:9}}>Not assessed</td>
 <td style={{padding:9}}>{r.cutoffDate}</td><td style={{padding:9}}>Level 4 queued</td><td style={{padding:9}}>{r.level4Score??"Pending"}</td><td style={{padding:9}}>{r.confidence??"Pending"}</td><td style={{padding:9}}>{r.blindPrediction??"Pending"}</td>
 <td style={{padding:9}}>{!reveal?"Hidden":verified?verified.approvalType:"Not verified"}</td><td style={{padding:9}}>{!reveal?"Hidden":verified?verified.actualOutcome:"Not verified"}</td>
 </tr>})}</tbody></table></div>
 <p style={{fontSize:12,color:"#526458"}}>Queue dates are scheduling/cutoff metadata, not independently confirmed PDUFA dates. Decision data is deliberately separated from blind predictions. The full FOCUS schema is shown; unavailable historical fields remain explicitly unverified.</p>
 </main>;
}
