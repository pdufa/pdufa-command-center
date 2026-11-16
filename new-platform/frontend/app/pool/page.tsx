import AssessmentLauncher from '../AssessmentLauncher';
import type { Metadata } from "next";
import FunnelWorkspace from "../FunnelWorkspace";
import ScientificStepsReadiness from "../ScientificStepsReadiness";
import Scientific456Workspace from "../Scientific456Workspace";
export const metadata:Metadata={title:"POOL — Master Trial Universe | PDUFA",description:"Preserved master inventory of all tracked source records, independent from post–Phase 3 Pipeline qualification."};
export default function PoolPage(){return <><AssessmentLauncher source="POOL"/><ScientificStepsReadiness cohort="POOL"/><details style={{margin:"12px 16px"}}><summary style={{cursor:"pointer",fontWeight:700}}>L04–L06 saved scientific research · select exact trial</summary><Scientific456Workspace cohort="POOL"/></details><FunnelWorkspace section="pool"/></>;}
