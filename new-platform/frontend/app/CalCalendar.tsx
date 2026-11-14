"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import styles from "./CalCalendar.module.css";

type ResearchCall = "APPROVAL_LEAN"|"CRL_LEAN"|"ABSTAIN"|"ALREADY_APPROVED";
type ResearchPrediction = {
  cycleId:string; call:ResearchCall; level:3; provisional:true; asOf:string;
  label:string; confidenceDescription:string; applicationStatusAsRecorded:string;
  indication:string; drug:string; applicationType:string;
  clinicalRationale:string; benefitRiskRationale:string; fdaCmcRationale:string;
  evidenceGap:string; sourceDate:string; sourceUrl:string; evidenceUrl:string;
  independentlyValidated:false; calibratedProbability:null;
};
type CalendarEvent = {
  id:string; ticker:string; company:string; date:string;
  marketCapUsd:number; ncts:string[]; drug:string; sourceUrl:string|null;
  cycleId:string|null; dateStatus:string; prediction:ResearchPrediction|null;
};
type UnscheduledCycle = {
  id:string; ticker:string; company:string; date:null;
  marketCapUsd:number; ncts:string[]; dateStatus:string; prediction:ResearchPrediction;
};
type CalendarPayload = {
  generatedAt:string; events:CalendarEvent[]; unscheduled:UnscheduledCycle[];
  research:{asOf:string;level:number;label:string;independentlyValidated:boolean};
};
const shortCall = (call:ResearchCall):string => ({
  APPROVAL_LEAN:"Approval lean",CRL_LEAN:"CRL lean",
  ABSTAIN:"Abstain",ALREADY_APPROVED:"Already approved"
})[call];
const callClass = (call:ResearchCall):string => ({
  APPROVAL_LEAN:styles.leanApproval,CRL_LEAN:styles.leanCrl,
  ABSTAIN:styles.leanAbstain,ALREADY_APPROVED:styles.leanDecided
})[call];

function PredictionSummary({prediction}:{prediction:ResearchPrediction|null}){
  if(!prediction)return <p className={styles.researchMissing}>
    No matched FOCUS application-level prediction is available for this published date.
  </p>;
  return <div className={styles.predictionPanel}>
    <div className={styles.predictionHeader}>
      <strong>Level {prediction.level} research · <span className={callClass(prediction.call)}>
        {shortCall(prediction.call)}</span></strong>
      <small>Frozen {prediction.asOf} · {prediction.indication}</small>
    </div>
    <p><strong>Unvalidated research hypothesis.</strong> No independently reviewed FDA forecast,
      numerical approval probability, or certainty rating. Application status: {
      prediction.applicationStatusAsRecorded.replaceAll("_"," ").toLowerCase()}.</p>
    <details>
      <summary>Clinical evidence, safety, FDA/CMC and source history</summary>
      <p><strong>Clinical:</strong> {prediction.clinicalRationale}</p>
      <p><strong>Safety / benefit-risk:</strong> {prediction.benefitRiskRationale}</p>
      <p><strong>Regulatory / CMC:</strong> {prediction.fdaCmcRationale}</p>
      <p><strong>Outstanding evidence:</strong> {prediction.evidenceGap}</p>
      <p><a href={prediction.evidenceUrl} target="_blank" rel="noopener noreferrer">
        Original clinical source</a>{" · "}
        <a href={prediction.sourceUrl} target="_blank" rel="noopener noreferrer">
          Application evidence</a></p>
    </details>
  </div>;
}
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

