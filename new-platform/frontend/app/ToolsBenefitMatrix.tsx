"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import {BENEFIT_GROUPS,benefitForTrial,rankAdvantages,type BenefitFeed,type BenefitRecord,type BenefitAdvantage,type BenefitGroup} from "../lib/benefit-assessments";
import type {ToolsSpreadsheetRow} from "./ToolsResultsSpreadsheet";
import css from "./ToolsBenefitMatrix.module.css";
import RegistryBenefitEvidence from "./RegistryBenefitEvidence";
import TrialTimelineSummary from "./TrialTimelineSummary";
import ToolsOptionNumber from "./ToolsOptionNumber";
import {toolsOptionCode} from "../lib/tools-option-code";
import {pacificToday} from "../lib/pipeline-timeline";
import {sourceReviewHint,type RegistryCoverage} from "../lib/registry-benefit-coverage";
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
  const [chosen,setChosen]=useState("");
  const [today,setToday]=useState("");
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
  const selected=rows.find(r=>r.nctId===chosen)||rows[0]||null;
  const evidence=selected?benefitForTrial(feed,selected):null;
  const overall=rankAdvantages(evidence);
  const selectedSourceHint=selected?sourceReviewHint(sourceIndex.get(selected.nctId),active):null;
  const studied=(record:BenefitRecord|null,group:BenefitGroup)=>
    !!record&&(group.fields.some(f=>record.facts[f.id])||record.advantages.some(a=>a.assessment===group.number));
  const researched=useMemo(()=>rows.filter(r=>benefitForTrial(feed,r)).length,[feed,rows]);
  return <section className={css.root} id="tools-benefit-assessments" aria-label="Resultant Trials — 20 competitive benefit assessments">
    <div className={css.intro}>
      <div><p className={css.eyebrow}>RESULTANT TRIALS · COMPETITIVE RESEARCH</p>
        <h3>20 Benefit Assessments</h3>
        <p>Filtered trials populate automatically from your selections. Every numbered heading sits above its own subcolumns. Open any group to see source-backed findings and strongest-to-weakest comparator advantages.</p>
      </div>
      <div className={css.count}><strong>{hasSelection?(loading||error?"—":total.toLocaleString("en-US")):"0"}</strong><span>selected NCT trial records</span></div>
    </div>
    <div className={css.notice}>
      <strong>Source integrity:</strong> Trials appear only after selecting a clinical stage or FDA designation. These are NCT study records, not yet reconciled distinct drug–indication programs. A Phase 3 screening match is not final Pipeline qualification. Source facts populate when available; research not completed remains <strong>Not assessed</strong>. Unverified superiority is never ranked as proven.
      {feedError&&<p role="alert">{feedError}</p>}
      {registryCoverage&&<p role="status"><strong>Official registry research archive:</strong> {registryCoverage.scanned} historical completed NCTs checked · {registryCoverage.postedResults} with posted results · {registryCoverage.withPrimaryMeasurements} with primary outcome measurements · {registryCoverage.withSeriousEventCounts} with serious-event counts. Last collected {registryCoverage.sourceAsOf.slice(0,10)}. These are source availability counts, not verified clinical advantages.</p>}
      {registryError&&<p role="status">Dated registry source coverage is unavailable or expired. No benefit conclusions are inferred.</p>}
      {feed&&!feedError&&<p>Evidence-backed assessments attached to current page: {researched} of {rows.length} NCT records. Missing evidence does not mean the drug has no advantage.</p>}
    </div>
    <div className={css.actions}>
      <label htmlFor="benefit-group-picker">Choose assessment (20 options)</label>
      <ToolsOptionNumber level={1} index={active-1} total={BENEFIT_GROUPS.length}/>
      <select id="benefit-group-picker" value={active} onChange={e=>setActive(Number(e.target.value))}>
        {BENEFIT_GROUPS.map(g=><option value={g.number} key={g.number}>{toolsOptionCode(1,g.number-1,BENEFIT_GROUPS.length)} · #{g.number} — {g.name}</option>)}
      </select>
    </div>
    {!hasSelection?<div className={css.empty} role="status">0 matching trials. Select at least one clinical stage or FDA designation above to populate the assessment spreadsheet.</div>:
      loading?<div className={css.empty} role="status">Loading source-matched resultant trials…</div>:
      error?<div className={css.empty} role="alert">Trial evidence unavailable. Assessment rows have not been asserted.</div>:
      rows.length===0?<div className={css.empty} role="status">
        <p>{total?"No records on this page. Use spreadsheet pagination below.":"No source-linked NCT trial records match these selected filters. This does not prove there are no eligible therapies."}</p>
      </div>:<>
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
                ?g.fields.map(f=><th key={f.id}>{f.label}</th>).concat([
                  <th key={"rank"+g.number}>Ranked advantages</th>,
                  <th key={"status"+g.number}>Evidence status</th>
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
                  ?[...g.fields.map(f=><td key={f.id}><FieldValue record={record} id={f.id}/></td>),
                    <td key={"rank"+g.number}><GroupAdvantage record={record} group={g}/></td>,
                    <td key={"status"+g.number}>{studied(record,g)?"Assessment evidence recorded":sourceReviewHint(sourceIndex.get(row.nctId),g.number)||"Not assessed"}</td>]
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
        <div className={css.groupMobile}>
          <div className={css.mobileGroupTitle}>
            <small>ASSESSMENT {active} OF 20</small><h4><ToolsOptionNumber level={1} index={active-1} total={BENEFIT_GROUPS.length}/> #{active} — {current.name}</h4>
          </div>
          {selectedSourceHint&&<p className={css.sourceHint}><strong>Official registry source:</strong> {selectedSourceHint}. See the expandable original-source evidence section below. Assessment conclusions remain Not assessed until reviewed.</p>}
          <div className={css.fieldScroll} role="region" aria-label={"Assessment "+active+" subcolumns"} tabIndex={0}>
            <table className={css.mobileTable}>
              <thead><tr>{current.fields.map(f=><th key={f.id}>{f.label}</th>)}</tr></thead>
              <tbody><tr>{current.fields.map(f=><td key={f.id}><FieldValue record={evidence} id={f.id}/></td>)}</tr></tbody>
            </table>
          </div>
          <details className={css.mobileAdv}>
            <summary>Competitive advantages · strongest first</summary>
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
  </section>;
}
