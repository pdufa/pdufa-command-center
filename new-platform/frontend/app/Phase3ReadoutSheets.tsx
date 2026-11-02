"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import {createPortal} from "react-dom";
import {parsePhase3CensusCsv} from "../lib/phase3-census-rows";
import {classifyPhase3Readouts,type ReadoutClassification,type ReadoutRow} from "../lib/phase3-public-readout";
import css from "./Phase3ReadoutSheets.module.css";
import TrialRaasDisclosure from "./TrialRaasDisclosure";
import TrialColumnFilterBar,{applyColumnFilters,type ColumnFilterState,type ColumnFilterField} from "./TrialColumnFilterBar";
import {BENEFIT_GROUPS,benefitForTrial,parseBenefitFeed,type BenefitFeed,type BenefitFact} from "../lib/benefit-assessments";
import {RANKED_BENEFIT_ASSESSMENTS} from "../lib/pipeline-benefit-assessments";
import {ALL_RESEARCH_FIELD_DEFINITIONS} from "../lib/pipeline-research-view";
import {exactReadoutBenefit,readoutResearchCoverage,sortPhase3Readouts,type Phase3ReadoutSortKey} from "../lib/phase3-readout-sort";
import {finalSurveyReadiness} from "../lib/final-survey-readiness";

type Bucket="pre"|"post"|"unverified";
/** Reversible visibility-only feature; existing trial data and research sources are unchanged. */
const SURVEY_RATINGS_PREVIEW_ENABLED=true;
const SURVEY_VISIBILITY_KEY="phase3-readout-survey-column-visible-v1";
const SYNTHESIS_COLUMN_ENABLED=true;
const SYNTHESIS_VISIBILITY_KEY="phase3-survey-conjunction-visible-v1";
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
type ReadoutKey=Exclude<Phase3ReadoutSortKey,"row"|"survey"|"synthesis">;
const readoutColumns:ColumnFilterField[]=[
 {key:"row",label:"Original row #"},
 {key:"ticker",label:"Ticker"},{key:"nctId",label:"NCT / trial"},
 {key:"company",label:"Company"},
 {key:"survey",label:"Survey Ratings · verified inputs"},
 {key:"synthesis",label:"SURVEY · evidence readiness"},
 {key:"drug",label:"Drug / therapy"},
 {key:"indication",label:"Indication"},{key:"status",label:"Registry status"},
 {key:"date",label:"Issuer release/check date"},{key:"source",label:"Evidence source"}
];
const postReadoutColumns:ColumnFilterField[]=[
 ...readoutColumns.slice(0,4),
 {key:"factorP",label:"Factor P · numeric threshold"},
 ...readoutColumns.slice(4)
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


/** One AND-gated, non-numeric synthesis of the existing 20 surveys / 38 questions.
 * This is not a new clinical assessment and may be hidden without touching the original columns.
 */
function SynthesisPanel({row,bucket,feed,researchStatus,onClose,onDetailedSurveys}:{
 row:ReadoutRow;bucket:"pre"|"post";feed:BenefitFeed|null;
 researchStatus:"idle"|"loading"|"ready"|"unavailable";
 onClose:()=>void;onDetailedSurveys:()=>void;
}){
 const panelRef=useRef<HTMLDivElement>(null);
 const closeRef=useRef(onClose);closeRef.current=onClose;
 useEffect(()=>{
   const previousFocus=document.activeElement instanceof HTMLElement?document.activeElement:null;
   const previousOverflow=document.body.style.overflow;
   document.body.style.overflow="hidden";
   panelRef.current?.focus();
   const handleKey=(event:KeyboardEvent)=>{
     if(event.key==="Escape"){event.preventDefault();closeRef.current();}
   };
   document.addEventListener("keydown",handleKey);
   return ()=>{document.removeEventListener("keydown",handleKey);
     document.body.style.overflow=previousOverflow;previousFocus?.focus();};
 },[]);
 const sameNct=feed?.records.filter(r=>r.nctId===row.nctId)||[];
 const record=sameNct.length===1?benefitForTrial(feed,{
   nctId:row.nctId,ticker:row.ticker,drug:row.evidence?.drug||"",
   indication:row.evidence?.indication||""}):null;
 const verified=(id:string)=>record?.facts[id]?.status==="VERIFIED";
 const any=(...ids:string[])=>ids.some(verified);
 const groups=SURVEY_SECTIONS.map(g=>{
   const fields=BENEFIT_GROUPS.filter(s=>s.number>=g.min&&s.number<=g.max).flatMap(s=>s.fields);
   const v=record?fields.filter(f=>verified(f.id)).length:0;
   const modeled=record?fields.filter(f=>record.facts[f.id]?.status==="MODELED").length:0;
   return {...g,verified:v,modeled,missing:fields.length-v-modeled,total:fields.length};
 });
 const rules=bucket==="pre"?[
   {label:"Historical issuer pre-release source check",passed:row.evidence?.kind==="PRE_AS_OF_CHECK",
    detail:"An older source check does not prove the company has not released data since."},
   {label:"Patient population and unmet need",passed:any("eligibleUsPatients","standardOfCare","unmetNeed"),
    detail:"At least one verified, exact-program patient-need input."},
   {label:"Competitive environment",passed:any("closestCompetitor","competitorCount","competitivePipelineThreat"),
    detail:"At least one sourced treatment-alternative or competitive input."},
   {label:"Valuation and shareholder risks",passed:any("valuationImpact","shareholderRisk"),
    detail:"At least one verified valuation or shareholder-risk research input."}
 ]:[
   {label:"Issuer Phase 3 data release",passed:row.evidence?.kind==="POST_PUBLIC_READOUT",
    detail:"A public results announcement is not an FDA filing or PDUFA confirmation."},
   {label:"Clinical benefit and effect magnitude",passed:!!verified("clinicalBenefit")&&!!verified("magnitude"),
    detail:"Both treatment effect and its size must be independently documented."},
   {label:"Safety and tolerability",passed:any("safetyAdvantage","seriousAes","discontinuation"),
    detail:"Verified safety data rather than a p-value alone."},
   {label:"Valuation and shareholder risks",passed:any("valuationImpact","shareholderRisk"),
    detail:"Investment expectations, financing and dilution are separate from clinical significance."}
 ];
 const checked=researchStatus==="ready";
 const audit=finalSurveyReadiness(groups,rules,checked&&!!record);
 const unverifiedQuestions=record?BENEFIT_GROUPS.flatMap(survey=>
   survey.fields.filter(field=>record.facts[field.id]?.status!=="VERIFIED").map(field=>({
     survey:survey.number,label:field.label,
     status:record.facts[field.id]?.status==="MODELED"?"Modeled only":"Not recorded"
   }))):[];
 const ready=audit.reviewReady;
 const summary=researchStatus==="loading"||researchStatus==="idle"?"Checking sources":
   researchStatus==="unavailable"?"Evidence unavailable":
   ready?"READY FOR EVIDENCE REVIEW":"ABSTAIN · EVIDENCE INCOMPLETE";
 return createPortal(<div className={css.surveyBackdrop} role="presentation"
     onClick={e=>{if(e.target===e.currentTarget)onClose();}}>
   <div ref={panelRef} className={css.surveyDialog} role="dialog" aria-modal="true"
      tabIndex={-1} aria-label={"SURVEY synthesis for "+row.ticker+" "+row.nctId}>
     <div className={css.surveyDialogHead}>
       <div><p className={css.surveyEyebrow}>{bucket==="pre"?"UPPER · 3 · BEFORE DATA RELEASE":"LOWER · P · AFTER DATA RELEASE"}</p>
         <h3>SURVEY · {row.ticker}</h3><p>{row.company} · {row.nctId}</p></div>
       <button className={css.surveyClose} type="button" onClick={onClose}>Close ✕</button>
     </div>
     <div className={css.surveyDialogBody}>
       <section className={css.conjunctionSection} aria-label="Combined survey conclusion">
         <p className={css.surveyEyebrow}>CONJUNCTIVE SURVEY SUMMARY</p>
         <h4>{bucket==="pre"?"Readout research readiness":"Post-readout research readiness"}</h4>
         <div className={css.conjunctionVerdict} role="status">{summary}</div>
         <p>Combination rule: <strong>all 5 groups have verified research inputs</strong>
           {" AND "}<strong>all relevant stage-specific checks pass</strong>.
           Modeled inputs are shown separately and cannot pass verified gates.
           This is an evidence-readiness decision, not an FDA probability or a forecast of stock appreciation.</p>
         <section className={css.finalSurveyCheckpoint} aria-label="Final SURVEY readiness and reluctant evidence grade">
           <h5>Final SURVEY · two independent grades</h5>
           <div className={css.finalSurveyGrades}>
             <div>
               <small>Grade 1 · Full analysis readiness</small>
               <strong>{audit.fullReadinessGrade}</strong>
               <span>Requires 38/38 source-verified questions, evidence in every group, and all four stage-specific checks.</span>
             </div>
             <div>
               <small>Grade 2 · Reluctant evidence-coverage grade</small>
               <strong>{audit.provisionalGrade}</strong>
               <span>Only the percentage of 38 source-verified research inputs. A ≥90%, B ≥75%, C ≥50%, D ≥25%, E below 25%. No grade without an exact record.</span>
             </div>
           </div>
           <p><strong>Source-verified coverage:</strong> {audit.assessable?
             audit.verified+" of "+audit.total+" ("+audit.verifiedPercent+"%) · "+audit.modeled+" modeled · "+audit.missing+" not recorded":
             "Not assessable — a unique source-matched study record and a valid research feed are required."}
           </p>
           <p><strong>Preliminary evidence-review gate:</strong> {audit.assessable?
             (audit.reviewReady?"PASS · all five groups represented and all stage checks passed":
              "NOT READY · "+audit.missingGroups.length+" groups without verified research · "+audit.failedGates.length+" stage checks not met"):
             "Not assessed"}
           </p>
           <p><strong>FDA decision forecast:</strong> ABSTAIN — this coverage audit cannot establish approval, a Complete Response Letter, an extension, or a probability. Scientific outcome calibration remains separate.</p>
           {audit.assessable&&<details className={css.finalSurveyMissing}>
             <summary>Review outstanding evidence · {unverifiedQuestions.length} not verified · {audit.failedGates.length} failed checks</summary>
             {audit.failedGates.length>0&&<div>
               <strong>Required stage checks not met</strong>
               <ul>{audit.failedGates.map(label=><li key={label}>{label}</li>)}</ul>
             </div>}
             {audit.missingGroups.length>0&&<p><strong>Groups without a verified input:</strong> {audit.missingGroups.join("; ")}</p>}
             <strong>Research questions still requiring verification</strong>
             {unverifiedQuestions.length?
               <ol>{unverifiedQuestions.map(q=><li key={q.survey+"|"+q.label}>
                 Survey {q.survey} · {q.label} — {q.status}
               </li>)}</ol>:<p>All 38 questions have source-verified inputs.</p>}
           </details>}
           <p className={css.conjunctionWarning}>The reluctant grade is a provisional research-completeness label, not a validated clinical-merit, investment-return or FDA-decision grade. An incomplete study must never receive a fictitious failure score.</p>
         </section>
         <h5>Five required groups · combined evidence</h5>
         <div className={css.conjunctionGroups}>
           {groups.map(g=><div key={g.key}>
             <strong>{g.key} · {g.name}</strong>
             <span>{record?g.verified+" verified · "+g.modeled+" modeled · "+g.missing+" unrecorded":"Not assessed"} ({g.total} questions)</span>
           </div>)}
         </div>
         <h5>Stage-specific checks</h5>
         <div className={css.conjunctionGates}>
           {rules.map(rule=><div key={rule.label}>
             <strong>{checked?(rule.passed?"Verified":"Not verified"):"Pending"} · {rule.label}</strong>
             <span>{rule.detail}</span>
           </div>)}
         </div>
         {researchStatus==="unavailable"&&<p role="alert">Research feed is unavailable; no readiness conclusion is inferred.</p>}
         {checked&&!record&&<p>No unique matching research record for this NCT, ticker, therapy and indication. Not assessed is not a failed trial result.</p>}
         <p className={css.conjunctionWarning}>
           {bucket==="pre"?
             "Readout guidance is not stored as a verified date/window in this dataset. This synthesis does not establish when results will be announced.":
             "A Phase 3 p-value does not by itself establish meaningful clinical benefit. FDA filing, accepted application and PDUFA action date require separate verification."}
         </p>
         <button type="button" className={css.surveyOpenButton} onClick={onDetailedSurveys}>
           Explore 20 surveys and 38 questions →
         </button>
       </section>
     </div>
   </div>
 </div>,document.body);
}

function TrialTable({rows,bucket,originalOrder,showSurveys,showSynthesis,
 onSurveyOpen,onRaasOpen,sort,desc,onSort,benefitFeed,researchStatus}:{
 rows:ReadoutRow[];bucket:"pre"|"post";originalOrder:readonly ReadoutRow[];
 showSurveys:boolean;showSynthesis:boolean;
 onSurveyOpen:(row:ReadoutRow,view:"details"|"synthesis")=>void;
 onRaasOpen:()=>void;
 sort:Phase3ReadoutSortKey;desc:boolean;onSort:(key:Phase3ReadoutSortKey)=>void;
 benefitFeed:BenefitFeed|null;researchStatus:"idle"|"loading"|"ready"|"unavailable";
}){
 const originalNumbers=new Map(originalOrder.map((row,index)=>[row.nctId,index+1]));
 const sortedHeader=(key:Phase3ReadoutSortKey,label:string,tooltip?:string)=>
   <th aria-sort={sort===key?(desc?"descending":"ascending"):"none"}>
     <button type="button" className={css.sortHeaderButton}
       title={tooltip||"Sort by "+label}
       aria-label={"Sort "+label+(sort===key?(desc?" ascending":" descending"):" ascending")}
       onClick={()=>onSort(key)}>
       <span>{label}</span>
       <span className={css.sortArrow} aria-hidden="true">{sort===key?(desc?"↓":"↑"):"↕"}</span>
     </button>
   </th>;
 const researchFor=(row:ReadoutRow)=>researchStatus==="ready"
   ?readoutResearchCoverage(row,bucket,benefitFeed):null;
  return <div className={css.tableScroll} role="region" aria-label={bucket+" Phase 3 trial spreadsheet"} tabIndex={0}>
    <table className={css.table}>
      <thead><tr>
        {sortedHeader("row","#","Original spreadsheet row number")}
        {sortedHeader("ticker","Ticker")}
        {sortedHeader("nctId","NCT / trial")}
        {sortedHeader("company","Company")}
        {bucket==="post"&&sortedHeader("factorP","Factor P · p-value","Sort by reported numeric p-value threshold, not FDA approval probability")}
        <th scope="col" title="Proposed phase-specific risk-adjusted appreciation score; grade not yet validated">{bucket==="pre"?"TOP-RAAS":"BOTTOM-RAAS"}</th>
        {showSurveys&&sortedHeader("survey","Survey Ratings","Sort by count of verified research inputs; not clinical quality")}
        {showSynthesis&&sortedHeader("synthesis","SURVEY","Sort by evidence-readiness gates; not expected stock appreciation")}
        {sortedHeader("drug","Drug / therapy")}
        {sortedHeader("indication","Indication")}
        {sortedHeader("status","Registered status")}
        {sortedHeader("date",bucket==="pre"?"Source checked":"Public release date")}
        {sortedHeader("source","Source evidence","Sort by evidence source URL")}
      </tr></thead>
      <tbody>{rows.length?rows.map((row,i)=><tr key={row.nctId}>
        <td>{originalNumbers.get(row.nctId)??i+1}</td><td><strong>{row.ticker}</strong></td>
        <td><a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
        <td><span>{row.company}</span>{" "}<span className={`${css.stageBadge} ${bucket==="pre"?css.stageThree:css.stageP}`} title={bucket==="pre"?"3 · Phase 3 public results not identified at the dated source check":"P · Public Phase 3 results released; a PDUFA date is not implied"} aria-label={bucket==="pre"?"Phase 3 pre-release as last checked":"Post Phase 3 public readout confirmed"}>{bucket==="pre"?"3":"P"}</span></td>
        {bucket==="post"&&<td className={css.factorPCell}>
          {row.evidence?.primaryEndpointP
            ? <a className={css.factorPValue} href={row.evidence.primaryEndpointP.sourceUrl} target="_blank" rel="noopener noreferrer" title={row.evidence.primaryEndpointP.endpoint+" · issuer source"}>{row.evidence.primaryEndpointP.display}</a>
            : <span className={css.factorPMissing} title="Exact Phase 3 primary endpoint p-value not verified in the referenced public readout">Not reported</span>}
        </td>}<td>
          <TrialRaasDisclosure row={row} bucket={bucket} researchStatus={researchStatus}
            coverage={researchFor(row)} benefitFeed={benefitFeed} onResearchRequest={onRaasOpen}/>
        </td>{showSurveys&&<td className={css.surveyCell}>
          <button type="button" className={css.surveyOpenButton} onClick={()=>onSurveyOpen(row,"details")}
            aria-label={"Explore five groups, twenty surveys and thirty-eight research questions for "+row.ticker+" "+row.nctId}>
            Surveys <span aria-hidden="true">→</span>
          </button>
          <small>{researchStatus==="loading"?"Loading verified inputs":
            researchFor(row)?researchFor(row)!.verified+" verified / 38":"Not assessed · 5 groups"}</small>
        </td>}{showSynthesis&&<td className={css.surveyCell}>
          <button type="button" className={css.surveyOpenButton} onClick={()=>onSurveyOpen(row,"synthesis")}
            aria-label={"Open SURVEY combined assessment for "+row.ticker+" "+row.nctId}>
            SURVEY <span aria-hidden="true">→</span>
          </button>
          <small>{researchFor(row)?
            (researchFor(row)!.ready?"Ready for evidence review":
              "Incomplete evidence · "+researchFor(row)!.passedChecks+"/4 gates"):
            "Evidence not assessed"}</small>
        </td>}<td>{txt(row.evidence?.drug||"")}</td>
        <td>{txt(row.evidence?.indication||"")}</td><td>{row.status.replaceAll("_"," ")}</td>
        <td>{row.evidence?.evidenceDate||"Not verified"}</td>
        <td>{row.evidence
          ? <a href={row.evidence.evidenceUrl} target="_blank" rel="noopener noreferrer">
            {bucket==="pre"?"Dated issuer check":"Public readout source"}</a>
          : "Not verified"}</td>
      </tr>):<tr><td colSpan={(bucket==="post"?11:10)+(showSurveys?1:0)+(showSynthesis?1:0)} className={css.empty}>No documented matches in this view. Unknown-release trials are not counted as pre-release.</td></tr>}</tbody>
    </table>
  </div>;
}
function Spreadsheet({bucket,rows,query,caption,showSurveys,showSynthesis,onSurveyOpen,
 benefitFeed,researchStatus,onResearchSort}:{
 bucket:"pre"|"post";rows:ReadoutRow[];query:string;caption:string;
 showSurveys:boolean;showSynthesis:boolean;benefitFeed:BenefitFeed|null;
 researchStatus:"idle"|"loading"|"ready"|"unavailable";onResearchSort:()=>void;
 onSurveyOpen:(row:ReadoutRow,view:"details"|"synthesis")=>void;
}){
  const [sort,setSort]=useState<Phase3ReadoutSortKey>("ticker");
  const [desc,setDesc]=useState(false);
  // Segment controls are intentionally independent for TOP and BOTTOM.
  // Start every segment collapsed, including after a fresh page load.
  const [sortSegmentOpen,setSortSegmentOpen]=useState(false);
  const [rowsSegmentOpen,setRowsSegmentOpen]=useState(false);
  const allSegmentsOpen=sortSegmentOpen&&rowsSegmentOpen;
  const toggleAllSegments=()=>{
    const next=!allSegmentsOpen;
    setSortSegmentOpen(next);
    setRowsSegmentOpen(next);
  };
  const resetSorting=()=>{
    setSort("ticker");
    setDesc(false);
  };
  const availableSortColumns=(bucket==="pre"?readoutColumns:postReadoutColumns)
    .filter(field=>(field.key!=="survey"||showSurveys)&&(field.key!=="synthesis"||showSynthesis));
  const setSortColumn=(key:Phase3ReadoutSortKey)=>{
    if((key==="survey"||key==="synthesis")&&researchStatus==="idle")onResearchSort();
    if(key===sort)setDesc(v=>!v);
    else{setSort(key);setDesc(false);}
  };
  useEffect(()=>{
    if(sort==="survey"&&!showSurveys||sort==="synthesis"&&!showSynthesis){
      setSort("ticker");setDesc(false);
    }
  },[sort,showSurveys,showSynthesis]);
  const matched=useMemo(()=>{
    const q=query.trim().toLowerCase();
    const found=rows.filter(x=>
      !q||[x.nctId,x.ticker,x.company,x.status,x.evidence?.drug||"",x.evidence?.indication||"",x.evidence?.evidenceDate||"",x.evidence?.primaryEndpointP?.display||""]
        .some(field=>field.toLowerCase().includes(q)));
    return sortPhase3Readouts(found,rows,sort,desc,bucket,benefitFeed);
  },[rows,query,sort,desc,bucket,benefitFeed]);
  const pre=bucket==="pre";
  return <section className={css.sheet} aria-label={pre?"Top pre-release spreadsheet":"Bottom post-release spreadsheet"}>
    <details className={css.sheetAccordion}>
      <summary className={css.sheetHeading}>
        <div><h3>{pre?"TOP SPREADSHEET · 3 · PHASE 3 DATA NOT RELEASED (AS LAST CHECKED)":"BOTTOM SPREADSHEET · P · PHASE 3 DATA RELEASED"}</h3>
          <p>{caption}</p></div>
        <strong className={css.sheetSummaryCount}>
          {number(rows.length)} documented trials · {number(matched.length)} matching
        </strong>
      </summary>
      <div className={css.sheetPanelActions}>
        <button type="button" onClick={()=>downloadCsv(bucket,matched)} disabled={!matched.length}>
          Export matching CSV</button>
        <button type="button" className={css.sheetSegmentAllButton}
          onClick={toggleAllSegments}
          aria-label={(allSegmentsOpen?"Collapse all":"Expand all")+" "+(pre?"TOP":"BOTTOM")+" spreadsheet segments"}>
          {allSegmentsOpen?"Collapse all segments ▴":"Expand all segments ▾"}
        </button>
      </div>
    <div className={css.sheetSegmentButtons} role="group"
      aria-label={(pre?"TOP · 3":"BOTTOM · P")+" collapsible spreadsheet segments"}>
      <button type="button" aria-expanded={sortSegmentOpen}
        aria-controls={bucket+"-phase3-sort-controls"}
        onClick={()=>setSortSegmentOpen(open=>!open)}>
        <span aria-hidden="true">{sortSegmentOpen?"▾":"▸"}</span>
        Sorting controls <small>{sortSegmentOpen?"Expanded":"Collapsed"}</small>
      </button>
      <button type="button" aria-expanded={rowsSegmentOpen}
        aria-controls={bucket+"-phase3-trial-rows"}
        onClick={()=>setRowsSegmentOpen(open=>!open)}>
        <span aria-hidden="true">{rowsSegmentOpen?"▾":"▸"}</span>
        Trial rows <small>{number(matched.length)} matching · {rowsSegmentOpen?"Expanded":"Collapsed"}</small>
      </button>
    </div>
    {sortSegmentOpen&&<div id={bucket+"-phase3-sort-controls"} className={css.postSort}>
      <label>Sort {pre?"pre-release":"post-release"} trials by{" "}
        <select aria-label={bucket+" release sort column"} value={sort}
          onChange={e=>{setSort(e.target.value as Phase3ReadoutSortKey);setDesc(false);if((e.target.value==="survey"||e.target.value==="synthesis")&&researchStatus==="idle")onResearchSort();}}>
          {availableSortColumns.map(field=><option key={field.key} value={field.key}>{field.label}</option>)}
        </select>
      </label>
      <button type="button" onClick={()=>setDesc(v=>!v)}>{desc?"Descending ↓":"Ascending ↑"}</button>
      <button type="button" className={css.resetSortingButton}
        onClick={resetSorting} disabled={sort==="ticker"&&!desc}
        aria-label={pre?"Reset TOP spreadsheet sorting to Ticker A to Z":"Reset BOTTOM spreadsheet sorting to Ticker A to Z"}
        title="Reset this spreadsheet to its default Ticker A–Z sort">
        ↺ Reset Sorting
      </button>
      {(sort==="survey"||sort==="synthesis")&&
        <span role="status" className={css.sortEvidenceState}>
          {researchStatus==="loading"?"Loading trial-specific survey evidence…":
           researchStatus==="unavailable"?"Survey research unavailable · unassessed rows remain in original order":
           "Sorted by documented evidence coverage, not medical success or stock appreciation"}
        </span>}
    </div>}
    {rowsSegmentOpen&&<div id={bucket+"-phase3-trial-rows"} className={css.sheetRowsSegment}>
      <TrialTable rows={matched} bucket={bucket} originalOrder={rows} showSurveys={showSurveys}
        showSynthesis={showSynthesis} sort={sort} desc={desc} onSort={setSortColumn}
        benefitFeed={benefitFeed} researchStatus={researchStatus} onSurveyOpen={onSurveyOpen}
         onRaasOpen={onResearchSort}/>
    </div>}
    </details>
  </section>;
}
/** Full historical issuer-cap census with dated issuer readouts, never registry-result proxy. */
export default function Phase3ReadoutSheets(){
  const [data,setData]=useState<ReadoutClassification|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [query,setQuery]=useState("");
  const [showSurveys,setShowSurveys]=useState(SURVEY_RATINGS_PREVIEW_ENABLED);
  const [showSynthesis,setShowSynthesis]=useState(SYNTHESIS_COLUMN_ENABLED);
  const [activeSurvey,setActiveSurvey]=useState<{row:ReadoutRow;bucket:"pre"|"post";view:"details"|"synthesis"}|null>(null);
  const [benefitFeed,setBenefitFeed]=useState<BenefitFeed|null>(null);
  const [researchStatus,setResearchStatus]=useState<"idle"|"loading"|"ready"|"unavailable">("idle");
  const [researchSortRequested,setResearchSortRequested]=useState(false);
  useEffect(()=>{
    if(!SURVEY_RATINGS_PREVIEW_ENABLED)return;
    try{if(window.localStorage.getItem(SURVEY_VISIBILITY_KEY)==="false")setShowSurveys(false);}catch{}
    try{if(window.localStorage.getItem(SYNTHESIS_VISIBILITY_KEY)==="false")setShowSynthesis(false);}catch{}
  },[]);
  const toggleSurveys=()=>{
    const next=!showSurveys;setShowSurveys(next);
    if(!next)setActiveSurvey(active=>active?.view==="details"?null:active);
    try{window.localStorage.setItem(SURVEY_VISIBILITY_KEY,String(next));}catch{}
  };
  const toggleSynthesis=()=>{
    const next=!showSynthesis;setShowSynthesis(next);
    if(!next)setActiveSurvey(active=>active?.view==="synthesis"?null:active);
    try{window.localStorage.setItem(SYNTHESIS_VISIBILITY_KEY,String(next));}catch{}
  };
  useEffect(()=>{
    if((!activeSurvey&&!researchSortRequested)||researchStatus!=="idle")return;
    setResearchStatus("loading");
    void fetch("/api/benefit-assessments",{cache:"no-store"})
      .then(async r=>{if(!r.ok)throw Error("Research unavailable");return parseBenefitFeed(await r.json());})
      .then(feed=>{setBenefitFeed(feed);setResearchStatus("ready");})
      .catch(()=>setResearchStatus("unavailable"));
  },[activeSurvey,researchSortRequested,researchStatus]);
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
      <p>Open only the section you want to work with. All segments start collapsed.</p>
    </div>
    <details className={css.topSegment} data-segment="phase3-overview">
      <summary className={css.topSegmentSummary}>Research overview &amp; source checks
        <span>▾</span>
      </summary>
      <div className={css.topSegmentBody}>
        <p>Two independent, source-linked spreadsheets from the {number(data.total)}-trial October 26, 2026 historical $300M–$10B issuer-cap census. Counted by distinct NCT, not by company or indication.</p>
        <div className={css.metrics}>
          <div><span>Pre-release · as last checked</span><strong>{number(data.pre.length)}</strong></div>
          <div><span>Post-release · documented</span><strong>{number(data.post.length)}</strong></div>
          <div><span>Release not established</span><strong>{number(data.unverified.length)}</strong></div>
        </div>
        <p className={css.caveat}><strong>Important:</strong> Pre-release means no issuer readout was identified at a dated source check (October 11, 2026); it is not a guarantee that the study is still unreleased today. Post-release requires a source-backed public Phase 3 announcement. ClinicalTrials.gov results-posting and “COMPLETED” status alone do not establish either category. This is historical research, not a current PDUFA-qualified or stock-buy list.</p>
      </div>
    </details>
    <details className={css.topSegment} data-segment="phase3-search">
      <summary className={css.topSegmentSummary}>Search across TOP &amp; BOTTOM spreadsheets
        <span>▾</span>
      </summary>
      <div className={css.topSegmentBody}>
        <label className={css.searchLabel} htmlFor="phase3-readout-search">Find an NCT, ticker, company, drug or indication across both spreadsheets</label>
        <div className={css.searchRow}>
          <input id="phase3-readout-search" type="search" value={query}
            onChange={e=>{setQuery(e.target.value);setUnknownPage(0)}}
            placeholder="Search trials…" maxLength={90}/>
          <button type="button" onClick={()=>{setQuery("");setUnknownPage(0)}} disabled={!query}>Clear</button>
        </div>
      </div>
    </details>
    {SURVEY_RATINGS_PREVIEW_ENABLED&&<details className={css.topSegment} data-segment="phase3-survey-ratings">
      <summary className={css.topSegmentSummary}>Survey Ratings column settings
        <span>▾</span>
      </summary>
      <div className={css.topSegmentBody}>
        <div className={css.surveyPreviewControls}>
          <div><strong>Survey Ratings preview</strong><span>Optional column · 5 groups · 20 surveys · 38 questions · no invented scores.</span></div>
          <button type="button" onClick={toggleSurveys} aria-pressed={showSurveys}>
            {showSurveys?"Hide Survey Ratings":"Show Survey Ratings"}
          </button>
        </div>
      </div>
    </details>}
    {SYNTHESIS_COLUMN_ENABLED&&<details className={css.topSegment} data-segment="phase3-survey-synthesis">
      <summary className={css.topSegmentSummary}>SURVEY combined assessment settings
        <span>▾</span>
      </summary>
      <div className={css.topSegmentBody}>
        <div className={css.surveyPreviewControls}>
          <div><strong>SURVEY · Combined assessment</strong>
            <span>One source-gated synthesis of your five groups, independent of the detailed survey display.</span></div>
          <button type="button" onClick={toggleSynthesis} aria-pressed={showSynthesis}>
            {showSynthesis?"Hide SURVEY":"Show SURVEY"}
          </button>
        </div>
      </div>
    </details>}
    <Spreadsheet bucket="pre" rows={data.pre} query={query}
      showSurveys={showSurveys} showSynthesis={showSynthesis}
      benefitFeed={benefitFeed} researchStatus={researchStatus}
      onResearchSort={()=>setResearchSortRequested(true)}
      onSurveyOpen={(row,view)=>setActiveSurvey({row,bucket:"pre",view})}
      caption="Trials without a documented issuer public release at their source-check date. Each row retains the check date and issuer link."/>
    <Spreadsheet bucket="post" rows={data.post} query={query}
      showSurveys={showSurveys} showSynthesis={showSynthesis}
      benefitFeed={benefitFeed} researchStatus={researchStatus}
      onResearchSort={()=>setResearchSortRequested(true)}
      onSurveyOpen={(row,view)=>setActiveSurvey({row,bucket:"post",view})}
      caption="Trials with a documented company public Phase 3 results announcement. Factor P shows the sourced primary-endpoint p-value where reported; it is not approval probability."/>
    {activeSurvey?.view==="details"&&<SurveyExplorer key={activeSurvey.bucket+"|"+activeSurvey.row.nctId}
      row={activeSurvey.row} bucket={activeSurvey.bucket} feed={benefitFeed}
      researchStatus={researchStatus} onClose={()=>setActiveSurvey(null)}/>}
    {activeSurvey?.view==="synthesis"&&<SynthesisPanel
      key={activeSurvey.bucket+"|"+activeSurvey.row.nctId+"|synthesis"}
      row={activeSurvey.row} bucket={activeSurvey.bucket} feed={benefitFeed}
      researchStatus={researchStatus} onClose={()=>setActiveSurvey(null)}
      onDetailedSurveys={()=>setActiveSurvey({...activeSurvey,view:"details"})}/>}
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
