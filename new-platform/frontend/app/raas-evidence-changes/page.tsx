/** Nightly source-change history; research signals only, no RAAS score mutation. */
import type {Metadata} from "next";
import Link from "next/link";
import savedHistory from "../../data/raas-registry-evidence-change-history.json";
import savedStatus from "../../data/raas-registry-evidence-change-status.json";
import css from "../raas-history/page.module.css";

export const metadata:Metadata={
 title:"RAAS · Trial Evidence Change History | PDUFA",
 description:"Dated ClinicalTrials.gov source revisions for exact NCT trials, with independent review flags and preserved source hashes."
};
type ChangeCategory=
 "RESULTS_FIRST_POSTED"|"RESULTS_POSTING_REVERSED"|
 "PRIMARY_OUTCOME_RESULTS_CHANGED"|"SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED"|
 "PRIMARY_ENDPOINT_PROTOCOL_CHANGED"|"TRIAL_DESIGN_CHANGED"|
 "TRIAL_CONTEXT_CHANGED"|"TRIAL_STATUS_CHANGED"|
 "RESULTS_PUBLICATION_DATE_CHANGED"|"REGISTRY_LAST_UPDATED_DATE_CHANGED"|
 "OTHER_OFFICIAL_SOURCE_PACKET_UPDATE";
type Summary={postedResults:boolean;registryStatus:string|null;
 registryLastUpdated:string|null;resultsFirstPosted:string|null;
 postedPrimaryOutcomeCount:number;seriousAdverseEventTermCount:number;
 primaryResultCount:number};
type Event={
 eventId:string;observedAt:string;nctId:string;ticker:string;sourceUrl:string;
 previousSourceHash:string;newSourceHash:string;changeCategories:ChangeCategory[];
 reviewFlag:"CLINICAL_OR_DESIGN_REVIEW_REQUIRED"|"OTHER_OFFICIAL_REGISTRY_UPDATE";
 candidateResearchMetricIds:string[];before:Summary;after:Summary;
 approvedRaasScore:null;calibratedFdaProbability:null;note:string;
};
type Status={
 auditState:string;previousSourceAsOf:string|null;latestSourceAsOf:string|null;
 recordedAt:string|null;trackedResearchNcts:number;sourceFetchAttempted:number;
 sourceFetchSucceeded:number;sourceFetchFailed:number;
 sourceHashChangedNcts:number;changedNctsThisAudit:number;
 reviewNeededNctsThisAudit:number;firstPostedRegistryResultsThisAudit:number;
 changedPrimaryResultsThisAudit:number;changedSafetyEvidenceThisAudit:number;
 changedPrimaryProtocolOrDesignThisAudit:number;totalRetainedHistoricalEvents:number;
 approvedRaasScoreUpdates:0;calibratedFdaForecastUpdates:0;scopeNote:string;
};
const records=savedHistory as unknown as {events:Event[];scope:string};
const status=savedStatus as unknown as Status;
const categoryLabel:Record<ChangeCategory,string>={
 RESULTS_FIRST_POSTED:"First registry results posting",
 RESULTS_POSTING_REVERSED:"Posted-results state reversed",
 PRIMARY_OUTCOME_RESULTS_CHANGED:"Primary outcome results revised",
 SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED:"Serious adverse-event data revised",
 PRIMARY_ENDPOINT_PROTOCOL_CHANGED:"Registered primary endpoint changed",
 TRIAL_DESIGN_CHANGED:"Trial design changed",
 TRIAL_CONTEXT_CHANGED:"Registered trial context changed",
 TRIAL_STATUS_CHANGED:"Registry study status changed",
 RESULTS_PUBLICATION_DATE_CHANGED:"Registry results-post date revised",
 REGISTRY_LAST_UPDATED_DATE_CHANGED:"Registry last-update date changed",
 OTHER_OFFICIAL_SOURCE_PACKET_UPDATE:"Other official source-packet revision"
};
const badgeStyle={border:"1px solid #c8ddcd",borderRadius:7,
 background:"#f2f8f4",padding:"8px 10px",fontSize:12} as const;
const filterField={border:"1px solid #bad1c1",borderRadius:6,
 background:"#fff",color:"#143a27",padding:8,fontSize:12} as const;
type Params={nctId?:string|string[];ticker?:string|string[];
 kind?:string|string[];page?:string|string[]};
