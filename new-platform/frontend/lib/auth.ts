import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const COOKIE_NAME = "pdufa_setup_session";
export const SESSION_MAX_AGE = 7 * 24 * 60 * 60;

function digest(value: string) {
  return createHash("sha256").update(value, "utf8").digest();
}

function signature(payload: string) {
  return createHmac("sha256", process.env.SESSION_SIGNING_KEY || "")
    .update(payload, "utf8").digest("hex");
}

export function authConfigured(): boolean {
  return Boolean(
    process.env.DASHBOARD_PASSWORD &&
    process.env.DASHBOARD_PASSWORD.length >= 12 &&
    process.env.SESSION_SIGNING_KEY &&
    process.env.SESSION_SIGNING_KEY.length >= 32
  );
}

export function checkPassword(password: unknown): boolean {
  if (!authConfigured() || typeof password !== "string") return false;
  return timingSafeEqual(digest(password), digest(process.env.DASHBOARD_PASSWORD || ""));
}

export function makeSession(): string {
  const payload = "v1." + String(Math.floor(Date.now() / 1000) + SESSION_MAX_AGE);
  return payload + "." + signature(payload);
}

export function hasSession(cookie: string | undefined): boolean {
  if (!authConfigured() || !cookie) return false;
  const parts = cookie.split(".");
  if (parts.length !== 3 || parts[0] !== "v1") return false;
  const expiry = Number(parts[1]);
  const now = Math.floor(Date.now() / 1000);
  if (!Number.isSafeInteger(expiry) || expiry <= now || expiry > now + SESSION_MAX_AGE) return false;
  if (!/^[a-f0-9]{64}$/.test(parts[2])) return false;
  const expected = Buffer.from(signature(parts[0] + "." + parts[1]), "hex");
  const received = Buffer.from(parts[2], "hex");
  return expected.length === received.length && timingSafeEqual(expected, received);
}
