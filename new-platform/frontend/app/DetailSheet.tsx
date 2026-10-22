"use client";
import {useEffect,useState} from "react";
export type DetailItem={id?:string;programId?:string;ticker?:string;company?:string;drug?:string;indication?:string;nctId?:string;stage?:string;pdufaDate?:string;marketCap?:number|null;fdaSource?:string;lastChecked?:string};
type Kind="trial"|"company"|"disease"|"all";
const missing="Not verified / not available";
export default function DetailSheet({item,onClose,initial="all"}:{item:DetailItem|null;onClose:()=>void;initial?:Kind}){
 const [kind,setKind]=useState<Kind>(initial);
 useEffect(()=>{setKind(initial)},[item,initial]);
 useEffect(()=>{if(!item)return;const key=(e:KeyboardEvent)=>{if(e.key==="Escape")onClose()};document.addEventListener("keydown",key);return()=>document.removeEventListener("keydown",key)},[item,onClose]);
 if(!item)return null;
 const field=(label:string,value:unknown)=><p style={{margin:"6px 0"}}><strong>{label}:</strong> {value===null||value===undefined||value===""?missing:String(value)}</p>;
 const source=item.fdaSource&&/^https:\/\//i.test(item.fdaSource)?item.fdaSource:null;
 return <div role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}} style={{position:"fixed",inset:0,zIndex:9999,background:"rgba(0,0,0,.65)",display:"flex",justifyContent:"center",alignItems:"center",padding:12}}>
 <section role="dialog" aria-modal="true" aria-label="Program details" style={{width:"min(850px,100%)",maxHeight:"92dvh",overflowY:"auto",background:"var(--panel-bg, #fff)",color:"var(--text, #172334)",border:"2px solid #244c73",borderRadius:14,padding:18,boxShadow:"0 14px 50px #0005"}}>
 <div style={{display:"flex",justifyContent:"space-between",gap:12,alignItems:"center"}}><h2 style={{margin:0}}>DETAILS · {item.company||item.ticker||item.drug||item.indication||"Program"}</h2><button type="button" className="secondary" onClick={onClose}>✕ CLOSE</button></div>
 <p className="subtle">Select the details to display. Missing historical FDA ratings and product sales are not estimated.</p>
 <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:14}}>{(["trial","company","disease","all"] as Kind[]).map(k=><button type="button" key={k} className={kind===k?"":"secondary"} aria-pressed={kind===k} onClick={()=>setKind(k)}>{k==="all"?"ALL DETAILS":k.toUpperCase()}</button>)}</div>
 {(kind==="trial"||kind==="all")&&<section className="panel" style={{padding:12,marginBottom:10}}><h3>TRIAL / PROGRAM</h3>{field("Program ID",item.programId||item.id)}{field("Drug",item.drug)}{field("Trial NCT",item.nctId)}{field("Phase / stage",item.stage)}{field("PDUFA",item.pdufaDate)}{item.nctId&&/^NCT\d{8}$/.test(item.nctId)&&<a href={"https://clinicaltrials.gov/study/"+item.nctId} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov record ↗</a>}</section>}
 {(kind==="company"||kind==="all")&&<section className="panel" style={{padding:12,marginBottom:10}}><h3>COMPANY</h3>{field("Company",item.company)}{field("Ticker",item.ticker)}{field("Market capitalization",typeof item.marketCap==="number"?"$"+item.marketCap.toLocaleString("en-US"):null)}{field("Previous PDUFA winners / ratings",null)}{field("Previous CRLs / setbacks",null)}{field("Other current pipeline programs",null)}{field("Approved-drug sales by product",null)}{field("Total approved-drug sales",null)}<p className="subtle">Historical outcomes, scores and sales require independently sourced company-level records; unavailable values are explicitly marked.</p></section>}
 {(kind==="disease"||kind==="all")&&<section className="panel" style={{padding:12,marginBottom:10}}><h3>DISEASE / INDICATION</h3>{field("Disease / indication",item.indication)}{field("Drug under review",item.drug)}{field("Sponsor / company",item.company||item.ticker)}{field("Competing programs and approved treatments",null)}</section>}
 <p className="subtle">Last source check: {item.lastChecked||missing}. {source&&<a href={source} target="_blank" rel="noopener noreferrer">FDA evidence ↗</a>}</p>
 <button type="button" className="secondary" onClick={onClose}>CLOSE DETAILS</button>
 </section></div>;
}
