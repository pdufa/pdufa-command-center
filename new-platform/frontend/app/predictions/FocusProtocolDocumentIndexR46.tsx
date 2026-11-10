import Link from "next/link";
import {FOCUS_R46_DOCUMENTS} from "../../lib/focus-r46-current-protocol-documents";

const shell={background:"#f6faf9",border:"1px solid #bcd5cc",borderRadius:12,
 padding:16,margin:"14px 0 18px"} as const;

export default function FocusProtocolDocumentIndexR46(){
 const data=FOCUS_R46_DOCUMENTS;
 if(!data)return <section aria-label="R46 source protocol document index" style={shell}>
   Original document-index source receipt or NCT identity check failed. The unverified document index is withheld.
 </section>;
 const urgent=[
   {nct:"NCT05126758",label:"CAPR · deramiocel",target:"Nov 22, 2026"},
   {nct:"NCT04544293",label:"SVRA · molgramostim",target:"Nov 22, 2026"},
   {nct:"NCT05208047",label:"COGT · GIST",target:"Nov 30, 2026"}
 ];
 return <section aria-label="R46 original current registry protocol and SAP document links" style={shell}>
  <h2 style={{fontSize:20,margin:"2px 0 7px"}}>Protocol and SAP documents · 29 FOCUS trials</h2>
  <p style={{fontSize:13,lineHeight:1.6}}>
    Current ClinicalTrials.gov record review found <strong>{data.counts.withCurrentProtocolAndSapAttachments}/29</strong> trials
    with protocol and SAP attachments, totaling <strong>{data.counts.documentEntries}</strong> document entries.
    The other <strong>{data.counts.withoutCurrentRegistryAttachments}</strong> have no current registry-attached documents;
    this does not mean original protocols or SAPs cannot be found elsewhere.
  </p>
  <p style={{fontSize:12,lineHeight:1.55}}>
    This is a <strong>source-document locator, not an independent review of the document contents</strong>.
    A document's printed date does not independently prove its first public posting, that its
    analysis plan was locked before unblinding, or compliance with statistical multiplicity.
    <a href={data.sourceArtifactUrl} target="_blank" rel="noopener noreferrer"
      style={{color:"#0b6756",fontWeight:700,marginLeft:5}}>Open exact original registry archive and protocol index</a>
  </p>
  <h3 style={{fontSize:16,margin:"14px 0 6px"}}>Earliest reported FDA decision targets — document readiness</h3>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:8,marginBottom:12}}>
    {urgent.map(u=>{
      const item=data.rows.find(r=>r.nct===u.nct);
      return <div key={u.nct} style={{background:"#fff",border:"1px solid #cfddd6",borderRadius:9,padding:10}}>
        <strong style={{fontSize:13}}>{u.label}</strong>
        <div style={{fontSize:11,color:"#52645d",margin:"3px 0"}}>Sponsor-reported target: {u.target}</div>
        <div style={{fontSize:12,fontWeight:700}}>
          {item?.attachments?"Protocol/SAP attached in current registry":"No current protocol/SAP attachment"}
        </div>
        <div style={{fontSize:11,color:"#7a5c33",marginTop:4}}>Original locked version unverified</div>
        <Link href={"/predictions/assessment?nct="+u.nct} style={{fontSize:12,color:"#0a6654"}}>
          Exact trial evidence review
        </Link>
      </div>;
    })}
  </div>
  <details style={{background:"#fff",border:"1px solid #cfddd6",borderRadius:9,padding:12}}>
   <summary style={{cursor:"pointer",fontWeight:800}}>
     Expand all 29 NCTs, attached protocol/SAP files and registry-document dates
   </summary>
   <div style={{overflowX:"auto",paddingTop:9}}>
    <table style={{borderCollapse:"collapse",width:"100%",minWidth:640,fontSize:12,textAlign:"left"}}>
     <thead><tr style={{background:"#ebf4ee"}}>
       {["Ticker","Exact NCT","Current protocol/SAP attachments","Document dates from registry","Reviewer status"].map(s=>
        <th key={s} style={{padding:8,borderBottom:"2px solid #d5e3db"}}>{s}</th>)}
     </tr></thead>
     <tbody>{data.rows.map(x=><tr key={x.nct}>
        <td style={{padding:8,borderBottom:"1px solid #e0e9e4",fontWeight:700}}>{x.ticker}</td>
        <td style={{padding:8,borderBottom:"1px solid #e0e9e4"}}>
         <Link href={"/predictions/assessment?nct="+x.nct} style={{color:"#0b6657"}}>{x.nct}</Link>
        </td>
        <td style={{padding:8,borderBottom:"1px solid #e0e9e4"}}>
         {x.attachments?x.attachments.map(d=><div key={d.filename}>{d.kind}: {d.filename}</div>):
           "No current attached document"}
        </td>
        <td style={{padding:8,borderBottom:"1px solid #e0e9e4"}}>
          {x.attachments?x.attachments.map(d=><div key={d.filename}>{d.registryDocumentDate}</div>):"Not available"}
        </td>
        <td style={{padding:8,borderBottom:"1px solid #e0e9e4"}}>
          Original publication and locked SAP NOT VERIFIED
        </td>
       </tr>)}</tbody>
    </table>
   </div>
  </details>
  <p style={{fontSize:12,margin:"12px 0 0",lineHeight:1.5}}>
   Source-file attachments do not establish statistical efficacy or FDA outcome. Independent clinical grades 0,
   validated application forecasts 0/23, historical backtests 0. All future official approval/CRL and review timing predictions remain ABSTAIN.
  </p>
 </section>;
}
