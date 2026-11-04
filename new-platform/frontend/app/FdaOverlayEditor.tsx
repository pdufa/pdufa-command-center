"use client";

import {useCallback,useEffect,useMemo,useState} from "react";
import AlpacaStockChart, {type FdaMilestone} from "./AlpacaStockChart";

type CustomMarker = {
  id:string; date:string; label:string; chartLabel:string; detail:string; color:string;
};
type VerifiedDisplayOverride = {
  id:string; date:string; label:string; chartLabel:string; color:string; visible:boolean;
};
type OverlayResponse = {
  programId:string; markers:CustomMarker[]; verifiedOverrides:VerifiedDisplayOverride[];
  version:number; updatedAt?:string|null;
};
const COLORS = [
  {name:"Purple",value:"#7c3aed"},
  {name:"Teal",value:"#0d9488"},
  {name:"Pink",value:"#db2777"},
  {name:"Blue",value:"#2563eb"},
  {name:"Amber",value:"#d97706"}
] as const;
const markerDateOk=(date:string)=>/^\d{4}-\d{2}-\d{2}$/.test(date) &&
  !Number.isNaN(Date.parse(date+"T00:00:00Z")) && new Date(date+"T00:00:00Z").toISOString().slice(0,10)===date;
const newMarker=():CustomMarker=>({
  id:"manual-"+Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,10),
  date:new Date().toISOString().slice(0,10),
  label:"Custom research marker",
  chartLabel:"Research note",
  detail:"",
  color:"#7c3aed"
});

