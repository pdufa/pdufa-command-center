import {redirect} from "next/navigation";
export const dynamic="force-dynamic";
/** Backward-compatible alias; one canonical exact-NCT history implementation. */
export default async function LegacyAnalyzeHistoryAlias({searchParams}:{
 searchParams:Promise<{nct?:string}>
}){
 const query=await searchParams;
 const nct=typeof query.nct==="string"&&/^NCT\d{8}$/.test(query.nct)?query.nct:null;
 redirect(nct?"/analyze-now?nct="+encodeURIComponent(nct):"/analyze-now");
}
