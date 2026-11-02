"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import {BENEFIT_GROUPS,benefitForTrial,rankAdvantages,type BenefitFeed,type BenefitRecord,type BenefitAdvantage,type BenefitGroup} from "../lib/benefit-assessments";
import type {ToolsSpreadsheetRow} from "./ToolsResultsSpreadsheet";
import css from "./ToolsBenefitMatrix.module.css";
import RegistryBenefitEvidence from "./RegistryBenefitEvidence";
import TrialTimelineSummary from "./TrialTimelineSummary";
import ToolsOptionNumber from "./ToolsOptionNumber";
import {pacificToday} from "../lib/pipeline-timeline";
import {sourceReviewHint,type RegistryCoverage} from "../lib/registry-benefit-coverage";
import {TOOLS_CLEAR_EVENT,TOOLS_STEP4_STORAGE_KEY,readToolsPreference,saveToolsPreference}
  from "../lib/tools-selection-persistence";
type Props={
  rows:ToolsSpreadsheetRow[];
  hasSelection:boolean;
  total:number;
  offset:number;
  loading:boolean;
  error:string;
  benefitFeed:BenefitFeed|null;
  benefitError:string;
};
const STEP4_SECTIONS=[
  {code:"4A",short:"Patients",label:"Patient opportunity",start:1,end:2},
  {code:"4B",short:"Clinical",label:"Clinical and competitive benefits",start:3,end:8},
  {code:"4C",short:"Access",label:"Access and commercial opportunity",start:9,end:14},
  {code:"4D",short:"Revenue",label:"Revenue and long-term value",start:15,end:18},
  {code:"4E",short:"Stock",label:"Stock appreciation and risk",start:19,end:20},
] as const;
type AssessmentMode="category"|"priority"|"clinical"|"all";
const PRIORITY_RESEARCH=[3,6,8,1,2,12,15,19,20] as const;
/** Navigation emphasis only: not a trained stock-appreciation ranking or investment score. */
const MODE_LABELS:{key:AssessmentMode;label:string}[]=[
  {key:"category",label:"Categories"},
  {key:"priority",label:"Investment focus"},
  {key:"clinical",label:"Medical benefits"},
  {key:"all",label:"All 20"},
];
const missing="Not assessed";
const short=(value?:string)=>value?.trim()||"Not recorded";
function FieldValue({record,id}:{record:BenefitRecord|null;id:string}){
  const fact=record?.facts[id];
  if(!fact)return <span className={css.pending}>{missing}</span>;
  return <details className={css.fieldDetail}>
    <summary>{String(fact.value)}{fact.status==="MODELED"?" (modeled)":""}</summary>
    <p><strong>Evidence status:</strong> {fact.status==="VERIFIED"?"Source-verified":"Modeled scenario"} · Confidence: {fact.confidence}</p>
    <p><strong>Method:</strong> {fact.method}</p>
    <p><strong>Source date:</strong> {fact.sourceDate} · <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Open evidence</a></p>
  </details>;
}
function RankedList({list,empty}:{list:BenefitAdvantage[];empty:string}){
  if(!list.length)return <p className={css.pending}>{empty}</p>;
  return <ol className={css.advList}>{list.map(a=><li key={a.id}>
    <strong>{a.title}</strong>
    <p><strong>Compared with:</strong> {a.comparator}</p>
    <p><strong>Measured difference:</strong> {a.comparison}</p>
    <p><strong>Evidence:</strong> {a.status==="VERIFIED"?"Source-verified":"Modeled"} · {a.confidence} confidence</p>
    <details><summary>Method &amp; source</summary>
      <p>{a.method}</p>
      <p>{a.sourceDate} · <a href={a.sourceUrl} target="_blank" rel="noopener noreferrer">Supporting source</a></p>
    </details>
  </li>)}</ol>;
}
function GroupAdvantage({record,group}:{record:BenefitRecord|null;group:BenefitGroup}){
  const ranked=rankAdvantages(record,group.number);
  return <details className={css.advDetail}>
    <summary>{ranked.length?ranked.length+" ranked advantage"+(ranked.length===1?"":"s"):"Not assessed"}</summary>
    <RankedList list={ranked} empty="No comparator-specific, verified competitive advantage ranking is available for this assessment."/>
  </details>;
}
export default function ToolsBenefitMatrix({rows,hasSelection,total,offset,loading,error,benefitFeed:feed,benefitError:feedError}:Props){
  const [registryCoverage,setRegistryCoverage]=useState<RegistryCoverage|null>(null);
  const [registryError,setRegistryError]=useState(false);
  const [active,setActive]=useState(1);
  const [mode,setMode]=useState<AssessmentMode>("category");
  const [chosen,setChosen]=useState("");
  const [selectionsRestored,setSelectionsRestored]=useState(false);
  const [today,setToday]=useState("");
  useEffect(()=>{
    const raw=readToolsPreference(TOOLS_STEP4_STORAGE_KEY);
    if(raw&&typeof raw==="object"&&!Array.isArray(raw)){
      const saved=raw as Record<string,unknown>;
      const nextMode:AssessmentMode=saved.mode==="category"||saved.mode==="priority"||
        saved.mode==="clinical"||saved.mode==="all"?saved.mode:"category";
      let nextActive=typeof saved.active==="number"&&Number.isInteger(saved.active)&&
        saved.active>=1&&saved.active<=20?saved.active:1;
      if(nextMode==="priority"&&!PRIORITY_RESEARCH.some(n=>n===nextActive))nextActive=PRIORITY_RESEARCH[0];
      if(nextMode==="clinical"&&(nextActive<3||nextActive>8))nextActive=3;
      setMode(nextMode);
      setActive(nextActive);
      if(typeof saved.chosen==="string"&&/^NCT\d{8}$/.test(saved.chosen))setChosen(saved.chosen);
    }
    setSelectionsRestored(true);
  },[]);
  useEffect(()=>{
    if(!selectionsRestored)return;
    saveToolsPreference(TOOLS_STEP4_STORAGE_KEY,{mode,active,chosen});
  },[mode,active,chosen,selectionsRestored]);
  useEffect(()=>{
    if(typeof window==="undefined")return;
    const clear=()=>{setMode("category");setActive(1);setChosen("");};
    window.addEventListener(TOOLS_CLEAR_EVENT,clear);
    return ()=>window.removeEventListener(TOOLS_CLEAR_EVENT,clear);
  },[]);
  useEffect(()=>{const update=()=>setToday(pacificToday());update();const timer=setInterval(update,60000);return ()=>clearInterval(timer);},[]);
  const scrollRegion=useRef<HTMLDivElement|null>(null);
  const groupHeaders=useRef<Record<number,HTMLTableCellElement|null>>({});
  useEffect(()=>{
    const region=scrollRegion.current,header=groupHeaders.current[active];
    if(!region||!header||window.matchMedia("(max-width:800px)").matches)return;
    const left=header.offsetLeft-region.clientWidth/3;
    region.scrollTo({left:Math.max(0,left),behavior:"smooth"});
  },[active]);
  useEffect(()=>{
    const controller=new AbortController();
    void fetch("/api/registry-benefit-coverage",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error("Source archive not current");
        const raw=await response.json() as RegistryCoverage;
        if(raw.schemaVersion!==1||raw.scanned!==375||!Array.isArray(raw.records))
          throw Error("Source coverage shape invalid");
        return raw;
      }).then(data=>{if(!controller.signal.aborted)setRegistryCoverage(data);})
      .catch(()=>{if(!controller.signal.aborted)setRegistryError(true);});
    return ()=>controller.abort();
  },[]);
  const sourceIndex=useMemo(()=>new Map(registryCoverage?.records.map(x=>[x.nctId,x])||[]),[registryCoverage]);
  const current=BENEFIT_GROUPS[active-1];
  const selectedSection=STEP4_SECTIONS.find(section=>active>=section.start&&active<=section.end)!;
  const modeChoices=mode==="category"
    ?BENEFIT_GROUPS.filter(g=>g.number>=selectedSection.start&&g.number<=selectedSection.end)
    :mode==="clinical"?BENEFIT_GROUPS.filter(g=>g.number>=3&&g.number<=8)
    :mode==="priority"?PRIORITY_RESEARCH.map(n=>BENEFIT_GROUPS[n-1])
    :BENEFIT_GROUPS;
  function changeMode(next:AssessmentMode){
    setMode(next);
    if(next==="priority")setActive(PRIORITY_RESEARCH[0]);
    else if(next==="clinical")setActive(3);
  }
  const selected=rows.find(r=>r.nctId===chosen)||rows[0]||null;
  const evidence=selected?benefitForTrial(feed,selected):null;
  const sourceVerified=current.fields.filter(f=>evidence?.facts[f.id]?.status==="VERIFIED").length;
  const scenarioModeled=current.fields.filter(f=>evidence?.facts[f.id]?.status==="MODELED").length;
  const notAssessedCount=Math.max(0,current.fields.length-sourceVerified-scenarioModeled);
  const overall=rankAdvantages(evidence);
  const selectedSourceHint=selected?sourceReviewHint(sourceIndex.get(selected.nctId),active):null;
  const studied=(record:BenefitRecord|null,group:BenefitGroup)=>
    !!record&&(group.fields.some(f=>record.facts[f.id])||record.advantages.some(a=>a.assessment===group.number));
  const researched=useMemo(()=>rows.filter(r=>benefitForTrial(feed,r)).length,[feed,rows]);
  return <section className={css.root} id="tools-benefit-assessments" aria-label="Resultant Trials — 20 competitive benefit assessments">
    <div className={css.intro}>
      <h3>Step 4 · Trial Assessments <span className={css.inlineCount}>20 metrics · {loading?"Loading":error?"Evidence unavailable":total.toLocaleString("en-US")+" matching trials"}</span></h3>
    </div>
    <div className={css.modeBar} role="group" aria-label="Step 4 organization mode">
      {MODE_LABELS.map(item=><button key={item.key} type="button"
        className={mode===item.key?css.modeActive:css.modeButton}
        aria-pressed={mode===item.key}
        onClick={()=>changeMode(item.key)}>{item.label}</button>)}
    </div>
    <div className={css.step4Compact} aria-label="Step 4 compact assessment controls">
      <div className={css.step4CategoryPanel}>
        <div className={css.step4CategoryHeading}>
          <strong>Five assessment categories</strong>
          <span>Select a category to see its assessments below.</span>
        </div>
        <div className={css.step4GroupButtons} role="group" aria-label="Step 4 five assessment groups">
          {STEP4_SECTIONS.map(section=><button type="button" key={section.code}
            className={mode==="category"&&selectedSection.code===section.code?css.step4GroupActive:css.step4GroupButton}
            aria-pressed={mode==="category"&&selectedSection.code===section.code}
            title={section.label+" · 4a"+section.start+"–4a"+section.end}
            onClick={()=>{setMode("category");setActive(section.start);}}>
            <span>{section.code} · {section.short}</span>
            <small>4a{section.start}–4a{section.end}</small>
          </button>)}
        </div>
      </div>
      <div className={css.step4MetricPicker}>
        <label htmlFor="benefit-group-picker">Assessment</label>
        <select id="benefit-group-picker" aria-label="Step 4 assessment 4a1 through 4a20"
          value={active} onChange={e=>setActive(Number(e.target.value))}>
          {modeChoices.map(g=><option value={g.number} key={g.number}>4a{g.number} — {g.name}</option>)}
        </select>
      </div>
    </div>
    {mode==="priority"&&<p className={css.modeHint}>Research-first shortlist only; order is not a proven return forecast or a stock buy ranking.</p>}
    <p className={css.evidenceSummary} aria-live="polite">
      <strong>4a{active} · {current.name}</strong> · {loading?"Loading matching trials":error?"Trial evidence unavailable"
        :!selected?"No matching NCT on this page"
        :feedError?"Assessment source unavailable"
        :!feed?"Assessment source loading"
        :sourceVerified+" / "+current.fields.length+" research fields source-verified"+(scenarioModeled?" · "+scenarioModeled+" modeled":"")}
    </p>
    <details className={css.fullAssessmentList} id="tools-step4-all20">
      <summary>All 20 assessments · optional full numbered list</summary>
      <div className={css.fullAssessmentGrid} role="group" aria-label="Complete separate Step 4 assessment list 1 through 20">
        {BENEFIT_GROUPS.map(g=><button type="button" key={g.number}
          className={active===g.number?css.fullAssessmentSelected:css.fullAssessmentItem}
          aria-pressed={active===g.number}
          aria-label={"Assessment "+g.number+" of 20 — "+g.name}
          onClick={event=>{setActive(g.number);setMode("all");event.currentTarget.closest("details")?.removeAttribute("open");}}>
          <span className={css.fullAssessmentNumber}>{g.number}</span>
          <span>4a{g.number} · {g.name}</span>
        </button>)}
      </div>
    </details>
    <details className={css.researchDisclosure} id="tools-step4-analysis">
      <summary>View analysis · 4a{active} — {current.name}</summary>
    <div className={css.notice}>
      <strong>Source integrity:</strong> Trials appear only after selecting a clinical stage or FDA designation. These are NCT study records, not yet reconciled distinct drug–indication programs. A Phase 3 screening match is not final Pipeline qualification. Source facts populate when available; research not completed remains <strong>Not assessed</strong>. Unverified superiority is never ranked as proven.
      {feedError&&<p role="alert">{feedError}</p>}
      {registryCoverage&&<p role="status"><strong>Official registry research archive:</strong> {registryCoverage.scanned} historical completed NCTs checked · {registryCoverage.postedResults} with posted results · {registryCoverage.withPrimaryMeasurements} with primary outcome measurements · {registryCoverage.withSeriousEventCounts} with serious-event counts. Last collected {registryCoverage.sourceAsOf.slice(0,10)}. These are source availability counts, not verified clinical advantages.</p>}
      {registryError&&<p role="status">Dated registry source coverage is unavailable or expired. No benefit conclusions are inferred.</p>}
      {feed&&!feedError&&<p>Evidence-backed assessments attached to current page: {researched} of {rows.length} NCT records. Missing evidence does not mean the drug has no advantage.</p>}
    </div>
    {!hasSelection?<div className={css.empty} role="status">0 matching trials. Select at least one clinical stage or FDA designation above to populate the assessment spreadsheet.</div>:
      loading?<div className={css.empty} role="status">Loading source-matched resultant trials…</div>:
      error?<div className={css.empty} role="alert">Trial evidence unavailable. Assessment rows have not been asserted.</div>:
      rows.length===0?<div className={css.empty} role="status">
        <p>{total?"No records on this page. Use spreadsheet pagination below.":"No source-linked NCT trial records match these selected filters. This does not prove there are no eligible therapies."}</p>
      </div>:<>
      <div className={css.ratingNavigator} role="group" aria-label="Browse assessment ratings horizontally">
        <button type="button" disabled={active===1} onClick={()=>setActive(n=>Math.max(1,n-1))}>← Previous rating</button>
        <span className={css.ratingNavLabel}>
          <strong>4a{active} · {current.name}</strong>
          <small>{notAssessedCount} of {current.fields.length} fields not assessed for {selected?.nctId}</small>
        </span>
        <button type="button" disabled={active===20} onClick={()=>setActive(n=>Math.min(20,n+1))}>Next rating →</button>
      </div>
      <div className={css.desktop} ref={scrollRegion} role="region" aria-label="Desktop horizontally scrollable 20-assessment spreadsheet" tabIndex={0}>
        <table className={css.matrixTable}>
          <thead>
            <tr><th className={css.identityHeading} colSpan={4} scope="colgroup">PROGRAM / NCT IDENTIFICATION</th>
              {BENEFIT_GROUPS.map(g=><th key={g.number} ref={node=>{groupHeaders.current[g.number]=node;}} colSpan={active===g.number?g.fields.length+2:1}
                className={active===g.number?css.activeHeading:css.groupHeading} scope="colgroup">
                <button type="button" aria-pressed={active===g.number} onClick={()=>setActive(g.number)}><ToolsOptionNumber level={1} index={g.number-1} total={BENEFIT_GROUPS.length}/> #{g.number} — {g.name} {active===g.number?"▴":"▾"}</button>
              </th>)}
            </tr>
            <tr>
              <th className={css.pin1}>#</th><th className={css.pin2}>Ticker / NCT</th>
              <th className={css.pin3}>Drug / therapy</th><th className={css.pin4}>Indication</th>
              {BENEFIT_GROUPS.map(g=>active===g.number
                ?g.fields.map((f,index)=><th key={f.id} className={css.selectedGroupCell+(index===0?" "+css.selectedFirst:"")}>{f.label}</th>).concat([
                  <th key={"rank"+g.number} className={css.selectedGroupCell}>Ranked advantages</th>,
                  <th key={"status"+g.number} className={css.selectedGroupCell+" "+css.selectedLast}>Evidence status</th>
                ])
                :<th key={"closed"+g.number}>Assessment status</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row,i)=>{
              const record=benefitForTrial(feed,row);
              return <tr key={row.id}>
                <td className={css.pin1}>{offset+i+1}</td>
                <td className={css.pin2}><strong>{short(row.ticker)}</strong><TrialTimelineSummary timeline={row.timeline} today={today} compact trial={row} benefitFeed={feed}/><a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(row.nctId)} target="_blank" rel="noopener noreferrer">{row.nctId}</a></td>
                <td className={css.pin3}>{short(row.drug)}</td><td className={css.pin4}>{short(row.indication)}</td>
                {BENEFIT_GROUPS.map(g=>active===g.number
                  ?[...g.fields.map((f,index)=><td key={f.id} className={css.selectedGroupCell+(index===0?" "+css.selectedFirst:"")}><FieldValue record={record} id={f.id}/></td>),
                    <td key={"rank"+g.number} className={css.selectedGroupCell}><GroupAdvantage record={record} group={g}/></td>,
                    <td key={"status"+g.number} className={css.selectedGroupCell+" "+css.selectedLast}>{studied(record,g)?"Assessment evidence recorded":sourceReviewHint(sourceIndex.get(row.nctId),g.number)||"Not assessed"}</td>]
                  :<td key={"closed"+g.number}><button type="button" className={css.statusButton} onClick={()=>setActive(g.number)}>{studied(record,g)?"Assessment evidence available":sourceReviewHint(sourceIndex.get(row.nctId),g.number)?"Registry data · review required":"Not assessed"} ▾</button></td>)}
              </tr>;
            })}
          </tbody>
        </table>
      </div>
      <div className={css.mobile}>
        <div className={css.mobilePicker}>
          <label htmlFor="benefit-trial-picker">Select a resultant trial</label>
          <select id="benefit-trial-picker" value={selected?.nctId||""} onChange={e=>setChosen(e.target.value)}>
            {rows.map(row=><option key={row.id} value={row.nctId}>{short(row.ticker)} · {row.nctId} · {short(row.drug)}</option>)}
          </select>
          {selected&&<div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:8}}>
            <strong>{short(selected.ticker)}</strong>
            <TrialTimelineSummary timeline={selected.timeline} today={today} compact trial={selected} benefitFeed={feed}/>
          </div>}
          <p className={css.subline}>{selected?short(selected.drug)+" · "+short(selected.indication):""}</p>
        </div>
        <details className={css.overall} open={undefined}>
          <summary>Overall drug competitive ranking</summary>
          <div className={css.detailBody}>
            <RankedList list={overall} empty="No evidence-reviewed overall drug ranking has been established for this exact drug–indication / NCT identity."/>
          </div>
        </details>
        <div className={css.groupMobile} aria-label={"Selected rating and right-hand ingredients for assessment "+active}>
          <div className={css.mobileGroupTitle}>
            <small>RATING {active} OF 20</small>
            <h4><ToolsOptionNumber level={1} index={active-1} total={BENEFIT_GROUPS.length}/> #{active} — {current.name}</h4>
            <p className={css.mobileMissing}><strong>{notAssessedCount} / {current.fields.length}</strong> fields not assessed</p>
            <small className={css.horizontalCue}>Ingredients →</small>
          </div>
          <div className={css.mobileIngredients}>
            <div className={css.fieldScroll} role="region" aria-label={"Scroll right through assessment "+active+" ingredient fields"} tabIndex={0}>
              <table className={css.mobileTable}>
                <thead><tr>{current.fields.map(f=><th key={f.id}>{f.label}</th>)}</tr></thead>
                <tbody><tr>{current.fields.map(f=><td key={f.id}><FieldValue record={evidence} id={f.id}/></td>)}</tr></tbody>
              </table>
            </div>
            <p className={css.swipeCue}>Swipe across the ingredient fields →</p>
            {selectedSourceHint&&<p className={css.sourceHint}><strong>Official registry source:</strong> {selectedSourceHint}. Source data requires assessment before a benefit rating is assigned.</p>}
            <details className={css.mobileAdv}>
              <summary>Ranked competitive advantages</summary>
              <div className={css.detailBody}><RankedList list={rankAdvantages(evidence,active)} empty="Not assessed. A comparator-specific, evidence-reviewed advantage ranking is not yet available."/></div>
            </details>
            <details className={css.mobileAdv}>
              <summary>Trial identity &amp; source</summary>
              <div className={css.detailBody}>
                <p>Source NCT: <a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(selected!.nctId)} target="_blank" rel="noopener noreferrer">{selected!.nctId}</a></p>
                <p>Company: {short(selected!.company)} · Recorded stage: {short(selected!.stage)}</p>
                <p>Drug–indication identity is source-reported and requires program-level verification before combining multiple NCTs.</p>
              </div>
            </details>
          </div>
        </div>
        <div className={css.next}>
          <button type="button" disabled={active===1} onClick={()=>setActive(v=>v-1)}>← Previous</button>
          <span>{active} / 20</span>
          <button type="button" disabled={active===20} onClick={()=>setActive(v=>v+1)}>Next →</button>
        </div>
        <p className={css.subline}>Showing records {offset+1}–{offset+rows.length} of {total}. Use the existing results pagination below to browse more trials.</p>
      </div>
      <div className={css.overallDesktop}>
        <details><summary>Overall drug advantage rankings (selected trial)</summary>
          <div className={css.mobilePicker}>
            <label htmlFor="benefit-desktop-trial">Study</label>
            <select id="benefit-desktop-trial" value={selected?.nctId||""} onChange={e=>setChosen(e.target.value)}>
              {rows.map(row=><option key={row.id} value={row.nctId}>{short(row.ticker)} · {row.nctId} · {short(row.drug)} · {short(row.indication)}</option>)}
            </select>
          </div>
          <RankedList list={overall} empty="No evidence-reviewed overall ranking has been established for this exact trial and drug–indication identity."/>
        </details>
      </div>
      {selected&&<RegistryBenefitEvidence nctId={selected.nctId} assessment={active}/>}
    </>}
    <p className={css.footer}>Automatic: filter-matched NCT identities, available vetted assessment fields, and official registry outcome/safety source packets for the selected trial. A scheduled collection job refreshes the historical completed-study source archive. These records are research inputs, not verified competitive superiority. Independent evidence for all 20 assessment categories and overall drug rankings remains incomplete; unsupported entries continue to show Not assessed.</p>
    </details>
  </section>;
}
