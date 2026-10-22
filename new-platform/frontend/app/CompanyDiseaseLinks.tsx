"use client";
import {useMemo,useState} from "react";
export type ProgramLink={id:string;ticker:string;company?:string;drug?:string;indication?:string;nctId?:string;pdufaDate?:string;fdaSource?:string;stage?:string};
const norm=(s:string)=>s.trim().toLowerCase().replace(/[^a-z0-9]+/g," ");
export default function CompanyDiseaseLinks({rows}:{rows:ProgramLink[]}){
 const [query,setQuery]=useState("");const [filter,setFilter]=useState<"all"|"company"|"disease"|"drug">("all");const [selected,setSelected]=useState("");const [limit,setLimit]=useState(50);
 const linked=useMemo(()=>{const m=new Map<string,ProgramLink>();for(const r of rows){const key=[r.id,r.ticker,r.drug,r.indication,r.nctId].join("|");if(!m.has(key))m.set(key,r)}return [...m.values()]},[rows]);
 const filtered=useMemo(()=>linked.filter(r=>{const terms=filter==="company"?[r.company,r.ticker]:filter==="disease"?[r.indication]:filter==="drug"?[r.drug]:[r.company,r.ticker,r.indication,r.drug,r.nctId];return terms.some(v=>norm(v||"").includes(norm(query)))&&(!selected||[r.company,r.ticker,r.indication,r.drug].some(v=>norm(v||"")===norm(selected)))}),[linked,query,filter,selected]);
 const companies=new Set(filtered.map(r=>norm(r.company||r.ticker)).filter(Boolean));const diseases=new Set(filtered.map(r=>norm(r.indication||"")).filter(Boolean));const drugs=new Set(filtered.map(r=>norm(r.drug||"")).filter(Boolean));
 return <section className="panel" style={{padding:14}} aria-label="Company disease drug FDA relationships">
 <h3>COMPANY ↔ DISEASE ↔ DRUG ↔ TRIAL ↔ PDUFA</h3>
 <p className="subtle">Cross-reference relationships found in the currently published scanner records. Indications are source text, not yet verified mappings to the DISEASE hierarchy. No external connections or changes to saved restrictions.</p>
 <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
 <input aria-label="Search company disease drug or trial" type="search" placeholder="Company, ticker, disease, drug or NCT ID" value={query} onChange={e=>{setQuery(e.target.value);setLimit(50)}} style={{minWidth:220,flex:"1 1 260px"}}/>
 <select aria-label="Search field" value={filter} onChange={e=>setFilter(e.target.value as typeof filter)}><option value="all">All fields</option><option value="company">Company / ticker</option><option value="disease">Disease / indication</option><option value="drug">Drug</option></select>
 {selected&&<button type="button" onClick={()=>setSelected("")}>CLEAR SELECTED: {selected}</button>}
 </div>
 <p role="status">{filtered.length.toLocaleString()} program records · {companies.size.toLocaleString()} companies · {diseases.size.toLocaleString()} indications · {drugs.size.toLocaleString()} drugs</p>
 <div style={{overflowX:"auto"}}><table style={{width:"100%",textAlign:"left",fontSize:13}}><thead><tr><th>Company / ticker</th><th>Disease / indication</th><th>Drug</th><th>Trial</th><th>PDUFA</th></tr></thead><tbody>
 {filtered.slice(0,limit).map((r,i)=><tr key={r.id+"-"+i}><td><button type="button" onClick={()=>{setSelected(r.company||r.ticker);setQuery("")}}>{r.company||r.ticker||"Unknown"} {r.ticker&&"("+r.ticker+")"}</button></td><td><button type="button" onClick={()=>{setSelected(r.indication||"");setQuery("")}}>{r.indication||"Unspecified"}</button></td><td><button type="button" onClick={()=>{setSelected(r.drug||"");setQuery("")}}>{r.drug||"Unspecified"}</button></td><td>{r.nctId||"—"}</td><td>{r.pdufaDate||"—"}</td></tr>)}
 </tbody></table></div>
 {filtered.length>limit&&<button type="button" onClick={()=>setLimit(v=>v+50)}>SHOW 50 MORE</button>}
 <p className="subtle">A blank field means no verified link is present in this published record. PDUFA dates are shown only for the specific program record, not inherited by other drugs or indications. Company, drug and indication labels are not evidence of corporate ownership or FDA approval.</p>
 </section>
}