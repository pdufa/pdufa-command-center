"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import {createPortal} from "react-dom";
import {parsePhase3CensusCsv} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutClassification,type ReadoutRow} from "../lib/phase3-public-readout";
import css from "./Phase3ReadoutSheets.module.css";
import TrialColumnFilterBar,{applyColumnFilters,type ColumnFilterState,type ColumnFilterField} from "./TrialColumnFilterBar";
import {BENEFIT_GROUPS,benefitForTrial,parseBenefitFeed,type BenefitFeed,type BenefitFact} from "../lib/benefit-assessments";
import {RANKED_BENEFIT_ASSESSMENTS} from "../lib/pipeline-benefit-assessments";
import {ALL_RESEARCH_FIELD_DEFINITIONS} from "../lib/pipeline-research-view";

type Bucket="pre"|"post"|"unverified";
/** Reversible visibility-only feature; existing trial data and research sources are unchanged. */
const SURVEY_RATINGS_PREVIEW_ENABLED=true;
const SURVEY_VISIBILITY_KEY="phase3-readout-survey-column-visible-v1";
const SURVEY_SECTIONS=[
 {key:"A",name:"Medical Impact",min:1,max:5},
 {key:"B",name:"Competitive Strength",min:6,max:8},
 {key:"C",name:"Market Opportunity",min:9,max:14},
 {key:"D",name:"Revenue Value",min:15,max:18},
 {key:"E",name:"Investment Potential",min:19,max:20}
] as const;
const SURVEY_QUESTION_IDS=BENEFIT_GROUPS.flatMap(s=>s.fields.map(f=>f.id));
const SURVEY_QUESTION_NUMBERS=new Map(SURVEY_QUESTION_IDS.map((id,i)=>[id,i+1]));
const SURVEY_FIELD_DETAILS=new Map<string,{purpose:string;evidence:string}>(
 ALL_RESEARCH_FIELD_DEFINITIONS.map(f=>[f.id,{purpose:f.purpose,evidence:f.evidence}]));
const LIMIT=50;
const number=(v:number)=>v.toLocaleString("en-US");
const txt=(v:string)=>v||"Not established";
type ReadoutKey="nctId"|"ticker"|"company"|"factorP"|"drug"|"indication"|"status"|"date"|"source";
const readoutColumns:ColumnFilterField[]=[
 {key:"ticker",label:"Ticker"},{key:"nctId",label:"NCT / trial"},
 {key:"company",label:"Company"},{key:"drug",label:"Drug / therapy"},
 {key:"indication",label:"Indication"},{key:"status",label:"Registry status"},
 {key:"date",label:"Issuer release/check date"},{key:"source",label:"Evidence source"}
];
const postReadoutColumns:ColumnFilterField[]=[
 ...readoutColumns.slice(0,3),
 {key:"factorP",label:"Factor P · primary endpoint p-value"},
 ...readoutColumns.slice(3)
];
const unknownColumns:ColumnFilterField[]=[
 {key:"nctId",label:"NCT / trial"},{key:"ticker",label:"Ticker"},
 {key:"company",label:"Company"},{key:"status",label:"Registry status"}
];
const readoutValue=(row:ReadoutRow,key:string):string=>{
 if(key==="factorP")return row.evidence?.primaryEndpointP?.display||"";
 if(key==="date")return row.evidence?.evidenceDate||"";
 if(key==="drug")return row.evidence?.drug||"";
 if(key==="indication")return row.evidence?.indication||"";
 if(key==="source")return row.evidence?.evidenceUrl||row.sourceUrl;
 return String(row[key as keyof Pick<ReadoutRow,"nctId"|"ticker"|"company"|"status">]||"");
};
function sortReadout(rows:ReadoutRow[],key:ReadoutKey,desc:boolean):ReadoutRow[]{
 return [...rows].sort((a,b)=>{
  const cmp=readoutValue(a,key).localeCompare(readoutValue(b,key),"en-US",{numeric:true,sensitivity:"base"});
  return (desc?-cmp:cmp)||a.nctId.localeCompare(b.nctId);
 });
}

