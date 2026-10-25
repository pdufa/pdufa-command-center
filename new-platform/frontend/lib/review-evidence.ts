/** Evidence pointers and review dates use the same rules as the read-only API. */
export function validReviewSource(value: unknown): value is string {
  if (typeof value !== "string" || !/^https:\/\//i.test(value) || /\s|\\/.test(value)) return false;
  try {
    const authority = value.slice(value.indexOf("://") + 3).split(/[/?#]/, 1)[0];
    const url = new URL(value);
    return !!authority && !authority.includes("@") && url.protocol === "https:" && !!url.hostname && !url.username && !url.password;
  } catch { return false; }
}

export function validReviewDate(value: unknown, today = new Date().toISOString().slice(0, 10)): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value < "0001-01-01") return false;
  const parsed = new Date(value + "T00:00:00.000Z");
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value && value <= today;
}
