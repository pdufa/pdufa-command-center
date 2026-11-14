"use client";

import {useEffect,useMemo,useRef,useState} from "react";
import focusRoster from "../../data/p3PostDataActive.json";
import styles from "./FocusPredictionNavigator.module.css";
import PredictionSourceRunControls from "./PredictionSourceRunControls";

type FocusRow=(typeof focusRoster.records)[number];
type FocusTicker={ticker:string;company:string;trials:FocusRow[]};

const focusTickers:FocusTicker[]=Array.from(new Set(focusRoster.records.map(row=>row.ticker)))
  .sort((a,b)=>a.localeCompare(b))
  .map(ticker=>{
    const trials=focusRoster.records.filter(row=>row.ticker===ticker);
    return {ticker,company:trials[0]?.company??ticker,trials};
  });

const outcomes=[
  {title:"FDA Approval",description:"FDA approval of this exact drug, indication, and application cycle."},
  {title:"Complete Response Letter (CRL)",description:"FDA action requiring deficiencies to be addressed before approval."},
  {title:"FDA Review Delay / Extension",description:"Potential change to the reported application review timeline."}
] as const;

function formatStatus(value:unknown){
  return typeof value==="string"&&value.trim()?value:"Not recorded";
}

export default function FocusPredictionNavigator(){
  const initial=focusTickers[0];
  const [ticker,setTicker]=useState(initial?.ticker??"");
  const [nct,setNct]=useState(initial?.trials[0]?.nct??"");
  const buttons=useRef<Record<string,HTMLButtonElement|null>>({});

  const selectedGroup=useMemo(()=>focusTickers.find(group=>group.ticker===ticker)??initial,[ticker,initial]);
  const selectedTrial=selectedGroup?.trials.find(row=>row.nct===nct)??selectedGroup?.trials[0];

  function chooseTicker(value:string){
    const group=focusTickers.find(item=>item.ticker===value);
    if(!group)return;
    setTicker(group.ticker);
    setNct(group.trials[0]?.nct??"");
  }
  function shiftTicker(direction:number){
    const index=focusTickers.findIndex(group=>group.ticker===ticker);
    const next=(index+direction+focusTickers.length)%focusTickers.length;
    chooseTicker(focusTickers[next]?.ticker??ticker);
  }
  useEffect(()=>{
    const button=buttons.current[ticker];
    if(button)button.scrollIntoView({behavior:"smooth",block:"nearest",inline:"center"});
  },[ticker]);

  return <section className={styles.navigator} aria-label="FOCUS trial outcome prediction navigator">
    <div className={styles.heading}>
      <div>
        <p className={styles.overline}>FOCUS RESEARCH ROSTER</p>
        <h2>Choose a ticker to examine its trials</h2>
        <p className={styles.description}>
          {focusTickers.length} tickers · {focusRoster.records.length} exact-NCT trials · snapshot {focusRoster.asOf}
        </p>
      </div>
      <div className={styles.arrows}>
        <button type="button" onClick={()=>shiftTicker(-1)} aria-label="Previous FOCUS ticker">‹</button>
        <button type="button" onClick={()=>shiftTicker(1)} aria-label="Next FOCUS ticker">›</button>
      </div>
    </div>

    <div className={styles.rail} role="group" aria-label="Scroll through FOCUS stock tickers">
      {focusTickers.map(group=><button
        key={group.ticker} ref={element=>{buttons.current[group.ticker]=element;}}
        className={styles.tickerButton} type="button"
        aria-pressed={ticker===group.ticker}
        onClick={()=>chooseTicker(group.ticker)}>
        <span aria-hidden="true" className={styles.tickerIcon}>⌁</span>
        <strong>{group.ticker}</strong>
        <small>{group.trials.length} {group.trials.length===1?"trial":"trials"}</small>
      </button>)}
    </div>

    <div className={styles.selection}>
      <div className={styles.issuer}>
        <span className={styles.label}>SELECTED COMPANY</span>
        <h3>{selectedGroup?.ticker??"Unspecified"}</h3>
        <p>{selectedGroup?.company??"No company recorded"}</p>
        <small>{selectedGroup?.trials.length??0} associated FOCUS {selectedGroup?.trials.length===1?"trial":"trials"}</small>
      </div>
      <div className={styles.trialSelection}>
        <span className={styles.label}>SELECT AN EXACT CLINICAL TRIAL</span>
        <div className={styles.nctButtons} role="group" aria-label="Clinical trials for the selected ticker">
          {selectedGroup?.trials.map(row=><button
            type="button" key={row.nct} className={styles.nctButton}
            aria-pressed={selectedTrial?.nct===row.nct}
            onClick={()=>setNct(row.nct)}>
            <span aria-hidden="true">◈</span> {row.nct}
          </button>)}
        </div>
        <p className={styles.tip}>Each NCT stays independent. The same ticker can represent multiple distinct clinical trials.</p>
      </div>
    </div>

    {selectedTrial&&<div className={styles.details} aria-live="polite" aria-atomic="false">
      <div className={styles.trialHeading}>
        <div>
          <span className={styles.label}>PREDICTION RESEARCH · EXACT TRIAL</span>
          <h3>{selectedGroup.ticker} · {selectedTrial.nct}</h3>
          <p>{selectedGroup.company}</p>
        </div>
        <div className={styles.readiness}><small>Current prediction</small><strong>ABSTAIN</strong></div>
      </div>
      <PredictionSourceRunControls key={selectedTrial.nct} nct={selectedTrial.nct}/>
      <div className={styles.sourceInfo}>
        <div>
          <span>Roster-reported filing status</span>
          <strong>{formatStatus(selectedTrial.fdaStatus)}</strong>
          <small>This entry is a dated source pointer, not yet checked against current FDA acceptance by the owner.</small>
        </div>
        <div>
          <span>Recorded PDUFA decision date</span>
          <strong>{formatStatus(selectedTrial.recordedPdufaDate)}</strong>
          <small>Never infer a confirmed decision date from a planned filing.</small>
        </div>
      </div>
      <div className={styles.outcomeGrid} aria-label={"FDA outcomes for "+selectedTrial.nct}>
        {outcomes.map(outcome=><article key={outcome.title} className={styles.outcome}>
          <h4>{outcome.title}</h4>
          <p>{outcome.description}</p>
          <strong className={styles.abstain}>ABSTAIN</strong>
          <small>Probability not validated or released</small>
        </article>)}
      </div>
      <div className={styles.certainty}>
        <div><strong>Owner-model certainty</strong><span>NOT VALIDATED</span></div>
        <p>Clinical source review, saved research history, and out-of-time FDA outcome calibration have not passed release requirements. These are status labels, not numerical predictions.</p>
      </div>
      <div className={styles.sources}>
        <span className={styles.label}>RECORDED EVIDENCE LINKS</span>
        <a href={"https://clinicaltrials.gov/study/"+selectedTrial.nct} target="_blank" rel="noopener noreferrer">ClinicalTrials.gov study ↗</a>
        <a href={selectedTrial.regulatoryUrl} target="_blank" rel="noopener noreferrer">Roster-listed regulatory / issuer source ↗</a>
        <a href={"/predictions/assessment?nct="+encodeURIComponent(selectedTrial.nct)}>Open specialty evidence worklist ↗</a>
      </div>
    </div>}
    <p className={styles.footerNote}>
      This navigator uses the dated FOCUS roster, not owner-confirmed live FDA applications. A visible trial is not a validated approval prediction.
    </p>
  </section>;
}
