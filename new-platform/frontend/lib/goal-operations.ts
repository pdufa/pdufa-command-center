/** Conservative operational readiness, grounded in the same saved audit used by SCANS.
 * A successful workflow is not proof that source, SMS, or Google Drive backups succeeded.
 */
import { scoreAuditView } from "./scoring-audit";
import type { GoalScanView } from "./goal-scan-evidence";

export type GoalOperationalState = {
  scan: { label:string; detail:string; date:string|null; url:string|null; concern:boolean };
  scoring: { label:string; detail:string; gaps:number|null; url:string|null; concern:boolean };
};
export function goalOperationalState(scan:GoalScanView|null, scoring:unknown, now=Date.now()):GoalOperationalState{
  const audit=scoreAuditView(scoring,now);
  const gaps=audit ? audit.audit.checks.filter(c=>c.Status==="DATA GAP"||c.Status==="REVIEW").length:null;
  const current=scan?.today===true && scan.status==="COMPLETE";
  const scanStatus=scan ? {
    label:scan.status==="PARTIAL" ? "Partial published evidence" :
      scan.status==="RUN_FAILED" ? "Published run failed" :
      scan.today ? "Published workflow completed" : "Previous-day report only",
    detail:"Pacific scan "+scan.date+". A successful run does not independently verify every FDA, SEC, GEM, or scoring input.",
    date:scan.date,url:scan.runUrl,concern:!current
  } : {label:"Not verified",detail:"No complete dated original scan run could be matched.",date:null,url:null,concern:true};
  const scoringStatus=audit ? {
    label:audit.audit.status==="NO_INPUT_GAPS_FOUND" && audit.freshness==="CURRENT"
      ? "Saved fields present; sources not certified" : audit.audit.status.replaceAll("_"," "),
    detail:(gaps===null?"Unknown":String(gaps))+" scoring-input checks need attention. Saved stock/FDA/financing snapshots only; "+(audit.freshness==="CURRENT"?"published within 48 hours":audit.freshness==="STALE"?"audit is older than 48 hours":"publication clock unverified")+".",
    gaps,concern:gaps!==0 || audit.freshness!=="CURRENT" || audit.audit.status!=="NO_INPUT_GAPS_FOUND",
    url:"https://github.com/pdufa/pdufa-command-center/actions/runs/"+audit.audit.source_scan.run_id
  } : {label:"Not verified",detail:"No valid scoring-input report is available. Missing inputs are not scores.",gaps:null,url:null,concern:true};
  return {scan:scanStatus,scoring:scoringStatus};
}
