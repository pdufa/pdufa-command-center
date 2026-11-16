"use client";
import FocusSavedAssessments from "../FocusSavedAssessments";
import Scientific456Workspace from "../Scientific456Workspace";
import {FocusLevelHeaders,FocusLevelSubheaders,FocusLevelCells,type FocusTrialLevels} from '../FocusLevelColumns';
import {FocusOverallHeaders,FocusOverviewCells,FocusTwentyHeaders,FocusTwentyCells} from '../FocusOverallLevelMatrix';
import {PredictionHeaders,PredictionCells,PredictionLegend} from '../PdufaPredictionColumns';
import AssessmentLauncher from '../AssessmentLauncher';
import ScientificStepsReadiness from '../ScientificStepsReadiness';
import {ExactTrialIntakeSelector} from '../ExactTrialScientificIntake';
import {useEffect,useMemo,useRef,useState} from "react";
import {readSavedFocus} from "../../lib/focus-saved-records";
import {provisionalFocusScore,provisionalFocusOverall} from "../../lib/focus-provisional-scores";
import {FOCUS_CHART_SNAPSHOT_TRIALS,FOCUS_CHART_SNAPSHOT_DATE} from "../../lib/focus-chart-snapshot";
import NumericSortSettings,{sortNumericRows,type NumericSortRule} from "../NumericSortSettings";
import Link from "next/link";
import TickerChartButton from "../TickerChartButton";
import IndicationIntelligence from "../IndicationIntelligence";
import CompanyDateBadges from "../CompanyDateBadges";
import snapshot from "../../data/p3PostDataActive.json";
import designationData from "../../data/focusFdaDesignations.json";
import {FOCUS_FINAL_TRIAL_AUDIT} from "../../lib/focus-final-gate-checks";

const source="https://docs.google.com/spreadsheets/d/1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU/edit#gid=202611061";
/** Snapshot of the user's source-of-truth Google Sheet. Historical 762-trial cohorts are not active listings. */
const trials=snapshot.records;
const designationByNct=new Map(designationData.records.map(r=>[r.nct,r]));
const finalGateAudit=FOCUS_FINAL_TRIAL_AUDIT;
const finalGateByNct=new Map(finalGateAudit.rows.map(row=>[row.nct,row]));

/** Same exact 32-NCT, 96-run pinned source evidence as the visible FOCUS chart.
 * These are documentary readiness scores; there is NO FDA approval forecast.
 * Preserve the source report identity so provisionalFocusScore enforces the same
 * immutable run/version/date guard as in the chart. Never fabricate values.
 */
const datedSourceLevels:Record<string,FocusTrialLevels>=Object.fromEntries(
 FOCUS_CHART_SNAPSHOT_TRIALS.map(trial=>[
  trial.nct,Object.fromEntries([1,2,3].map(level=>{
   const report=trial.levels[String(level)]?.report;
   return [String(level),{
    state:report?'COMPLETED':'NOT RUN',
    report:report?{...report,fdaPrediction:{
     outcome:report.fdaPrediction?.outcome||'ABSTAIN',confidence:'NOT_VALIDATED'
    }}:null,
    missingEvidence:[]
   }];
  }))
 ])
);
const evidenceColumnScores=(nct:string,levels?:FocusTrialLevels)=>{
 const values:Record<string,number|null>={};
 for(const level of [1,2,3])
  values[String(level)]=provisionalFocusScore(nct,level,levels?.[String(level)]?.report)?.evidenceReadinessScore??null;
 values.overall=provisionalFocusOverall(nct,levels)?.evidenceReadinessScore??null;
 return values;
};
const datedSourceScores:Record<string,Record<string,number|null>>=Object.fromEntries(
 FOCUS_CHART_SNAPSHOT_TRIALS.map(t=>[t.nct,evidenceColumnScores(t.nct,datedSourceLevels[t.nct])])
);

