"use client";
import { pipelineDayCounts, type TimelineDates } from "../lib/pipeline-timeline";

export function PipelineTimelineHeaders(){
  return <>
    <th title="Calendar days since the verified public Phase 3 data-release announcement, not primary completion or results posting.">Days since Phase 3 data release</th>
    <th title="Calendar days to the sourced FDA PDUFA decision target. Research window ends three days before the target.">Days to PDUFA</th>
  </>;
}
export function PipelineTimelineCells({dates,today}:{dates?:TimelineDates|null;today:string}){
  const current=dates||{phase3DataRelease:null,pdufaTarget:null};
  const counts=pipelineDayCounts(current,today);
  const released=counts.daysSincePhase3Release;
  const due=counts.daysToPdufa;
  return <>
    <td className="pipeline-days-since-release">
      <strong>{!today?"Calculating…":released===null?"Not verified":released.toLocaleString("en-US")+" days"}</strong>
      {current.phase3DataRelease && <small>Released {current.phase3DataRelease.date} · <a href={current.phase3DataRelease.sourceUrl} target="_blank" rel="noopener noreferrer">Evidence ↗</a></small>}
      {!current.phase3DataRelease && <small>Awaiting verified public Phase 3 results-release date and source. Trial completion is not a release.</small>}
      {current.phase3DataRelease && released===null && <small>Release is not yet in the past or the reference date is invalid.</small>}
    </td>
    <td className="pipeline-days-to-pdufa">
      <strong>{!today?"Calculating…":due===null?"Not verified":due>0?due.toLocaleString("en-US")+" days":due===0?"Today":"Passed "+Math.abs(due).toLocaleString("en-US")+" days ago"}</strong>
      {current.pdufaTarget && <small>Target {current.pdufaTarget.date} · <a href={current.pdufaTarget.sourceUrl} target="_blank" rel="noopener noreferrer">Evidence ↗</a></small>}
      {!current.pdufaTarget && <small>No source-verified FDA PDUFA target linked to this exact trial.</small>}
      {due!==null && <small>{counts.cutoffReached
        ?"Phase 3 → PDUFA − 3 research window has reached its cutoff."
        :"Research window open until 3 calendar days before PDUFA."}</small>}
    </td>
  </>;
}