export default function FdaOverlayEditor({
  programId,ticker,verifiedEvents
}:{
  programId:string;ticker:string;verifiedEvents:readonly FdaMilestone[];
}) {
  const [open,setOpen]=useState(false);
  const [markers,setMarkers]=useState<CustomMarker[]>([]);
  const [verifiedOverrides,setVerifiedOverrides]=useState<VerifiedDisplayOverride[]>([]);
  const [version,setVersion]=useState<number|null>(null);
  const [status,setStatus]=useState("Loading saved annotations…");
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(false);
  const [dirty,setDirty]=useState(false);
  const [lastSaved,setLastSaved]=useState<string|null>(null);

  const endpoint="/api/fda-overlay/"+encodeURIComponent(programId);
  const load=useCallback(async(signal?:AbortSignal)=>{
    setLoading(true);
    try{
      const response=await fetch(endpoint,{cache:"no-store",signal});
      if(!response.ok)throw Error(response.status===401?
        "Sign in to the PDUFA dashboard, then reload annotations.":
        "Cannot load saved markers (HTTP "+response.status+").");
      const data:OverlayResponse=await response.json();
      if(data.programId!==programId||!Number.isSafeInteger(data.version)||
        !Array.isArray(data.markers)||!Array.isArray(data.verifiedOverrides))
        throw Error("Saved markers do not match this exact Program ID or are on an older backend.");
      if(signal?.aborted)return;
      setMarkers(data.markers);
      setVerifiedOverrides(data.verifiedOverrides);
      setVersion(data.version);
      setLastSaved(data.updatedAt||null);
      setStatus("FDA display edits and custom annotations loaded from persistent program storage.");
      setDirty(false);
    }catch(e){
      if(signal?.aborted)return;
      setStatus(e instanceof Error?e.message:"Annotation storage unavailable.");
      setVersion(null);
    }finally{if(!signal?.aborted)setLoading(false);}
  },[endpoint,programId]);

  useEffect(()=>{
    const ctrl=new AbortController();
    void load(ctrl.signal);
    return ()=>ctrl.abort();
  },[load]);

  const originalDisplay=(event:FdaMilestone):VerifiedDisplayOverride=>({
    id:event.id||"", date:event.date, label:event.label, chartLabel:event.chartLabel,
    color:event.color||(event.planned?"#d97706":"#7c3aed"), visible:true,
  });
  const getDisplay=(event:FdaMilestone):VerifiedDisplayOverride=>
    verifiedOverrides.find(o=>o.id===event.id)||originalDisplay(event);
  const editVerified=(id:string,patch:Partial<Omit<VerifiedDisplayOverride,"id">>)=>{
    const source=verifiedEvents.find(event=>event.id===id);
    if(!source)return;
    setVerifiedOverrides(old=>{
      const existing=old.find(v=>v.id===id);
      const updated={...(existing||originalDisplay(source)),...patch,id};
      return existing?old.map(v=>v.id===id?updated:v):[...old,updated];
    });
    setDirty(true);
  };
  const resetVerified=(id:string)=>{
    setVerifiedOverrides(old=>old.filter(v=>v.id!==id));
    setDirty(true);
  };
  const combined=useMemo<FdaMilestone[]>(()=>[
    ...verifiedEvents.map(event=>{
      const override=verifiedOverrides.find(o=>o.id===event.id);
      return override?{
        ...event,...override,edited:true,originalDate:event.date,custom:false,
      }:{...event,visible:true};
    }),
    ...markers.map(m=>({...m,custom:true,source:undefined}))
  ],[verifiedEvents,verifiedOverrides,markers]);

  const edit=(id:string,field:keyof CustomMarker,value:string)=>{
    if(field==="id")return;
    setMarkers(old=>old.map(m=>m.id===id?{...m,[field]:value}:m));
    setDirty(true);
  };
  const moveDate=(id:string,date:string)=>{
    if(!markerDateOk(date)||date<"2000-01-01"||date>"2100-12-31")return;
    if(id.startsWith("verified-"))editVerified(id,{date});
    else edit(id,"date",date);
  };
  const save=async()=>{
    if(version===null||loading||saving)return;
    if(markers.length>40){setStatus("Limit: 40 custom markers per program.");return;}
    if([...markers,...verifiedOverrides].some(m=>!markerDateOk(m.date)||
      m.date<"2000-01-01"||m.date>"2100-12-31"||!m.label.trim()||!m.chartLabel.trim())){
      setStatus("Correct the date, title and short chart label for every marker.");return;
    }
    if(verifiedOverrides.some(o=>!verifiedEvents.some(e=>e.id===o.id))){
      setStatus("Unrecognized verified event in edits. Reload first.");return;
    }
    setSaving(true);setStatus("Saving FDA display edits and custom annotations…");
    try{
      const response=await fetch(endpoint,{
        method:"PUT",headers:{"content-type":"application/json"},
        body:JSON.stringify({version,markers,verifiedOverrides}),cache:"no-store",
      });
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw Error(response.status===409?
        "Markers changed in another session. Reload before saving to avoid overwriting them.":
        data?.detail||data?.error||"Save failed (HTTP "+response.status+").");
      if(data.programId!==programId||!Number.isSafeInteger(data.version))
        throw Error("Server returned an invalid save confirmation.");
      setVersion(data.version);
      setLastSaved(data.updatedAt||null);
      setDirty(false);
      setStatus("FDA overlay saved for "+programId+". Your display edits will remain when you reopen the chart.");
    }catch(e){setStatus(e instanceof Error?e.message:"Save failed.");}
    finally{setSaving(false);}
  };

  const controls:React.CSSProperties={background:"#fff",color:"#263b4e",border:"1px solid #adbfcb",
    borderRadius:6,padding:"8px 9px",fontSize:14,minHeight:40,width:"100%",boxSizing:"border-box"};
  const action:React.CSSProperties={padding:"9px 12px",border:"1px solid #8a99a9",
    background:"#f8fbfd",color:"#163650",borderRadius:6,fontSize:13,fontWeight:700};

  return <section aria-label="Alpaca chart with editable FDA overlays">
    <AlpacaStockChart ticker={ticker} programId={programId} milestones={combined}
      onMoveMilestone={open&&version!==null?moveDate:undefined}/>
    <div style={{background:"#f6f9fc",padding:14,border:"1px solid #b6cbd6",borderRadius:10,margin:"12px 0"}}>
      <div style={{display:"flex",gap:10,justifyContent:"space-between",alignItems:"center",flexWrap:"wrap"}}>
        <div><strong>FDA overlay editor</strong>
          <div style={{fontSize:12,color:"#435569"}}>{verifiedEvents.length} sourced events editable on chart · {verifiedOverrides.length} display overrides · {markers.length} custom markers</div></div>
        <button type="button" onClick={()=>setOpen(v=>!v)} style={action}
          aria-expanded={open}>{open?"CLOSE EDITOR":"EDIT FDA OVERLAY"}</button>
      </div>
      {open&&<div style={{marginTop:14}}>
        <p style={{fontSize:13,margin:"0 0 12px",color:"#334155"}}>
          You can edit every existing FDA marker's chart date, label, color and visibility.
          The verified original FDA date and source link are always preserved below. Edited dates are user adjustments, not new official FDA announcements.
          Change a date field or drag a visible event line on the chart. Click SAVE OVERLAY to persist your changes.
        </p>
        <div style={{display:"flex",gap:9,flexWrap:"wrap",alignItems:"center",marginBottom:12}}>
          <button type="button" style={action} disabled={version===null||markers.length>=40}
            onClick={()=>{setMarkers(a=>[...a,newMarker()]);setDirty(true);}}>+ ADD CUSTOM MARKER</button>
          <button type="button" style={action} disabled={!dirty||version===null||saving}
            onClick={()=>void save()}>{saving?"SAVING…":"SAVE OVERLAY"}</button>
          <button type="button" style={action} disabled={loading||saving}
            onClick={()=>void load()}>RELOAD SAVED</button>
        </div>
        <div role="status" style={{fontSize:12,marginBottom:10,color:dirty?"#99550c":"#28634e"}}>
          {status} {dirty?"· UNSAVED CHANGES":""}
          {lastSaved&&!dirty?" · Last saved "+new Date(lastSaved).toLocaleString():""}
        </div>
        <details open style={{margin:"12px 0",padding:12,border:"1px solid #9db7ca",borderRadius:8,background:"#fff"}}>
          <summary style={{fontSize:14,fontWeight:750,cursor:"pointer"}}>EDIT EXISTING FDA MARKERS ({verifiedEvents.length})</summary>
          {verifiedEvents.map(event=>{
            const o=getDisplay(event),isEdited=verifiedOverrides.some(v=>v.id===event.id);
            return <fieldset key={event.id||event.date}
              style={{margin:"12px 0",padding:12,border:"1px solid #bfcddb",borderRadius:8,minWidth:0}}>
              <legend style={{fontSize:13,fontWeight:700,padding:"0 5px"}}>{event.chartLabel}{isEdited?" · USER-EDITED":""}</legend>
              <div style={{fontSize:12,marginBottom:10,color:"#445369"}}>
                <strong>Verified original:</strong> {event.date} · {event.label} ·
                {event.source&&<a style={{marginLeft:5}} href={event.source} target="_blank" rel="noopener noreferrer">View original source</a>}
              </div>
              <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:10}}>
                <label style={{fontSize:12,fontWeight:600}}>Displayed date (editable)
                  <input style={controls} type="date" value={o.date}
                    min="2000-01-01" max="2100-12-31"
                    onChange={e=>editVerified(o.id,{date:e.target.value})} />
                </label>
                <label style={{fontSize:12,fontWeight:600}}>Displayed event label
                  <input style={controls} maxLength={100} value={o.label}
                    onChange={e=>editVerified(o.id,{label:e.target.value})}/>
                </label>
                <label style={{fontSize:12,fontWeight:600}}>Short chart label
                  <input style={controls} maxLength={30} value={o.chartLabel}
                    onChange={e=>editVerified(o.id,{chartLabel:e.target.value})}/>
                </label>
                <label style={{fontSize:12,fontWeight:600}}>Line color
                  <select style={controls} value={o.color}
                    onChange={e=>editVerified(o.id,{color:e.target.value})}>
                    {COLORS.map(color=><option key={color.value} value={color.value}>{color.name}</option>)}
                  </select>
                </label>
              </div>
              <label style={{fontSize:13,display:"flex",alignItems:"center",gap:8,marginTop:12}}>
                <input type="checkbox" checked={o.visible}
                  onChange={e=>editVerified(o.id,{visible:e.target.checked})}
                  style={{width:18,height:18}}/>
                Show this FDA marker on chart
              </label>
              {isEdited&&<p style={{fontSize:12,color:"#99550c",margin:"8px 0 0"}}>
                User-adjusted chart display · Original sourced date remains {event.date}.
              </p>}
              <button type="button" style={{...action,marginTop:9}} onClick={()=>resetVerified(o.id)}
                disabled={!isEdited}>RESTORE ORIGINAL MARKER</button>
            </fieldset>;
          })}
        </details>
        {markers.map((m,index)=><fieldset key={m.id}
          style={{margin:"12px 0",padding:12,border:"1px solid #9db7ca",borderRadius:8,background:"#fff",minWidth:0}}>
          <legend style={{fontSize:13,fontWeight:700,padding:"0 5px"}}>Custom marker {index+1} · Unverified</legend>
          <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:10}}>
            <label style={{fontSize:12,fontWeight:600}}>Date
              <input style={controls} type="date" value={m.date} onChange={e=>edit(m.id,"date",e.target.value)} />
            </label>
            <label style={{fontSize:12,fontWeight:600}}>Marker title
              <input style={controls} maxLength={100} value={m.label} onChange={e=>edit(m.id,"label",e.target.value)}/>
            </label>
            <label style={{fontSize:12,fontWeight:600}}>Short chart label
              <input style={controls} maxLength={30} value={m.chartLabel} onChange={e=>edit(m.id,"chartLabel",e.target.value)}/>
            </label>
            <label style={{fontSize:12,fontWeight:600}}>Marker color
              <select style={controls} value={m.color} onChange={e=>edit(m.id,"color",e.target.value)}>
                {COLORS.map(color=><option key={color.value} value={color.value}>{color.name}</option>)}
              </select>
            </label>
          </div>
          <label style={{fontSize:12,fontWeight:600,display:"block",marginTop:10}}>Research notes
            <textarea style={{...controls,minHeight:70,resize:"vertical"}} maxLength={500} value={m.detail}
              onChange={e=>edit(m.id,"detail",e.target.value)}/>
          </label>
          <button type="button" style={{...action,marginTop:8,color:"#9e2436"}}
            onClick={()=>{setMarkers(a=>a.filter(item=>item.id!==m.id));setDirty(true);}}>
            DELETE CUSTOM MARKER
          </button>
        </fieldset>)}
        <p style={{fontSize:12,marginTop:12,color:"#435569"}}>
          The <strong>verified source records are never overwritten</strong>. Only your chart presentation settings
          and separate custom annotations are saved. Changes to official FDA dates require new verified source evidence.
        </p>
      </div>}
    </div>
  </section>;
}
