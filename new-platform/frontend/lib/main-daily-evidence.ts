import inventory from "../data/mainAcceptanceInventory.json";
import snapshots from "../data/mainDailyEvidenceSnapshots.json";
import deployment from "../data/mainProductionDeploymentEvidence.json";
import { AUDIT_GROUPS } from "./installation-audit-summary";
import type { DatedSnapshot } from "./daily-system-progress";

export const MAIN_DAILY_SCOPE = "MAIN/core-platform-gates/v2";
const scope = MAIN_DAILY_SCOPE;
const policySource = "https://github.com/pdufa/pdufa-command-center/blob/44c2b45a4d5d7b853e1544a31d87cba43fcbbcf4/docs/main-technical-installation-scope-20261025.md";
const stages = ["code", "deployment", "runtime", "evidence"] as const;
const states = new Set(["Verified", "Code present", "Preview READY", "Partial", "Not verified", "Not audited"]);
const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
// The dated gate inventory is immutable historical evidence. The active
// POOL/Pipeline installation criteria have changed, so never silently
// reinterpret older gate IDs as newly established qualifications.
const gateIds = inventory.gates.map(gate => ({id:gate.id,component:gate.component,stage:gate.stage}));
const record = (v: unknown): Record<string, unknown> => {
  if (!v || typeof v !== "object" || Array.isArray(v)) throw new Error("Malformed evidence record");
  return v as Record<string, unknown>;
};
const timestamp = (v: unknown): number => {
  if (typeof v !== "string" || !/^\d{4}-\d{2}-\d{2}T.*Z$/.test(v) || !Number.isFinite(Date.parse(v))) throw new Error("Invalid evidence timestamp");
  return Date.parse(v);
};
const pacificDay = (ms: number) => new Intl.DateTimeFormat("en-CA", {
  timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit",
}).format(new Date(ms));

export type MainEvidenceAudit = {
  valid: boolean; reason: string; history: DatedSnapshot[];
  verified: number; signals: number; partial: number; unverified: number;
  total: number; acceptedSections: number; sections: number;
  observations: {id:string; status:string; evidenceUri:string; note:string}[];
};

/** Only exact per-gate proof can contribute to the fixed MAIN numerator.
 * Production build metadata proves deployment, not complete runtime acceptance.
 */
