"use client";

import {useEffect,useState} from "react";
import Link from "next/link";
import TradingDashboard,{type TradingTicker} from "../TradingDashboard";

type Identity={programId:string;ticker:string;drug?:string|null};
type WatchTradeResponse={
 watch:string[];trade:string[];identities:Identity[];
};
const isProgram=(id:string)=>/^PDUFA-[0-9]{6,}$/.test(id);

export default function ChartsWorkspace(){
 const [records,setRecords]=useState<TradingTicker[]>([]);
 const [status,setStatus]=useState<"loading"|"ready"|"error">("loading");
 const [problem,setProblem]=useState("");
 useEffect(()=>{
  const ctrl=new AbortController();
  void fetch("/api/program-watch-trade",{cache:"no-store",signal:ctrl.signal})
   .then(async response=>{
    if(!response.ok)throw Error(response.status===401?
      "Sign in to the PDUFA dashboard before opening saved charts.":
      "Unable to load saved Watch/Trade program identities (HTTP "+response.status+").");
    const data=await response.json() as WatchTradeResponse;
    if(!Array.isArray(data.watch)||!Array.isArray(data.trade)||!Array.isArray(data.identities)){
      throw Error("Saved Watch/Trade response is incomplete.");
    }
    const byId=new Map(data.identities.filter(x=>x&&typeof x.programId==="string"&&
      isProgram(x.programId)&&typeof x.ticker==="string"&&x.ticker.trim())
      .map(x=>[x.programId,x] as const));
    const used=new Set<string>();
    const asTicker=(id:string,kind:"watch"|"trade"):TradingTicker|null=>{
      const identity=byId.get(id);
      if(!identity||used.has(id))return null;
      used.add(id);
      return {programId:id,kind,ticker:identity.ticker,drug:identity.drug||undefined};
    };
    const list=[
      ...data.watch.map(id=>asTicker(id,"watch")),
      ...data.trade.map(id=>asTicker(id,"trade"))
    ].filter((x):x is TradingTicker=>x!==null);
    if(!ctrl.signal.aborted){setRecords(list);setStatus("ready");}
   })
   .catch(e=>{if(!ctrl.signal.aborted){setStatus("error");setProblem(e instanceof Error?e.message:"Chart selections unavailable.");}});
  return ()=>ctrl.abort();
 },[]);
 return <main className="shell" style={{maxWidth:1350,margin:"0 auto",padding:"16px 12px 42px"}}>
  <p><Link href="/">PDUFA Dashboard</Link> / CHARTS</p>
  <h1>ALPACA CHARTS + FDA OVERLAYS</h1>
  <p>Saved Watch/Trade selections provide the ticker and permanent program identity automatically. FDA milestones
   never transfer between different programs. Chart research does not place trades.</p>
  {status==="loading"&&<p role="status">Loading saved Watch/Trade program identifiers…</p>}
  {status==="error"&&<section className="panel" role="alert"><strong>Charts temporarily unavailable</strong>
    <p>{problem}</p><p><Link href="/">Dashboard / sign in</Link></p></section>}
  {status==="ready"&&<>
   <TradingDashboard tickers={records} tagsReady={true}/>
   {records.length===0&&<p>There are no saved permanent Watch/Trade program selections to chart yet.
    Select a verified program in the app before expecting its ticker to appear here.</p>}
  </>}
  <p style={{marginTop:18}}>For the source-linked CYTK demonstration, open <Link href="/alpaca-cytk">CYTK FDA chart and editor</Link>.
   Other programs have no automatic FDA milestone feed until exact application evidence is connected.</p>
 </main>;
}
