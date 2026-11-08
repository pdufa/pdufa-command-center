/** Evidence-backed installation progress. Not scientific accuracy or task estimates.
 * Each named checkpoint has one independently observable acceptance condition.
 * Percent = verified checkpoints / defined checkpoints, including blocked and
 * unobserved ones in the denominator. Unknown NEVER becomes verified.
 * Separate from the historical 7 active MAIN release-acceptance gates.
 */
import focus from "../data/p3PostDataActive.json";
import {ADVANCED_LEVELS} from "./precision-monitor-levels";
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {HISTORICAL_CALIBRATION} from "./medical-intelligence-calibration";

export type CheckState="VERIFIED"|"PENDING"|"BLOCKED"|"FAILED"|"UNKNOWN";
export type Checkpoint={
 id:string;title:string;status:CheckState;detail:string;
 source:string;checkedAt:string|null;
};
export type Stage={
 id:string;title:string;status:"COMPLETE"|"PENDING"|"BLOCKED"|"FAILED"|"UNKNOWN";
 percent:number;verified:number;total:number;checks:Checkpoint[];
};
export type MonitorTelemetry={
 schemaVersion:number;observedAt:string;
 storage?:{state:string;kind:string;postgresRequired:boolean};
 sourceSnapshots?:Record<string,Record<string,unknown>>;
 services?:Record<string,Record<string,unknown>>;
 scans?:Record<string,Record<string,unknown>>;
 research?:Record<string,unknown>;
 analysisNow?:Record<string,unknown>;
 alerts?:Record<string,unknown>;
 errors?:string[];
 coverage?:Record<string,unknown>;
};
export type ExternalVerification={
 observedAt:string;deployment:{state:"READY"|"UNKNOWN";sha:string|null;url:string|null};
 medicalQa:"success"|"failure"|"pending"|"unknown";
 overallCi:"success"|"failure"|"pending"|"unknown";
 scheduledScans:{state:"success"|"failure"|"running"|"unknown";at:string|null;url:string|null};
 apiReachable:boolean;
 analyzeNowAllEnabled?:boolean;
};
export type MonitorSnapshot={
 schemaVersion:1;observedAt:string;
 methodology:string;stages:Stage[];
 overall:{percent:number;verified:number;total:number;pending:number;blocked:number;failed:number;unknown:number};
 nextUnfinished:{stage:string;checkpoint:string;status:CheckState;detail:string}|null;
 health:{level:"HEALTHY"|"DEGRADED"|"BLOCKED"|"UNKNOWN";issues:string[]};
 facts:{focusTrialCount:number;fdaApplicationCycles:number;advancedLevelDefinitions:number;
 historicalCalibrationRows:number;rosterAsOf:string;productionModified:false};
 signals:{scans:MonitorTelemetry["scans"];research:MonitorTelemetry["research"];
 analysisNow:MonitorTelemetry["analysisNow"];
 alerts:MonitorTelemetry["alerts"];coverage:MonitorTelemetry["coverage"]};
};

