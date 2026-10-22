"use client";
import {useEffect,useMemo,useState} from "react";
import {buildDiseaseIndex,diseasePath,emptyDiseaseEdits,restoreDiseaseEdits,DISEASE_STORAGE_KEY,LEGACY_DISEASE_STORAGE_KEY,type DiseaseEdits} from "../lib/disease-catalog";
export type ProgramLink={id:string;ticker:string;company?:string;drug?:string;indication?:string;nctId?:string;pdufaDate?:string;fdaSource?:string;stage?:string};
const norm=(s:string)=>s.trim().toLowerCase().replace(/[^a-z0-9]+/g," ");
export default function CompanyDiseaseLinks({rows}:{rows:ProgramLink[]}){
 const [edits,setEdits]=useState<DiseaseEdits>(emptyDiseaseEdits);
 useEffect(()=>{try{const saved=localStorage.getItem(DISEASE_STORAGE_KEY)||localStorage.getItem(LEGACY_DISEASE_STORAGE_KEY);if(saved)setEdits(restoreDiseaseEdits(JSON.parse(saved)));}catch{}},[]);
 const diseaseIndex=useMemo(()=>buildDiseaseIndex(edits),[edits]);
 const diseaseNames=useMemo(()=>{const m=new Map<string,typeof diseaseIndex.unique[number][]>();for(const node of diseaseIndex.unique){for(const name of [node.name,node.sourceName,...(node.aliases||[])]){const key=norm(name||"");if(!key)continue;const list=m.get(key)||[];if(!list.some(n=>(n.sourceId||n.id)===(node.sourceId||node.id)))list.push(node);m.set(key,list)}}return m},[diseaseIndex]);
 const diseaseMatch=(indication?:string)=>{const matches=diseaseNames.get(norm(indication||""))||[];return matches.length===1?matches[0]:null};
 const [query,setQuery]=useState("");const [filter,setFilter]=useState<"all"|"company"|"disease"|"drug">("all");const [selected,setSelected]=useState("");const [limit,setLimit]=useState(50);
 const linked=useMemo(()=>{const m=new Map<string,ProgramLink>();for(const r of rows){const key=[r.id,r.ticker,r.drug,r.indication,r.nctId].join("|");if(!m.has(key))m.set(key,r)}return [...m.values()]},[rows]);
 const filtered=useMemo(()=>linked.filter(r=>{const terms=filter==="company"?[r.company,r.ticker]:filter==="disease"?[r.indication]:filter==="drug"?[r.drug]:[r.company,r.ticker,r.indication,r.drug,r.nctId];return terms.some(v=>norm(v||"").includes(norm(query)))&&(!selected||[r.company,r.ticker,r.indication,r.drug].some(v=>norm(v||"")===norm(selected)))}),[linked,query,filter,selected]);
 const matchedCount=filtered.filter(r=>!!diseaseMatch(r.indication)).length;
 const companies=new Set(filtered.map(r=>norm(r.company||r.ticker)).filter(Boolean));const diseases=new Set(filtered.map(r=>norm(r.indication||"")).filter(Boolean));const drugs=new Set(filtered.map(r=>norm(r.drug||"")).filter(Boolean));
 return <section className="panel" style={{padding:14}} aria-label="Company disease drug FDA relationships">
 <h3>COMPANY ↔ DISEASE ↔ DRUG ↔ TRIAL ↔ PDUFA</h3>
 <p className="subtle">Cross-reference relationships found in the currently published scanner records. Indications are matched conservatively against the bundled DISEASE hierarchy using exact names or aliases. Ambiguous and unmatched indications remain unclassified. No external connections or changes to saved restrictions.</p>
 <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
 <input aria-label="Search company disease drug or trial" type="search" placeholder="Company, ticker, disease, drug or NCT ID" value={query} onChange={e=>{setQuery(e.target.value);setLimit(50)}} style={{minWidth:220,flex:"1 1 260px"}}/>
 <select aria-label="Search field" value={filter} onChange={e=>setFilter(e.target.value as typeof filter)}><option value="all">All fields</option><option value="company">Company / ticker</option><option value="disease">Disease / indication</option><option value="drug">Drug</option></select>
 {selected&&<button type="button" onClick={()=>setSelected("")}>CLEAR SELECTED: {selected}</button>}
 </div>
 <p role="status">{filtered.length.toLocaleString()} program records · {companies.size.toLocaleString()} companies · {diseases.size.toLocaleString()} indications · {drugs.size.toLocaleString()} drugs · {matchedCount.toLocaleString()} exact disease matches</p>
 <div style={{overflowX:"auto"}}><table style={{width:"100%",textAlign:"left",fontSize:13}}><thead><tr><th>Company / ticker</th><th>Disease / indication</th><th>Classification / match</th><th>Drug</th><th>Trial</th><th>PDUFA</th></tr></thead><tbody>
 {filtered.slice(0,limit).map((r,i)=><tr key={r.id+"-"+i}><td><button type="button" onClick={()=>{setSelected(r.company||r.ticker);setQuery("")}}>{r.company||r.ticker||"Unknown"} {r.ticker&&"("+r.ticker+")"}</button></td><td><button type="button" onClick={()=>{setSelected(r.indication||"");setQuery("")}}>{r.indication||"Unspecified"}</button></td><td>{diseaseMatch(r.indication)?<span title="Exact name or alias match; not a manually verified clinical classification">{diseasePath(diseaseMatch(r.indication)!.id,diseaseIndex).map(n=>n.name).join(" → ")} · Exact text match</span>:"Unmatched / review"}</td><td><button type="button" onClick={()=>{setSelected(r.drug||"");setQuery("")}}>{r.drug||"Unspecified"}</button></td><td>{r.nctId||"—"}</td><td>{r.pdufaDate||"—"}</td></tr>)}
 </tbody></table></div>
 {filtered.length>limit&&<button type="button" onClick={()=>setLimit(v=>v+50)}>SHOW 50 MORE</button>}
 <p className="subtle">A blank field means no verified link is present in this published record. PDUFA dates are shown only for the specific program record, not inherited by other drugs or indications. Company, drug and indication labels are not evidence of corporate ownership or FDA approval.</p>
 </section>
}