import Link from "next/link";
import {HISTORICAL_ARCHIVE_FILES,readHistoricalArchive,type HistoricalArchiveSource} from "../../../lib/historical-analysis-archive";
export const metadata={title:"Historical RAAS records · Read-only archive | PDUFA"};
export const dynamic="force-dynamic";
export default async function HistoricalArchivePage({searchParams}:{searchParams:Promise<{nctId?:string}>}){
 const query=await searchParams,nctId=query.nctId&&/^NCT\d{8}$/.test(query.nctId)?query.nctId:undefined;
 const sources=await Promise.all((Object.keys(HISTORICAL_ARCHIVE_FILES) as HistoricalArchiveSource[]).map(async source=>{
  try{const record=await readHistoricalArchive(source,nctId);return {source,total:record.totalRecords,matched:record.matchedRecords,available:true};}
  catch{return {source,total:null,matched:null,available:false};}
 }));
 return <main style={{maxWidth:950,margin:"32px auto",padding:20}} data-historical-archive="read-only">
  <h1>Historical RAAS records</h1><p>Permanent read-only archive. Original observations, ratings, dates and history are retained as recorded. These records do not feed active analysis, predictions, certainty judgments or scans.</p>
  <form method="get"><label>Exact NCT <input name="nctId" pattern="NCT[0-9]{8}" defaultValue={nctId} placeholder="NCT00000000"/></label>{" "}<button type="submit">Find historical records</button></form>
  <ul>{sources.map(item=><li key={item.source} style={{margin:"14px 0"}}><strong>{item.source.replaceAll("-"," ")}</strong>{" · "}{item.available?`${item.matched} matching / ${item.total} preserved records`:"Source unavailable; records unchanged"}{" · "}<a href={"/api/archive/raas?source="+item.source+(nctId?"&nctId="+nctId:"")}>Read original JSON records</a></li>)}</ul>
  <p><a href="https://github.com/pdufa/pdufa-command-center/tree/main/new-platform/frontend/data" target="_blank" rel="noopener noreferrer">Browse preserved source records in the repository</a></p>
  <p><Link href="/focus">FOCUS</Link>{" · "}<Link href="/pool">POOL</Link>{" · "}<Link href="/preview/deep-medical-intelligence">Independent medical intelligence preview</Link></p>
 </main>;
}