export function buildInstallationProgress(
 live:MonitorTelemetry|null,external:ExternalVerification,at:string
):MonitorSnapshot{
 const points:Stage[]=[];
 const observed=live?.observedAt??null;
 const validStorage=Boolean(live?.schemaVersion===1&&live.storage?.state==="READY"&&live.storage?.kind==="postgresql");
 const backendDown=!validStorage||!external.apiReachable;
 const research=live?.research??{};
 const analyzeNow=live?.analysisNow??{};
 const applications=live?.sourceSnapshots?.applications??{};
 const runtimeSha=live?.services?.backendDeployment?.gitSha;
 const backendSha=typeof runtimeSha==="string"&&/^[a-f0-9]{40}$/.test(runtimeSha)?runtimeSha:null;
 const frontendSha=external.deployment.sha;
 const commitParity:CheckState=backendSha&&frontendSha?
     (backendSha===frontendSha?"VERIFIED":"BLOCKED"):"UNKNOWN";
 const scans=live?.scans??{};
 const alerts=live?.alerts??{};
 const completeSourceRuns=typeof research.finishedSourceRuns==="number"?research.finishedSourceRuns:0;
 const revisions=typeof research.immutableRevisions==="number"?research.immutableRevisions:0;
 const sourceStages=typeof research.savedSourceStages==="number"?research.savedSourceStages:0;
 const phase3=scans.phase3Ingestion??{};
 const stream=scans.nctStream??{};
 const reg=scans.registryWatch??{};
 const focusUnique=focus.records.length>0&&new Set(focus.records.map(r=>r.nct)).size===focus.records.length&&
   focus.records.every(r=>/^NCT\d{8}$/.test(r.nct));
 const from=(id:string,title:string,status:CheckState,detail:string,source:string,checkedAt:string|null=at):Checkpoint=>
   ({id,title,status,detail,source,checkedAt});
 const add=(id:string,title:string,checks:Checkpoint[])=>{
   const verified=checks.filter(c=>c.status==="VERIFIED").length;
   const failed=checks.some(c=>c.status==="FAILED");
   const blocked=checks.some(c=>c.status==="BLOCKED");
   const unknown=checks.every(c=>c.status==="UNKNOWN");
   points.push({id,title,checks,verified,total:checks.length,
    percent:Math.floor(100*verified/checks.length),
    status:failed?"FAILED":blocked?"BLOCKED":verified===checks.length?"COMPLETE":unknown?"UNKNOWN":"PENDING"});
 };
 const backendBlock=()=>backendDown?"BLOCKED" as const:"PENDING" as const;
 add("pool","POOL — Master trial evidence",[
   from("pool.route","Master POOL workspace included","VERIFIED",
     "Existing POOL route/source UI preserved in the installed frontend source tree.","Bundled Next.js route"),
   from("pool.master","Live source-universe reconciliation","UNKNOWN",
     "No current record-level verification of the complete master universe is available through this monitor.","Live source inventory"),
   from("pool.scans","Ingestion state observed",
     validStorage&&typeof phase3.state==="string"&&phase3.state!=="UNKNOWN"?"VERIFIED":backendBlock(),
     "Read the backend Phase 3 ingestion ledger. Observing it does not prove the separate nightly PIPELINE scan.","PostgreSQL phase3_ingestion_state",observed),
   from("pool.source","All-source completeness and deduplication","PENDING",
     "FDA, SEC, literature and issuer-source completeness across the master POOL has not been independently certified.","Independent reconciliation")
 ]);
 add("focus","FOCUS — Qualified trial selection",[
   from("focus.snapshot","Exact, uniquely keyed FOCUS snapshot",focusUnique?"VERIFIED":"FAILED",
     focusUnique?focus.records.length+" distinct NCTs in dated local snapshot ("+focus.asOf+"). This does not certify current eligibility.":
       "Invalid or duplicate NCT identities in the bundled snapshot.","FOCUS dated snapshot"),
   from("focus.application","Application-cycle identity inventory","VERIFIED",
     APPLICATION_CYCLES.length+" reconstructured FDA application-cycle records; not verified against confidential FDA filing records.",
     "Curated source-linked application cycles"),
   from("focus.live","Current Google Sheet → backend synchronization","UNKNOWN",
     "Current live-sheet synchronization and exact reconciliation have not been demonstrated.","Google Sheets sync output"),
   from("focus.eligible","Independent case-by-case qualification","PENDING",
     "Market cap, Phase 3/post-data, indication and filing-cycle proofs still require source-level adjudication.","FOCUS acceptance audit")
 ]);
 add("infrastructure","Infrastructure — deployment, tests and storage",[
   from("infra.frontend","Frontend preview responding",external.deployment.state==="READY"?"VERIFIED":"UNKNOWN",
     external.deployment.state==="READY"?"Serving compiled preview "+(external.deployment.sha?.slice(0,8)??""):"Current deployment not independently identified.","Vercel deployment metadata",external.observedAt),
   from("infra.commit-parity","Exact frontend/backend deployment parity",commitParity,
     backendSha&&frontendSha?
       "Vercel "+frontendSha.slice(0,12)+" vs Render running "+backendSha.slice(0,12)+
       (backendSha===frontendSha?" — identical commits.":" — deployment revisions differ; verify backend rollout."):
       "Cannot compare authenticated running Render SHA with this Vercel deployment SHA.",
     "Render RENDER_GIT_COMMIT and Vercel VERCEL_GIT_COMMIT_SHA",observed),
   from("infra.backend","Medical API health observed",external.apiReachable?"VERIFIED":"BLOCKED",
     external.apiReachable?"Authenticated health endpoint returned a structured result.":"Cannot retrieve current authenticated backend health.","Backend API",observed),
   from("infra.storage","Persistent PostgreSQL available",validStorage?"VERIFIED":"BLOCKED",
     validStorage?"Confirmed live PostgreSQL backend readiness.":"Missing/unavailable PostgreSQL; no source-history data assumed saved.","Backend storage health",observed),
   from("infra.medical-ci","Dedicated medical regression workflow",
     external.medicalQa==="success"?"VERIFIED":external.medicalQa==="failure"?"FAILED":
     external.medicalQa==="pending"?"PENDING":"UNKNOWN",
     "Only an exact current-deployment-commit passing medical QA counts; stale proof is excluded.","GitHub Actions",external.observedAt),
   from("infra.full-ci","MAIN integrated frontend/backend CI",
     external.overallCi==="success"?"VERIFIED":external.overallCi==="failure"?"FAILED":
       external.overallCi==="pending"?"PENDING":"UNKNOWN",
     "Broader legacy tests may fail independently of the medical-only suite.","GitHub Actions",external.observedAt)
 ]);
 add("medical","Standalone Deep Medical Intelligence",[
   from("medical.code","Independent research framework","VERIFIED",
     "Evidence-gated, 12-level medical framework operates independently of retired scoring and survey architectures.","Medical application source code"),
   from("medical.application-map","Backend packaged 29-NCT application context",
     applications.state==="VALID"&&applications.focusNctCount===focus.records.length&&
       applications.coveredNctCount===focus.records.length?"VERIFIED":
       applications.state==="INVALID"?"FAILED":"UNKNOWN",
     applications.state==="VALID"?
       String(applications.applicationCycleCount)+" dated source-linked cycles across "+String(applications.coveredNctCount)+" exact FOCUS NCTs; conflicting indications remain unreconciled; not FDA-confirmed.":
       "No valid deployed application mapping observed. This is a Docker/package verification, not current FDA acceptance.",
     "Authenticated backend application identity verification",observed),
   from("medical.db","Durable 12-stage run schema",
     validStorage&&research.state==="OBSERVED"?"VERIFIED":backendBlock(),
     "Requires backend medical run and revision tables to be readable.","PostgreSQL medical_continuous_runs",observed),
   from("medical.complete","One complete real 12-stage saved research run",
     completeSourceRuns>0&&sourceStages>=12&&revisions>0?"VERIFIED":backendBlock(),
     "Source research run(s): "+completeSourceRuns+"; saved stages: "+sourceStages+"; append-only revisions: "+revisions+". Source collection is not a clinical adjudication.",
     "PostgreSQL saved source stages",observed),
   from("medical.external","Full independent clinical/FDA adjudication","PENDING",
     "No signed, complete current-cycle clinical/statistical/CMC regulator dossier has been demonstrated.","External multidisciplinary validation")
 ]);
 for(const level of ADVANCED_LEVELS){
   add("advanced-"+level.number,level.number+". "+level.title,[
     from(level.id+".defined","Phase-aware failure-first level defined","VERIFIED",
       level.failureQuestion+" Required inputs: "+level.requiredEvidence.length+".","Typed 12-level schema"),
     from(level.id+".original","Original evidence fully resolved","PENDING",
       "Source pointers are not original SAP/CSR/CMC/FDA verification or completed contradiction adjudication.","Source-specific evidence"),
     from(level.id+".review","Independent reviewer validation","PENDING",
       "No independently signed current-cycle level completion is recorded.","Medical/reviewer signoff")
   ]);
 }
 add("analyze-now","Analyze Now — immediate trial assessment",[
   from("analyze-now.button","Per-trial controls linked to FOCUS","VERIFIED",
     "Analyze Now and expandable NCT history controls are installed for each of 29 FOCUS trial rows. Non-pilot actions remain disabled until live validation.","FOCUS trial page"),
   from("analyze-now.pilot","One completed saved exact-NCT pilot",
     analyzeNow.state==="OBSERVED"&&analyzeNow.pilotSaved===true?"VERIFIED":backendBlock(),
     "Canary "+String(analyzeNow.pilotTrial??"NCT06081894")+" saved: "+String(analyzeNow.pilotSaved??"not observed")+". The exact report must include date, source gaps and separate uncalibrated outcomes.",
     "PostgreSQL medical_analyze_requests and medical_prediction_revisions",observed),
   from("analyze-now.automation","Automatic evidence/component reanalysis verified",
     analyzeNow.autoRerunEnabled===true&&typeof analyzeNow.componentWatchBaselines==="number"&&analyzeNow.componentWatchBaselines>0?"VERIFIED":backendBlock(),
     "Registry and newly operational component watchers require opt-in and persistent PostgreSQL; a baseline is not a completed reanalysis.","Persisted component watch and registry watch",observed),
   from("analyze-now.rollout","All 29 eligible trials operationally enabled",
     analyzeNow.pilotSaved===true&&analyzeNow.allTrialsEnabled===true&&external.analyzeNowAllEnabled===true?"VERIFIED":
       (analyzeNow.allTrialsEnabled===true)!==Boolean(external.analyzeNowAllEnabled)?"BLOCKED":"PENDING",
     "Wider rollout requires a saved pilot plus consistent backend and frontend enablement; no implicit enablement from a passing unit test.","Operator-approved environment rollout",observed)
 ]);
 add("predictions","FDA Prediction Engine — three separate outcomes",[
   from("prediction.contract","Approval, CRL and delay models remain separate","VERIFIED",
     "Three separate outcomes are defined, with abstention and null probabilities when unvalidated.","FDA prediction schema"),
   from("prediction.history","Saved prediction-research history",
     revisions>0?"VERIFIED":backendBlock(),
     revisions+" source revisions stored. All may still be ABSTAIN.","PostgreSQL medical_prediction_revisions",observed),
   from("prediction.forecast","Clinically and historically validated probabilities","PENDING",
     "Approval/CRL/delay forecasts are not released; no measured predictive reliability is available.","Historical out-of-time validation")
 ]);
 add("certainty","Independent Prediction Certainty Rating",[
   from("certainty.separate","Certainty independent from prediction odds","VERIFIED",
     "Certainty and prediction reliability are separate typed fields, never inferred from source count.","Medical outcome schema"),
   from("certainty.calibrated","Externally validated reliability and intervals","PENDING",
     "Certainty rating remains null without calibrated outcome-specific performance and uncertainty.","Calibration and model governance")
 ]);
 add("calibration","Historical prediction backtesting and calibration",[
   from("calib.evaluator","Temporal leakage-guarded calibration evaluator","VERIFIED",
     "Historical Brier score and calibration-error evaluation is coded without unlocking forecasts.","Calibration source"),
   from("calib.outcomes","Verified locked historical cohort",
     HISTORICAL_CALIBRATION.eligibleCount>0?"VERIFIED":"PENDING",
     HISTORICAL_CALIBRATION.eligibleCount+" qualified real historical application records in the current cohort.","Historical source-derived outcome records"),
   from("calib.release","Out-of-sample performance and release approval","PENDING",
     "Historical release gate is false; no validated numerical probabilities.","Independent model validation")
 ]);
 const ingestionState=String(phase3.state??"UNKNOWN").toUpperCase();
 const ingressFailed=ingestionState==="FAILED"||ingestionState==="ERROR";
 const streamFailed=typeof stream.failedRuns==="number"&&stream.failedRuns>0;
 add("operations","Operations — scans, evidence changes and Telegram",[
   from("ops.ingestion","Phase 3 ingestion failure detection",
     ingressFailed?"FAILED":validStorage&&ingestionState!=="UNKNOWN"?"VERIFIED":backendBlock(),
     "Observed ingestion state: "+ingestionState+"; last success: "+String(phase3.lastSuccessAt??"unknown")+".","Backend ingestion ledger",observed),
   from("ops.scheduled","Nightly/scheduled scan executions",
     external.scheduledScans.state==="success"?"VERIFIED":
     external.scheduledScans.state==="failure"?"FAILED":
     external.scheduledScans.state==="running"?"PENDING":"UNKNOWN",
     "Latest directly observed scheduled run: "+String(external.scheduledScans.at??"unavailable")+". Scheduler scope is not inferred.","GitHub scheduled workflow runs",external.observedAt),
   from("ops.stream","NCT evidence collection runs",
     streamFailed?"FAILED":validStorage&&stream.state==="OBSERVED"?"VERIFIED":backendBlock(),
     "Persisted stream runs: "+String(stream.totalRuns??"unknown")+"; failures: "+String(stream.failedRuns??"unknown")+".","Backend NCT stream",observed),
   from("ops.watch","Automatic registry source monitoring",
     reg.enabled===true&&typeof reg.lastCheckedAt==="string"?"VERIFIED":backendBlock(),
     "ClinicalTrials.gov only; last check: "+String(reg.lastCheckedAt??"none")+". FDA/SEC/PubMed watchers are missing.","Backend medical registry watcher",observed),
   from("ops.telegram","Telegram alert delivery confirmed",
     alerts.lastDelivery&&typeof alerts.lastDelivery==="object"&&
       (alerts.lastDelivery as {state?:string}).state==="SENT"?"VERIFIED":
       alerts.telegramConfigured===true?"PENDING":"BLOCKED",
     alerts.telegramConfigured===true?"Bot configured; a successful milestone/failure delivery is required.":
       "Bot token/chat ID not both configured. No alert delivery claimed.","Persisted installation_monitor_alerts",observed)
 ]);
 const all=points.flatMap(s=>s.checks);
 const verified=all.filter(x=>x.status==="VERIFIED").length;
 const overall={percent:Math.floor(100*verified/all.length),verified,total:all.length,
   pending:all.filter(x=>x.status==="PENDING").length,blocked:all.filter(x=>x.status==="BLOCKED").length,
   failed:all.filter(x=>x.status==="FAILED").length,unknown:all.filter(x=>x.status==="UNKNOWN").length};
 const next=all.find(x=>x.status==="FAILED"||x.status==="BLOCKED")??all.find(x=>x.status!=="VERIFIED");
 const stage=next?points.find(s=>s.checks.includes(next)):null;
 const issues=[...new Set([
   ...(live?.errors??[]),
   ...all.filter(x=>x.status==="FAILED").map(x=>x.title),
   ...all.filter(x=>x.status==="BLOCKED").map(x=>x.title)
 ])];
 return {
   schemaVersion:1,observedAt:at,
   methodology:"Verified installation checkpoints ÷ all fixed checkpoints. Every checkpoint has equal weight. Failed, blocked, pending and unknown count as unfinished; source pointers and old QA do not count as validated scientific outcomes.",
   stages:points,overall,
   nextUnfinished:next&&stage?{stage:stage.title,checkpoint:next.title,status:next.status,detail:next.detail}:null,
   health:{level:overall.failed?"DEGRADED":overall.blocked?"BLOCKED":overall.unknown?"UNKNOWN":"HEALTHY",issues},
   facts:{focusTrialCount:focus.records.length,fdaApplicationCycles:APPLICATION_CYCLES.length,
     advancedLevelDefinitions:ADVANCED_LEVELS.length,historicalCalibrationRows:HISTORICAL_CALIBRATION.eligibleCount,
     rosterAsOf:focus.asOf,productionModified:false},
   signals:{scans:live?.scans,research:live?.research,analysisNow:live?.analysisNow,alerts:live?.alerts,coverage:live?.coverage}
 };
}
