"use client";
import {useEffect,useState} from "react";

type Technical={asOf:string;close:number;sma20:number;sma50:number;atr14:number;
  belowSma20TwoCloses:boolean;trailingStop:string};
type ExitResult={programId:string;ticker:string;status:string;reason:string;provider:string;
  checkedAt:string;paperPosition?:boolean|null;positionScope:string;paperAverageEntry?:number;
  marketFeed:string;technical?:Technical;pdufaDate?:string;daysToPdufa?:number;
  pdufaVerified?:boolean;orderExecutionEnabled:boolean;validatedTradingStrategy:boolean};

function money(value:number|undefined){return typeof value==="number"&&Number.isFinite(value)?
  "$"+value.toFixed(value<1?4:2):"—";}

export default function StayExitSignal({programId,ticker}:{programId:string;ticker:string}){
  const [state,setState]=useState<ExitResult|null>(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    let busy=false;
    setState(null);setError("");
    const refresh=async()=>{
      if(busy||document.visibilityState==="hidden")return;
      busy=true;
      try{
        const res=await fetch("/api/exit-signal/"+encodeURIComponent(programId),
          {cache:"no-store",signal:controller.signal});
        if(!res.ok)throw Error("Alpaca STAY/EXIT unavailable: HTTP "+res.status);
        const data=await res.json() as ExitResult;
        if(data.programId!==programId||data.ticker!==ticker||data.provider!=="ALPACA")
          throw Error("Stock/program identity mismatch");
        if(!controller.signal.aborted){setState(data);setError("");}
      }catch(e){if(!controller.signal.aborted){setState(null);setError(String(e));}}
      finally{busy=false;}
    };
    void refresh();
    const interval=setInterval(()=>void refresh(),60000);
    document.addEventListener("visibilitychange",refresh);
    return()=>{controller.abort();clearInterval(interval);
      document.removeEventListener("visibilitychange",refresh);};
  },[ticker,programId]);
  const data=state?.ticker===ticker&&state?.programId===programId?state:null;
  const code=error?"UNAVAILABLE":data?.status||"LOADING";
  const exit=code==="EXIT_WARNING";
  const hold=code==="STAY";
  const message=code==="WAIT"?"WAIT — NO ALPACA PAPER HOLDING":
    exit?"EXIT WARNING — REVIEW SELL CONDITIONS":
    hold?"STAY — NO EXIT TRIGGER":
    code==="STAY_REVIEW"?"HOLDING — VERIFY PDUFA EVIDENCE":
    code==="LOADING"?"CHECKING ALPACA POSITION AND SIP DAILY DATA":
    "STAY/EXIT UNAVAILABLE — VERIFY CONNECTION";
  return <section className={"entry-signal "+(exit?"entry-signal-missing":
      hold?"entry-signal-green":"entry-signal-wait")}
      aria-label={ticker+" Alpaca paper position exit signal"} aria-live="polite">
    <div className="entry-signal-title"><strong>{message}</strong></div>
    <p>{error||data?.reason||"Checking today's last completed session and paper position."}</p>
    {data?.paperPosition===true&&<p className="small">
      PAPER POSITION DETECTED · Average paper entry {money(data.paperAverageEntry)} ·
      This does not confirm a holding at another broker.
    </p>}
    {data?.technical&&<div className="entry-signal-prices">
      <span>LAST CLOSE<strong>{money(data.technical.close)}</strong></span>
      <span>SMA20<strong>{money(data.technical.sma20)}</strong></span>
      <span>ATR14<strong>{money(data.technical.atr14)}</strong></span>
    </div>}
    {data?.technical&&<p className="small">
      {data.technical.asOf} · Two closes below SMA20:
      {data.technical.belowSma20TwoCloses?" YES — EXIT WARNING":" NO"} ·
      SMA50 {money(data.technical.sma50)}
      {data.pdufaVerified?" · Verified PDUFA "+data.pdufaDate+" · "+
        data.daysToPdufa+" days":" · PDUFA not verified for exit timing"}
    </p>}
    <small>Alpaca paper holdings only · split-adjusted historical SIP close data ·
      provisional trading rules, not backtested · no orders submitted.
      An exact entry-dated 2×ATR trailing stop is unavailable until a position
      history and stop ledger are verified.</small>
  </section>;
}
