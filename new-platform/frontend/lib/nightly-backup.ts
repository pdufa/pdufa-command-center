/** Dedicated DST-aware admission gate for Vercel Cron, independent of GitHub schedule. */
export const SCAN_WORKFLOW = "pdufa-overnight-sequential.yml";
export const SCAN_REPO = "pdufa/pdufa-command-center";
export const SCAN_TITLE = "ALL + GEM — PDUFA overnight";
const ACTIVE = new Set(["queued","in_progress","waiting","requested","pending"]);
export type Decision =
  | { action:"skip"; night:string; reason:string; runId?:number }
  | { action:"error"; night:string; reason:string }
  | { action:"dispatch"; night:string; reason:string; scanMode:"FULL"|"DELTA"; gemAction:"RESCAN_ALL"|"REVERIFY_PARTIAL" };
export function pacificTime(date:Date) {
  if (!Number.isFinite(date.getTime())) throw Error("Invalid date");
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit",
    hour:"2-digit",hourCycle:"h23",weekday:"short"
  }).formatToParts(date);
  const get=(key:string)=>parts.find(x=>x.type===key)?.value||"";
  return {night:[get("year"),get("month"),get("day")].join("-"),
          hour:Number(get("hour")),weekday:get("weekday")};
}
export function backupDecision(history:unknown,now:Date):Decision {
  const {night,hour,weekday}=pacificTime(now);
  if (hour<21||hour>23) return {action:"skip",night,reason:"Outside nighttime recovery window"};
  if (!Array.isArray(history)||history.length>=100)
    return {action:"error",night,reason:"Missing or potentially truncated workflow history"};
  for (const row of history) {
    if (!row||typeof row!=="object")return {action:"error",night,reason:"Malformed GitHub history"};
    const r=row as Record<string,unknown>;
    if(r.event!=="workflow_dispatch"||r.head_branch!=="main"||
       r.path!==".github/workflows/"+SCAN_WORKFLOW||r.display_title!==SCAN_TITLE)continue;
    if(typeof r.created_at!=="string"||!Number.isFinite(Date.parse(r.created_at))||
       typeof r.status!=="string"||typeof r.id!=="number"||!Number.isSafeInteger(r.id))
      return {action:"error",night,reason:"Malformed existing full scan"};
    const created=new Date(r.created_at);
    if(created.getTime()>now.getTime()+60000)
      return {action:"error",night,reason:"Future-dated scan; clock uncertain"};
    if(ACTIVE.has(r.status))return {action:"skip",night,runId:r.id,reason:"Existing full sequence active"};
    const pacific=pacificTime(created);
    if(pacific.night===night&&pacific.hour>=21)
      return {action:"skip",night,runId:r.id,reason:r.conclusion==="success"
        ?"Today's full sequence already completed":
        "Today's full sequence already launched (check failure status; no automatic duplicate)"};
  }
  const full=weekday==="Sun";
  return {action:"dispatch",night,reason:full?"Missing Sunday full sequence":"Missing weekday delta sequence",
          scanMode:full?"FULL":"DELTA",gemAction:full?"RESCAN_ALL":"REVERIFY_PARTIAL"};
}
