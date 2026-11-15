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
 const [surveyExpanded,setSurveyExpanded]=useState(false);
 const [verifiedNctByEvent,setVerifiedNctByEvent]=useState<Record<string,string>>({});
 const filtered=useMemo(()=>{
  const subset=year==="2026"?rows.filter(r=>(r.ticker+" "+r.eventKey).toLowerCase().includes(search.toLowerCase())):[];
  return sortNumericRows(subset,sortRules,(r,c)=>{
   const verified=reveal?known.find(k=>k.ticker===r.ticker&&k.actualFdaActionDate===r.cutoffDate):undefined;
   if(c==="ticker")return r.ticker;
   if(c==="trial")return "Not linked";
   if(c==="company")return "Not recorded";
   if(c==="designations")return "Not verified";
   if(c==="marketCap")return null;
   if(c==="application")return r.eventKey.split("|")[2]||"Not recorded";
   if(c==="sources")return "Evidence pending";
   if(c==="gates")return "Not assessed";
   if(c==="cutoffDate")return r.cutoffDate;
   if(c==="assessmentLevel")return "Level 4 queued";
   if(c==="level4Score")return r.level4Score;
   if(c==="confidence")return r.confidence;
   if(c==="prediction")return r.blindPrediction;
   if(c==="decisionType")return verified?.approvalType??null;
   if(c==="decision")return verified?.actualOutcome??null;
   if(c==="overall")return "Not assessed";
   if(c==="level4")return r.level4Score;
   if(/^level(?:[1-9]|1[0-9]|20)$/.test(c))return null;
   return null;
  },r=>r.eventKey);
 },[year,search,sortRules,reveal]);
 return <main style={{maxWidth:1400,margin:"24px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif"}}>
 <nav style={{display:"flex",gap:14,marginBottom:16}}><Link href="/focus">FOCUS</Link><strong>PAST</strong><Link href="/pool">POOL</Link></nav>
 <AssessmentLauncher source="HISTORICAL"/><ScientificStepsReadiness cohort="PAST"/><PastSavedAssessments/>
 <h1>PAST — Historical PDUFA trials</h1>
  <div aria-label="Top table sorting controls" style={{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap",margin:"12px 0 18px"}}>
 <NumericSortSettings scope="past" columns={[{id:"ticker",label:"Ticker"},{id:"trial",label:"NCT / Trial"},{id:"company",label:"Company"},{id:"designations",label:"FDA Special Designations"},{id:"marketCap",label:"Market cap ($B)"},{id:"application",label:"FDA / PDUFA path"},{id:"sources",label:"Sources"},{id:"gates",label:"7 gate checks"},{id:"cutoffDate",label:"PDUFA queue date"},{id:"assessmentLevel",label:"Assessment level"},{id:"level4Score",label:"Score"},{id:"confidence",label:"Confidence"},{id:"prediction",label:"Blind prediction"},{id:"decisionType",label:"FDA Decision Type"},{id:"decision",label:"FDA Decision"},{id:"overall",label:"Overall Score"},{id:"level1",label:"L01-Trial identity"},{id:"level2",label:"L02-Current phase"},{id:"level3",label:"L03-Source evidence"},{id:"level4",label:"L04-Study protocol"},{id:"level5",label:"L05-Population"},{id:"level6",label:"L06-Efficacy"},{id:"level7",label:"L07-Statistics"},{id:"level8",label:"L08-Safety"},{id:"level9",label:"L09-Clinical benefit"},{id:"level10",label:"L10-Comparator"},{id:"level11",label:"L11-Subgroups"},{id:"level12",label:"L12-Data gaps"},{id:"level13",label:"L13-Regulatory history"},{id:"level14",label:"L14-FDA alignment"},{id:"level15",label:"L15-Manufacturing"},{id:"level16",label:"L16-Benefit–risk"},{id:"level17",label:"L17-Exceptions"},{id:"level18",label:"L18-External evidence"},{id:"level19",label:"L19-Confidence"},{id:"level20",label:"L20-Integrated review"}]} onApply={setSortRules}/>
  <button type="button" aria-label="Survey Columns" aria-expanded={surveyExpanded} onClick={()=>setSurveyExpanded(v=>!v)} style={{padding:"9px 14px",borderRadius:8,border:"1px solid #789987",background:"#e6f2ea",color:"#173d2b",fontWeight:700,cursor:"pointer"}}>{surveyExpanded?"▾ Hide Survey Columns":"▸ Survey Columns"}</button>
  </div>
 <p>Year-by-year historical cohort. The 2026 queue is an evidence-freeze research queue, not a verified complete FDA decision census. No missing values are treated as zero or as a negative decision.</p>
 <div style={{display:"flex",gap:12,alignItems:"center",flexWrap:"wrap",marginBottom:16}}>
 <label>Year <select aria-label="PDUFA year" value={year} onChange={e=>setYear(e.target.value)}>{Array.from({length:10},(_,i)=>2026-i).map(y=><option key={y}>{y}</option>)}</select></label>
 <label>Search <input aria-label="Search historical trials" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Ticker or application"/></label>
 <label><input type="checkbox" checked={reveal} onChange={e=>setReveal(e.target.checked)}/> Show historical comparison data (unverified event match; exclude from blind scoring)</label>
 </div>
 <p><strong>{filtered.length}</strong> queued historical records for {year}. {year!=="2026"?"Historical cohort not imported for this year.":""}</p>
 <div style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>
 <style>{`table.assessment-expandable:not(.survey-expanded):not(:has(details.assessment-toggle[open])) .assessment-level{display:none} .assessment-toggle{display:inline-block;margin-left:6px;vertical-align:middle}.assessment-toggle summary{display:inline-flex;align-items:center;justify-content:center;width:25px;height:25px;border:1px solid #7e9f8b;border-radius:5px;cursor:pointer;background:#fff;color:#173d2b;font-weight:800;list-style:none}.assessment-toggle summary::-webkit-details-marker{display:none}.assessment-toggle .when-open{display:none}.assessment-toggle[open] .when-open{display:inline}.assessment-toggle[open] .when-closed{display:none}`}</style>
 <table className={surveyExpanded?"assessment-expandable survey-expanded":"assessment-expandable"} style={{borderCollapse:"collapse",minWidth:1650,width:"100%",fontSize:13}}>
 <thead style={{background:"#e6f2ea"}}><tr>{["Ticker","NCT / Trial","Company","FDA Special Designations","Market cap ($B)","FDA / PDUFA path","Sources","7 gate checks","PDUFA date (unverified queue date)","Assessment level","Score","Confidence","Blind prediction","FDA Decision Type","FDA Decision"].map(h=><th key={h} style={{textAlign:"left",padding:10,whiteSpace:"nowrap"}}>{h}</th>)}<PredictionHeaders/><th style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>Overall Score <details className="assessment-toggle"><summary aria-label="Expand or collapse 20 assessment columns" title="Expand or collapse all 20 assessment levels"><span className="when-closed">＋</span><span className="when-open">−</span></summary></details></th>{assessmentLevelLabels.map((label,i)=><th className="assessment-level" key={label} title={`Level ${i+1}: ${label}. Detailed score shown only when available.`} style={{padding:10,whiteSpace:"nowrap",textAlign:"left"}}>L{String(i+1).padStart(2,"0")}-{label}</th>)}</tr></thead>
 <tbody>{filtered.map((r,i)=>{const name=r.eventKey.split("|")[2]||"Not recorded";const candidates=known.filter(k=>k.ticker===r.ticker&&k.actualFdaActionDate===r.cutoffDate);const tentative=candidates.length===1?candidates[0]:null;const comparisonLabel=candidates.length>1?"Ambiguous historical matches":candidates.length===1?"Unverified match: ":"Not verified";
 return <tr key={r.eventKey} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
 <td style={{padding:9,fontWeight:700}}>{r.ticker}</td><td style={{padding:9}}><details><summary>Not linked - enter candidate NCT</summary><label>Exact NCT <input aria-label={"Candidate NCT for "+r.eventKey} value={verifiedNctByEvent[r.eventKey]??""} onChange={e=>setVerifiedNctByEvent(prev=>({...prev,[r.eventKey]:e.target.value.toUpperCase()}))} placeholder="NCT12345678" maxLength={11}/></label>{/^NCT\d{8}$/.test(verifiedNctByEvent[r.eventKey]??"")?<ExactTrialIntakeSelector cohort="PAST" nctId={verifiedNctByEvent[r.eventKey]}/>:<p>Historical event-to-NCT linkage remains unverified; no intake displayed.</p>}</details></td><td style={{padding:9}}>Not recorded</td><td style={{padding:9}}>Not verified</td><td style={{padding:9}}>—</td>
 <td style={{padding:9}}>{name}</td><td style={{padding:9}}>Evidence pending</td><td style={{padding:9}}>Not assessed</td>
 <td style={{padding:9}}>{r.cutoffDate}</td><td style={{padding:9}}>Level 4 queued</td><td style={{padding:9}}>{r.level4Score??"Pending"}</td><td style={{padding:9}}>{r.confidence??"Pending"}</td><td style={{padding:9}}>{r.blindPrediction??"Pending"}</td>
 <td style={{padding:9}}>{!reveal?"Hidden":tentative?comparisonLabel+tentative.approvalType:comparisonLabel}</td><td style={{padding:9}}>{!reveal?"Hidden":tentative?comparisonLabel+tentative.actualOutcome:comparisonLabel}</td><PredictionCells nct={verifiedNctByEvent[r.eventKey]}/><td style={{padding:9,whiteSpace:"nowrap"}}>Not assessed</td>{assessmentLevelLabels.map((label,i)=><td className="assessment-level" key={label} title={`Level ${i+1}: ${label}`} style={{padding:9,whiteSpace:"nowrap"}}>{i===3&&r.level4Score!==null?r.level4Score:"Not assessed"}</td>)}
 </tr>})}</tbody></table></div>
 <PredictionLegend/><p style={{fontSize:12,color:"#526458"}}>Queue dates are scheduling/cutoff metadata, not independently confirmed PDUFA dates. Historical comparisons are matched only by ticker and date, not by source-verified FDA event identity; do not treat these as confirmed FDA decisions. Decision data is deliberately separated from blind predictions. The full FOCUS schema is shown; unavailable historical fields remain explicitly unverified.</p>
 </main>;
}
