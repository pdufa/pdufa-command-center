import type {Metadata} from "next";
import IndicationIntelligence from "../IndicationIntelligence";
export const metadata:Metadata={
 title:"INDICATIONS — POOL / FOCUS Clinical Intelligence | PDUFA",
 description:"Unified source-linked disease hierarchy, phase matrix and exact-NCT trial dossier."
};
export default function IndicationsPage(){
 return <main style={{maxWidth:1500,margin:"20px auto",padding:"0 16px",fontFamily:"system-ui,sans-serif"}}>
  <IndicationIntelligence mode="indications"/>
 </main>;
}
