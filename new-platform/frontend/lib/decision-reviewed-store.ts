import {constants} from "node:fs";
import {open, realpath} from "node:fs/promises";
import {createHash} from "node:crypto";
import {isAbsolute, join} from "node:path";
import type {DecisionIdentity, ReviewedDecisionEvidence} from "./decision-workstream";
import {MAX_REVIEWED_MANIFEST_BYTES, parseReviewedDecisionManifest, validateDecisionIdentity} from "./decision-reviewed-manifest";

export type ReviewedDecisionRead = {status:"AVAILABLE_FOR_REVIEW"; evidence:ReviewedDecisionEvidence; manifestSha256:string}
  | {status:"UNCONFIGURED"|"MISSING"|"INVALID"};

/** Opt-in local source only. Never creates a manifest, follows a file symlink, or changes configuration. */
export async function loadReviewedDecisionEvidence(identity:DecisionIdentity, directory:string|undefined):Promise<ReviewedDecisionRead> {
  try { validateDecisionIdentity(identity); } catch { return {status:"INVALID"}; }
  if (!directory) return {status:"UNCONFIGURED"};
  if (!isAbsolute(directory) || typeof constants.O_NOFOLLOW !== "number") return {status:"INVALID"};
  let file;
  try {
    const root = await realpath(directory);
    file = await open(join(root, identity.programId + "." + identity.stage + ".json"), constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    const stat = await file.stat();
    if (!stat.isFile() || stat.size > MAX_REVIEWED_MANIFEST_BYTES) return {status:"INVALID"};
    const buffer = Buffer.alloc(MAX_REVIEWED_MANIFEST_BYTES + 1);
    let total = 0;
    while (total < buffer.length) {
      const {bytesRead} = await file.read(buffer, total, buffer.length - total, total);
      if (!bytesRead) break;
      total += bytesRead;
    }
    const after = await file.stat();
    if (total > MAX_REVIEWED_MANIFEST_BYTES || total !== stat.size || stat.size !== after.size
        || stat.mtimeMs !== after.mtimeMs || stat.ctimeMs !== after.ctimeMs) return {status:"INVALID"};
    const bytes = buffer.subarray(0, total);
    const evidence = parseReviewedDecisionManifest(JSON.parse(bytes.toString("utf8")), identity);
    return {status:"AVAILABLE_FOR_REVIEW", evidence, manifestSha256:createHash("sha256").update(bytes).digest("hex")};
  } catch (error) {
    return {status:(error as NodeJS.ErrnoException)?.code === "ENOENT" ? "MISSING" : "INVALID"};
  } finally { await file?.close(); }
}
