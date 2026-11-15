"use client";
import {useMemo,useState} from "react";
import Link from "next/link";
import NumericSortSettings,{sortNumericRows,type NumericSortRule} from "../NumericSortSettings";
import historical from "../../data/level4BlindAssessmentQueue20261112.json";
import comparisons from "../../data/blindHistoricalComparisons2026.json";

type HistoricalRow={eventKey:string;ticker:string;cutoffDate:string;level4Score:number|null;blindPrediction:string|null;confidence:number|null;status:string};
const rows=historical.historical2026 as HistoricalRow[];
const known=comparisons.records;
const assessmentLevelLabels=["Trial identity","Current phase","Source evidence","Study protocol","Population","Efficacy","Statistics","Safety","Clinical benefit","Comparator","Subgroups","Data gaps","Regulatory history","FDA alignment","Manufacturing","Benefit–risk","Exceptions","External evidence","Confidence","Integrated review"];
export default function PastPage(){
 const [year,setYear]=useState("2026");
 const [search,setSearch]=useState("");
 const [reveal,setReveal]=useState(false);
 const [sortRules,setSortRules]=useState<NumericSortRule[]>([]);
 const filtered=useMemo(()=>{const subset=year==="2026"?rows.filter(r=>(r.ticker+" "+r.eventKey).toLowerCase().includes(search.toLowerCase())):[];return sortNumericRows(subset,sortRules,(r,c)=>c==="level4Score"?r.level4Score:c==="confidence"?r.confidence:c==="L4"?r.level4Score:null,r=>r.eventKey)},[year,search,sortRules]);
 return <main style={{maxWidth:1400,margin:"24px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif"}}>
 <nav style={{display:"flex",gap:14,marginBottom:16}}><Link href="/focus">FOCUS</Link><strong>PAST</strong><Link href="/pool">POOL</Link></nav>
 <h1>PAST — Historical PDUFA trials</h1>
 <p>Year-by-year historical cohort. The 2026 queue is an evidence-freeze research queue, not a verified complete FDA decision census. No missing values are treated as zero or as a negative decision.</p>
 <div style={{display:"flex",gap:12,alignItems:"center",flexWrap:"wrap",marginBottom:16}}>
 <label>Year <select aria-label="PDUFA year" value={year} onChange={e=>setYear(e.target.value)}>{Array.from({length:10},(_,i)=>2026-i).map(y=><option key={y}>{y}</option>)}</select></label>
 <label>Search <input aria-label="Search historical trials" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Ticker or application"/></label>
 <label><input type="checkbox" checked={reveal} onChange={e=>setReveal(e.target.checked)}/> Reveal verified FDA decisions (exclude from blind scoring)</label>
 </div>
 <NumericSortSettings scope="past" columns={[{id:"level4Score",label:"Overall Level 4 Score"},{id:"confidence",label:"Confidence %"},{id:"L4",label:"Level 4 detailed score"}]} onApply={setSortRules}/>
 <p><strong>{filtered.length}</strong> queued historical records for {year}. {year!=="2026"?"Historical cohort not imported for this year.":""}</p>
 <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
 <style>{`table.assessment-expandable:not(:has(details.assessment-toggle[open])) .assessment-level{display:none} .assessment-toggle{display:inline-block;margin-left:6px;vertical-align:middle}.assessment-toggle summary{display:inline-flex;align-items:center;justify-content:center;width:25px;height:25px;border:1px solid #7e9f8b;border-radius:5px;cursor:pointer;background:#fff;color:#173d2b;font-weight:800;list-style:none}.assessment-toggle summary::-webkit-details-marker{display:none}.assessment-toggle .when-open{display:none}.assessment-toggle[open] .when-open{display:inline}.assessment-toggle[open] .when-closed{display:none}`}</style>
 <table className="assessment-expandable" style={{borderCollapse:"collapse",minWidth:1650,width:"100%",fontSize:13}}>
 <thead style={{background:"#e6f2ea"}}><tr>{["Ticker","NCT / Trial","Company","FDA Special Designations","Market cap ($B)","FDA / PDUFA path","Sources","7 gate checks","PDUFA date (unverified queue date)","Assessment level","Score","Confidence","Blind prediction","FDA Decision Type","FDA Decision"].map(h=><th key={h} style={{textAlign:"left",padding:10,whiteSpace:"nowrap"}}>{h}</th>)}<th style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>Overall Score <details className="assessment-toggle"><summary aria-label="Expand or collapse 20 assessment columns" title="Expand or collapse all 20 assessment levels"><span className="when-closed">＋</span><span className="when-open">−</span></summary></details></th>{assessmentLevelLabels.map((label,i)=><th className="assessment-level" key={label} title={`Level ${i+1}: ${label}. Detailed score shown only when available.`} style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>L{i+1} · {label}</th>)}</tr></thead>
 <tbody>{filtered.map((r,i)=>{const name=r.eventKey.split("|")[2]||"Not recorded";const verified=known.find(k=>k.ticker===r.ticker&&k.actualFdaActionDate===r.cutoffDate);
 return <tr key={r.eventKey} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
 <td style={{padding:9,fontWeight:700}}>{r.ticker}</td><td style={{padding:9}}>Not linked</td><td style={{padding:9}}>Not recorded</td><td style={{padding:9}}>Not verified</td><td style={{padding:9}}>—</td>
 <td style={{padding:9}}>{name}</td><td style={{padding:9}}>Evidence pending</td><td style={{padding:9}}>Not assessed</td>
 <td style={{padding:9}}>{r.cutoffDate}</td><td style={{padding:9}}>Level 4 queued</td><td style={{padding:9}}>{r.level4Score??"Pending"}</td><td style={{padding:9}}>{r.confidence??"Pending"}</td><td style={{padding:9}}>{r.blindPrediction??"Pending"}</td>
 <td style={{padding:9}}>{!reveal?"Hidden":verified?verified.approvalType:"Not verified"}</td><td style={{padding:9}}>{!reveal?"Hidden":verified?verified.actualOutcome:"Not verified"}</td><td style={{padding:9,whiteSpace:"nowrap"}}>Not assessed</td>{assessmentLevelLabels.map((label,i)=><td className="assessment-level" key={label} title={`Level ${i+1}: ${label}`} style={{padding:9,whiteSpace:"nowrap"}}>{i===3&&r.level4Score!==null?r.level4Score:"Not assessed"}</td>)}
 </tr>})}</tbody></table></div>
 <p style={{fontSize:12,color:"#526458"}}>Queue dates are scheduling/cutoff metadata, not independently confirmed PDUFA dates. Decision data is deliberately separated from blind predictions. The full FOCUS schema is shown; unavailable historical fields remain explicitly unverified.</p>
 </main>;
}