function csvCell(v:string|number){
  const value=String(v??"");
  const safe=/^[=+@-]/.test(value)?"'"+value:value;
  return '"'+safe.replace(/"/g,'""')+'"';
}
function downloadCsv(bucket:Bucket,rows:ReadoutRow[]){
  const fields=["NCT","Ticker","Company",...(bucket==="post"?["Factor P (Phase 3 primary endpoint p-value)"]:[]),"ClinicalTrials.gov status","Release classification","Evidence date","Drug","Indication","Release evidence","Registry link"];
  const table=[fields,...rows.map(row=>[
    row.nctId,row.ticker,row.company,...(bucket==="post"?[row.evidence?.primaryEndpointP?.display||"Not reported"]:[]),row.status,
    bucket==="pre"?"No public issuer release verified as of source check":
      bucket==="post"?"Public issuer Phase 3 readout confirmed":"Unverified",
    row.evidence?.evidenceDate||"",row.evidence?.drug||"",row.evidence?.indication||"",
    row.evidence?.evidenceUrl||"",row.sourceUrl
  ])];
  const csv="\ufeff"+table.map(r=>r.map(csvCell).join(",")).join("\r\n")+"\r\n";
  const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement("a");
  anchor.href=url;anchor.download="phase3-"+bucket+"-readout-research.csv";
  document.body.append(anchor);anchor.click();anchor.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}

/** Source-backed survey navigator. A recorded research input is not a rating or stock forecast. */
function SurveyExplorer({row,bucket,feed,researchStatus,onClose}:{
 row:ReadoutRow;bucket:"pre"|"post";feed:BenefitFeed|null;
 researchStatus:"idle"|"loading"|"ready"|"unavailable";onClose:()=>void;
}){
 const panelRef=useRef<HTMLDivElement>(null);
 const closeRef=useRef(onClose);
 closeRef.current=onClose;
 const [groupKey,setGroupKey]=useState<(typeof SURVEY_SECTIONS)[number]["key"]>("A");
 const [surveyRank,setSurveyRank]=useState(1);
 const [gapsOnly,setGapsOnly]=useState(false);
 useEffect(()=>{
   const previousFocus=document.activeElement instanceof HTMLElement?document.activeElement:null;
   const previousOverflow=document.body.style.overflow;
   document.body.style.overflow="hidden";
   panelRef.current?.focus();
   const handleKey=(event:KeyboardEvent)=>{
     if(event.key==="Escape"){event.preventDefault();closeRef.current();}
   };
   document.addEventListener("keydown",handleKey);
   return ()=>{
     document.removeEventListener("keydown",handleKey);
     document.body.style.overflow=previousOverflow;
     previousFocus?.focus();
   };
 },[]);
 const section=SURVEY_SECTIONS.find(g=>g.key===groupKey)||SURVEY_SECTIONS[0];
 const surveys=BENEFIT_GROUPS.filter(x=>x.number>=section.min&&x.number<=section.max);
 // An NCT can have multiple products. Never join survey records by ticker alone.
 const matches=feed?.records.filter(x=>x.nctId===row.nctId)||[];
 const record=matches.length===1?benefitForTrial(feed,{
   nctId:row.nctId,ticker:row.ticker,drug:row.evidence?.drug||"",
   indication:row.evidence?.indication||""}):null;
 const fact=(id:string):BenefitFact|null=>record?.facts[id]||null;
 const coverage=(fields:readonly {id:string}[])=>{
   const verified=record?fields.filter(f=>fact(f.id)?.status==="VERIFIED").length:0;
   const modeled=record?fields.filter(f=>fact(f.id)?.status==="MODELED").length:0;
   return {verified,modeled,gaps:fields.length-verified-modeled};
 };
 const all=coverage(BENEFIT_GROUPS.flatMap(x=>x.fields));
 const groupFields=surveys.flatMap(x=>x.fields);
 const groupCoverage=coverage(groupFields);
 const currentIndex=surveys.findIndex(x=>x.number===surveyRank);
 const changeGroup=(key:(typeof SURVEY_SECTIONS)[number]["key"],first:number)=>{
   setGroupKey(key);setSurveyRank(first);setGapsOnly(false);
 };
 const moveSurvey=(direction:-1|1)=>{
   const next=surveys[Math.max(0,Math.min(surveys.length-1,currentIndex+direction))];
   if(next)setSurveyRank(next.number);
 };
 return createPortal(
   <div className={css.surveyBackdrop} role="presentation"
     onClick={event=>{if(event.target===event.currentTarget)onClose();}}>
     <div ref={panelRef} className={css.surveyDialog} role="dialog" aria-modal="true"
       tabIndex={-1} aria-label={"Survey Ratings for "+row.ticker+" "+row.nctId}>
   <div className={css.surveyDialogHead}>
     <div>
       <p className={css.surveyEyebrow}>{bucket==="pre"?"UPPER · 3 · PHASE 3 BEFORE READOUT":"LOWER · P · PHASE 3 AFTER READOUT"}</p>
       <h3>Survey Ratings · {row.ticker}</h3>
       <p>{row.company} · {row.nctId}</p>
     </div>
     <button type="button" className={css.surveyClose} onClick={onClose} autoFocus>Close ✕</button>
   </div>
   <div className={css.surveyDialogBody}>
     <p className={css.surveyClarification}><strong>Research coverage, not a numerical rating.</strong>
       {" "}All 5 groups, 20 surveys and 38 questions are included. Scores remain
       {" "}<strong>Not graded</strong> until source-backed scoring rules are validated.
       Missing research never equals clinical failure or a zero score.</p>
     <div className={css.surveyOverview}>
       <div><small>Groups</small><strong>5</strong></div>
       <div><small>Surveys</small><strong>20</strong></div>
       <div><small>Questions</small><strong>{SURVEY_QUESTION_IDS.length}</strong></div>
       <div><small>Verified inputs</small><strong>{record?all.verified+" / 38":"Not assessed"}</strong></div>
     </div>
     {researchStatus==="loading"&&<p role="status" className={css.surveyStatus}>Checking exact-NCT survey evidence…</p>}
     {researchStatus==="unavailable"&&<p role="status" className={css.surveyStatus}>Research feed unavailable. Questions remain visible without scores.</p>}
     {researchStatus==="ready"&&!record&&<p role="status" className={css.surveyStatus}>No unambiguous NCT + ticker + therapy + indication research match. Missing percentages and trial scores are not assumed.</p>}
     {record&&<p role="status" className={css.surveyStatus}>Matched research inputs: {all.verified} verified · {all.modeled} modeled · {all.gaps} unrecorded. This is evidence coverage, not medical merit.</p>}
     <h4 className={css.surveyLabel}>1 · Survey groups</h4>
     <div className={css.surveyGroupRail} role="group" aria-label="Five survey groups">
       {SURVEY_SECTIONS.map(g=>{
         const groupSurveys=BENEFIT_GROUPS.filter(x=>x.number>=g.min&&x.number<=g.max);
         const fields=groupSurveys.flatMap(x=>x.fields),c=coverage(fields);
         return <button type="button" className={css.surveyGroupButton} key={g.key}
           aria-pressed={groupKey===g.key} onClick={()=>changeGroup(g.key,g.min)}>
           <strong>{g.key} · {g.name}</strong>
           <small>{groupSurveys.length} surveys · {fields.length} questions</small>
           <small>{record?c.verified+" verified · "+c.gaps+" gaps":"Not graded"}</small>
         </button>;
       })}
     </div>
     <div className={css.surveyLabelRow}>
       <h4 className={css.surveyLabel}>2 · {section.name}</h4>
       <span>{surveys.length} surveys · {groupFields.length} questions</span>
     </div>
     <div className={css.surveyCoverage}>
       <strong>Combined group rating: Not graded</strong>
       <span>{record?groupCoverage.verified+" verified · "+groupCoverage.modeled+" modeled · "+groupCoverage.gaps+" research gaps":"Evidence coverage not assessed"}</span>
     </div>
     <div className={css.surveyNavigation}>
       <button type="button" disabled={currentIndex<=0} onClick={()=>moveSurvey(-1)}>← Previous</button>
       <span>Survey {surveyRank||"—"} · {Math.max(0,currentIndex)+1}/{surveys.length}</span>
       <button type="button" disabled={currentIndex>=surveys.length-1} onClick={()=>moveSurvey(1)}>Next →</button>
     </div>
     <div className={css.surveyRail} role="region" aria-label="Surveys and horizontally expanding questions" tabIndex={0}>
       {surveys.map(survey=>{
         const selected=survey.number===surveyRank;
         const questions=survey.fields.filter(f=>!gapsOnly||!fact(f.id));
         const c=coverage(survey.fields);
         const spec=RANKED_BENEFIT_ASSESSMENTS.find(s=>s.rank===survey.number);
         return <div className={selected?css.surveyClusterActive:css.surveyCluster} key={survey.number}>
           <button type="button" className={css.surveyClusterHeader} aria-expanded={selected}
             onClick={()=>setSurveyRank(selected?0:survey.number)}>
             <strong>{survey.number}. {survey.name}</strong>
             <small>{survey.fields.length} questions · {record?c.verified+" verified":"Not graded"}</small>
             <span aria-hidden="true">{selected?"◀ Collapse":"Expand ▶"}</span>
           </button>
           {selected&&<div className={css.surveyQuestions}>
             {questions.length?questions.map(f=>{
               const detail=SURVEY_FIELD_DETAILS.get(f.id);
               const input=fact(f.id);
               return <article className={css.surveyQuestion} key={f.id}>
                 <small className={css.surveyQuestionNum}>QUESTION {SURVEY_QUESTION_NUMBERS.get(f.id)}</small>
                 <h5>{f.label}</h5>
                 <strong className={input?.status==="VERIFIED"?css.surveyVerified:input?.status==="MODELED"?css.surveyModeled:css.surveyUnscored}>
                   {input?.status==="VERIFIED"?"Verified input":input?.status==="MODELED"?"Modeled input":"Not assessed"}
                 </strong>
                 <p>{detail?.purpose||spec?.objective||"Survey question"}</p>
                 <p><strong>Evidence needed:</strong> {detail?.evidence||"Source-backed trial research"}</p>
                 {input?<div className={css.surveyFact}>
                   <p><strong>Value:</strong> {String(input.value)}</p>
                   <p><strong>Confidence:</strong> {input.confidence} · {input.sourceDate}</p>
                   <p><strong>Method:</strong> {input.method}</p>
                   <a href={input.sourceUrl} target="_blank" rel="noopener noreferrer">Open evidence source</a>
                 </div>:<p className={css.surveyUnscored}>No exact-trial survey input recorded; no rating assigned.</p>}
               </article>;
             }):<p className={css.surveyNoGaps}>No unrecorded questions in this survey.</p>}
           </div>}
         </div>;
       })}
     </div>
     <div className={css.surveyFoot}>
       <label><input type="checkbox" checked={gapsOnly} onChange={e=>setGapsOnly(e.target.checked)}/>
         Show unrecorded questions only</label>
       <span>Swipe sideways. Select a survey to expand its component questions to the right.</span>
     </div>
     {row.evidence?.evidenceUrl&&<p className={css.surveySource}>
       <a href={row.evidence.evidenceUrl} target="_blank" rel="noopener noreferrer">
         Issuer {bucket==="post"?"readout":"source check"} · {row.evidence.evidenceDate}</a>
       {" "}— not proof that every survey metric has been researched.</p>}
   </div>
     </div>
   </div>,document.body);
}

function TrialTable({rows,bucket,showSurveys,onSurveyOpen}:{
 rows:ReadoutRow[];bucket:Bucket;showSurveys:boolean;onSurveyOpen:(row:ReadoutRow)=>void;
}){
  return <div className={css.tableScroll} role="region" aria-label={bucket+" Phase 3 trial spreadsheet"} tabIndex={0}>
    <table className={css.table}>
      <thead><tr>
        <th>#</th><th>Ticker</th><th>NCT / trial</th><th>Company</th>
        {bucket==="post"&&<th title="Verified Phase 3 primary-endpoint statistical p-value, not FDA approval probability">Factor P · p-value</th>}
        {showSurveys&&<th>Survey Ratings</th>}
        <th>Drug / therapy</th><th>Indication</th><th>Registered status</th>
        <th>{bucket==="pre"?"Source checked":bucket==="post"?"Public release date":"Public release"}</th><th>Source evidence</th>
      </tr></thead>
      <tbody>{rows.length?rows.map((row,i)=><tr key={row.nctId}>
        <td>{i+1}</td><td><strong>{row.ticker}</strong></td>
        <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
        <td><span>{row.company}</span>{" "}<span className={`${css.stageBadge} ${bucket==="pre"?css.stageThree:css.stageP}`} title={bucket==="pre"?"3 · Phase 3 public results not identified at the dated source check":"P · Public Phase 3 results released; a PDUFA date is not implied"} aria-label={bucket==="pre"?"Phase 3 pre-release as last checked":"Post Phase 3 public readout confirmed"}>{bucket==="pre"?"3":"P"}</span></td>
        {bucket==="post"&&<td className={css.factorPCell}>
          {row.evidence?.primaryEndpointP
            ? <a className={css.factorPValue} href={row.evidence.primaryEndpointP.sourceUrl} target="_blank" rel="noopener noreferrer" title={row.evidence.primaryEndpointP.endpoint+" · issuer source"}>{row.evidence.primaryEndpointP.display}</a>
            : <span className={css.factorPMissing} title="Exact Phase 3 primary endpoint p-value not verified in the referenced public readout">Not reported</span>}
        </td>}{showSurveys&&<td className={css.surveyCell}>
          <button type="button" className={css.surveyOpenButton} onClick={()=>onSurveyOpen(row)}
            aria-label={"Explore five groups, twenty surveys and thirty-eight research questions for "+row.ticker+" "+row.nctId}>
            Surveys <span aria-hidden="true">→</span>
          </button>
          <small>5 groups · 20 surveys</small>
        </td>}<td>{txt(row.evidence?.drug||"")}</td>
        <td>{txt(row.evidence?.indication||"")}</td><td>{row.status.replaceAll("_"," ")}</td>
        <td>{row.evidence?.evidenceDate||"Not verified"}</td>
        <td>{row.evidence
          ? <a href={row.evidence.evidenceUrl} target="_blank" rel="noopener noreferrer">
            {bucket==="pre"?"Dated issuer check":"Public readout source"}</a>
          : "Not verified"}</td>
      </tr>):<tr><td colSpan={(bucket==="post"?10:9)+(showSurveys?1:0)} className={css.empty}>No documented matches in this view. Unknown-release trials are not counted as pre-release.</td></tr>}</tbody>
    </table>
  </div>;
}
function Spreadsheet({bucket,rows,query,caption,showSurveys,onSurveyOpen}:{
 bucket:"pre"|"post";rows:ReadoutRow[];query:string;caption:string;
 showSurveys:boolean;onSurveyOpen:(row:ReadoutRow)=>void;
}){
  const [sort,setSort]=useState<ReadoutKey>("ticker");
  const [desc,setDesc]=useState(false);
  const matched=useMemo(()=>{
    const q=query.trim().toLowerCase();
    const found=rows.filter(x=>
      !q||[x.nctId,x.ticker,x.company,x.status,x.evidence?.drug||"",x.evidence?.indication||"",x.evidence?.evidenceDate||"",x.evidence?.primaryEndpointP?.display||""]
        .some(field=>field.toLowerCase().includes(q)));
    return sortReadout(found,sort,desc);
  },[rows,query,sort,desc]);
  const pre=bucket==="pre";
  return <section className={css.sheet} aria-label={pre?"Top pre-release spreadsheet":"Bottom post-release spreadsheet"}>
    <div className={css.sheetHeading}>
      <div><h3>{pre?"TOP SPREADSHEET · 3 · PHASE 3 DATA NOT RELEASED (AS LAST CHECKED)":"BOTTOM SPREADSHEET · P · PHASE 3 DATA RELEASED"}</h3>
        <p>{caption}</p></div>
      <div className={css.actions}>
        <strong>{number(rows.length)} documented trials · {number(matched.length)} matching</strong>
        <button type="button" onClick={()=>downloadCsv(bucket,matched)} disabled={!matched.length}>
          Export matching CSV</button>
      </div>
    </div>
    <div className={css.postSort}>
      <label>Sort {pre?"pre-release":"post-release"} trials by{" "}
        <select aria-label={bucket+" release sort column"} value={sort}
          onChange={e=>setSort(e.target.value as ReadoutKey)}>
          {(pre?readoutColumns:postReadoutColumns).map(field=><option key={field.key} value={field.key}>{field.label}</option>)}
        </select>
      </label>
      <button type="button" onClick={()=>setDesc(v=>!v)}>{desc?"Descending ↓":"Ascending ↑"}</button>
    </div>
    <TrialTable rows={matched} bucket={bucket} showSurveys={showSurveys} onSurveyOpen={onSurveyOpen}/>
  </section>;
}
/** Full historical issuer-cap census with dated issuer readouts, never registry-result proxy. */
export default function Phase3ReadoutSheets(){
  const [data,setData]=useState<ReadoutClassification|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [query,setQuery]=useState("");
  const [showSurveys,setShowSurveys]=useState(SURVEY_RATINGS_PREVIEW_ENABLED);
  const [activeSurvey,setActiveSurvey]=useState<{row:ReadoutRow;bucket:"pre"|"post"}|null>(null);
  const [benefitFeed,setBenefitFeed]=useState<BenefitFeed|null>(null);
  const [researchStatus,setResearchStatus]=useState<"idle"|"loading"|"ready"|"unavailable">("idle");
  useEffect(()=>{
    if(!SURVEY_RATINGS_PREVIEW_ENABLED)return;
    try{if(window.localStorage.getItem(SURVEY_VISIBILITY_KEY)==="false")setShowSurveys(false);}catch{}
  },[]);
  const toggleSurveys=()=>{
    const next=!showSurveys;setShowSurveys(next);
    if(!next)setActiveSurvey(null);
    try{window.localStorage.setItem(SURVEY_VISIBILITY_KEY,String(next));}catch{}
  };
  useEffect(()=>{
    if(!activeSurvey||researchStatus!=="idle")return;
    setResearchStatus("loading");
    void fetch("/api/benefit-assessments",{cache:"no-store"})
      .then(async r=>{if(!r.ok)throw Error("Research unavailable");return parseBenefitFeed(await r.json());})
      .then(feed=>{setBenefitFeed(feed);setResearchStatus("ready");})
      .catch(()=>setResearchStatus("unavailable"));
  },[activeSurvey,researchStatus]);
  const [unknownPage,setUnknownPage]=useState(0);
  const [unknownFilters,setUnknownFilters]=useState<ColumnFilterState>({});
  const [unknownSort,setUnknownSort]=useState<ReadoutKey>("nctId");
  const [unknownDesc,setUnknownDesc]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();
    Promise.all([
      fetch("/phase3-census-2026-10-26.csv",{cache:"no-store",signal:controller.signal}),
      fetch("/phase3-public-readout-evidence-2026-11-01.json",{cache:"no-store",signal:controller.signal})
    ]).then(async ([census,evidence])=>{
      if(!census.ok||!evidence.ok)throw Error("Published sources unavailable.");
      const censusData=parsePhase3CensusCsv(await census.text());
      const result=classifyPhase3Readouts(await evidence.json(),censusData.rows);
      return result;
    }).then(result=>{if(!controller.signal.aborted)setData(result);})
      .catch(()=>{if(!controller.signal.aborted)setError("Release-classification evidence could not be validated. No counts asserted.");})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[]);
  const unknown=useMemo(()=>{
    const q=query.trim().toLowerCase();
    const pageRows=(data?.unverified||[]).filter(x=>!q||
      [x.nctId,x.ticker,x.company,x.status].some(s=>s.toLowerCase().includes(q)));
    return sortReadout(applyColumnFilters(pageRows,unknownFilters,readoutValue),
      unknownSort,unknownDesc);
  },[data,query,unknownFilters,unknownSort,unknownDesc]);
  const pages=Math.ceil(unknown.length/LIMIT);
  const activePage=Math.min(unknownPage,Math.max(0,pages-1));
  if(loading)return <section className={css.root} role="status">Loading dated Phase 3 release spreadsheets…</section>;
  if(error||!data)return <section className={css.root} role="alert">{error||"Readout research unavailable"}</section>;
  return <section className={css.root} id="tools-phase3-release-sheets" aria-label="Pre-release and post-release Phase 3 spreadsheets">
    <div className={css.title}>
      <h2>Phase 3 · Public Data Release</h2>
      <p>Two independent, source-linked spreadsheets from the {number(data.total)}-trial October 26, 2026 historical $300M–$10B issuer-cap census. Counted by distinct NCT, not by company or indication.</p>
    </div>
    <div className={css.metrics}>
      <div><span>Pre-release · as last checked</span><strong>{number(data.pre.length)}</strong></div>
      <div><span>Post-release · documented</span><strong>{number(data.post.length)}</strong></div>
      <div><span>Release not established</span><strong>{number(data.unverified.length)}</strong></div>
    </div>
    <p className={css.caveat}><strong>Important:</strong> Pre-release means no issuer readout was identified at a dated source check (October 11, 2026); it is not a guarantee that the study is still unreleased today. Post-release requires a source-backed public Phase 3 announcement. ClinicalTrials.gov results-posting and “COMPLETED” status alone do not establish either category. This is historical research, not a current PDUFA-qualified or stock-buy list.</p>
    <label className={css.searchLabel} htmlFor="phase3-readout-search">Find an NCT, ticker, company, drug or indication across both spreadsheets</label>
    <div className={css.searchRow}>
      <input id="phase3-readout-search" type="search" value={query}
        onChange={e=>{setQuery(e.target.value);setUnknownPage(0)}}
        placeholder="Search trials…" maxLength={90}/>
      <button type="button" onClick={()=>{setQuery("");setUnknownPage(0)}} disabled={!query}>Clear</button>
    </div>
    {SURVEY_RATINGS_PREVIEW_ENABLED&&<div className={css.surveyPreviewControls}>
      <div><strong>Survey Ratings preview</strong><span>Optional column · 5 groups · 20 surveys · 38 questions · no invented scores.</span></div>
      <button type="button" onClick={toggleSurveys} aria-pressed={showSurveys}>
        {showSurveys?"Hide Survey Ratings":"Show Survey Ratings"}
      </button>
    </div>}
    <Spreadsheet bucket="pre" rows={data.pre} query={query}
      showSurveys={showSurveys} onSurveyOpen={row=>setActiveSurvey({row,bucket:"pre"})}
      caption="Trials without a documented issuer public release at their source-check date. Each row retains the check date and issuer link."/>
    <Spreadsheet bucket="post" rows={data.post} query={query}
      showSurveys={showSurveys} onSurveyOpen={row=>setActiveSurvey({row,bucket:"post"})}
      caption="Trials with a documented company public Phase 3 results announcement. Factor P shows the sourced primary-endpoint p-value where reported; it is not approval probability."/>
    {showSurveys&&activeSurvey&&<SurveyExplorer key={activeSurvey.bucket+"|"+activeSurvey.row.nctId}
      row={activeSurvey.row} bucket={activeSurvey.bucket} feed={benefitFeed}
      researchStatus={researchStatus} onClose={()=>setActiveSurvey(null)}/>}
    <details className={css.unverified}>
      <summary><strong>Release status not verified · {number(data.unverified.length)} trials</strong> <span>Expand for research queue</span></summary>
      <div className={css.pendingBody}>
        <p>These NCTs are neither assumed pre-release nor post-release. They require dated issuer announcement searches or other direct public-results evidence. A missing registry posting is not evidence of an unreleased readout.</p>
        <div className={css.actions}>
          <strong>{number(unknown.length)} matching unverified NCTs</strong>
          <button type="button" onClick={()=>downloadCsv("unverified",unknown)}>Export unverified CSV</button>
        </div>
        <TrialColumnFilterBar title="Unverified readout queue" fields={unknownColumns}
          filters={unknownFilters} onChange={next=>{setUnknownFilters(next);setUnknownPage(0)}}
          hint="These are unverified announcements, not presumed pre-release or post-release. Filters are independent of the other two tables.">
          <label style={{fontSize:12}}>Sort by
            <select aria-label="Unverified release sort column" value={unknownSort}
              onChange={e=>{setUnknownSort(e.target.value as ReadoutKey);setUnknownPage(0)}}>
              {unknownColumns.map(field=><option key={field.key} value={field.key}>{field.label}</option>)}
            </select>
          </label>
          <button type="button" onClick={()=>{setUnknownDesc(v=>!v);setUnknownPage(0)}}>
            {unknownDesc?"Descending ↓":"Ascending ↑"}</button>
        </TrialColumnFilterBar>
        <div className={css.tableScroll} role="region" aria-label="Unverified Phase 3 readout research queue" tabIndex={0}>
          <table className={css.table}>
            <thead><tr><th>NCT</th><th>Ticker</th><th>Company</th><th>Registry status</th><th>Public readout</th></tr></thead>
            <tbody>{unknown.slice(activePage*LIMIT,(activePage+1)*LIMIT).map(row=><tr key={row.nctId}>
              <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
              <td>{row.ticker}</td><td>{row.company}</td><td>{row.status.replaceAll("_"," ")}</td>
              <td>Not verified — research required</td>
            </tr>)}</tbody>
          </table>
        </div>
        <div className={css.pagination}>
          <button type="button" disabled={activePage===0} onClick={()=>setUnknownPage(n=>Math.max(0,n-1))}>Previous 50</button>
          <span>Page {pages?activePage+1:0} of {pages}</span>
          <button type="button" disabled={activePage>=pages-1} onClick={()=>setUnknownPage(n=>n+1)}>Next 50</button>
        </div>
      </div>
    </details>
    <p className={css.footer}>Dated source files: {data.sourceFiles.join(" and ")}. Classification research snapshot: {data.sourceAsOf}. Unverified does not mean unreleased, and all counts remain limited by the 741-trial issuer-cap research census.</p>
  </section>;
}
