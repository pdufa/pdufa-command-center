"use client";
import {useEffect,useState} from "react";

type Status={mode:"SANDBOX";configured:boolean;connected:boolean;
  allowsProductionTrading:false;orderPlacementEnabled:false;brokerPreviewEnabled:false};
type Account={name:string;accountType:string;status:string};
const postJson=async(path:string,body?:unknown)=>{
  const response=await fetch(path,{method:"POST",headers:{
    ...(body?{"Content-Type":"application/json"}:{}),
  },body:body?JSON.stringify(body):undefined,cache:"no-store"});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(typeof data.error==="string"?data.error:"E*TRADE sandbox connection unavailable");
  return data;
};

export default function WtEtradeSandboxConnect(){
  const [status,setStatus]=useState<Status|null>(null);
  const [error,setError]=useState("");
  const [verifier,setVerifier]=useState("");
  const [accounts,setAccounts]=useState<Account[]|null>(null);
  const [busy,setBusy]=useState(false);
  const refresh=async()=>{
    try{
      const response=await fetch("/api/etrade-sandbox/status",{cache:"no-store"});
      if(!response.ok)throw new Error(response.status===401?"Sign in to the dashboard to use E*TRADE sandbox.":"Connection status unavailable");
      setStatus(await response.json() as Status);setError("");
    }catch(e){setStatus(null);setError(e instanceof Error?e.message:"Connection unavailable");}
  };
  useEffect(()=>{void refresh();},[]);
  const connect=async()=>{
    if(!verifier.trim())return;
    setBusy(true);setError("");
    try{
      await postJson("/api/etrade-sandbox/complete",{verifier:verifier.trim()});
      setVerifier("");setAccounts(null);await refresh();
    }catch(e){setError(e instanceof Error?e.message:"Authorization failed");}
    finally{setBusy(false);}
  };
  const inspect=async()=>{
    setBusy(true);setError("");
    try{
      const response=await fetch("/api/etrade-sandbox/accounts",{cache:"no-store"});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.error||"Sandbox account list unavailable");
      setAccounts(Array.isArray(data.accounts)?data.accounts:[]);
    }catch(e){setAccounts(null);setError(e instanceof Error?e.message:"Sandbox lookup failed");}
    finally{setBusy(false);}
  };
  const disconnect=async()=>{
    setBusy(true);setError("");
    try{await postJson("/api/etrade-sandbox/disconnect");setAccounts(null);await refresh();}
    catch(e){setError(e instanceof Error?e.message:"Could not disconnect");}
    finally{setBusy(false);}
  };
  return <section aria-label="E*TRADE sandbox authorization" data-etrade-sandbox-only="true"
    style={{border:"1px solid #acccbd",borderRadius:12,padding:16,margin:"12px 0",background:"#f4faf6"}}>
    <h3 style={{marginTop:0}}>E*TRADE developer sandbox · connection setup</h3>
    <p style={{fontSize:13}}>Sandbox authorization only. Market orders and live E*TRADE access are not wired.
      A sandbox login does not connect your actual brokerage account or preview a live order.</p>
    <p role="status"><strong>{status?.connected?"SANDBOX CONNECTED":
      status?.configured?"SANDBOX READY TO AUTHORIZE":status?"SANDBOX KEYS REQUIRED":"CHECKING SETUP"}</strong>
      {" · "}Order submission: DISABLED · Broker order preview: DISABLED</p>
    {!status?.configured&&<p style={{fontSize:13}}>To activate sandbox access, create an E*TRADE
      developer sandbox key and configure these secure server-side Vercel variables:
      <code> ETRADE_SANDBOX_CONSUMER_KEY</code>, <code>ETRADE_SANDBOX_CONSUMER_SECRET</code>,
      and <code>ETRADE_SANDBOX_COOKIE_KEY</code> (64-character hexadecimal AES key).
      Do not paste keys or passwords into ChatGPT or this page. Use
      the <a href="https://developer.etrade.com/getting-started" target="_blank"
      rel="noopener noreferrer">official E*TRADE developer portal</a>.</p>}
    {status?.configured&&!status.connected&&<>
      <p style={{fontSize:13}}>1. Open E*TRADE's secure authorization page and obtain its verification code.
        The code is short-lived. 2. Return here and enter that code. This connects <strong>sandbox only</strong>.</p>
      <a href="/api/etrade-sandbox/begin" target="_blank" rel="noopener noreferrer">Open E*TRADE sandbox authorization</a>
      <div style={{marginTop:10,display:"flex",flexWrap:"wrap",gap:8,alignItems:"center"}}>
        <label htmlFor="etrade-sandbox-verifier">Authorization code</label>
        <input id="etrade-sandbox-verifier" value={verifier} autoComplete="off"
          onChange={e=>setVerifier(e.target.value)} maxLength={64} placeholder="Code from E*TRADE"/>
        <button type="button" disabled={busy||!/^[A-Za-z0-9]{4,64}$/.test(verifier.trim())}
          onClick={()=>void connect()}>Complete sandbox connection</button>
      </div>
    </>}
    {status?.connected&&<div style={{display:"flex",gap:12,flexWrap:"wrap",alignItems:"center"}}>
      <button type="button" disabled={busy} onClick={()=>void inspect()}>Verify sandbox account list</button>
      <button type="button" disabled={busy} onClick={()=>void disconnect()}>Disconnect sandbox</button>
      {accounts!==null&&<p style={{width:"100%",fontSize:13}}>Sandbox sample accounts ({accounts.length}):
        {accounts.length===0?" No sample accounts returned.":accounts.map((a,i)=><span key={i}>
          {" "}{a.name} ({a.accountType}, {a.status}){i===accounts.length-1?"":","}
        </span>)}
        {" "}These are test-data records, not verified live brokerage accounts.</p>}
    </div>}
    {error&&<p role="alert" style={{fontSize:13,color:"#a43232"}}>{error}</p>}
    <p style={{fontSize:12,marginBottom:0}}>E*TRADE sandbox token expires after a short session and must be renewed by
      authorizing again. No account details, tokens, or consumer secrets are exposed to the WT browser UI.
      There is <strong>no route to submit or place orders</strong> in this integration.</p>
  </section>;
}
