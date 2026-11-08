"use client";
import {useCallback,useEffect,useState} from "react";

type Preflight={
 ready:boolean;enabled?:boolean;storageReady?:boolean;workerReady?:boolean;
 canaryNct?:string|null;status?:string;error?:string
};
export default function CanaryReadiness(){
 const [loading,setLoading]=useState(true);
 const [value,setValue]=useState<Preflight|null>(null);
 const refresh=useCallback(async()=>{
   setLoading(true);
   try{
     const response=await fetch("/api/analyze-now/readiness",{cache:"no-store"});
     const data=await response.json() as Preflight;
     setValue(data&&typeof data==="object"?data:{ready:false,error:"Invalid readiness result"});
   }catch{
     setValue({ready:false,error:"Could not check live backend readiness"});
   }finally{
     setLoading(false);
   }
 },[]);
 useEffect(()=>{void refresh();},[refresh]);
 return <section aria-label="Live Analyze Now canary readiness"
     style={{border:"1px solid #bdd0c6",borderRadius:10,padding:12,margin:"13px 0",background:"#f7faf8"}}>
   <div style={{display:"flex",gap:10,alignItems:"center",justifyContent:"space-between",flexWrap:"wrap"}}>
     <strong>Live backend readiness</strong>
     <button type="button" onClick={()=>void refresh()} disabled={loading}
       style={{border:"1px solid #bacfc5",borderRadius:6,padding:"6px 10px",background:"white",color:"#173d2b"}}>
       {loading?"Checking…":"Recheck readiness"}
     </button>
   </div>
   <p role="status" aria-live="polite" style={{margin:"8px 0 0",fontSize:13}}>
     {loading?"Checking the isolated backend and persistent storage…":
       value?.ready?"Ready for the single approved source-only canary run.":
       value?.error?value.error:
       "Blocked: isolated PostgreSQL, medical pilot activation, or worker initialization is not verified."}
   </p>
   {!loading&&value&&!value.error&&
     <p style={{margin:"5px 0 0",fontSize:12,color:"#53695d"}}>
       Medical pilot: {value.enabled?"Enabled":"Not enabled"} ·
       PostgreSQL: {value.storageReady?"Ready":"Not verified"} ·
       Source worker: {value.workerReady?"Ready":"Not initialized"}
     </p>}
 </section>;
}
