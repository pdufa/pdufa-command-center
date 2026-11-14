import type { Metadata } from "next";
import FunnelWorkspace from "../FunnelWorkspace";
import ScientificStepsReadiness from "../ScientificStepsReadiness";
export const metadata:Metadata={title:"POOL — Master Trial Universe | PDUFA",description:"Preserved master inventory of all tracked source records, independent from post–Phase 3 Pipeline qualification."};
export default function PoolPage(){return <><ScientificStepsReadiness cohort="POOL"/><FunnelWorkspace section="pool"/></>;}
