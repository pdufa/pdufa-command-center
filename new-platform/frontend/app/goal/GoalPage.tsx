"use client";
import {useRouter} from "next/navigation";
import GoalDashboard, {type GoalSection} from "../GoalDashboard";
export default function GoalPage(){
 const router=useRouter();
 const onOpen=(section:GoalSection)=>{
  const path=section==="SCANS"?"/scans":section==="RESULTS"?"/results":
    section==="RESTRICTIONS"?"/restrictions":"/pipeline";
  router.push(path);
 };
 return <GoalDashboard records={null} pipelineCount={null}
    gemJrCount={null} gemCount={null} restrictions={null}
    impactRows={null} impactEntries={null}
    sourceAsOf={null} sourceState={null} onOpen={onOpen}/>;
}