export function auditMainDailyEvidence(inventoryInput: unknown, snapshotsInput: unknown, proofInput: unknown): MainEvidenceAudit {
  const empty: MainEvidenceAudit = {valid:false,reason:"MAIN evidence not verified",history:[],verified:0,signals:0,partial:0,unverified:0,total:0,acceptedSections:0,sections:0,observations:[]};
  try {
    const inv = record(inventoryInput);
    if (inv.schemaVersion !== 1 || inv.scope !== scope || inv.policySource !== policySource || !Array.isArray(inv.gates) || inv.gates.length !== 31 || gateIds.length !== 31) throw new Error("Frozen 31-gate scope changed");
    const source = inv.source;
    if (typeof source !== "string" || !/^https:\/\/github\.com\/pdufa\/pdufa-command-center\/blob\/[0-9a-f]{40}\/new-platform\/frontend\/app\/installation-audit\/page\.tsx$/.test(source)) throw new Error("Inventory needs an immutable source");
    for (const [i, expected] of gateIds.entries()) {
      const gate = record(inv.gates[i]);
      if (gate.id !== expected.id || gate.component !== expected.component || gate.stage !== expected.stage) throw new Error("Missing, duplicate or reassigned gate");
    }
    if (JSON.stringify(inv.excluded) !== JSON.stringify([{component:"Core Platform",stage:"evidence",reason:"Not applicable in the original inventory"}])) throw new Error("Excluded gate changed");
    if (!Array.isArray(snapshotsInput) || snapshotsInput.length === 0 || snapshotsInput.length > 400) throw new Error("Dated observations missing");
    const proofs = new Map<string, Record<string, unknown>>();
    for (const candidate of Array.isArray(proofInput) ? proofInput : [proofInput]) {
      const proof = record(candidate);
      const proofMs = timestamp(proof.observedAt);
      const readyMs = timestamp(proof.readyAt);
      if (proof.type !== "vercel-production-deployment" || proof.projectId !== "prj_7VRIuXH3FzUseTmXkzLDYQbEAd5l" || proof.projectName !== "pdufa-new-dashboard" || proof.repository !== "pdufa/pdufa-command-center" || proof.branch !== "main" || proof.target !== "production" || proof.state !== "READY" || readyMs > proofMs) throw new Error("Production deployment proof not established");
      if (typeof proof.commit !== "string" || !/^[0-9a-f]{40}$/.test(proof.commit) || typeof proof.id !== "string" || !/^dpl_[A-Za-z0-9]+$/.test(proof.id)) throw new Error("Exact production identity missing");
      if (typeof proof.url !== "string" || !/^https:\/\/pdufa-new-dashboard-[a-z0-9]+-pdufa\.vercel\.app$/.test(proof.url) || !Array.isArray(proof.aliases) || !proof.aliases.includes("pdufa-new-dashboard.vercel.app") || proof.evidenceUri !== "https://vercel.com/pdufa/pdufa-new-dashboard/"+proof.id.slice(4)) throw new Error("Production alias or evidence link mismatch");
      if (proofs.has(proof.id)) throw new Error("Duplicate deployment proof");
      proofs.set(proof.id, proof);
    }
    let previousDay = "";
    let result = empty;
    const history: DatedSnapshot[] = [];
    for (const input of snapshotsInput) {
      const row = record(input);
      const recordedMs = timestamp(row.recordedAt);
      if (recordedMs > Date.now()) throw new Error("Future-dated observation");
      if (row.schemaVersion !== 1 || row.scope !== scope || row.policySource !== policySource || row.inventorySource !== source || row.timezone !== "America/Los_Angeles" || row.asOf !== pacificDay(recordedMs) || typeof row.asOf !== "string" || row.asOf <= previousDay) throw new Error("Snapshot date, order or inventory mismatch");
      if (!Array.isArray(row.observations) || row.observations.length !== gateIds.length) throw new Error("Complete per-gate observations required");
      let verified = 0, signals = 0, partial = 0, unverified = 0;
      const observations: MainEvidenceAudit["observations"] = [];
      for (const [i, expected] of gateIds.entries()) {
        const observation = record(row.observations[i]);
        if (observation.id !== expected.id || typeof observation.status !== "string" || !states.has(observation.status) || typeof observation.note !== "string" || !observation.note.trim()) throw new Error("Invalid gate observation");
        if (observation.status === "Verified") {
          const proof = proofs.get(observation.proofId as string);
          if (!proof) throw new Error("Verified gate lacks exact dated proof");
          const proofMs = timestamp(proof.observedAt);
          if (expected.id !== "core-platform.deployment" || observation.proofId !== proof.id || observation.evidenceUri !== proof.evidenceUri || row.productionCommit !== proof.commit || proofMs > recordedMs || pacificDay(proofMs) !== row.asOf) throw new Error("Verified gate lacks exact dated proof");
          verified++;
        } else {
          const expectedSource = expected.component === "Final Acceptance" ? policySource : source;
          if (observation.evidenceUri !== expectedSource || observation.proofId !== undefined) throw new Error("Unverified status source mismatch");
          if (observation.status === "Code present" || observation.status === "Preview READY") signals++;
          else if (observation.status === "Partial") partial++;
          else unverified++;
        }
        observations.push({id:expected.id,status:observation.status,evidenceUri:observation.evidenceUri as string,note:observation.note});
      }
      const acceptedSections = [...new Set(gateIds.map(gate=>gate.component))].filter(component => gateIds
        .filter(gate => gate.component === component)
        .every(gate => observations.find(o => o.id === gate.id)?.status === "Verified")).length;
      const snapshotEvidenceUri = observations.find(o => o.status === "Verified")?.evidenceUri ?? source;
      history.push({asOf:row.asOf,systems:{SCIENCE:null,OUTCOME:null,MAIN:{completed:verified,total:gateIds.length,scope,evidenceUri:snapshotEvidenceUri}}});
      result = {valid:true,reason:"Dated MAIN gate baseline; deployment metadata verifies one gate only.",history,verified,signals,partial,unverified,total:gateIds.length,acceptedSections,sections:new Set(gateIds.map(gate=>gate.component)).size,observations};
      previousDay = row.asOf;
    }
    return result;
  } catch (error) {
    return {...empty,reason:error instanceof Error ? error.message : "MAIN evidence not verified"};
  }
}

export const MAIN_DAILY_EVIDENCE = auditMainDailyEvidence(inventory, snapshots, deployment);
