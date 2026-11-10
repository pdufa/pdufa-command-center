"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import styles from "./CalCalendar.module.css";

type CalendarEvent = {
  id:string; ticker:string; company:string; date:string;
  marketCapUsd:number; ncts:string[]; drug:string; sourceUrl:string|null;
};
type CalendarPayload = {generatedAt:string; events:CalendarEvent[]};
const monthNames = ["January","February","March","April","May","June",
  "July","August","September","October","November","December"];
const dollar = (amount:number) => amount >= 1000000000 ?
  "$" + (amount/1000000000).toFixed(2) + "B" : "$" + Math.round(amount/1000000) + "M";
const monthNumber = (iso:string) => Number(iso.slice(0,4))*12 + Number(iso.slice(5,7))-1;
const monthName = (month:number) => monthNames[((month%12)+12)%12] + " " + Math.floor(month/12);
const displayDate = (iso:string) => new Date(iso+"T12:00:00Z").toLocaleDateString("en-US",
  {timeZone:"UTC",year:"numeric",month:"short",day:"numeric"});
function pacificToday():string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit"
  }).formatToParts(new Date());
  const part = (type:string) => parts.find(p=>p.type===type)?.value || "01";
  return part("year")+"-"+part("month")+"-"+part("day");
}

export default function CalCalendar({onSelectCompany,embedded=false}:{onSelectCompany?:(ticker:string,eventId?:string)=>void;embedded?:boolean}={}){
  const [payload,setPayload] = useState<CalendarPayload|null>(null);
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(true);
  const [today,setToday] = useState(pacificToday);
  const [offset,setOffset] = useState(0);
  const [minCap,setMinCap] = useState(0.3);
  const [maxCap,setMaxCap] = useState(10);
  const [activeTicker,setActiveTicker] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(()=>{
    setToday(pacificToday());
    const controller = new AbortController();
    fetch("/api/cal",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if (!response.ok) throw new Error("Published FOCUS calendar could not be loaded.");
        return response.json() as Promise<CalendarPayload>;
      })
      .then(data=>{
        if (!Array.isArray(data.events) || !data.generatedAt) throw new Error("Calendar format invalid.");
        setPayload(data);
        setError("");
      })
      .catch(err=>{if (!controller.signal.aborted) setError(err instanceof Error?err.message:"Calendar unavailable.");})
      .finally(()=>{if (!controller.signal.aborted) setLoading(false);});
    return ()=>controller.abort();
  },[]);

  const events = useMemo(()=>[...(payload?.events || [])].filter(e=>
    e.marketCapUsd>=minCap*1000000000 && e.marketCapUsd<=maxCap*1000000000)
      .sort((a,b)=>a.date.localeCompare(b.date)||a.ticker.localeCompare(b.ticker)||a.id.localeCompare(b.id)),
    [payload,minCap,maxCap]);
  const byTicker = useMemo(()=>{
    const groups = new Map<string,CalendarEvent[]>();
    for (const event of events) groups.set(event.ticker,[...(groups.get(event.ticker)||[]),event]);
    return groups;
  },[events]);
  const sequence = useMemo(()=>{
    const map = new Map<string,string>();
    for (const group of byTicker.values()) {
      const future = group.filter(e=>e.date>=today);
      future.forEach((e,index)=>map.set(e.id,index===0?"NEXT":"#"+(index+1)));
    }
    return map;
  },[byTicker,today]);
  const base = monthNumber(today);
  const last = Math.max(base,...events.map(event=>monthNumber(event.date)));
  const maxOffset = last-base;
  const safeOffset = Math.min(Math.max(-12,offset),maxOffset);
  const month = base+safeOffset;
  const year = Math.floor(month/12);
  const monthInYear = ((month%12)+12)%12;
  const first = new Date(Date.UTC(year,monthInYear,1)).getUTCDay();
  const monthDays = new Date(Date.UTC(year,monthInYear+1,0)).getUTCDate();
  const slots = Array.from({length:Math.ceil((first+monthDays)/7)*7},(_,index)=>{
    const day=index-first+1;
    return day>0&&day<=monthDays?day:null;
  });
  const dayEvents = new Map<number,CalendarEvent[]>();
  for (const e of events) {
    if (monthNumber(e.date)!==month) continue;
    const day=Number(e.date.slice(8,10));
    dayEvents.set(day,[...(dayEvents.get(day)||[]),e]);
  }
  const activeEvents = byTicker.get(activeTicker)||[];
  const nextActive = activeEvents.find(e=>e.date>=today);
  const latestActive = activeEvents[activeEvents.length-1];
  const past = events.filter(e=>e.date<today).length;
  const ahead = events.length-past;
  const openCompany = (ticker:string,eventId?:string) => {
    setActiveTicker(ticker);
    onSelectCompany?.(ticker,eventId);
    if (!embedded && !dialogRef.current?.open) dialogRef.current?.showModal();
  };

  return <main className={embedded?styles.page+" "+styles.embedded:styles.page}>
    {!embedded&&<header className={styles.heading}>
      <div><span className={styles.eyebrow}>FOCUS · RESEARCH CALENDAR</span>
        <h1>CAL</h1>
        <p>PDUFA target dates for published issuers within the selected market-cap band. Click a ticker for the company pop-up and every recorded application date.</p>
      </div>
      <a href="/focus" className={styles.focusLink}>View FOCUS source</a>
    </header>}
    <section className={styles.toolbar} aria-label="CAL controls">
      <div className={styles.capGroup}>
        <label>Minimum market cap
          <select value={minCap} onChange={e=>setMinCap(Number(e.target.value))}>
            <option value={0.3}>$300M</option><option value={0.5}>$500M</option>
            <option value={1}>$1B</option><option value={3}>$3B</option>
          </select>
        </label>
        <label>Maximum market cap
          <select value={maxCap} onChange={e=>setMaxCap(Number(e.target.value))}>
            <option value={3}>$3B</option><option value={5}>$5B</option>
            <option value={10}>$10B</option>
          </select>
        </label>
      </div>
      <div className={styles.totals} aria-live="polite">
        <strong>{events.length}</strong> published targets · <strong>{ahead}</strong> upcoming · <strong>{past}</strong> past dates
      </div>
    </section>
    <div className={styles.disclaimer}>
      Dates are <strong>source-reported FDA/PDUFA targets, not verified FDA outcomes</strong>. Past dates do not automatically mean approval or cycle closure. Market caps are published snapshots, not live quotes.
      {payload?.generatedAt && <span> Source snapshot: {displayDate(payload.generatedAt.slice(0,10))}.</span>}
    </div>
    {loading && <p role="status" className={styles.notice}>Loading published calendar…</p>}
    {error && <p role="alert" className={styles.error}>{error} The CAL page will not invent replacement dates.</p>}
    <section className={styles.calendarPanel} aria-label="PDUFA calendar">
      <div className={styles.scroller}>
        <button type="button" className={styles.arrow} disabled={safeOffset<=-12}
          aria-label="Previous month" onClick={()=>setOffset(safeOffset-1)}>‹</button>
        <div className={styles.monthTitle}><h2>{monthName(month)}</h2>
          <span>{safeOffset===0?"Current month":safeOffset<0?Math.abs(safeOffset)+" months back":safeOffset+" months ahead"}</span>
        </div>
        <button type="button" className={styles.arrow} disabled={safeOffset>=maxOffset}
          aria-label="Next month" onClick={()=>setOffset(safeOffset+1)}>›</button>
        <button type="button" className={styles.today} onClick={()=>setOffset(0)}>Today</button>
      </div>
      <label className={styles.rangeLabel} htmlFor="cal-month-scroll">Scroll months: 12 back → last published future PDUFA</label>
      <input id="cal-month-scroll" className={styles.monthSlider} type="range" min={-12}
        max={Math.max(-12,maxOffset)} step={1} value={safeOffset}
        onChange={e=>setOffset(Number(e.target.value))}/>
      <div className={styles.rangeEnds}><span>{monthName(base-12)}</span><span>Now</span>
        <span>Last: {monthName(last)}</span></div>
      <div className={styles.gridScroll}>
        <div className={styles.grid} role="grid" aria-label={monthName(month)}>
          {["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(day=>
            <div role="columnheader" className={styles.weekday} key={day}>{day}</div>)}
          {slots.map((day,index)=>{
            const dayEntries=day===null?[]:dayEvents.get(day)||[];
            const isToday = day!==null && year===Number(today.slice(0,4)) &&
              monthInYear===Number(today.slice(5,7))-1 && day===Number(today.slice(8,10));
            return <div role="gridcell" key={index} className={styles.dayCell+(day===null?" "+styles.blank:"")+(isToday?" "+styles.currentDay:"")}>
              {day!==null && <><div className={styles.dayNumber}>{day}</div>
                <div className={styles.events}>
                  {dayEntries.map(event=><button type="button" key={event.id}
                    title={event.company+" · "+(event.drug||"Drug not recorded")+" · "+displayDate(event.date)}
                    aria-label={event.ticker+", "+event.company+", "+displayDate(event.date)+", open company details"}
                    onClick={()=>openCompany(event.ticker,event.id)}
                    className={styles.eventChip+(sequence.get(event.id)==="NEXT"?" "+styles.nextChip:"")}>
                    <span aria-hidden="true" className={styles.dot}>●</span>
                    <span>{event.ticker}</span>
                    {sequence.has(event.id)&&<small>{sequence.get(event.id)}</small>}
                  </button>)}
                </div></>}
            </div>;
          })}
        </div>
      </div>
      <div className={styles.legend}><span><b className={styles.legendNext}>●</b> Next target for ticker</span>
        <span><b>●</b> Additional or past target</span></div>
      <div className={styles.agenda}>
        <h3>{monthName(month)} — {events.filter(e=>monthNumber(e.date)===month).length} published target(s)</h3>
        {events.filter(e=>monthNumber(e.date)===month).length===0 && <p>No published PDUFA targets for this month in the current market-cap filter.</p>}
        {events.filter(e=>monthNumber(e.date)===month).map(event=>
          <button type="button" key={event.id} className={styles.agendaRow}
            onClick={()=>openCompany(event.ticker,event.id)}>
            <span>{displayDate(event.date)}</span>
            <strong>{event.ticker}</strong>
            <span>{event.drug||event.company}</span>
            <em>{sequence.get(event.id)||(event.date<today?"Past target":"Future target")}</em>
          </button>)}
      </div>
    </section>
    {!embedded&&<dialog className={styles.dialog} ref={dialogRef} aria-label="Company PDUFA details"
      onClick={e=>{if(e.target===e.currentTarget)e.currentTarget.close();}}>
      <div className={styles.dialogInner}>
        <div className={styles.modalTop}><div><span className={styles.eyebrow}>COMPANY PDUFA CYCLES</span>
          <h2>{activeTicker} — {activeEvents[0]?.company||"Company"}</h2></div>
          <button type="button" className={styles.close} aria-label="Close company details"
            onClick={()=>dialogRef.current?.close()}>×</button>
        </div>
        <p><strong>{activeEvents.length}</strong> published {activeEvents.length===1?"target":"targets"} for this ticker
          {latestActive&&" · Last recorded target: "+displayDate(latestActive.date)}.</p>
        {nextActive ? <p className={styles.nextSummary}>Next upcoming PDUFA target: <strong>{displayDate(nextActive.date)}</strong> · {nextActive.drug||"Drug not recorded"}</p>
          : <p className={styles.disclaimer}>No remaining future target is recorded for this ticker. An FDA outcome or final cycle closure has not been established.</p>}
        <div className={styles.modalRows}>
          {activeEvents.map(event=><article key={event.id} className={styles.companyEntry}>
            <div className={styles.companyTitle}><strong>{displayDate(event.date)}</strong>
              <span className={sequence.get(event.id)==="NEXT"?styles.tagNext:styles.tag}>
                {sequence.get(event.id)||(event.date<today?"Past target":"Future target")}</span></div>
            <h3>{event.drug||"Drug / indication not recorded"}</h3>
            <p>Market cap at publication: <strong>{dollar(event.marketCapUsd)}</strong></p>
            <p>Linked trials: {event.ncts.length?event.ncts.map((nct,i)=>
              <span key={nct}>{i>0?", ":""}<a href={"https://clinicaltrials.gov/study/"+nct}
                target="_blank" rel="noopener noreferrer">{nct}</a></span>):"Not recorded"}</p>
            <p>FDA outcome: <strong>Not recorded in this calendar source</strong></p>
            {event.sourceUrl&&<a href={event.sourceUrl} target="_blank" rel="noopener noreferrer">Open original source ↗</a>}
          </article>)}
        </div>
        <p className={styles.modalFoot}>Dates may change. A passed target is not a confirmed approval, CRL, or closed PDUFA cycle.</p>
      </div>
    </dialog>}
  </main>;
}
