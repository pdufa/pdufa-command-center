import Link from "next/link";
import type {Metadata} from "next";
import EvidenceRecoveryBoardR68 from "./EvidenceRecoveryBoardR68";

export const metadata:Metadata={
 title:"FOCUS Original Scientific Evidence Recovery | PDUFA",
 description:"Read-only, exact-NCT source availability and original evidence recovery for 29 FOCUS trials; no scientific grade or validated FDA forecast."
};

export default function EvidenceRecoveryPage(){
 return <main>
   <div style={{maxWidth:1200,margin:"0 auto",padding:"17px 14px 0",fontSize:13}}>
     <Link href="/predictions" style={{color:"#087560",fontWeight:750}}>
       FDA Predictions research dashboard
     </Link> {" · "}
     <Link href="/predictions/assessment" style={{color:"#087560",fontWeight:750}}>
       Full scientific assessment
     </Link>
   </div>
   <EvidenceRecoveryBoardR68 />
 </main>;
}
