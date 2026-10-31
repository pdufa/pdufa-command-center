"use client";

import {useEffect,useState,type FormEvent} from "react";
import Link from "next/link";
import SiteHealthStatus from "./SiteHealthStatus";
import NctLiveStream from "./NctLiveStream";

type AuthState="checking"|"login"|"ready"|"unavailable";
const links=[
  {href:"/pool",title:"POOL — Master Trial Universe",desc:"The unrestricted published trial and regulatory-record universe. No eligibility gate deletes POOL records."},
  {href:"/pipeline",title:"PIPELINE — Post–Phase 3 Screening",desc:"Public issuer, $300M–$10B market cap and verified final pivotal Phase 3 evidence. Unverified items remain in review."},
  {href:"/patient-population",title:"#1 — Patient Population",desc:"Source-linked research and evidence completeness for the first commercial-benefit assessment."},
  {href:"/goal",title:"GOAL — Research Operations",desc:"Daily source status, upcoming events, and Pipeline-only analysis progress."},
  {href:"/scans",title:"SCANS — Collection and Verification",desc:"Source audit, scan progress and controls, including Phase 3 posted results."},
  {href:"/results",title:"RESULTS — Dated Scan Reports",desc:"Saved daily research results and historical scan evidence."},
  {href:"/restrictions",title:"RESTRICTIONS — Pipeline Eligibility",desc:"Three hard scope gates and status of verification before commercial assessments."},
  {href:"/predictions",title:"PREDICTIONS — FDA Outcome Research",desc:"Research-only outcome evidence; no unsupported regulatory probability."},
];
export default function Home() {
 const [auth,setAuth]=useState<AuthState>("checking");
 const [password,setPassword]=useState("");
 const [error,setError]=useState("");
 useEffect(()=>{
   const controller=new AbortController();
   void fetch("/api/auth",{cache:"no-store",signal:controller.signal})
    .then(async response=>{
      if(response.status===503){setAuth("unavailable");return;}
      if(!response.ok)throw Error("Auth unavailable");
      setAuth((await response.json()).authenticated?"ready":"login");
    }).catch(()=>{if(!controller.signal.aborted)setAuth("unavailable")});
   return()=>controller.abort();
 },[]);
 async function signIn(e:FormEvent<HTMLFormElement>){
   e.preventDefault();setError("");
   const response=await fetch("/api/auth",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({password})}).catch(()=>null);
   if(response?.ok){setPassword("");setAuth("ready")}
   else setError("Sign-in failed. Check your password.");
 }
 async function signOut(){
   await fetch("/api/auth",{method:"DELETE"}).catch(()=>null);
   setAuth("login");
 }
 return <main className="shell">
  <div className="topline">PDUFA COMMAND CENTER · POOL → PIPELINE</div>
  <h1>PDUFA Command Center</h1>
  {auth==="checking" && <p role="status">Checking account session…</p>}
  {auth==="unavailable" && <section className="panel"><h2>Setup unavailable</h2><p>Authentication is not configured or the session service could not be reached. Research data is withheld.</p></section>}
  {auth==="login" && <form className="panel login" onSubmit={signIn}>
    <h2>Sign in</h2><label htmlFor="password">Password</label>
    <input id="password" type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/>
    <button type="submit">Sign in</button>{error&&<p role="alert">{error}</p>}
  </form>}
  {auth==="ready" && <>
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:12,flexWrap:"wrap"}}>
      <SiteHealthStatus/><button type="button" className="secondary" onClick={()=>void signOut()}>Sign out</button>
    </div>
    <p>The active research sequence is <strong>POOL → PIPELINE → scientific, regulatory and commercial-benefit assessments</strong>. Historic research configurations are not eligibility gates.</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(250px,1fr))",gap:13,margin:"18px 0"}}>
      {links.map(x=><Link key={x.href} href={x.href}
        style={{display:"block",background:"#fff",border:"1px solid #adc6b1",borderRadius:10,padding:16,textDecoration:"none",color:"#17452f"}}>
        <strong style={{display:"block",marginBottom:8}}>{x.title}</strong><small style={{lineHeight:1.5,color:"#436454"}}>{x.desc}</small>
      </Link>)}
    </div>
    <NctLiveStream/>
    <p><a href="https://docs.google.com/spreadsheets/d/1FSRXFXc4u2KTpdyP-vSbWil-Fgtrj3ucELSk2kpQAG0/edit" target="_blank" rel="noopener noreferrer">Patient Population — Recommended Columns spreadsheet</a></p>
  </>}
 </main>;
}
