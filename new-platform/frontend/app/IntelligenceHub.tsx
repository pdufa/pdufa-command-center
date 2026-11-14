"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import Link from "next/link";
import CalCalendar from "./CalCalendar";
import {APPLICATION_CYCLES} from "../lib/medical-intelligence-applications";
import styles from "./IntelligenceHub.module.css";

type View="cal"|"company"|"news";
type Layout="single"|"dual"|"all";
type ResearchPrediction={cycleId:string;call:"APPROVAL_LEAN"|"CRL_LEAN"|"ABSTAIN"|"ALREADY_APPROVED";
  label:string;level:number;asOf:string;independentlyValidated:false;calibratedProbability:null;
  clinicalRationale:string;benefitRiskRationale:string;fdaCmcRationale:string;
  evidenceGap:string;sourceUrl:string;evidenceUrl:string;};
type CalendarEvent={id:string;ticker:string;company:string;date:string;drug:string;marketCapUsd:number;
  ncts:string[];sourceUrl:string|null;cycleId?:string|null;prediction?:ResearchPrediction|null;dateStatus?:string};
type UndatedCycle={id:string;ticker:string;company:string;marketCapUsd:number;ncts:string[];
  prediction:ResearchPrediction;date:null;dateStatus:string};
type ClinicalPhaseRow={nct:string;ticker:string;phase:string[]|null;registryStatus:string|null;
  sourceStatus:"OFFICIAL_REGISTRY_RETRIEVED"|"OFFICIAL_SOURCE_UNAVAILABLE";
  registryUpdated:string|null;sourceUrl:string};
type ClinicalPhasePayload={checkedAt:string;ageStatus:"RECENT"|"STALE";
  records:ClinicalPhaseRow[]};
const phaseLabel=(phases:string[]|null)=>!phases||phases.length===0?"Phase not reported":
  phases.includes("PHASE2")&&phases.includes("PHASE3")?"Phase 2/3":
  phases.map(p=>p==="EARLY_PHASE1"?"Early Phase 1":
    p==="NA"?"Not applicable":p.replace("PHASE","Phase ")).join(" · ");
const registryStatusLabel=(status:string|null)=>status?
  status.toLowerCase().replaceAll("_"," "):"Registry status unavailable";
type NewsEntry={id:string;title:string;publishedAt:string|null;sourceUrl:string;sourceName:string;
  kind:"FDA_ARTICLE"|"APPLICATION_SOURCE_RECORD";ticker:string|null;cycleId:string|null;drug:string|null;
  ncts:string[];verification:"OFFICIAL_FDA_PUBLICATION"|"SOURCE_LINK_RECORDED";
  matchStatus:"UNREVIEWED_EXACT_DRUG_MENTION"|"NOT_MAPPED"|"CYCLE_SOURCE_RECORD";
  impact:"NOT_ASSESSED";description:string};
type NewsPayload={feedStatus:string;fetchedAt:string;articles:NewsEntry[];records:NewsEntry[];note:string};
type AutomationStatus={state:string;baselineAt?:string|null;lastCheckedAt?:string|null;
  statuses?:Record<string,number>;note?:string};
const date=(s:string|null|undefined)=>s?new Date(s.length===10?s+"T12:00:00Z":s).toLocaleDateString("en-US",
  {year:"numeric",month:"short",day:"numeric",timeZone:"UTC"}):"Not recorded";