export default function FocusPage(){
 const [sortRules,setSortRules]=useState<NumericSortRule[]>([]);
 // A successful sort should visibly change which FOCUS rows the owner sees,
 // not just silently close the modal while the table remains off screen.
 const applyFocusSort=(next:NumericSortRule[])=>{
  setSortRules(next);
  window.requestAnimationFrame(()=>window.requestAnimationFrame(()=>{
   document.getElementById('focus-sort-feedback')?.scrollIntoView({
    behavior:'smooth',block:'start'
   });
   tableScrollRef.current?.scrollTo({left:0,behavior:'auto'});
  }));
 };
 const [surveyExpanded,setSurveyExpanded]=useState(false);
 const tableScrollRef=useRef<HTMLDivElement>(null);
 // The full research table can be horizontally scrolled on phones; provide
 // a deterministic way back to the primary source-backed evidence columns.
 const showScoreColumns=()=>{
  setSurveyExpanded(false);
  tableScrollRef.current?.scrollTo({left:0,behavior:'smooth'});
 };
 const [savedScores,setSavedScores]=useState<Record<string,Record<string,number|null>>>(datedSourceScores);
 const [savedLevels,setSavedLevels]=useState<Record<string,FocusTrialLevels>>(datedSourceLevels);
 const [usingDatedSource,setUsingDatedSource]=useState(true);
 useEffect(()=>{
  let active=true;
  async function refresh(){
   try{
    const data=await readSavedFocus() as {status?:string;total?:number;trials?:{nct:string;levels:FocusTrialLevels}[]};
    if(!active)return;
    const expected=new Set(trials.map(t=>t.nct)),members=data.trials||[];
    if(data.status!=='DATABASE_SAVED_RECONCILED_OWNER_ROSTER'||
       data.total!==expected.size||members.length!==expected.size||
       new Set(members.map(t=>t.nct)).size!==expected.size||
       members.some(t=>!expected.has(t.nct)||!t.levels||[1,2,3].some(level=>{
        const report=t.levels[String(level)]?.report;
        return !!report&&(report.nct!==t.nct||report.level!==level||report.mode!=='CURRENT_EVIDENCE');
       })))throw Error('Saved exact-trial source roster unavailable');
    const levels:Record<string,FocusTrialLevels>=Object.fromEntries(members.map(t=>[t.nct,t.levels]));
    const scores:Record<string,Record<string,number|null>>={};
    for(const trial of members){
      const candidate=evidenceColumnScores(trial.nct,trial.levels);
      if(candidate.overall===null||[1,2,3].some(level=>candidate[String(level)]===null))
       throw Error('New or mismatched research run: use dated, labeled evidence snapshot until rescored');
      scores[trial.nct]=candidate;
    }
    setSavedLevels(levels);
    setSavedScores(scores);
    setUsingDatedSource(false);
   }catch{if(active){
    // No 0s or blanks on network failure; show the same pinned 96 survey
    // observations already used by the chart, clearly labeled as dated.
    setSavedLevels(datedSourceLevels);setSavedScores(datedSourceScores);
    setUsingDatedSource(true);
   }}
  }
  void refresh();
  const timer=setInterval(()=>void refresh(),30000);
  const onFocus=()=>void refresh();
  window.addEventListener('focus',onFocus);
  return()=>{active=false;clearInterval(timer);window.removeEventListener('focus',onFocus);};
 },[]);
 const sortedTrials=useMemo(()=>sortNumericRows(trials,sortRules,(t,c)=>{
  const gate=finalGateByNct.get(t.nct);
  const designations=designationByNct.get(t.nct)?.designations;
  if(c==="ticker")return t.ticker;
  if(c==="nct")return t.nct;
  if(c==="company")return t.company;
  if(c==="designations")return designations?.length?designations.map(d=>d.label).join(" · "):"Not verified";
  if(c==="marketCap")return t.marketCap;
  if(c==="fdaStatus")return t.fdaStatus;
  if(c==="sources")return t.resultsUrl;
  if(c==="gates")return gate?gate.independentlyVerified:null;
  if(c==="overall")return savedScores[t.nct]?.overall??null;
  if(c==="direction")return null;
  const savedLevel=/^level([1-3])$/.exec(c);
  if(savedLevel)return savedScores[t.nct]?.[savedLevel[1]]??null;
  if(/^level(?:[4-9]|1[0-9]|20)$/.test(c))return null;
  return null;
 },t=>t.nct),[sortRules,savedScores]);
 return <main style={{maxWidth:1220,margin:"28px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif",color:"#173d2b"}}>
  <nav style={{display:"flex",gap:18,marginBottom:18}}><Link href="/pool">POOL</Link><Link href="/indications">INDICATIONS</Link><Link href="/tools">TOOLS</Link></nav>
  <h1>FOCUS</h1>
  <p><a href="#focus-site-spreadsheet" style={{display:"inline-block",padding:"9px 13px",background:"#edf8ef",border:"1px solid #789987",borderRadius:7,fontWeight:700,marginRight:10}}>Open FOCUS spreadsheet · Overall + L01–L03</a></p>
  <p><a href="#focus-chart-quick-view" style={{display:"inline-block",padding:"9px 13px",background:"#e8f3ed",border:"1px solid #7baf99",borderRadius:7,fontWeight:700}}>View four-line FOCUS chart</a></p>
  <div aria-label="Top table sorting controls" style={{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap",margin:"12px 0 18px"}}>
  <NumericSortSettings scope="focus" columns={[{id:"overall",label:"Overall prediction survey result — Evidence Readiness /100",shortLabel:"Overall Score /100"},{id:"ticker",label:"Ticker"},{id:"nct",label:"NCT / Trial"},{id:"company",label:"Company"},{id:"designations",label:"FDA Special Designations"},{id:"marketCap",label:"Market cap ($B)"},{id:"fdaStatus",label:"FDA / PDUFA path"},{id:"sources",label:"Sources"},{id:"gates",label:"7 gate checks"},{id:"direction",label:"FDA prediction direction",disabled:true,unavailableReason:"no validated prediction"},{id:"level1",label:"L01-Trial identity"},{id:"level2",label:"L02-Current phase"},{id:"level3",label:"L03-Source evidence"},{id:"level4",label:"L04-Study protocol",disabled:true,unavailableReason:"level not yet scored"},{id:"level5",label:"L05-Population",disabled:true,unavailableReason:"level not yet scored"},{id:"level6",label:"L06-Efficacy",disabled:true,unavailableReason:"level not yet scored"},{id:"level7",label:"L07-Statistics",disabled:true,unavailableReason:"level not yet scored"},{id:"level8",label:"L08-Safety",disabled:true,unavailableReason:"level not yet scored"},{id:"level9",label:"L09-Clinical benefit",disabled:true,unavailableReason:"level not yet scored"},{id:"level10",label:"L10-Comparator",disabled:true,unavailableReason:"level not yet scored"},{id:"level11",label:"L11-Subgroups",disabled:true,unavailableReason:"level not yet scored"},{id:"level12",label:"L12-Data gaps",disabled:true,unavailableReason:"level not yet scored"},{id:"level13",label:"L13-Regulatory history",disabled:true,unavailableReason:"level not yet scored"},{id:"level14",label:"L14-FDA alignment",disabled:true,unavailableReason:"level not yet scored"},{id:"level15",label:"L15-Manufacturing",disabled:true,unavailableReason:"level not yet scored"},{id:"level16",label:"L16-Benefit–risk",disabled:true,unavailableReason:"level not yet scored"},{id:"level17",label:"L17-Exceptions",disabled:true,unavailableReason:"level not yet scored"},{id:"level18",label:"L18-External evidence",disabled:true,unavailableReason:"level not yet scored"},{id:"level19",label:"L19-Confidence",disabled:true,unavailableReason:"level not yet scored"},{id:"level20",label:"L20-Integrated review",disabled:true,unavailableReason:"level not yet scored"}]} onApply={applyFocusSort} activeRules={sortRules}/>
  <button type="button" data-testid="focus-overall-sort-control"
    aria-label="Sort Overall prediction survey result"
    onClick={()=>applyFocusSort([{column:"overall",direction:
      sortRules.length===1&&sortRules[0].column==="overall"&&sortRules[0].direction==="desc"?"asc":"desc"}])}
    style={{padding:"9px 14px",borderRadius:8,border:"1px solid #789987",
      background:"#e6f2ea",color:"#173d2b",fontWeight:700,cursor:"pointer"}}>
   {sortRules.length===1&&sortRules[0].column==="overall"&&sortRules[0].direction==="desc"?
     "Overall Score: Low → High ↑":"Sort Overall Score: High → Low ↓"}
  </button>
  <button type="button" aria-label="Survey Columns" aria-expanded={surveyExpanded} onClick={()=>setSurveyExpanded(v=>!v)} style={{padding:"9px 14px",borderRadius:8,border:"1px solid #789987",background:"#e6f2ea",color:"#173d2b",fontWeight:700,cursor:"pointer"}}>{surveyExpanded?"▾ Hide Survey Columns":"▸ Survey Columns"}</button>
  </div>
  <style>{`
   .focus-mobile-score-view{display:none}
   @media (max-width:740px){
    .focus-mobile-score-view{display:block}
    .focus-mobile-score-view table{table-layout:fixed;width:100%}
    .focus-mobile-score-view th,.focus-mobile-score-view td{overflow:hidden;text-overflow:clip}
   }
  `}</style>
  <h2 id="focus-site-spreadsheet" style={{fontSize:22,margin:"12px 0 6px",scrollMarginTop:104}}>FOCUS spreadsheet · Overall Score + L01–L03 (32 trials)</h2>
  <p style={{fontSize:13,margin:"0 0 8px"}}>On phones, the compact score grid shows Overall and L01–L03 without sideways scrolling. The full spreadsheet below keeps the same scores immediately after the ticker; L04–L20 appear only when Survey Columns is expanded.</p>
  <p data-testid="focus-main-grid-evidence-source" role="status" style={{
    margin:"8px 0 12px",padding:"9px 12px",border:"1px solid #a5c5b0",borderRadius:8,
    background:"#f1f8f3",fontSize:13
  }}>
   <strong>FOCUS L01–L03 and Overall: 32/32 trial evidence scores populated.</strong>
   {" "}{usingDatedSource?
     "Source: dated, verified 2026-11-15 research snapshot. Live authenticated records are unavailable, newer or not fully reconciled.":
     "Source: 32/32 current reports reconciled with the immutable source checks."}
   {" "}These numbers measure source-documentation readiness (not drug efficacy, scientific validation,
   FDA approval probability or a directional approval call). L01–L03 scores are visible beside Overall;
   expand Survey Columns for L04–L20. Snapshot date: {FOCUS_CHART_SNAPSHOT_DATE}.
  </p>
  <div id="focus-sort-feedback" data-testid="focus-sort-feedback" role="status"
   aria-live="polite" style={{margin:"12px 0 8px",padding:"9px 12px",
    border:"1px solid #95bea0",background:"#f1f8f3",borderRadius:8,fontSize:13,
    scrollMarginTop:104}}>
   {sortRules.length?<>
    <strong>Sort applied: {sortRules.map((r,i)=>
     (i+1)+". "+(r.column==="overall"?"Overall Score":/^level[0-9]+$/.test(r.column)?
      "Level "+r.column.slice(5):r.column)+" · "+
      (r.direction==="desc"?"High → Low":"Low → High")).join(" / ")}</strong>
    {" "}· {sortedTrials.length} trials
    {(sortRules[0]?.column==="level1"&&new Set(trials.map(t=>savedScores[t.nct]?.["1"])).size===1||
       sortRules[0]?.column==="gates"&&new Set(trials.map(t=>finalGateByNct.get(t.nct)?.independentlyVerified??null)).size===1)&&
       <div data-testid="focus-sort-all-tied-notice" style={{fontWeight:600,marginTop:4}}>
        All 32 trials have the same value for this column, so sorting it cannot change their score ranking.
       </div>}
    <div data-testid="focus-sort-confirmation-rows" style={{marginTop:4}}>
     First: {sortedTrials[0]?.ticker} ({sortedTrials[0]?.nct.slice(-4)}) ·
     Overall {sortedTrials[0]?savedScores[sortedTrials[0].nct]?.overall??"—":"—"}/100
     {" "} | Last: {sortedTrials.at(-1)?.ticker} ({sortedTrials.at(-1)?.nct.slice(-4)}) ·
     Overall {sortedTrials.at(-1)?savedScores[sortedTrials.at(-1)!.nct]?.overall??"—":"—"}/100
    </div>
   </>:<span>Original FOCUS trial order · {sortedTrials.length} trials. Apply a column sort to see the active order here.</span>}
  </div>
  <section className="focus-mobile-score-view" data-testid="focus-mobile-score-view"
   aria-label="FOCUS mobile score columns: Overall and Levels 1, 2, 3"
   style={{border:"1px solid #b9cebe",borderRadius:9,margin:"12px 0",padding:"8px 5px",background:"#fff"}}>
   <div style={{fontSize:13,fontWeight:700,margin:"2px 5px 8px"}}>All 32 trials · Overall + Level 1, 2, 3</div>
   <table style={{borderCollapse:"collapse",fontSize:12,width:"100%",tableLayout:"fixed"}}
     data-testid="focus-mobile-score-table">
    <colgroup><col style={{width:"24%"}}/><col style={{width:"19%"}}/>
     <col style={{width:"19%"}}/><col style={{width:"19%"}}/><col style={{width:"19%"}}/></colgroup>
    <thead style={{background:"#e6f2ea"}}>
     <tr><th scope="col" style={{textAlign:"left",padding:"9px 4px"}}>Ticker / trial</th>
      <th scope="col" style={{padding:"9px 2px"}}>Overall</th>
      <th scope="col" style={{padding:"9px 2px"}}>L01</th>
      <th scope="col" style={{padding:"9px 2px"}}>L02</th>
      <th scope="col" style={{padding:"9px 2px"}}>L03</th></tr>
    </thead>
    <tbody>{sortedTrials.map(t=><tr key={t.nct} style={{borderTop:"1px solid #dbe9de"}}>
     <th scope="row" style={{textAlign:"left",padding:"8px 4px",fontWeight:700}}>
      <Link href={"/predictions/assessment?nct="+encodeURIComponent(t.nct)}>{t.ticker}</Link>
      <div style={{fontSize:10,fontWeight:400}}>{t.nct.slice(-4)}</div>
     </th>
     {(["overall","1","2","3"] as const).map(key=><td
       key={key} data-testid={"focus-mobile-score-"+key} style={{
        textAlign:"center",padding:"8px 2px",fontWeight:key==="overall"?800:600,
        background:key==="overall"?"#eff7f0":undefined
       }}>{savedScores[t.nct]?.[key]??"—"}</td>)}
    </tr>)}</tbody>
   </table>
   <p style={{fontSize:11,margin:"8px 5px 3px",color:"#526458"}}>
    Provisional source-documentation readiness /100, not FDA approval predictions.
    Scores are from the dated 2026-11-15 snapshot unless 32 current reports reconcile.
   </p>
  </section>
  <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap",margin:"8px 0"}}>
   <button type="button" data-testid="focus-reset-horizontal-scroll"
    onClick={showScoreColumns}
    style={{padding:"9px 13px",border:"1px solid #789987",borderRadius:8,
      background:"#e6f2ea",fontWeight:700,color:"#173d2b",cursor:"pointer"}}>
    ◀ Show Overall + L01–L03 columns
   </button>
   <span style={{fontSize:12,color:"#526458"}}>In the full spreadsheet, this returns to the leftmost scores.</span>
  </div>
  <div ref={tableScrollRef} data-testid="focus-full-table-scroller"
    style={{overflowX:"auto",border:"1px solid #b9cebe",borderRadius:8}}>

  {/* Collapsed research columns are removed from the DOM, not just hidden
      with :has CSS, which was unreliable in the phone's table layout. */}
   <table className={surveyExpanded?"assessment-expandable survey-expanded":"assessment-expandable"} style={{width:"100%",borderCollapse:"collapse",minWidth:970,fontSize:14}}>
    <thead style={{background:"#e6f2ea"}}><tr><th style={{padding:10,textAlign:"left"}}>Ticker</th><FocusOverallHeaders expanded={surveyExpanded} onToggle={()=>setSurveyExpanded(v=>!v)}/><FocusTwentyHeaders startLevel={1} endLevel={3}/><th style={{padding:10,textAlign:"left"}}>NCT / Trial</th><th style={{padding:10,textAlign:"left"}}>Company</th><th style={{padding:10,textAlign:"left"}}>FDA Special Designations</th><th style={{padding:10,textAlign:"right"}}>Market cap ($B)</th><th style={{padding:10,textAlign:"left"}}>FDA / PDUFA path</th><th style={{padding:10}}>Sources</th><th style={{padding:10}}>7 gate checks</th>{surveyExpanded&&<FocusTwentyHeaders className="assessment-level" startLevel={4} endLevel={20}/>}<PredictionHeaders/><FocusLevelHeaders/></tr><tr><th colSpan={surveyExpanded?32:15}>Level 1-3 saved scientific research</th><FocusLevelSubheaders/></tr></thead>
    <tbody>{sortedTrials.map((t,i)=>{const gateAudit=finalGateByNct.get(t.nct);const d=designationByNct.get(t.nct);return <tr key={t.nct} style={{borderTop:"1px solid #dbe9de",background:i%2?"#f7faf8":"white"}}>
      <td style={{padding:10,fontWeight:700}}><TickerChartButton ticker={t.ticker}/></td><FocusOverviewCells nct={t.nct} levels={savedLevels[t.nct]}/><FocusTwentyCells nct={t.nct} levels={savedLevels[t.nct]} startLevel={1} endLevel={3}/>
      <td style={{padding:10}}><a href={"https://clinicaltrials.gov/study/"+t.nct} target="_blank" rel="noopener noreferrer">{t.nct}</a><div style={{marginTop:5,fontSize:12}}><Link href={"/analyze-now?nct="+encodeURIComponent(t.nct)}>View exact-trial research history</Link><div><Link href={"/assessments?nct="+encodeURIComponent(t.nct)+"#scientific456"}>L04–L06 saved scientific research</Link></div></div><details><summary>Exact-trial source intake</summary><ExactTrialIntakeSelector cohort="FOCUS" nctId={t.nct}/></details></td>
      <td style={{padding:10}}>{t.company}<CompanyDateBadges nctId={t.nct} timeline={null} recordedReleaseDate={"recordedReleaseDate" in t && typeof t.recordedReleaseDate==="string" ? t.recordedReleaseDate : null} recordedPdufaDate={"recordedPdufaDate" in t && typeof t.recordedPdufaDate==="string" ? t.recordedPdufaDate : null} releaseSource={t.resultsUrl} pdufaSource={t.regulatoryUrl}/></td>
      <td style={{padding:10,minWidth:220,verticalAlign:"top",fontSize:12}}>
       {d?.designations.length?<><strong>{d.designations.map(x=>x.label).join(" · ")}</strong>
        <details style={{marginTop:5}}><summary style={{cursor:"pointer"}}>Branch 6 · Regulatory evidence ({d.designations.length})</summary>
          {d.designations.map((x,i)=><div key={i} style={{padding:"7px 0",borderTop:"1px solid #dce7e0"}}>
           <strong>{x.label}</strong> · {x.kind.replaceAll("_"," ")} · {x.verification==="FDA_DOCUMENT"?"FDA document":"Sponsor/SEC report"}
           <div>{x.scope}</div>{x.grantDate&&<div>Recorded date: {x.grantDate}</div>}
           <a href={x.sourceUrl} target="_blank" rel="noopener noreferrer">Original designation evidence</a>
          </div>)}
        </details>
        <details style={{marginTop:5}}><summary style={{cursor:"pointer"}}>Branch 7 · FDA precedents and failure checks</summary>
          <div>Check whether historical FDA decisions for the same indication and regulatory pathway required additional studies, revised labeling, CMC changes or resulted in a CRL.</div>
          <div>Unknown: confidential FDA feedback, inspection outcomes, and whether the designation changes this application's approval risk.</div>
          <div>Designation alone is not proof of approval or a favorable forecast. No historical comparator adjudication completed here.</div>
        </details>
       </>:<span title={d?.notes||"No confirmed special designation for exact drug and indication; not a claim that no designation exists."}>Not verified</span>}
       </td>
      <td style={{padding:10,textAlign:"right"}}>{(t.marketCap/1e9).toFixed(2)}</td>
      <td style={{padding:10}}>{t.fdaStatus}</td>
      <td style={{padding:10,whiteSpace:"nowrap"}}><a href={t.resultsUrl} target="_blank" rel="noopener noreferrer">Phase 3 source</a>{" · "}<a href={t.regulatoryUrl} target="_blank" rel="noopener noreferrer">FDA source</a></td>
      <td style={{padding:10,minWidth:240,verticalAlign:"top"}}>{gateAudit?<details><summary style={{cursor:"pointer",fontWeight:650}}>{gateAudit.independentlyVerified} / {gateAudit.gates.length} verified · expand</summary>
        <div style={{fontSize:12,margin:"9px 0 0"}}>{gateAudit.gates.map(g=><div key={g.id} style={{borderTop:"1px solid #dbe9de",padding:"7px 0"}}>
          <strong>{g.title}</strong><div>{g.state==="RECORDED_POINTER"?"Source pointer only":g.state==="SOURCE_REVIEW_REQUIRED"?"Needs source review":"Missing evidence"}</div>
          <div>{g.note}</div>{g.sourceUrl&&<a href={g.sourceUrl} target="_blank" rel="noopener noreferrer">Inspect source</a>}
        </div>)}</div>
      </details>:<span role="alert">Gate identity mismatch — not verified</span>}</td>{surveyExpanded&&<FocusTwentyCells nct={t.nct} levels={savedLevels[t.nct]} className="assessment-level" startLevel={4} endLevel={20}/>}<PredictionCells nct={t.nct}/><FocusLevelCells nct={t.nct} levels={savedLevels[t.nct]}/>
    </tr>;})}</tbody>
   </table>
  </div>
  <p data-testid="focus-owner-only" style={{padding:"10px 12px",background:"#eefaf5",border:"1px solid #b9cebe",borderRadius:8}}>
    <strong>OWNER-ONLY LEVELS 1–20:</strong> You check and accept FOCUS assessments.
    No external scientific reviewer, source attestor, independent challenger, or third-party signoff is required.
    Original source links, missing-evidence flags, and safety and phase checks remain.
  </p>
  <AssessmentLauncher source="FOCUS"/><FocusSavedAssessments/><details><summary style={{cursor:"pointer",fontWeight:700}}>L04–L06 scientific research · saved versions, evidence gaps, historical mode</summary><Scientific456Workspace cohort="FOCUS"/></details><ScientificStepsReadiness cohort="FOCUS"/>
  <IndicationIntelligence mode="focus"/>
  <p><strong>{trials.length} distinct NCT trials</strong> · Final-list Phase 3 / post-Phase 3 candidates · Reported $300M–$10B market caps · Source-linked FDA pathways for owner checks; no external verification gate.</p>
  <p>Snapshot of the final Google Sheets list as of {snapshot.asOf}. Recorded listing, readout and FDA-path links are evidence pointers, not an owner-reviewed finding of trial eligibility or a successful nightly sync. Completed trials remain if their program may continue toward approval. No retired or historical research-only cohort is included.</p>
  <p><a href={source} target="_blank" rel="noopener noreferrer" style={{fontWeight:700}}>Open and edit the source-of-truth FOCUS spreadsheet</a></p>
  <p><Link href="/analyze-now?nct=NCT06081894">Open Analyze Now · PostgreSQL-backed saved research canary</Link> · Requires secure backend readiness; no FDA probabilities are released.</p>
  <p style={{fontSize:13}}>Active research uses clinical and regulatory source observations. Historical ratings are retained separately in the read-only archive and do not contribute to this view.</p>
  <section aria-label="Final trial gate coverage" style={{border:"1px solid #b9cebe",padding:14,borderRadius:8,marginBottom:14}}>
    <h2 style={{margin:"0 0 8px",fontSize:18}}>Acceptance gates · final FOCUS trials only</h2>
    <p style={{margin:"0 0 7px"}}><strong>{finalGateAudit.trialCount} exact NCTs</strong> from the dated FOCUS list · <strong>{finalGateAudit.checksPerTrial} checks per trial</strong> · <strong>{finalGateAudit.totalChecks} trial checks</strong>.</p>
    <p style={{margin:"0 0 7px"}}>Owner-reviewed assessments: <strong>0</strong> · Source pointers recorded: {finalGateAudit.pointers} · Awaiting source review: {finalGateAudit.review} · Missing evidence: {finalGateAudit.missing}.</p>
    <p style={{fontSize:13,margin:0}}>Only these exact final-list NCTs are evaluated; the early-phase POOL, historical Phase 3 census and all-phase TOOLS counts are not included. Recorded links or scheduled jobs are not completed clinical, regulatory or live synchronization verification. Current list as of {finalGateAudit.asOf}.</p>
  </section>
  <PredictionLegend/><p style={{fontSize:12,color:"#4f6556",marginTop:15}}>Some entries are planned NDA/BLA filings rather than FDA-accepted submissions. Source snapshots require continued review.</p>
 </main>;
}
