import {NextRequest, NextResponse} from "next/server";
import {authConfigured, COOKIE_NAME, hasSession} from "../../../../lib/auth";
import {validateDecisionIdentity} from "../../../../lib/decision-reviewed-manifest";
import {loadReviewedDecisionEvidence} from "../../../../lib/decision-reviewed-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = {"Cache-Control":"private, no-store"};

/** Only authenticated reads. Review metadata is never promoted to independent validation. */
export async function GET(req:NextRequest, context:{params:Promise<{programId:string}>}) {
  const reply = (body:unknown, status:number) => NextResponse.json(body, {status, headers});
  if (!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value))
    return reply({error:"Authentication required"}, 401);
  const {programId} = await context.params;
  let identity;
  try {
    identity = validateDecisionIdentity({programId, exactKey:req.nextUrl.searchParams.get("identity"),
      trialId:req.nextUrl.searchParams.get("trialId"), ticker:req.nextUrl.searchParams.get("ticker"),
      stage:req.nextUrl.searchParams.get("stage")});
  } catch { return reply({error:"Exact program, trial, ticker and assessment stage required"}, 422); }
  const result = await loadReviewedDecisionEvidence(identity, process.env.PDUFA_DECISION_EVIDENCE_DIR);
  if (result.status !== "AVAILABLE_FOR_REVIEW") return reply({error:"Reviewed decision evidence unavailable", reason:result.status}, result.status === "MISSING" ? 404 : 503);
  return reply({schemaVersion:1, identity, evidence:result.evidence, manifestSha256:result.manifestSha256,
    researchOnly:true, modelValidated:false, probability:null, tradeAuthorized:false}, 200);
}