const cap=(n:number)=>n>=1e9?"$"+(n/1e9).toFixed(2)+"B":"$"+Math.round(n/1e6)+"M";
const validTicker=(s:string)=>/^[A-Z0-9.-]{1,10}$/.test(s);
const kinds={cal:"CAL",company:"COMPANY",news:"NEWS"} as const;
function CompanyDetails({ticker,calendar,undated,clinicalPhases,phaseCheckedAt,phaseAgeStatus,
  phaseLoadState,cycleId,onCycle,onNews,onCal}:{ticker:string;
  calendar:CalendarEvent[];undated:UndatedCycle[];
  clinicalPhases:ClinicalPhaseRow[];phaseCheckedAt:string|null;
  phaseAgeStatus:"RECENT"|"STALE"|null;phaseLoadState:"LOADING"|"AVAILABLE"|"UNAVAILABLE";
  cycleId:string;onCycle:(id:string)=>void;onNews:()=>void;onCal:()=>void}){
  const events=calendar.filter(e=>e.ticker===ticker).sort((a,b)=>a.date.localeCompare(b.date));
  const pending=undated.filter(e=>e.ticker===ticker);
  const cycles=APPLICATION_CYCLES.filter(c=>c.ticker===ticker);
  const profile=events[0]||pending[0];
  const nowParts=new Intl.DateTimeFormat("en-US",{timeZone:"America/Los_Angeles",
    year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const nowPart=(type:string)=>nowParts.find(part=>part.type===type)?.value||"01";
  const now=nowPart("year")+"-"+nowPart("month")+"-"+nowPart("day");
  const next=events.find(e=>e.date>=now && e.prediction?.call!=="ALREADY_APPROVED");
  const phaseByNct=new Map(clinicalPhases.map(t=>[t.nct,t]));
  const nextCandidates=cycles.filter(c=>c.stage!=="APPROVED_ALREADY" &&
    (!c.reportedGoal||c.reportedGoal>=now)).sort((a,b)=>
    (a.reportedGoal===null?1:0)-(b.reportedGoal===null?1:0) ||
    (a.reportedGoal||"").localeCompare(b.reportedGoal||"") || a.drug.localeCompare(b.drug));
  const completedOrPast=cycles.length-nextCandidates.length;
  const current=cycles.find(c=>c.id===cycleId)||nextCandidates[0]||cycles[0];
  const currentResearch=events.find(e=>e.cycleId===current?.id)?.prediction ||
    pending.find(e=>e.id===current?.id)?.prediction || null;
  return <div className={styles.companyDetails}>
    {!ticker?<p>Select a ticker from CAL to view the company and all recorded application cycles.</p>:<>
      <h2>{ticker} <span className={styles.companyName}>{profile?.company||ticker}</span></h2>
      <div className={styles.summary}>
        <div><small>Market cap · source snapshot</small><strong>{profile?cap(profile.marketCapUsd):"Not published"}</strong></div>
        <div><small>Next published PDUFA</small><strong>{next?date(next.date):"No future target recorded"}</strong></div>
        <div><small>Recorded application cycles</small><strong>{cycles.length}</strong></div>
      </div>
      <section className={styles.nextCandidates} aria-label="Next PDUFA candidates and clinical phases">
        <div className={styles.nextCandidatesHeader}>
          <h3>Next PDUFA candidates <small>({nextCandidates.length} FOCUS application cycles)</small></h3>
          <p>Tracked FOCUS candidates only · next source-reported FDA targets first,
            then applications without assigned PDUFA dates.</p>
        </div>
        {phaseLoadState==="AVAILABLE"?
          <p className={styles.phaseStamp}>Clinical phase source: ClinicalTrials.gov,
            checked {date(phaseCheckedAt)}{phaseAgeStatus==="STALE"?
              " · STALE (older than 72 hours)":""}.</p>:
          <p className={styles.phaseStamp}>Clinical phase records {
            phaseLoadState==="LOADING"?"loading":"unavailable; not inferred"}.</p>}
        {nextCandidates.length===0&&<p className={styles.caveat}>
          No upcoming or undated candidate application is recorded for this company in FOCUS.
          This does not establish that the company has no other pipeline programs.
        </p>}
        <div className={styles.candidateList}>
          {nextCandidates.map((c,i)=>{
            const research=events.find(e=>e.cycleId===c.id)?.prediction||
              pending.find(e=>e.id===c.id)?.prediction;
            return <article className={styles.candidateCard} key={c.id}>
              <button className={styles.candidateChoose} type="button"
                aria-pressed={current?.id===c.id} onClick={()=>onCycle(c.id)}>
                <strong>{i===0?"NEXT · ":""}{c.drug}</strong>
                <span>{c.indication}</span>
              </button>
              <div className={styles.candidateMeta}>
                <div><small>Next PDUFA goal</small><strong>{
                  c.reportedGoal?date(c.reportedGoal):"Not assigned"}</strong></div>
                <div><small>FDA application stage</small><strong>{
                  c.stage.replaceAll("_"," ").toLowerCase()} · {c.applicationType}</strong></div>
                <div><small>Preliminary Level 3</small><strong>{
                  research?.label||"No research call recorded"}</strong></div>
              </div>
              <div className={styles.candidatePhases}>
                <strong>Clinical trial phases</strong>
                {c.ncts.map(nct=>{
                  const entry=phaseByNct.get(nct);
                  const verified=phaseLoadState==="AVAILABLE" &&
                    entry?.sourceStatus==="OFFICIAL_REGISTRY_RETRIEVED";
                  return <div key={nct} className={styles.phaseRow}>
                    <a href={"https://clinicaltrials.gov/study/"+nct}
                      target="_blank" rel="noopener noreferrer">{nct}</a>
                    <b>{verified?phaseLabel(entry.phase):"Unverified / unavailable"}</b>
                    <small>{verified?registryStatusLabel(entry.registryStatus):
                      "No current verified registry phase"}</small>
                  </div>;
                })}
              </div>
              <button className={styles.candidateDetailLink} type="button"
                onClick={()=>onCycle(c.id)}>View application assessment and source details</button>
            </article>;
          })}
        </div>
        <p className={styles.caveat}>{completedOrPast>0?
          completedOrPast+" past-goal or already-approved cycle(s) are excluded from this upcoming list. ":""}
          Phase 3 clinical evidence is not an FDA filing stage or an assigned PDUFA date.
          Company pipeline programs outside FOCUS are not asserted to be included.</p>
      </section>
      {cycles.length>1&&<label className={styles.cycleSelector}>Drug / indication — choose exact FDA cycle
        <select value={current?.id||""} onChange={e=>onCycle(e.target.value)}>
          {cycles.map(c=><option key={c.id} value={c.id}>{c.drug} · {c.indication}</option>)}
        </select>
      </label>}
      {current&&<section className={styles.cycle}>
        <strong className={styles.subhead}>Selected application · {current.applicationType}</strong>
        <h3>{current.drug}</h3>
        <p><strong>Indication:</strong> {current.indication}</p>
        <p><strong>Application status:</strong> {current.stage.replaceAll("_"," ")} · sponsor / source reported</p>
        <p><strong>Reported FDA goal:</strong> {date(current.reportedGoal)}</p>
        <p><strong>Linked NCTs:</strong> {current.ncts.map((nct,i)=><span key={nct}>
          {i?", ":""}<a href={"https://clinicaltrials.gov/study/"+nct} target="_blank" rel="noopener noreferrer">{nct}</a>
          {" · "}<Link href={"/analyze-now?nct="+nct}>Saved revision history</Link>{" · "}<Link href={"/predictions/assessment?nct="+nct}>Levels 1–6 assessments</Link>
        </span>)}</p>
        <p><strong>Scientific question:</strong> {current.criticalQuestion}</p>
        {currentResearch?<div className={styles.researchForecast}>
          <p><strong>Level {currentResearch.level} research prediction:</strong>{" "}
            <strong>{currentResearch.label}</strong> · frozen {date(currentResearch.asOf)}</p>
          <p><strong>Preliminary, not independently validated.</strong> No calibrated FDA
            approval probability or clinical review signoff is available.</p>
          <details><summary>Evidence, safety, regulatory risks and sources</summary>
            <p><strong>Clinical:</strong> {currentResearch.clinicalRationale}</p>
            <p><strong>Benefit-risk:</strong> {currentResearch.benefitRiskRationale}</p>
            <p><strong>FDA / CMC:</strong> {currentResearch.fdaCmcRationale}</p>
            <p><strong>Missing:</strong> {currentResearch.evidenceGap}</p>
            <p><a href={currentResearch.evidenceUrl} target="_blank" rel="noopener noreferrer">
              Clinical source</a>{" · "}
              <a href={currentResearch.sourceUrl} target="_blank" rel="noopener noreferrer">
                Application source</a></p>
          </details>
        </div>:<p className={styles.caveat}>No matched provisional research call is available
          for this exact FDA application cycle.</p>}
        <p><strong>Source dated:</strong> {date(current.sourceDate)} · <a href={current.sourceUrl} target="_blank" rel="noopener noreferrer">Original sponsor / SEC source</a></p>
        <p className={styles.caveat}>Cycle status is a source-linked research record, not FDA adjudication. No clinical outcome or approval probability is inferred.</p>
      </section>}
      <section className={styles.eventsBlock}>
        <h3>Published PDUFA timeline ({events.length})</h3>
        {events.length===0?<p>No published PDUFA dates for this issuer in the $300M–$10B feed.</p>:
          events.map(e=><article className={styles.dateRow} key={e.id}>
            <strong>{date(e.date)}</strong><span>{e.drug||"Drug not recorded"}
              {e.prediction&&<small> · L3 provisional: {e.prediction.label}</small>}</span>
            <small>{e.prediction?.call==="ALREADY_APPROVED"?
              "Already approved · not a pending FDA decision":
              e.id===next?.id?"Next recorded target":
              e.date<now?"Past target — outcome unverified":"Additional future target"}</small>
          </article>)}
      </section>
      <div className={styles.actions}>
        <button type="button" onClick={onNews}>Related NEWS</button>
        <button type="button" className={styles.outline} onClick={onCal}>Return to CAL</button>
        <Link href="/predictions">Prediction readiness</Link>
      </div>
      <p className={styles.caveat}>Prior prediction and evidence versions remain under exact-NCT history. A linked document alone does not trigger a validated FDA forecast.</p>
    </>}
  </div>;
}
function NewsDetails({payload,ticker,cycleId,newsFilter,setNewsFilter,automation,onSelectCompany}:{payload:NewsPayload|null;
  ticker:string;cycleId:string;newsFilter:string;setNewsFilter:(s:string)=>void;
  automation:AutomationStatus|null;onSelectCompany:(ticker:string,cycleId:string|null)=>void}){
  const [expanded,setExpanded]=useState<string|null>(null);
  const all=useMemo(()=>[...(payload?.articles||[]),...(payload?.records||[])], [payload]);
  const filtered=all.filter(x=>{
    if(newsFilter==="official")return x.kind==="FDA_ARTICLE";
    if(newsFilter==="documents")return x.kind==="APPLICATION_SOURCE_RECORD"&&(!ticker||x.ticker===ticker);
    return Boolean(ticker)&&x.ticker===ticker&&(!cycleId||x.cycleId===cycleId);
  }).sort((a,b)=>(b.publishedAt||"").localeCompare(a.publishedAt||""));
  return <section className={styles.newsDetails}>
    <header className={styles.newsTop}><h2>NEWS</h2><span className={styles.feedIndicator}>
      {payload?.feedStatus==="LIVE_FDA_RSS"?"FDA RSS available":"FDA live feed unavailable / loading"}</span></header>
    <p className={styles.intro}>Official FDA articles and source-linked issuer filings are displayed separately. A drug-name mention is <strong>not</strong> a verified application match or FDA outcome.</p>
    <div className={styles.monitor}><strong>Automatic evidence reassessment:</strong>{" "}
      {automation?.state==="RUNNING"?"FDA official-source watcher checked "+date(automation.lastCheckedAt):
       automation?.state==="NOT_ENABLED"?"Not enabled on durable backend":
       "Runtime not verified (sign-in / backend readiness may be required)"}
      <span> · Existing source-only worker · Prior revisions retained · FDA probabilities: ABSTAIN</span>
    </div>
    <label className={styles.feedSelect}>News scope
      <select value={newsFilter} onChange={e=>setNewsFilter(e.target.value)}>
        <option value="related">Selected company + application</option>
        <option value="documents">Company source documents</option>
        <option value="official">All official FDA RSS headlines</option>
      </select>
    </label>
    <p className={styles.counter}>{filtered.length} source-linked {filtered.length===1?"item":"items"}{ticker?" · "+ticker:""}</p>
    {!filtered.length&&<p className={styles.empty}>No matching sources in this feed. That does not mean no news exists; a company announcement may not yet be collected or verified.</p>}
    <div className={styles.newsList}>{filtered.slice(0,100).map(entry=><article key={entry.id} className={styles.newsCard}>
      <div className={styles.sourceRow}><span>{entry.kind==="FDA_ARTICLE"?"Official FDA article":"Recorded application source"}</span><small>{date(entry.publishedAt)}</small></div>
      <h3><a href={entry.sourceUrl} target="_blank" rel="noopener noreferrer">{entry.title}</a></h3>
      <p>{entry.description}</p>
      <p className={styles.meta}>{entry.sourceName} · {entry.ticker||"Not linked to a FOCUS company"}{entry.cycleId?" · "+entry.cycleId:""}</p>
      {entry.ticker&&entry.cycleId&&<button type="button" className={styles.companyJump}
        onClick={()=>onSelectCompany(entry.ticker!,entry.cycleId)}>
        Open {entry.ticker} COMPANY record ↗
      </button>}
      <div className={styles.verifiedLine}>
        <span>{entry.verification==="OFFICIAL_FDA_PUBLICATION"?"FDA-hosted publication":"Source link recorded, independently unverified"}</span>
        <span>{entry.matchStatus==="UNREVIEWED_EXACT_DRUG_MENTION"?"Automatic drug-name match — unreviewed":entry.matchStatus==="CYCLE_SOURCE_RECORD"?"Dated cycle source record":"No exact application linkage"}</span>
      </div>
      <button type="button" className={styles.expand} onClick={()=>setExpanded(expanded===entry.id?null:entry.id)}>
        {expanded===entry.id?"Hide impact details":"Source and impact details"} <span aria-hidden="true">{expanded===entry.id?"−":"+"}</span>
      </button>
      {expanded===entry.id&&<div className={styles.impact}>
        <p><strong>FDA effect:</strong> Not assessed. No decision, CRL or date revision is inferred.</p>
        <p><strong>Prediction:</strong> No verified prediction revision can be attributed to this article from the display feed. Existing versions remain immutable.</p>
        <p><strong>Linked trial IDs:</strong> {entry.ncts.length?entry.ncts.map(nct=><span key={nct}><Link href={"/predictions/assessment?nct="+nct}>{nct} assessments</Link>{" "}</span>):"None verified"}</p>
        <p><strong>Source:</strong> <a href={entry.sourceUrl} target="_blank" rel="noopener noreferrer">Inspect original document ↗</a></p>
      </div>}
    </article>)}</div>
    <p className={styles.caveat}>A source automatically linked by keyword needs exact-cycle and substantive-evidence validation before it is used for reassessment. The official article feed may be incomplete.</p>
  </section>;
}

export default function IntelligenceHub({initialView="cal"}:{initialView?:View}){
  const [view,setView]=useState<View>(initialView);
  const [layout,setLayout]=useState<Layout>("single");
  const [ticker,setTicker]=useState("");
  const [cycleId,setCycleId]=useState("");
  const [focusDate,setFocusDate]=useState("");
  const [focusKey,setFocusKey]=useState(0);
  const [calendar,setCalendar]=useState<CalendarEvent[]>([]);
  const [undated,setUndated]=useState<UndatedCycle[]>([]);
  const [phasePayload,setPhasePayload]=useState<ClinicalPhasePayload|null>(null);
  const [phaseLoadState,setPhaseLoadState]=useState<"LOADING"|"AVAILABLE"|"UNAVAILABLE">("LOADING");
  const [news,setNews]=useState<NewsPayload|null>(null);
  const [automation,setAutomation]=useState<AutomationStatus|null>(null);
  const [newsFilter,setNewsFilter]=useState("related");
  const [error,setError]=useState("");
  const popup=useRef<HTMLDialogElement>(null);

  useEffect(()=>{
    const controller=new AbortController();
    setLayout(window.innerWidth>=1150?"all":window.innerWidth>=760?"dual":"single");
    Promise.allSettled([
      fetch("/api/cal",{cache:"no-store",signal:controller.signal}).then(async r=>{if(!r.ok)throw Error("CAL unavailable");return r.json();}),
      fetch("/api/news",{cache:"no-store",signal:controller.signal}).then(async r=>{if(!r.ok)throw Error("NEWS unavailable");return r.json();}),
      fetch("/api/news-automation-status",{cache:"no-store",signal:controller.signal}).then(async r=>{if(!r.ok)throw Error("Automated research not connected");return r.json();}),
      fetch("/api/company-phase-status",{cache:"no-store",signal:controller.signal}).then(async r=>{
        if(!r.ok)throw Error("Clinical phase registry source unavailable");
        return r.json() as Promise<ClinicalPhasePayload>;
      })
    ]).then(results=>{
      if(controller.signal.aborted)return;
      if(results[0].status==="fulfilled"&&Array.isArray(results[0].value.events)){
        const records=results[0].value.events as CalendarEvent[];
        setCalendar(records);
        const pending=Array.isArray(results[0].value.unscheduled)?
          results[0].value.unscheduled as UndatedCycle[]:[];
        setUndated(pending);
        setTicker(prev=>prev||records[0]?.ticker||pending[0]?.ticker||"");
      }else setError("Published CAL data unavailable; no dates invented.");
      if(results[1].status==="fulfilled")setNews(results[1].value as NewsPayload);
      else setError(prev=>prev+" NEWS feed unavailable.");
      if(results[2].status==="fulfilled")setAutomation(results[2].value as AutomationStatus);
      if(results[3].status==="fulfilled"&&Array.isArray(results[3].value.records)){
        setPhasePayload(results[3].value as ClinicalPhasePayload);
        setPhaseLoadState("AVAILABLE");
      }else setPhaseLoadState("UNAVAILABLE");
    });
    return ()=>controller.abort();
  },[]);

  const tickers=useMemo(()=>[...new Set([...calendar.map(e=>e.ticker),
    ...undated.map(e=>e.ticker)])].sort(),[calendar,undated]);
  const selectedCycles=APPLICATION_CYCLES.filter(c=>c.ticker===ticker);
  const resolvedCycle=selectedCycles.find(c=>c.id===cycleId)?.id || selectedCycles[0]?.id||"";
  const onCompany=(nextTicker:string,eventId?:string)=>{
    if(!validTicker(nextTicker))return;
    setTicker(nextTicker);
    const event=calendar.find(e=>e.id===eventId);
    const pending=undated.find(c=>c.id===eventId);
    if (event) {setFocusDate(event.date);setFocusKey(key=>key+1);}
    const possible=APPLICATION_CYCLES.filter(c=>c.ticker===nextTicker&&event &&
      c.ncts.some(n=>event.ncts.includes(n))&&
      (!event.drug||c.drug.toLowerCase()===event.drug.toLowerCase()));
    const matchedId=event?.cycleId || pending?.prediction.cycleId ||
      (possible.length===1?possible[0].id:"");
    setCycleId(matchedId);
    setNewsFilter("related");
    setView("company");
    if(!popup.current?.open)popup.current?.showModal();
  };
  const goCal=()=>{
    const active=APPLICATION_CYCLES.find(c=>c.id===resolvedCycle);
    const candidate=calendar.filter(e=>e.ticker===ticker&&
      (!active||e.ncts.some(n=>active.ncts.includes(n))))
      .sort((a,b)=>a.date.localeCompare(b.date));
    const future=candidate.find(e=>e.date>=new Date().toISOString().slice(0,10));
    setFocusDate((future||candidate[0])?.date||"");
    setFocusKey(k=>k+1);
    setView("cal");
  };
  const jumpFromNews=(nextTicker:string,nextCycle:string|null)=>{
    if(!validTicker(nextTicker))return;
    setTicker(nextTicker);
    setCycleId(nextCycle||"");
    setView("company");
  };
  const panelOrder:View[]=view==="company"?["company","news","cal"]:view==="news"?["news","company","cal"]:["cal","company","news"];
  const visible=layout==="all"?panelOrder:layout==="dual"?panelOrder.slice(0,2):[view];
  const phaseProps={
    clinicalPhases:phasePayload?.records||[],phaseCheckedAt:phasePayload?.checkedAt||null,
    phaseAgeStatus:phasePayload?.ageStatus||null,phaseLoadState
  };
  const panel=(name:View)=>name==="cal"?<CalCalendar embedded onSelectCompany={onCompany}
      focusDate={focusDate} focusKey={focusKey}/>:
    name==="company"?<CompanyDetails ticker={ticker} calendar={calendar} undated={undated} {...phaseProps} cycleId={resolvedCycle}
      onCycle={setCycleId} onNews={()=>{setView("news");setNewsFilter("related");}} onCal={goCal}/>:
    <NewsDetails payload={news} ticker={ticker} cycleId={resolvedCycle}
      newsFilter={newsFilter} setNewsFilter={setNewsFilter} automation={automation}
      onSelectCompany={jumpFromNews}/>;
  return <main className={styles.page}>
    <header className={styles.pageHeader}><div><span className={styles.eyebrow}>PDUFA RESEARCH INTELLIGENCE</span>
      <h1>CAL · COMPANY · NEWS</h1><p>Linked by exact ticker, drug, application cycle and NCT. Source-reported information only.</p></div>
      <Link href="/focus">FOCUS roster</Link></header>
    <section className={styles.toolbar} aria-label="Linked intelligence display controls">
      <nav className={styles.tabs} aria-label="Select intelligence view">
        {(["cal","company","news"] as const).map(name=><button key={name} type="button"
          aria-pressed={view===name} className={view===name?styles.selected:""}
          onClick={()=>{setView(name);if(name==="news")setNewsFilter("related");}}>{kinds[name]}</button>)}
        <button type="button" aria-pressed={layout==="all"} className={layout==="all"?styles.selected:""}
          onClick={()=>setLayout("all")}>ALL 3</button>
      </nav>
      <div className={styles.settings}>
        <label>Display
          <select value={layout} onChange={e=>setLayout(e.target.value as Layout)}>
            <option value="single">Single</option><option value="dual">Dual</option><option value="all">All three</option>
          </select>
        </label>
        <label>Company
          <select value={ticker} onChange={e=>{setTicker(e.target.value);setCycleId("");}}>
            {!ticker&&<option value="">Select a ticker</option>}
            {tickers.map(t=><option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        {selectedCycles.length>1&&<label>Review cycle
          <select value={resolvedCycle} onChange={e=>setCycleId(e.target.value)}>
            {selectedCycles.map(c=><option key={c.id} value={c.id}>{c.drug} · {c.indication}</option>)}
          </select></label>}
      </div>
    </section>
    {error&&<p role="alert" className={styles.error}>{error}</p>}
    <section className={styles.viewGrid+" "+(layout==="all"?styles.all:layout==="dual"?styles.dual:styles.single)}>
      {visible.map(name=><div className={styles.panel} key={name} aria-label={kinds[name]+" workspace"}>{panel(name)}</div>)}
    </section>
    <dialog className={styles.modal} ref={popup} aria-label="Company detail popup"
      onClick={e=>{if(e.target===e.currentTarget)e.currentTarget.close();}}>
      <div className={styles.modalHead}><strong>COMPANY · {ticker}</strong>
        <button type="button" onClick={()=>popup.current?.close()} aria-label="Close company popup">×</button></div>
      <CompanyDetails ticker={ticker} calendar={calendar} undated={undated} {...phaseProps} cycleId={resolvedCycle}
        onCycle={setCycleId} onNews={()=>{popup.current?.close();setView("news");setNewsFilter("related");}}
        onCal={()=>{popup.current?.close();goCal();}}/>
    </dialog>
  </main>;
}
