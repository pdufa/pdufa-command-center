import { NextRequest, NextResponse } from "next/server";
import { authConfigured, checkPassword, COOKIE_NAME, hasSession, makeSession, SESSION_MAX_AGE } from "../../../lib/auth";

export const runtime = "nodejs";

function sameOrigin(req: NextRequest) {
  const origin = req.headers.get("origin");
  return !origin || origin === req.nextUrl.origin;
}

export async function GET(req: NextRequest) {
  if (!authConfigured()) {
    return NextResponse.json({ error: "Setup not configured" }, { status: 503 });
  }
  return NextResponse.json(
    { authenticated: hasSession(req.cookies.get(COOKIE_NAME)?.value) },
    { headers: { "Cache-Control": "no-store" } }
  );
}

export async function POST(req: NextRequest) {
  if (!sameOrigin(req)) return NextResponse.json({ error: "Origin not allowed" }, { status: 403 });
  if (!authConfigured()) return NextResponse.json({ error: "Setup not configured" }, { status: 503 });
  const input = await req.json().catch(() => ({}));
  if (!checkPassword(input.password)) return NextResponse.json({ error: "Invalid password" }, { status: 401 });
  const response = NextResponse.json({ authenticated: true });
  response.cookies.set(COOKIE_NAME, makeSession(), {
    httpOnly: true, secure: process.env.NODE_ENV === "production",
    sameSite: "strict", path: "/", maxAge: SESSION_MAX_AGE
  });
  return response;
}

export async function DELETE(req: NextRequest) {
  if (!sameOrigin(req)) return NextResponse.json({ error: "Origin not allowed" }, { status: 403 });
  const response = NextResponse.json({ authenticated: false });
  response.cookies.delete(COOKIE_NAME);
  return response;
}
