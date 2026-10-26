import { NextRequest, NextResponse } from "next/server";
import { authConfigured, COOKIE_NAME, hasSession } from "../../../lib/auth";
import { readNightlyHealth, unavailableNightlyHealth } from "../../../lib/main-phase3-nightly-health";

// Public GitHub repository evidence read via the SERVER, not a live trade list.
// GitHub UTC cron can produce intentionally skipped DST-alternate jobs.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

async function githubJson(url:string):Promise<unknown> {
  if(!url.startsWith("https://api.github.com/repos/pdufa/pdufa-command-center/actions/"))
    throw new Error("Unexpected GitHub source");
  const response=await fetch(url,{
    headers:{
      Accept:"application/vnd.github+json",
      "X-GitHub-Api-Version":"2022-11-28",
      "User-Agent":"pdufa-main-phase3-nightly-readonly",
    },
    next:{revalidate:120},
    signal:AbortSignal.timeout(8000),
  });
  if(!response.ok)throw new Error("GitHub scheduled research run could not be verified");
  return response.json();
}

export async function GET(req:NextRequest) {
  if(!authConfigured() || !hasSession(req.cookies.get(COOKIE_NAME)?.value)){
    return NextResponse.json({error:"Authentication required"},{
      status:401,headers:{"Cache-Control":"private, no-store"}
    });
  }
  const now=new Date();
  try {
    const health=await readNightlyHealth(githubJson,now);
    return NextResponse.json(health,{headers:{"Cache-Control":"private, no-store"}});
  } catch {
    // A failed GitHub request or malformed payload is UNKNOWN, not a passed
    // scan, and is distinct from GitHub's explicitly reported failed job.
    return NextResponse.json(unavailableNightlyHealth(now),{
      status:503,headers:{"Cache-Control":"private, no-store"}
    });
  }
}
