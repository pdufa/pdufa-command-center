/** Read-only 60-metric validation worklist; never use evidence coverage as an
 * investment rating. This route is linked from both Phase 3 spreadsheets.
 */
import type {Metadata} from "next";
import Link from "next/link";
import {buildRaasMetricValidationWorklist,raasDocumentedTrialOptions,type RaasWorklistTrial} from "../../lib/raas-metric-validation-worklist";
import type {RaasStage} from "../../lib/raas-metric-specs";
import css from "./page.module.css";

export const metadata:Metadata={
 title:"RAAS TOP/BOTTOM · 60 Metric Validation Worklist | PDUFA",
 description:"All 60 risk-adjusted appreciation assessment metrics, exact-trial source evidence and unapproved calibration gaps."
};
type Params={stage?:string|string[];nctId?:string|string[];ticker?:string|string[];
 drug?:string|string[];indication?:string|string[]};
const first=(x:string|string[]|undefined)=>typeof x==="string"?x:"";
const safe=(x:string)=>x.length<=200?x:"";
function hrefForTrial(t:RaasWorklistTrial|null,stage:RaasStage):string{
 const args=new URLSearchParams({stage});
 if(t){
  args.set("nctId",t.nctId);args.set("ticker",t.ticker);
  if(t.drug)args.set("drug",t.drug);
  if(t.indication)args.set("indication",t.indication);
 }
 return "/raas-worklist?"+args.toString()+"#raas-"+(stage==="pre"?"top":"bottom")+"-worklist";
}
export default async function RaasWorklistPage({searchParams}:{searchParams:Promise<Params>}){
 const q=await searchParams;
 const anchorStage:RaasStage=first(q.stage)==="post"?"post":"pre";
 const rawNct=first(q.nctId),rawTicker=first(q.ticker);
 const trial= /^NCT\d{8}$/.test(rawNct)&&/^[A-Z0-9.\-]{1,12}$/.test(rawTicker)?
  {nctId:rawNct,ticker:rawTicker,drug:safe(first(q.drug)),indication:safe(first(q.indication))}:null;
 const invalidContext=!!(rawNct||rawTicker)&&trial===null;
 const data=buildRaasMetricValidationWorklist(trial);
 const available=raasDocumentedTrialOptions();
 return <main className={css.root} data-raas-validation-worklist={data.scope}>
  <header className={css.header}>
   <Link href="/tools" className={css.back}>← TOP / BOTTOM spreadsheets</Link>
   <h1>RAAS · 60-metric validation worklist</h1>
   <p>Thirty TOP pre-readout metrics and thirty BOTTOM post-readout metrics, each with its required source, current evidence leads, missing verification and calibration status.</p>
  </header>
  <div className={css.stats}>
   <div><strong>60 / 60</strong><span>Metric requirements inventoried</span></div>
   <div><strong>{data.approvedCalibrations} / 60</strong><span>Independently approved calibrations</span></div>
   <div><strong>{data.sourceMappedMetrics} / 60</strong><span>{trial?"Source-mapped metric areas for the selected trial across both stages":"Source-mapped areas in saved research across both stages"}</span></div>
   <div><strong>— / 100</strong><span>Overall RAAS remains unapproved</span></div>
  </div>
  <p className={css.notice}><strong>Research worklist, not a trading score.</strong> A single source lead does not establish a verified metric assessment, FDA approval probability, or expected stock appreciation. Missing evidence receives no 0/100 grade. Snapshot: {data.sourceAsOf}; all 60 metrics remain subject to historical holdout and source-time checks.</p>
  <nav className={css.stageNav} aria-label="Jump to TOP or BOTTOM RAAS metrics">
   <Link href={hrefForTrial(trial,"pre")} aria-current={anchorStage==="pre"?"location":undefined}>TOP · 30 metrics</Link>
   <Link href={hrefForTrial(trial,"post")} aria-current={anchorStage==="post"?"location":undefined}>BOTTOM · 30 metrics</Link>
   <Link href="/raas-scan">Full 60-metric readiness scan</Link>
  </nav>
  <section className={css.context} aria-label="Trial source filter">
   <h2>Evidence context</h2>
   {invalidContext&&<p className={css.notice}>Invalid trial identity in the URL. Showing global source examples; no trial-specific score is inferred.</p>}
   <p>{trial?
    <>Exact trial <strong>{trial.ticker} · {trial.nctId}</strong>{trial.drug?" · "+trial.drug:""}{trial.indication?" · "+trial.indication:""}. Sources are matched by NCT, issuer, stage and supplied therapy identity.</>:
    <>All saved example programs. A source attached to another trial is never an approved grade or a source for the trial you are researching.</>}</p>
   <div className={css.trials}>
    <Link href="/raas-worklist" className={!trial?css.selected:undefined}>All source examples</Link>
    {available.map(t=><Link key={(t.stage||"")+"|"+t.nctId+"|"+t.ticker}
      href={hrefForTrial(t,t.stage||"pre")}
      className={trial?.nctId===t.nctId&&trial.ticker===t.ticker?css.selected:undefined}>
      {t.stage==="pre"?"TOP":"BOTTOM"} · {t.ticker} · {t.nctId}
     </Link>)}
   </div>
  </section>
  {(["pre","post"] as const).map(stage=>{
   const stageItems=data.items.filter(x=>x.stage===stage);
   const stats=data.byStage[stage];
   const groups=[...new Map(stageItems.map(x=>[x.groupId,{id:x.groupId,name:x.group,weight:x.groupWeight}])).values()];
   return <section id={"raas-"+(stage==="pre"?"top":"bottom")+"-worklist"} className={css.stage} key={stage}
    data-raas-worklist-stage={stage}>
    <div className={css.stageTitle}>
     <div><span className={css.eyebrow}>{stage==="pre"?"TOP · BEFORE PHASE 3 RESULTS":"BOTTOM · AFTER PHASE 3 RESULTS"}</span>
      <h2>{stage==="pre"?"TOP-RAAS":"BOTTOM-RAAS"} · all 30 metrics</h2></div>
     <strong>{stats.mapped}/30 linked to source examples · {stats.calibrated}/30 calibrated</strong>
    </div>
    <p className={css.muted}>Six scored categories, each with five metric requirements. Expand any category and then any metric to inspect source evidence, blockers and the exact requirements for approval.</p>
    {groups.map(group=>{
     const g=stageItems.filter(x=>x.groupId===group.id);
     const linked=g.filter(x=>x.sourceCount>0).length;
     return <details key={group.id} className={css.group} data-raas-validation-group={stage+"|"+group.id}>
      <summary><strong>{group.name}</strong><span>{linked}/5 source-linked · {group.weight}% category weight · 0 approved trial grades</span><i aria-hidden="true">▸</i></summary>
      <div className={css.groupBody}>
       {g.map(metric=><details key={metric.id} className={css.metric}
         data-raas-validation-metric={metric.id}>
        <summary>
         <span className={css.metricName}><small>{metric.id}</small><strong>{metric.name}</strong></span>
         <span className={metric.sourceCount?css.sourceLinked:css.sourceMissing}>{metric.sourceCount?metric.sourceCount+" source lead(s)":"No mapped sources"}</span>
         <span className={css.unapproved}>Grade pending</span>
         <i aria-hidden="true">▸</i>
        </summary>
        <div className={css.metricBody}>
         <div className={css.infoRow}><strong>Required evidence</strong><p>{metric.requiredEvidence}</p></div>
         <div className={css.infoRow}><strong>Proposed scoring interpretation (not calibrated)</strong><p>{metric.scoreRule}</p></div>
         <div className={css.infoRow}><strong>Critical risk to investigate</strong><p>{metric.criticalRisk}</p></div>
         <div className={css.infoRow}><strong>Preliminary assessment</strong><p>{metric.sourceCount?"Dated research leads identified; effect, quality, uncertainty and rating still unreviewed.":"No metric-specific lead in the selected saved source context. Nothing has been graded."}</p></div>
         <div className={css.reviewGrid}>
          <div><span>Validated metric score</span><strong>— / 100 · pending</strong></div>
          <div><span>Calibration approval</span><strong>{metric.calibrationApproved?"Approved, trial assessment still pending":"Not approved"}</strong></div>
          <div><span>Issuer-disjoint train / holdout</span><strong>{metric.historicalTrainIssuers} / 30 · {metric.historicalHoldoutIssuers} / 30</strong></div>
          <div><span>Held-out high / low groups</span><strong>{metric.historicalHighHoldoutIssuers} / 5 · {metric.historicalLowHoldoutIssuers} / 5</strong></div>
         </div>
         <h4>Recorded metric-specific sources · {metric.sourceCount}</h4>
         {metric.sourceLeads.length===0?<p className={css.muted}>No dated source linked to this metric for the selected context. Other trials' evidence is not substituted.</p>:
          <ul className={css.evidenceList}>{metric.sourceLeads.map(source=>
           <li key={source.origin+"|"+source.nctId+"|"+source.id}>
            <strong>{source.ticker} · {source.nctId} · {source.title}</strong>
            <span>{source.date} · {source.origin==="PROSPECTIVE"?"Recorded prospective source lead":"Historical pilot observation"}</span>
            <p>{source.note}</p>
            <a href={source.sourceUrl} target="_blank" rel="noopener noreferrer">Open dated source</a>
           </li>)}</ul>}
         <h4>What is missing before an approved grade?</h4>
         <ol className={css.missingList}>{metric.missingRequirements.map((s,i)=><li key={i}>{s}</li>)}</ol>
         <p className={css.muted}><strong>Historical audit:</strong> {metric.readinessReason}</p>
        </div>
       </details>)}
      </div>
     </details>;
    })}
   </section>;
  })}
  <footer className={css.footer}>
   <strong>Release gate: not passed</strong>
   <p>Historical FDA target-year census, same-issuer share continuity, independent price confirmation, predeclared metric thresholds, 30/30 disjoint holdout and exact trial reviews are still required. This page is generated from the dated, committed RAAS research feeds; it does not claim live FDA or brokerage market updates.</p>
   <Link href="/tools#tools-phase3-release-sheets">Return to TOP and BOTTOM spreadsheets</Link>
  </footer>
 </main>;
}