const first=(x:string|string[]|undefined)=>typeof x==="string"?x:"";
const limit=30;
export default async function RegistryChangeHistoryPage({
 searchParams
}:{searchParams:Promise<Params>}){
 const query=await searchParams;
 const nctId=first(query.nctId).toUpperCase().trim().slice(0,40);
 const ticker=first(query.ticker).toUpperCase().trim().slice(0,24);
 const kind=first(query.kind);
 const allowed=new Set(["all","review","efficacy","safety","protocol","source"]);
 const selection=allowed.has(kind)?kind:"all";
 const events=records.events.filter(e=>
  (!nctId||e.nctId.includes(nctId))&&
  (!ticker||e.ticker.toUpperCase().includes(ticker))&&
  (selection==="all"||
   (selection==="review"&&e.reviewFlag==="CLINICAL_OR_DESIGN_REVIEW_REQUIRED")||
   (selection==="efficacy"&&e.changeCategories.some(c=>
    ["RESULTS_FIRST_POSTED","PRIMARY_OUTCOME_RESULTS_CHANGED",
     "RESULTS_POSTING_REVERSED"].includes(c)))||
   (selection==="safety"&&e.changeCategories.includes("SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED"))||
   (selection==="protocol"&&e.changeCategories.some(c=>
    ["PRIMARY_ENDPOINT_PROTOCOL_CHANGED","TRIAL_DESIGN_CHANGED",
     "TRIAL_CONTEXT_CHANGED"].includes(c)))||
   (selection==="source"&&e.reviewFlag==="OTHER_OFFICIAL_REGISTRY_UPDATE"))
 ).reverse();
 const pages=Math.max(1,Math.ceil(events.length/limit));
 const parsed=Number.parseInt(first(query.page),10);
 const page=Number.isFinite(parsed)&&parsed>0?Math.min(parsed,pages):1;
 const display=events.slice((page-1)*limit,page*limit);
 const href=(newPage:number)=>{
  const params=new URLSearchParams();
  if(nctId)params.set("nctId",nctId);
  if(ticker)params.set("ticker",ticker);
  if(selection!=="all")params.set("kind",selection);
  params.set("page",String(newPage));
  return "/raas-evidence-changes?"+params.toString();
 };
 return <main className={css.root} data-raas-registry-source-change-history="ungraded">
  <header className={css.header}>
   <Link className={css.back} href="/raas-evidence-backlog">
    ← Back to 762-trial research evidence queue</Link>
   <h1>RAAS · nightly trial evidence changes</h1>
   <p>Source-frozen ClinicalTrials.gov revisions, separated from historic
    ratings. Click any trial to inspect what changed, its previous and current
    source fingerprint, and which RAAS research metrics may require reassessment.</p>
  </header>
  <p className={css.disclaimer}>
   <strong>Research-only source-change monitor.</strong> This checks the saved
   registry source before and after each successful scheduled collection.
   An NCT record changing is not proof of a Phase 3 public readout or
   an FDA PASS, CRL or EXTENSION. No source revision automatically
   creates or changes a RAAS grade, score, or calibrated forecast.
   Retired GEM / GEM JR scans are not involved.
  </p>
  <section className={css.stats} data-raas-registry-last-diff={status.auditState}>
   {([
    [status.trackedResearchNcts,"Research NCTs tracked, not current Pipeline-eligible"],
    [status.changedNctsThisAudit,"NCTs with changed official source packet · last comparison"],
    [status.reviewNeededNctsThisAudit,"New clinical/design review flags · last comparison"],
    [status.firstPostedRegistryResultsThisAudit,"Newly posted registry results · last comparison"],
    [status.sourceFetchFailed,"Failed source fetches · last comparison"],
    [status.totalRetainedHistoricalEvents,"Retained historical revision events"]
   ] as const).map(([v,label])=><div key={label}>
    <strong>{v}</strong><span>{label}</span>
   </div>)}
  </section>
  <p className={css.notice}>
   <strong>Audit state: {status.auditState.replaceAll("_"," ")}.</strong>
   {" "}{status.recordedAt?
    <>Comparison recorded {status.recordedAt}. Old snapshot{" "}
     {status.previousSourceAsOf}, new snapshot {status.latestSourceAsOf}.
     The latest collection successfully retrieved {status.sourceFetchSucceeded} of{" "}
     {status.sourceFetchAttempted} NCTs.</>:
    <>The change history is initialized, but no completed before/after
     nightly comparison has been published yet. Zero new events is
     <strong> not evidence of zero changes</strong>.</>}
   {" "}Source-retrieval errors are tracked independently; they never count
   as no new clinical results.
  </p>
  <section className={css.section}>
   <div className={css.sectionTitle}>
    <h2>Trial source revision history</h2>
    <a href="/api/raas-registry-evidence-changes" download
     style={badgeStyle}>Export all retained events (CSV)</a>
   </div>
   <form method="get" action="/raas-evidence-changes"
    style={{display:"flex",gap:9,flexWrap:"wrap",alignItems:"end",marginBottom:16}}>
    <label style={{display:"grid",gap:4,fontSize:12,fontWeight:700}}>
     NCT ID
     <input name="nctId" defaultValue={nctId}
      placeholder="NCT..." maxLength={40} style={filterField}/>
    </label>
    <label style={{display:"grid",gap:4,fontSize:12,fontWeight:700}}>
     Ticker
     <input name="ticker" defaultValue={ticker}
      placeholder="Ticker" maxLength={24} style={filterField}/>
    </label>
    <label style={{display:"grid",gap:4,fontSize:12,fontWeight:700}}>
     Change type
     <select name="kind" defaultValue={selection} style={filterField}>
      <option value="all">All changes</option>
      <option value="review">Independent review needed</option>
      <option value="efficacy">New/revised efficacy outcomes</option>
      <option value="safety">Revised serious safety evidence</option>
      <option value="protocol">Protocol, design or trial context</option>
      <option value="source">Administrative/source-only revisions</option>
     </select>
    </label>
    <button type="submit" style={filterField}>Apply filters</button>
    <Link href="/raas-evidence-changes">Clear filters</Link>
   </form>
   <p style={{fontSize:12}}>
    {events.length} matching retained source revisions · page {page} of {pages}.
    Revisions are shown newest first; each recorded observation time
    is when the system saw the change, not the source's original event date.
   </p>
   {display.length===0?<p className={css.notice}>
    {status.recordedAt?
     "No retained source revisions match these filters. This does not establish missing historical outcomes.":
     "No source-change events have been captured yet. Future successful nightly comparisons populate this view."}
   </p>:<div style={{display:"grid",gap:10}}>
    {display.map(event=><details key={event.eventId}
      data-raas-source-revision-nct={event.nctId}
      style={{border:"1px solid #d0e2d6",borderRadius:9,background:"#fff",padding:12}}>
     <summary style={{cursor:"pointer",display:"flex",
      flexWrap:"wrap",justifyContent:"space-between",gap:10}}>
      <span style={{display:"grid",gap:3}}>
       <strong>{event.ticker} · {event.nctId}</strong>
       <small>Detected {event.observedAt}</small>
       <small>{event.changeCategories.map(c=>categoryLabel[c]).join(" · ")}</small>
      </span>
      <strong style={{fontSize:12}}>
       {event.reviewFlag==="CLINICAL_OR_DESIGN_REVIEW_REQUIRED"?
        "Independent review required":"Source update only"} ▸
      </strong>
     </summary>
     <div style={{display:"grid",gap:10,fontSize:12,lineHeight:1.6,marginTop:14}}>
      <p><strong>Previous source hash:</strong> <code>{event.previousSourceHash}</code></p>
      <p><strong>New source hash:</strong> <code>{event.newSourceHash}</code></p>
      <p><strong>Registered results before → after:</strong>{" "}
       {String(event.before.postedResults)} → {String(event.after.postedResults)}.
       {" "}Primary outcomes {event.before.postedPrimaryOutcomeCount} →{" "}
       {event.after.postedPrimaryOutcomeCount}; serious event terms{" "}
       {event.before.seriousAdverseEventTermCount} →{" "}
       {event.after.seriousAdverseEventTermCount}.
      </p>
      <p><strong>Original registry updated date:</strong>{" "}
       {event.before.registryLastUpdated||"not stated"} →{" "}
       {event.after.registryLastUpdated||"not stated"}.
       {" "}Results first posted: {event.after.resultsFirstPosted||"not stated"}.
      </p>
      <p><strong>Candidate metrics for research recheck:</strong>{" "}
       {event.candidateResearchMetricIds.join(", ")||"No specific metrics assigned"}.
       These are prompts to review evidence, not changes to stored grades.
      </p>
      <p>{event.note}</p>
      <p><a href={event.sourceUrl} target="_blank" rel="noopener noreferrer">
       Open original official ClinicalTrials.gov record</a>
       {" "}· <Link href={"/raas-trial-review?"+new URLSearchParams({
        nctId:event.nctId,ticker:event.ticker
       }).toString()}>Open exact trial 60-metric RAAS review</Link>
      </p>
     </div>
    </details>)}
   </div>}
   {pages>1&&<nav aria-label="Registry evidence source change history pages"
    style={{display:"flex",alignItems:"center",gap:14,marginTop:18}}>
    {page>1&&<Link href={href(page-1)}>Previous page</Link>}
    <span>Page {page} / {pages}</span>
    {page<pages&&<Link href={href(page+1)}>Next page</Link>}
   </nav>}
  </section>
  <p className={css.foot}>
   Append-only source-change entries retain the prior and current official
   source hashes. The full original source can still evolve on ClinicalTrials.gov;
   this is an audit of what the collector observed, not an FDA adjudication
   or archival reproduction of all versions. Historical RAAS score
   timestamps remain untouched.
  </p>
 </main>;
}
