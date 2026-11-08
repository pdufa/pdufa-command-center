import {redirect} from "next/navigation";
/** Compatibility redirect to an explicit immutable archive, never a calculator. */
export default async function RetiredHistoryRoute({searchParams}:{searchParams:Promise<{nctId?:string}>}){
 const {nctId}=await searchParams;
 redirect("/archive/raas"+(nctId&&/^NCT\d{8}$/.test(nctId)?"?nctId="+nctId:""));
}
