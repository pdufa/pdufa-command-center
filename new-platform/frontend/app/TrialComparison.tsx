"use client";

import {useEffect,useMemo,useState,type CSSProperties} from "react";
import {parseBenefitFeed,type BenefitFeed,type BenefitFact} from "../lib/benefit-assessments";
import type {PipelineResearchRow} from "../lib/pipeline-research-view";
import {
  screenComparisonCandidates,trialComparisonKey,comparisonSnapshot,comparisonCaveat
} from "../lib/trial-comparison";

type PageResponse={view:string;offset:number;limit:number;total:number;rows:PipelineResearchRow[];
  nextOffset:number|null;datasetVersion:string};
type SelectedTrial={key:string;row:PipelineResearchRow;
  evidence:ReturnType<typeof comparisonSnapshot>};

const panel:CSSProperties={background:"#fff",border:"1px solid #d5dee8",borderRadius:10,
  padding:16,marginBottom:16};
const control:CSSProperties={border:"1px solid #9caec0",borderRadius:6,padding:"9px 10px",
  background:"#fff",color:"#10233a",width:"100%",maxWidth:"100%",fontSize:14};
const muted:CSSProperties={color:"#52677d",fontSize:13};
const heading:CSSProperties={textAlign:"left",padding:"12px 10px",borderBottom:"1px solid #ccd6e0"};
const cell:CSSProperties={padding:"12px 10px",borderBottom:"1px solid #e1e7ee",
  verticalAlign:"top",minWidth:200};
const button:CSSProperties={border:"1px solid #345b7d",background:"#163a59",color:"white",
  borderRadius:7,padding:"10px 12px",cursor:"pointer"};

async function loadScreenedPipeline(signal:AbortSignal):Promise<PipelineResearchRow[]>{
  const rows:PipelineResearchRow[]=[];
  let next=0,total:number|null=null,version:string|null=null;
  for(let batch=0;batch<100;batch++){
    const response=await fetch("/api/scope-funnel?view=pipeline&offset="+next+"&limit=200",
      {signal,cache:"no-store"});
    if(!response.ok)throw Error(response.status===401?"Sign in to review Pipeline trials":
      "Verified Pipeline research is unavailable ("+response.status+")");
    const page=await response.json() as PageResponse;
    if(page.view!=="pipeline"||page.offset!==next||page.limit!==200
      ||!Number.isSafeInteger(page.total)||page.total<0||page.total>20000
      ||!Array.isArray(page.rows)||page.rows.length>200||!page.datasetVersion
      ||(total!==null&&(page.total!==total||page.datasetVersion!==version)))
      throw Error("Pipeline source changed or returned an invalid page. Comparison withheld.");
    total=page.total;
    version=page.datasetVersion;
    rows.push(...page.rows);
    if(rows.length>page.total)throw Error("Pipeline research pagination count invalid");
    if(page.nextOffset===null){
      if(rows.length!==page.total)throw Error("Incomplete Pipeline research; comparison withheld");
      return screenComparisonCandidates(rows);
    }
    if(page.nextOffset!==next+page.rows.length||page.nextOffset<=next)
      throw Error("Pipeline pagination was inconsistent; comparison withheld");
    next=page.nextOffset;
  }
  throw Error("Pipeline research could not be retrieved completely");
}

const describe=(r:PipelineResearchRow)=>
  r.ticker+" · "+(r.drug||"Unknown therapy")+" · "+(r.indication||"Unverified indication")+" · "+r.nctId;
const number=(v:number)=>v.toLocaleString("en-US");
function Fact({fact}:{fact:BenefitFact|null}){
  if(!fact)return <span style={muted}>Not assessed</span>;
  return <div>
    <span>{String(fact.value)} {fact.status==="MODELED"?"(modeled; not verified)":""}</span>
    <div style={muted}>{fact.status==="VERIFIED"?"Source verified":"Scenario"} · {fact.confidence}
      {" · "}source {fact.sourceDate}</div>
    <details>
      <summary style={{cursor:"pointer",fontSize:13}}>Method and source</summary>
      <p style={muted}>{fact.method}</p>
      <a href={fact.sourceUrl} rel="noopener noreferrer" target="_blank">Read original source</a>
    </details>
  </div>;
}

