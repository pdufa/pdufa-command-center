"use client";
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import ScientificStepsReadiness from "../ScientificStepsReadiness";
import PastSavedAssessments from "../PastSavedAssessments";
import AssessmentLauncher from "../AssessmentLauncher";
import {ExactTrialIntakeSelector} from "../ExactTrialScientificIntake";
import {useMemo,useState} from "react";
import Link from "next/link";
import NumericSortSettings,{sortNumericRows,type NumericSortRule} from "../NumericSortSettings";
import historical from "../../data/level4BlindAssessmentQueue20261112.json";
import regulatoryResearch from "../../data/past2026RegulatoryResearch20261115.json";

type HistoricalRow={eventKey:string;ticker:string;cutoffDate:string;level4Score:number|null;blindPrediction:string|null;confidence:number|null;status:string};
const rows=historical.historical2026 as HistoricalRow[];
const regulatoryByEvent=new Map(regulatoryResearch.records.map(item=>[item.eventKey,item]));
const assessmentLevelLabels=["Trial identity","Current phase","Source evidence","Study protocol","Population","Efficacy","Statistics","Safety","Clinical benefit","Comparator","Subgroups","Data gaps","Regulatory history","FDA alignment","Manufacturing","Benefit–risk","Exceptions","External evidence","Confidence","Integrated review"];
export default function PastPage(){
 const [year,setYear]=useState("2026");
 const [search,setSearch]=useState("");
 const [reveal,setReveal]=useState(false);
 const [sortRules,setSortRules]=useState<NumericSortRule[]>([]);
 const [candidateNctByEvent,setCandidateNctByEvent]=useState<Record<string,string>>({});
 const filtered=useMemo(()=>{
  const subset=year==="2026"?rows.filter(r=>(r.ticker+" "+r.eventKey).toLowerCase().includes(search.toLowerCase())):[];
  return sortNumericRows(subset,sortRules,(r,c)=>{
   const verified=reveal?regulatoryByEvent.get(r.eventKey):undefined;
   if(c==="ticker")return r.ticker;
   if(c==="trial")return "Not linked";
   if(c==="company")return "Not recorded";
   if(c==="designations")return "Not verified";
   if(c==="marketCap")return null;
   if(c==="application")return regulatoryByEvent.get(r.eventKey)?.product??r.eventKey.split("|")[2]??"Not recorded";
   if(c==="sources")return regulatoryByEvent.has(r.eventKey)?"FDA action source available · NCT not linked":"Evidence pending";
   if(c==="gates")return "Not assessed";
   if(c==="cutoffDate")return r.cutoffDate;
   if(c==="actualActionDate")return verified?.actualFdaActionDate??null;
   if(c==="assessmentLevel")return "Level 4 queued";
   if(c==="level4Score")return r.level4Score;
   if(c==="confidence")return r.confidence;
   if(c==="prediction")return r.blindPrediction;
   if(c==="decisionType")return verified?.applicationDescription??null;
   if(c==="decision")return verified?.fdaAction??null;
   if(c==="overall")return "Not assessed";
   if(c==="level4")return r.level4Score;
   if(/^level(?:[1-9]|1[0-9]|20)$/.test(c))return null;
   return null;
  },r=>r.eventKey);
 },[year,search,sortRules,reveal]);
 return <main style={{maxWidth:1400,margin:"24px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif"}}>
 <nav style={{display:"flex",gap:14,marginBottom:16}}><Link href="/focus">FOCUS</Link><strong>PAST</strong><Link href="/pool">POOL</Link></nav>
 <AssessmentLauncher source="HISTORICAL" historicalYear={year}/><ScientificStepsReadiness cohort="PAST"/><PastSavedAssessments/>
 <h1>PAST — Historical PDUFA trials</h1>
 <p>Year-by-year historical cohort. The 2026 research queue now includes source-linked PDUFA goals and separately revealed FDA outcomes; it is not a verified complete FDA decision census or an exact NCT roster. Missing scientific evidence is never scored as zero.</p>
 <div style={{display:"flex",gap:12,alignItems:"center",flexWrap:"wrap",marginBottom:16}}>
 <label>Year <select aria-label="PDUFA year" value={year} onChange={e=>setYear(e.target.value)}>{Array.from({length:10},(_,i)=>2026-i).map(y=><option key={y}>{y}</option>)}</select></label>
 <label>Search <input aria-label="Search historical trials" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Ticker or application"/></label>
 <label><input type="checkbox" checked={reveal} onChange={e=>setReveal(e.target.checked)}/> Reveal separately sourced FDA actions (post-outcome research; excluded from blind scoring)</label>
 </div>
 <NumericSortSettings scope="past" columns={[{id:"ticker",label:"Ticker"},{id:"trial",label:"NCT / Trial"},{id:"company",label:"Company"},{id:"designations",label:"FDA Special Designations"},{id:"marketCap",label:"Market cap ($B)"},{id:"application",label:"FDA / PDUFA path"},{id:"sources",label:"Sources"},{id:"gates",label:"7 gate checks"},{id:"cutoffDate",label:"PDUFA goal date"},{id:"actualActionDate",label:"Actual FDA action date"},{id:"assessmentLevel",label:"Assessment level"},{id:"level4Score",label:"Score"},{id:"confidence",label:"Confidence"},{id:"prediction",label:"Blind prediction"},{id:"decisionType",label:"FDA Decision Type"},{id:"decision",label:"FDA Decision"},{id:"overall",label:"Overall Score"},{id:"level1",label:"L01-Trial identity"},{id:"level2",label:"L02-Current phase"},{id:"level3",label:"L03-Source evidence"},{id:"level4",label:"L04-Study protocol"},{id:"level5",label:"L05-Population"},{id:"level6",label:"L06-Efficacy"},{id:"level7",label:"L07-Statistics"},{id:"level8",label:"L08-Safety"},{id:"level9",label:"L09-Clinical benefit"},{id:"level10",label:"L10-Comparator"},{id:"level11",label:"L11-Subgroups"},{id:"level12",label:"L12-Data gaps"},{id:"level13",label:"L13-Regulatory history"},{id:"level14",label:"L14-FDA alignment"},{id:"level15",label:"L15-Manufacturing"},{id:"level16",label:"L16-Benefit–risk"},{id:"level17",label:"L17-Exceptions"},{id:"level18",label:"L18-External evidence"},{id:"level19",label:"L19-Confidence"},{id:"level20",label:"L20-Integrated review"}]} onApply={setSortRules}/>
 <p><strong>{filtered.length}</strong> queued historical records for {year}. {year!=="2026"?"Historical cohort not imported for this year.":""}</p>
 <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
 <style>{`table.assessment-expandable:not(:has(details.assessment-toggle[open])) .assessment-level{display:none} .assessment-toggle{display:inline-block;margin-left:6px;vertical-align:middle}.assessment-toggle summary{display:inline-flex;align-items:center;justify-content:center;width:25px;height:25px;border:1px solid #7e9f8b;border-radius:5px;cursor:pointer;background:#fff;color:#173d2b;font-weight:800;list-style:none}.assessment-toggle summary::-webkit-details-marker{display:none}.assessment-toggle .when-open{display:none}.assessment-toggle[open] .when-open{display:inline}.assessment-toggle[open] .when-closed{display:none}`}</style>
 <table className="assessment-expandable" style={{borderCollapse:"collapse",minWidth:1650,width:"100%",fontSize:13}}>
 <thead style={{background:"#e6f2ea"}}><tr>{["Ticker","NCT / Trial","Company","FDA Special Designations","Market cap ($B)","FDA / PDUFA path","Sources","7 gate checks","PDUFA target date (source-linked; not NCT-verified)","Actual FDA action date (reveal)","Assessment level","Score","Confidence","Blind prediction","FDA Decision Type","FDA Decision"].map(h=><th key={h} style={{textAlign:"left",padding:10,whiteSpace:"nowrap"}}>{h}</th>)}<PredictionHeaders/><th style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>Overall Score <details className="assessment-toggle"><summary aria-label="Expand or collapse 20 assessment columns" title="Expand or collapse all 20 assessment levels"><span className="when-closed">＋</span><span className="when-open">−</span></summary></details></th>{assessmentLevelLabels.map((label,i)=><th className="assessment-level" key={label} title={`Level ${i+1}: ${label}. Detailed score shown only when available.`} style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>L{String(i+1).padStart(2,"0")}-{label}</th>)}</tr></thead>
 <tbody>{filtered.map((r,i)=>{const name=r.eventKey.split("|")[2]||"Not recorded";const regulatory=regulatoryByEvent.get(r.eventKey);
 return <tr key={r.eventKey} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
 <td style={{padding:9,fontWeight:700}}>{r.ticker}</td><td style={{padding:9}}><details><summary>Not linked - enter candidate NCT</summary><label>Exact NCT <input aria-label={"Candidate NCT for "+r.eventKey} value={candidateNctByEvent[r.eventKey]??""} onChange={e=>setCandidateNctByEvent(prev=>({...prev,[r.eventKey]:e.target.value.toUpperCase()}))} placeholder="NCT12345678" maxLength={11}/></label>{/^NCT\d{8}$/.test(candidateNctByEvent[r.eventKey]??"")?<ExactTrialIntakeSelector cohort="PAST" nctId={candidateNctByEvent[r.eventKey]}/>:<p>Historical event-to-NCT linkage remains unverified; no intake displayed.</p>}</details></td><td style={{padding:9}}>Not recorded</td><td style={{padding:9}}>Not verified</td><td style={{padding:9}}>—</td>
 <td style={{padding:9}}>{regulatory?.product??name}</td><td style={{padding:9}}>{regulatory?<><a href={regulatory.targetEvidenceUrl} target="_blank" rel="noopener noreferrer">PDUFA target source</a>{reveal&&<> · <a href={regulatory.actionEvidenceUrl} target="_blank" rel="noopener noreferrer">FDA action source</a></>}<small style={{display:"block"}}>Regulatory evidence only; FDA event–NCT link not verified</small></>:"Evidence pending"}</td><td style={{padding:9}}>Not assessed</td>
 <td style={{padding:9}}>{r.cutoffDate}</td><td style={{padding:9}}>{!reveal?"Hidden":regulatory?.actualFdaActionDate??(regulatory?.actionReportedDate?"Announced "+regulatory.actionReportedDate:"FDA action date unverified")}</td><td style={{padding:9}}>Not assessed · NCT link pending</td><td style={{padding:9}}>{r.level4Score??"Pending"}</td><td style={{padding:9}}>{r.confidence??"Pending"}</td><td style={{padding:9}}>{r.blindPrediction??"Pending"}</td>
 <td style={{padding:9}}>{!reveal?"Hidden":regulatory?.applicationDescription??"Not verified"}</td><td style={{padding:9}}>{!reveal?"Hidden":regulatory?.fdaAction??"Not verified"}</td><PredictionCells/><td style={{padding:9,whiteSpace:"nowrap"}}>Not assessed</td>{assessmentLevelLabels.map((label,i)=><td className="assessment-level" key={label} title={`Level ${i+1}: ${label}`} style={{padding:9,whiteSpace:"nowrap"}}>{i===3&&r.level4Score!==null?r.level4Score:"Not assessed"}</td>)}
 </tr>})}</tbody></table></div>
 <PredictionLegend/><p style={{fontSize:12,color:"#526458"}}>PAST 2026 target-date leads now have separate regulator/sponsor source links and post-action research. Exact FDA event-to-NCT/application/review-cycle links remain unverified; regulatory sources never enter scientific historical scoring. Actual FDA action dates and outcomes are withheld until you explicitly reveal them. Some reported approval announcements are not proof of the exact FDA letter date. The full FOCUS schema is shown; unavailable historical fields remain explicitly unverified.</p>
 </main>;
}
