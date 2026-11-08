"use client";
import {useEffect,useState,type FormEvent} from "react";
import Link from "next/link";

type AuthState="checking"|"login"|"ready"|"unavailable";
const active=[
 {href:"/pool",title:"POOL — Master Trial Universe",desc:"The original complete source inventory. No subset replaces or deletes master trial records."},
 {href:"/focus",title:"FOCUS — Eligible Phase 3 Results",desc:"Public Phase 3 results, $300M–$10B issuer market cap and an active FDA/PDUFA filing or decision path."},
];

export default function Home(){
 const [auth,setAuth]=useState<AuthState>("checking");
 const [password,setPassword]=useState("");
 const [error,setError]=useState("");
 useEffect(()=>{
  const controller=new AbortController();
  void fetch("/api/auth",{cache:"no-store",signal:controller.signal})
    .then(async res=>{if(res.status===503){setAuth("unavailable");return;}if(!res.ok)throw Error("Auth unavailable");setAuth((await res.json()).authenticated?"ready":"login");})
    .catch(()=>{if(!controller.signal.aborted)setAuth("unavailable")});
  return ()=>controller.abort();
 },[]);
 async function signIn(e:FormEvent<HTMLFormElement>){
  e.preventDefault();setError("");
  const response=await fetch("/api/auth",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password})}).catch(()=>null);
  if(response?.ok){setPassword("");setAuth("ready");}else setError("Sign-in failed. Check your password.");
 }
 async function signOut(){await fetch("/api/auth",{method:"DELETE"}).catch(()=>null);setAuth("login");}
 return <main className="shell">
  <div className="topline">PDUFA COMMAND CENTER · POOL → FOCUS</div>
  <h1>PDUFA Command Center</h1>
  {auth==="checking"&&<p role="status">Checking account session…</p>}
  {auth==="unavailable"&&<section className="panel"><h2>Sign-in unavailable</h2><p>The authentication service is unavailable; source data is withheld.</p></section>}
  {auth==="login"&&<form className="panel login" onSubmit={signIn}>
   <h2>Sign in</h2><label htmlFor="password">Password</label>
   <input id="password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/>
   <button type="submit">Sign in</button>{error&&<p role="alert">{error}</p>}
  </form>}
  {auth==="ready"&&<>
   <button type="button" onClick={()=>void signOut()} style={{marginBottom:14}}>Sign out</button>

   <Link href="/precision-monitoring" aria-label="Open PDUFA Precision Monitoring System" data-testid="precision-monitoring-launch"
    style={{display:"block",textDecoration:"none",background:"linear-gradient(135deg,#092536,#104b56)",border:"2px solid #1bcba0",borderRadius:14,padding:"18px 20px",margin:"0 0 20px",color:"#effffb",boxShadow:"0 5px 19px rgba(6,46,52,.18)"}}>
    <strong style={{display:"block",fontSize:21,marginBottom:6}}>◈ PDUFA Precision Monitoring System</strong>
    <span style={{display:"block",fontSize:14,lineHeight:1.6,color:"#c2fff2"}}>
      Open live installation dashboard · FOCUS ticker scroller · 12 medical analysis levels · evidence history
    </span>
    <span style={{display:"inline-block",marginTop:11,fontWeight:800,background:"#18a986",borderRadius:8,padding:"7px 12px",color:"#062724"}}>
      Open monitoring dashboard ›
    </span>
   </Link>
   <p>The two active trial populations are the complete <strong>POOL</strong> and screened <strong>FOCUS</strong>. Historical source records remain available for audit, not as additional active trial lists.</p>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(260px,1fr))",gap:13,margin:"18px 0"}}>
    {active.map(x=><Link href={x.href} key={x.href} style={{display:"block",background:"#fff",border:"1px solid #adc6b1",borderRadius:10,padding:16,textDecoration:"none",color:"#17452f"}}>
     <strong style={{display:"block",marginBottom:8}}>{x.title}</strong><small style={{lineHeight:1.5,color:"#436454"}}>{x.desc}</small>
    </Link>)}
   </div>
   <p style={{fontSize:13,lineHeight:1.55,marginTop:8}}>
    <Link href="/main">MAIN · Technical status and evidence gates</Link>
    {" "}· <Link href="/precision-monitoring">Precision Monitoring Dashboard</Link>
    {" "}— a read-only operating status view, not another trial population.
   </p>
  </>}
 </main>;
}