export default function CalCalendar({onSelectCompany,embedded=false,focusDate,focusKey}:{onSelectCompany?:(ticker:string,eventId?:string)=>void;embedded?:boolean;focusDate?:string;focusKey?:number}={}){
  const [payload,setPayload] = useState<CalendarPayload|null>(null);
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(true);
  const [today,setToday] = useState(pacificToday);
  const [offset,setOffset] = useState(0);
  const [minCap,setMinCap] = useState(0.3);
  const [maxCap,setMaxCap] = useState(10);
  const [activeTicker,setActiveTicker] = useState("");
  const [showPredictions,setShowPredictions] = useState(true);
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(()=>{
    if (focusDate && /^\d{4}-\d{2}-\d{2}$/.test(focusDate)) {
      setOffset(monthNumber(focusDate)-monthNumber(pacificToday()));
    }
  },[focusDate,focusKey]);

  useEffect(()=>{
    setToday(pacificToday());
    const controller = new AbortController();
    fetch("/api/cal",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if (!response.ok) throw new Error("Published FOCUS calendar could not be loaded.");
        return response.json() as Promise<CalendarPayload>;
      })
      .then(data=>{
        if (!Array.isArray(data.events) || !Array.isArray(data.unscheduled) ||
            !data.generatedAt || !data.research?.asOf) throw new Error("Calendar format invalid.");
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
  const undated = useMemo(()=>(payload?.unscheduled||[]).filter(e=>
    e.marketCapUsd>=minCap*1000000000 && e.marketCapUsd<=maxCap*1000000000),
    [payload,minCap,maxCap]);
  const isPastOrDecided = (e:CalendarEvent) =>
    e.date<today || e.prediction?.call==="ALREADY_APPROVED";
  const byTicker = useMemo(()=>{
    const groups = new Map<string,CalendarEvent[]>();
    for (const event of events) groups.set(event.ticker,[...(groups.get(event.ticker)||[]),event]);
    return groups;
  },[events]);
  const sequence = useMemo(()=>{
    const map = new Map<string,string>();
    for (const group of byTicker.values()) {
      const future = group.filter(e=>e.date>=today && e.prediction?.call!=="ALREADY_APPROVED");
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
  const activeUndated = undated.filter(e=>e.ticker===activeTicker);
  const nextActive = activeEvents.find(e=>e.date>=today && e.prediction?.call!=="ALREADY_APPROVED");
  const latestActive = activeEvents[activeEvents.length-1];
  const past = events.filter(isPastOrDecided).length;
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
        <p>Upcoming PDUFA targets with provisional Level 3 research predictions for each FDA application.
          Click a ticker to compare linked clinical trials, expected decisions, risks and sources.</p>
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
      <label className={styles.predictionSwitch}>
        <input type="checkbox" checked={showPredictions}
          onChange={e=>setShowPredictions(e.target.checked)}/>
        Show Level 3 research predictions
      </label>
      <div className={styles.totals} aria-live="polite">
        <strong>{events.length}</strong> application targets · <strong>{ahead}</strong> upcoming ·
        <strong> {past}</strong> past / decided · <strong>{undated.length}</strong> awaiting a date
      </div>
    </section>
    <div className={styles.disclaimer}>
      Dates are <strong>source-reported FDA/PDUFA targets, not independently verified FDA outcomes</strong>.
      Predictions are <strong>preliminary Level 3-style research, not validated FDA forecasts or probabilities</strong>.
      A separate application can have a different prediction even under the same ticker.
      Known already-approved cycles are marked and excluded from upcoming counts.
      Market caps are snapshots, not live quotes.
      {payload?.generatedAt && <span> Calendar snapshot: {displayDate(payload.generatedAt.slice(0,10))}.</span>}
      {payload?.research?.asOf && <span> Prediction research frozen: {displayDate(payload.research.asOf)}.</span>}
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
                    title={event.company+" · "+(event.drug||"Drug not recorded")+" · "+displayDate(event.date)+
                      " · "+(event.prediction?shortCall(event.prediction.call)+" (unvalidated research)":"No assessment")}
                    aria-label={event.ticker+", "+event.company+", "+displayDate(event.date)+
                      ", "+(event.prediction?shortCall(event.prediction.call)+" provisional research":"no prediction")+
                      ", open company details"}
                    onClick={()=>openCompany(event.ticker,event.id)}
                    className={styles.eventChip+(sequence.get(event.id)==="NEXT"?" "+styles.nextChip:"")+
                      (event.prediction?.call==="ALREADY_APPROVED"?" "+styles.decidedChip:"")}>
                    <span aria-hidden="true" className={styles.dot}>●</span>
                    <span className={styles.chipTicker}>{event.ticker}</span>
                    {sequence.has(event.id)&&<small>{sequence.get(event.id)}</small>}
                    {showPredictions&&event.prediction&&<span
                      className={styles.chipCall+" "+callClass(event.prediction.call)}>
                      {shortCall(event.prediction.call)}</span>}
                  </button>)}
                </div></>}
            </div>;
          })}
        </div>
      </div>
      <div className={styles.legend}><span><b className={styles.legendNext}>●</b> Next source-reported target</span>
        <span><b>●</b> Additional target</span>
        <span className={styles.legendSample+" "+styles.leanApproval}>Approval lean</span>
        <span className={styles.legendSample+" "+styles.leanCrl}>CRL lean</span>
        <span className={styles.legendSample+" "+styles.leanAbstain}>Abstain</span>
        <span className={styles.legendSample+" "+styles.leanDecided}>Already approved</span>
        <span>All research directions are provisional</span>
      </div>
      <div className={styles.agenda}>
        <h3>{monthName(month)} — {events.filter(e=>monthNumber(e.date)===month).length} published target(s)</h3>
        {events.filter(e=>monthNumber(e.date)===month).length===0 && <p>No published PDUFA targets for this month in the current market-cap filter.</p>}
        {events.filter(e=>monthNumber(e.date)===month).map(event=>
          <button type="button" key={event.id} className={styles.agendaRow}
            onClick={()=>openCompany(event.ticker,event.id)}>
            <span>{displayDate(event.date)}</span>
            <strong>{event.ticker}</strong>
            <span>{event.drug||event.company}</span>
            <span className={styles.agendaCall}>
              {showPredictions && event.prediction ?
                <span className={callClass(event.prediction.call)}>
                  {shortCall(event.prediction.call)} · L3 research</span> :
                (event.prediction?"Research prediction hidden":"Prediction not yet available")}
            </span>
            <em>{sequence.get(event.id)||
              (event.prediction?.call==="ALREADY_APPROVED"?"Already decided":
                event.date<today?"Past target":"Future target")}</em>
          </button>)}
      </div>
      <section className={styles.undated} aria-label="FOCUS applications without a published FDA goal date">
        <h3>FOCUS applications awaiting a published FDA goal date ({undated.length})</h3>
        <p>Research calls are shown here until a dated application target is published.
          Filing plans are never placed on an invented calendar date.</p>
        {undated.map(c=><button type="button" className={styles.undatedRow}
          key={c.id} onClick={()=>openCompany(c.ticker,c.id)}>
          <strong>{c.ticker}</strong>
          <span>{c.prediction.drug} · {c.prediction.indication}</span>
          <span className={callClass(c.prediction.call)}>
            {showPredictions?shortCall(c.prediction.call):"Date pending"}</span>
          <small>{c.dateStatus==="FDA_GOAL_DATE_NOT_ASSIGNED"?
            "No FDA review goal assigned":"Goal not yet verified for CAL"}</small>
        </button>)}
      </section>
    </section>
    {!embedded&&<dialog className={styles.dialog} ref={dialogRef} aria-label="Company PDUFA details"
      onClick={e=>{if(e.target===e.currentTarget)e.currentTarget.close();}}>
      <div className={styles.dialogInner}>
        <div className={styles.modalTop}><div><span className={styles.eyebrow}>COMPANY PDUFA CYCLES</span>
          <h2>{activeTicker} — {activeEvents[0]?.company||activeUndated[0]?.company||"Company"}</h2></div>
          <button type="button" className={styles.close} aria-label="Close company details"
            onClick={()=>dialogRef.current?.close()}>×</button>
        </div>
        <p><strong>{activeEvents.length}</strong> published calendar {activeEvents.length===1?"target":"targets"}
          {activeUndated.length>0&&" · "+activeUndated.length+" application(s) awaiting dates"}
          {latestActive&&" · Last recorded target: "+displayDate(latestActive.date)}.</p>
        {nextActive ? <p className={styles.nextSummary}>Next upcoming PDUFA target: <strong>{displayDate(nextActive.date)}</strong> · {nextActive.drug||"Drug not recorded"}</p>
          : <p className={styles.disclaimer}>No remaining future target is recorded for this ticker. An FDA outcome or final cycle closure has not been established.</p>}
        <div className={styles.modalRows}>
          {activeEvents.map(event=><article key={event.id} className={styles.companyEntry}>
            <div className={styles.companyTitle}><strong>{displayDate(event.date)}</strong>
              <span className={sequence.get(event.id)==="NEXT"?styles.tagNext:styles.tag}>
                {sequence.get(event.id)||(event.date<today?"Past target":"Future target")}</span></div>
            <h3>{event.drug||"Drug / indication not recorded"}</h3>
            <PredictionSummary prediction={event.prediction}/>
            <p>Market cap at publication: <strong>{dollar(event.marketCapUsd)}</strong></p>
            <p>Linked trials: {event.ncts.length?event.ncts.map((nct,i)=>
              <span key={nct}>{i>0?", ":""}<a href={"https://clinicaltrials.gov/study/"+nct}
                target="_blank" rel="noopener noreferrer">{nct}</a>{" · "}<a href={"/predictions/assessment?nct="+nct}>Assessments</a></span>):"Not recorded"}</p>
            <p>FDA review-cycle status: <strong>{
              event.prediction?.call==="ALREADY_APPROVED"?
                "Previously approved; this date is not a pending decision":
                "No verified final outcome recorded by the calendar"}</strong></p>
            {event.sourceUrl&&<a href={event.sourceUrl} target="_blank" rel="noopener noreferrer">Open original source ↗</a>}
          </article>)}
          {activeUndated.map(c=><article key={c.id} className={styles.companyEntry}>
            <div className={styles.companyTitle}><strong>FDA target date not assigned</strong>
              <span className={styles.tag}>Undated application</span></div>
            <h3>{c.prediction.drug} · {c.prediction.indication}</h3>
            <PredictionSummary prediction={c.prediction}/>
            <p>Linked clinical trials: {c.ncts.map((nct,i)=><span key={nct}>
              {i?", ":""}<a href={"https://clinicaltrials.gov/study/"+nct}
                target="_blank" rel="noopener noreferrer">{nct}</a>{" · "}<a href={"/predictions/assessment?nct="+nct}>Assessments</a></span>)}</p>
          </article>)}
        </div>
        <p className={styles.modalFoot}>Source-reported dates can change. Forecasts are unvalidated
          research hypotheses, not FDA outcomes or trade instructions. Updated source evidence
          does not automatically mean a new prediction has been adjudicated.</p>
      </div>
    </dialog>}
  </main>;
}
