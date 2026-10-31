/** Read-only calendar-day metrics for exact-NCT post-Phase 3 research.
 * Never substitute registry primary completion / results posting dates for a
 * public Phase 3 results RELEASE, and never infer an FDA action date.
 */
export type TimelineEvidence = {
  date: string;
  sourceUrl: string;
  status: "VERIFIED";
};
export type TimelineDates = {
  phase3DataRelease: TimelineEvidence | null;
  pdufaTarget: TimelineEvidence | null;
};
export type TimelineSourceFields = {
  phase3ReadoutDate?: unknown;
  phase3ReadoutSource?: unknown;
  phase3ReadoutVerified?: unknown;
  /** Legacy research hint, only accepted when explicitly identified as a public release. */
  phase3Date?: unknown;
  phase3Source?: unknown;
  phase3DateKind?: unknown;
  phase3DateVerified?: unknown;
  pdufaDate?: unknown;
  pdufaSource?: unknown;
  pdufaTargetVerified?: unknown;
};
const datePattern = /^\d{4}-\d{2}-\d{2}$/;
function dateDays(value:unknown):number|null{
  if(typeof value!=="string" || !datePattern.test(value))return null;
  const ms=Date.parse(value+"T00:00:00.000Z");
  if(!Number.isFinite(ms) || new Date(ms).toISOString().slice(0,10)!==value)return null;
  return ms/86400000;
}
function sourcedEvent(date:unknown,source:unknown,verified:unknown):TimelineEvidence|null{
  if(dateDays(date)===null || typeof source!=="string" || !/^https:\/\/[^\s]+$/i.test(source)
     || verified!==true)return null;
  return {date:date as string,sourceUrl:source,status:"VERIFIED"};
}
export function exactProgramTimeline(
  row:TimelineSourceFields | null | undefined,
  identityIsExact:boolean,
):TimelineDates {
  if(!row || !identityIsExact)return {phase3DataRelease:null,pdufaTarget:null};
  const primary=sourcedEvent(row.phase3ReadoutDate,row.phase3ReadoutSource,row.phase3ReadoutVerified);
  const legacy=row.phase3DateKind==="PUBLIC_RESULTS_RELEASE"
    ?sourcedEvent(row.phase3Date,row.phase3Source,row.phase3DateVerified):null;
  return {
    phase3DataRelease:primary||legacy,
    pdufaTarget:sourcedEvent(row.pdufaDate,row.pdufaSource,row.pdufaTargetVerified),
  };
}
export function pacificToday(now:Date=new Date()):string{
  const parts=new Intl.DateTimeFormat("en-US",{
    timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit",
  }).formatToParts(now);
  const get=(type:string)=>parts.find(x=>x.type===type)?.value||"";
  return get("year")+"-"+get("month")+"-"+get("day");
}
export function pipelineDayCounts(
  dates:TimelineDates, today:string,
):{daysSincePhase3Release:number|null; daysToPdufa:number|null; cutoffReached:boolean|null}{
  const now=dateDays(today);
  if(now===null)return {daysSincePhase3Release:null,daysToPdufa:null,cutoffReached:null};
  const release=dateDays(dates.phase3DataRelease?.date);
  const pdufa=dateDays(dates.pdufaTarget?.date);
  return {
    daysSincePhase3Release:release!==null && release<=now?now-release:null,
    daysToPdufa:pdufa!==null?pdufa-now:null,
    cutoffReached:pdufa!==null ? pdufa-now<=3:null,
  };
}