export default function TrialComparison(){
  const [all,setAll]=useState<PipelineResearchRow[]>([]);
  const [feed,setFeed]=useState<BenefitFeed|null>(null);
  const [chosen,setChosen]=useState<string[]>(["",""]);
  const [filter,setFilter]=useState("");
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [benefitWarning,setBenefitWarning]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    void loadScreenedPipeline(controller.signal)
      .then(rows=>{if(!controller.signal.aborted)setAll(rows);})
      .catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:"Pipeline unavailable");})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    void fetch("/api/benefit-assessments",{signal:controller.signal,cache:"no-store"})
      .then(async response=>{
        if(!response.ok)throw Error("Verified benefit feed unavailable");
        return parseBenefitFeed(await response.json());
      })
      .then(result=>{if(!controller.signal.aborted)setFeed(result);})
      .catch(()=>{if(!controller.signal.aborted)setBenefitWarning(
        "Benefit evidence feed is unavailable. No verified benefit findings can be displayed.");});
    return ()=>controller.abort();
  },[]);

  const options=useMemo(()=>{
    const query=filter.trim().toLowerCase();
    const matches=query?all.filter(row=>describe(row).toLowerCase().includes(query)):all;
    return {matching:matches.length,shown:matches.slice(0,150)};
  },[all,filter]);
  const lookup=useMemo(()=>new Map(all.map(row=>[trialComparisonKey(row),row])),[all]);
  const selected=useMemo(()=>
    chosen.map(key=>{
      const row=lookup.get(key);
      return row?{key,row,evidence:comparisonSnapshot(row,feed)}:null;
    }),[chosen,lookup,feed]);
  const present=selected.filter((t):t is SelectedTrial=>t!==null);
  const canCompare=present.length>=2&&present.length===new Set(present.map(t=>t.key)).size;
  const edit=(index:number,key:string)=>setChosen(before=>before.map((value,i)=>i===index?key:value));
  const caveat=comparisonCaveat(present.map(t=>t.row));

  return <main style={{background:"#f4f7fa",color:"#10233a",minHeight:"100vh",
    padding:"24px max(12px, 3vw)",fontFamily:"Arial, sans-serif"}}>
    <div style={{maxWidth:1650,margin:"0 auto"}}>
      <p style={{...muted,textTransform:"uppercase",fontWeight:700}}>PDUFA · PIPELINE RESEARCH</p>
      <h1 style={{fontSize:30,margin:"8px 0"}}>Compare Trials</h1>
      <p style={{maxWidth:1050,lineHeight:1.6}}>
        Compare the same 20 benefit assessment groups for two or more exact-NCT research records.
        This view uses the existing screened post-Phase 3 Pipeline and independently sourced benefit facts.
        It does not treat registry completion as proof of positive Phase 3 results or FDA eligibility.
      </p>

      <section style={panel} aria-label="Trial selection">
        <h2 style={{fontSize:19,marginTop:0}}>Select trials to compare</h2>
        <p style={muted}>Screened records: {loading?"Loading…":error?"Unavailable":number(all.length)}.
          Historical market-cap screening is not live issuer qualification.</p>
        {error&&<p role="alert" style={{color:"#a32020"}}>{error}</p>}
        {benefitWarning&&<p role="status" style={{color:"#9a5810"}}>{benefitWarning}</p>}
        <label htmlFor="compare-search" style={{display:"block",fontWeight:700,marginBottom:6}}>
          Search ticker, drug, indication or NCT
        </label>
        <input id="compare-search" style={{...control,maxWidth:700}} value={filter}
          onChange={event=>setFilter(event.target.value)} placeholder="Type a ticker, drug, indication or NCT ID"/>
        <p style={muted}>Showing {options.shown.length} of {options.matching} matching records.
          Refine the search to find a specific trial.</p>
        <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit, minmax(240px,1fr))",gap:12,marginTop:14}}>
          {chosen.map((value,index)=><div key={index} style={{minWidth:0}}>
            <label htmlFor={"compare-choice-"+index} style={{fontWeight:700,display:"block",marginBottom:6}}>
              Trial {String.fromCharCode(65+index)}
            </label>
            <select id={"compare-choice-"+index} style={control} value={value}
              onChange={event=>edit(index,event.target.value)} disabled={loading||!!error}>
              <option value="">Choose a trial</option>
              {value&&!options.shown.some(row=>trialComparisonKey(row)===value)&&lookup.has(value)&&
                <option value={value}>{describe(lookup.get(value)!)}</option>}
              {options.shown.map(row=>{
                const key=trialComparisonKey(row);
                return <option key={key} value={key}
                  disabled={chosen.some((entry,i)=>i!==index&&entry===key)}>{describe(row)}</option>;
              })}
            </select>
            {index>=2&&<button type="button" style={{...button,marginTop:8,background:"#46576b"}}
              onClick={()=>setChosen(before=>before.filter((_,i)=>i!==index))}>
              Remove trial {String.fromCharCode(65+index)}
            </button>}
          </div>)}
        </div>
        <button type="button" style={{...button,marginTop:14}} disabled={chosen.length>=5||loading||!!error}
          onClick={()=>setChosen(before=>[...before,""])}>Add another trial</button>
      </section>

      {canCompare?<section aria-label="Evidence comparison">
        <div style={panel}>
          <h2 style={{fontSize:20,marginTop:0}}>Decision status: ABSTAIN — comparative winner not established</h2>
          <p>Evidence completeness does not mean clinical superiority. The current 20 assessments do not supply
            a validated cross-disease composite scoring rubric, matched head-to-head endpoint comparisons,
            or independently validated approval probabilities. A numerical winner would be unsupported.</p>
          <p style={{fontWeight:700}}>{caveat}</p>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(200px,1fr))",gap:12}}>
            {present.map(t=><div key={t.key} style={{border:"1px solid #c6d3e0",borderRadius:8,padding:12}}>
              <h3 style={{fontSize:16,marginTop:0}}>{t.row.ticker} — {t.row.drug}</h3>
              <p style={muted}>{t.row.indication}</p>
              <p><strong>{t.evidence.verified}</strong> source-verified fields of {t.evidence.required}
                {" "}· {t.evidence.modeled} modeled</p>
              <p style={muted}>{t.evidence.readiness==="PARTIAL_EVIDENCE"
                ?"Partial evidence recorded":"Not assessed"}
                {" · "}Market-cap record as of {t.row.capAsOf}</p>
              <a href={"https://clinicaltrials.gov/study/"+encodeURIComponent(t.row.nctId)}
                target="_blank" rel="noopener noreferrer">{t.row.nctId} — registry</a>
            </div>)}
          </div>
        </div>
        <div style={panel}>
          <h2 style={{fontSize:20,marginTop:0}}>All 20 assessments — side by side</h2>
          <p style={muted}>Each expandable cell displays exact-identity source facts and methods.
            Blank findings remain Not assessed; modeled scenarios never count as verified results.</p>
          <div style={{overflowX:"auto"}} role="region" tabIndex={0} aria-label="20-assessment comparison table">
            <table style={{width:"100%",borderCollapse:"collapse",tableLayout:"auto"}}>
              <thead><tr>
                <th scope="col" style={{...heading,minWidth:210,position:"sticky",left:0,background:"#fff",zIndex:1}}>
                  Assessment</th>
                {present.map(t=><th scope="col" key={t.key} style={{...heading,minWidth:220}}>
                  {t.row.ticker} · {t.row.nctId}</th>)}
              </tr></thead>
              <tbody>
                {present[0].evidence.groups.map((g,i)=><tr key={g.rank}>
                  <th scope="row" style={{...cell,minWidth:210,position:"sticky",left:0,
                    background:"#fff",fontWeight:700}}>#{g.rank} — {g.title}</th>
                  {present.map(t=>{
                    const current=t.evidence.groups[i];
                    return <td key={t.key} style={cell}>
                      <span>{current.verified} verified · {current.modeled} modeled</span>
                      <details style={{marginTop:8}}>
                        <summary style={{cursor:"pointer",color:"#174e79",fontWeight:700}}>
                          {current.verified||current.modeled?"View evidence":"Not assessed"} ▾
                        </summary>
                        <div style={{marginTop:10}}>
                          {current.fields.map(f=><div key={f.id}
                            style={{borderTop:"1px solid #e1e7ee",padding:"9px 0"}}>
                            <strong style={{display:"block",marginBottom:4}}>{f.label}</strong>
                            <Fact fact={f.fact}/>
                          </div>)}
                        </div>
                      </details>
                    </td>;
                  })}
                </tr>)}
              </tbody>
            </table>
          </div>
        </div>
        <div style={panel}>
          <h2 style={{fontSize:20,marginTop:0}}>Independent decisions</h2>
          <p><strong>Clinical evidence:</strong> ABSTAIN until valid comparable endpoints, patient populations,
            meaningful effects and safety data can be established.</p>
          <p><strong>Commercial opportunity:</strong> ABSTAIN until sourced market, pricing, access and
            competitive assumptions support a comparable model.</p>
          <p><strong>Risk-adjusted investment:</strong> ABSTAIN until current valuation, financing, ownership
            and independently justified outcome assumptions support scenarios.</p>
          <p><strong>FDA PASS / CRL / EXTENSION:</strong> Not inferred from the benefit assessments.
            Consult the separate PREDICTIONS tab for independently supported outcomes.</p>
        </div>
      </section>:
      <section style={panel} role="status">
        <strong>Choose two distinct trials to begin.</strong>
        <p style={muted}>The 20 assessments will appear once at least two different research records are selected.
          No trial comparison, clinical ranking or investment conclusion is asserted beforehand.</p>
      </section>}
    </div>
  </main>;
}
