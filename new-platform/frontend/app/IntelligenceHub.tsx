"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import Link from "next/link";
import CalCalendar from "./CalCalendar";
import {APPLICATION_CYCLES} from "../lib/medical-intelligence-applications";
import styles from "./IntelligenceHub.module.css";

type View="cal"|"company"|"news";
type Layout="single"|"dual"|"all";
type CalendarEvent={id:string;ticker:string;company:string;date:string;drug:string;marketCapUsd:number;ncts:string[];sourceUrl:string|null};
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
function CompanyDetails({ticker,calendar,cycleId,onCycle,onNews,onCal}:{ticker:string;calendar:CalendarEvent[];cycleId:string;
  onCycle:(id:string)=>void;onNews:()=>void;onCal:()=>void}){
  const events=calendar.filter(e=>e.ticker===ticker).sort((a,b)=>a.date.localeCompare(b.date));
  const cycles=APPLICATION_CYCLES.filter(c=>c.ticker===ticker);
  const profile=events[0];
  const current=cycles.find(c=>c.id===cycleId)||cycles[0];
  const now=new Date().toISOString().slice(0,10);
  const next=events.find(e=>e.date>=now);
  return <div className={styles.companyDetails}>
    {!ticker?<p>Select a ticker from CAL to view the company and all recorded application cycles.</p>:<>
      <h2>{ticker} <span className={styles.companyName}>{profile?.company||ticker}</span></h2>
      <div className={styles.summary}>
        <div><small>Market cap · source snapshot</small><strong>{profile?cap(profile.marketCapUsd):"Not published"}</strong></div>
        <div><small>Next published PDUFA</small><strong>{next?date(next.date):"No future target recorded"}</strong></div>
        <div><small>Recorded application cycles</small><strong>{cycles.length}</strong></div>
      </div>
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
          {" · "}<Link href={"/analyze-now?nct="+nct}>Saved revision history</Link>
        </span>)}</p>
        <p><strong>Scientific question:</strong> {current.criticalQuestion}</p>
        <p><strong>Source dated:</strong> {date(current.sourceDate)} · <a href={current.sourceUrl} target="_blank" rel="noopener noreferrer">Original sponsor / SEC source</a></p>
        <p className={styles.caveat}>Cycle status is a source-linked research record, not FDA adjudication. No clinical outcome or approval probability is inferred.</p>
      </section>}
      <section className={styles.eventsBlock}>
        <h3>Published PDUFA timeline ({events.length})</h3>
        {events.length===0?<p>No published PDUFA dates for this issuer in the $300M–$10B feed.</p>:
          events.map(e=><article className={styles.dateRow} key={e.id}>
            <strong>{date(e.date)}</strong><span>{e.drug||"Drug not recorded"}</span>
            <small>{e.id===next?.id?"Next recorded target":e.date<now?"Past target — outcome unverified":"Additional future target"}</small>
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
function NewsDetails({payload,ticker,cycleId,newsFilter,setNewsFilter,automation}:{payload:NewsPayload|null;
  ticker:string;cycleId:string;newsFilter:string;setNewsFilter:(s:string)=>void;
  automation:AutomationStatus|null}){
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
        <p><strong>Linked trial IDs:</strong> {entry.ncts.length?entry.ncts.join(", "):"None verified"}</p>
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
  const [calendar,setCalendar]=useState<CalendarEvent[]>([]);
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
      fetch("/api/news-automation-status",{cache:"no-store",signal:controller.signal}).then(async r=>{if(!r.ok)throw Error("Automated research not connected");return r.json();})
    ]).then(results=>{
      if(controller.signal.aborted)return;
      if(results[0].status==="fulfilled"&&Array.isArray(results[0].value.events)){
        const records=results[0].value.events as CalendarEvent[];
        setCalendar(records);
        setTicker(prev=>prev||records[0]?.ticker||"");
      }else setError("Published CAL data unavailable; no dates invented.");
      if(results[1].status==="fulfilled")setNews(results[1].value as NewsPayload);
      else setError(prev=>prev+" NEWS feed unavailable.");
      if(results[2].status==="fulfilled")setAutomation(results[2].value as AutomationStatus);
    });
    return ()=>controller.abort();
  },[]);

  const tickers=useMemo(()=>[...new Set(calendar.map(e=>e.ticker))].sort(),[calendar]);
  const selectedCycles=APPLICATION_CYCLES.filter(c=>c.ticker===ticker);
  const resolvedCycle=selectedCycles.find(c=>c.id===cycleId)?.id || selectedCycles[0]?.id||"";
  const onCompany=(nextTicker:string,eventId?:string)=>{
    if(!validTicker(nextTicker))return;
    setTicker(nextTicker);
    const event=calendar.find(e=>e.id===eventId);
    const possible=APPLICATION_CYCLES.filter(c=>c.ticker===nextTicker&&event &&
      c.ncts.some(n=>event.ncts.includes(n))&&
      (!event.drug||c.drug.toLowerCase()===event.drug.toLowerCase()));
    setCycleId(possible.length===1?possible[0].id:"");
    setNewsFilter("related");
    setView("company");
    if(!popup.current?.open)popup.current?.showModal();
  };
  const panelOrder:View[]=view==="company"?["company","news","cal"]:view==="news"?["news","company","cal"]:["cal","company","news"];
  const visible=layout==="all"?panelOrder:layout==="dual"?panelOrder.slice(0,2):[view];
  const panel=(name:View)=>name==="cal"?<CalCalendar embedded onSelectCompany={onCompany}/>:
    name==="company"?<CompanyDetails ticker={ticker} calendar={calendar} cycleId={resolvedCycle}
      onCycle={setCycleId} onNews={()=>{setView("news");setNewsFilter("related");}} onCal={()=>setView("cal")}/>:
    <NewsDetails payload={news} ticker={ticker} cycleId={resolvedCycle}
      newsFilter={newsFilter} setNewsFilter={setNewsFilter} automation={automation}/>;
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
      <CompanyDetails ticker={ticker} calendar={calendar} cycleId={resolvedCycle}
        onCycle={setCycleId} onNews={()=>{popup.current?.close();setView("news");setNewsFilter("related");}}
        onCal={()=>{popup.current?.close();setView("cal");}}/>
    </dialog>
  </main>;
}
