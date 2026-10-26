export type SystemName = "SCIENCE" | "OUTCOME" | "MAIN";
export type VerifiedCount = { completed: number; total: number; scope: string; evidenceUri: string };
export type DatedSnapshot = { asOf: string; systems: Record<SystemName, VerifiedCount | null> };
export type ProgressResult = { percent: number | null; changePp: number | null; remainingPp: number | null; etaDays: number | null; etaDate: string | null; status: "NOT_VERIFIED" | "BASELINE_ONLY" | "MEASURED" };

function validDate(s: unknown): number | null {
  if (typeof s !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const ms = Date.parse(s + "T00:00:00Z");
  return Number.isFinite(ms) && new Date(ms).toISOString().slice(0, 10) === s ? ms : null;
}
function validCount(c: VerifiedCount | null | undefined): c is VerifiedCount {
  if (!c || !Number.isSafeInteger(c.completed) || !Number.isSafeInteger(c.total)
    || c.total <= 0 || c.completed < 0 || c.completed > c.total
    || typeof c.scope !== "string" || !c.scope.trim() || typeof c.evidenceUri !== "string") return false;
  try {const u = new URL(c.evidenceUri); return u.protocol === "https:" && !u.username && !u.password;} catch {return false;}
}
const dayMs = 86400000;

/** Adjacent dates establish daily change. Eight actual daily observations spanning
 * seven days are required for an ETA; two sparse endpoints are insufficient.
 */
export function calculateProgress(name: SystemName, previous: DatedSnapshot | null, current: DatedSnapshot | null, history: readonly DatedSnapshot[] = []): ProgressResult {
  const empty: ProgressResult = {percent:null,changePp:null,remainingPp:null,etaDays:null,etaDate:null,status:"NOT_VERIFIED"};
  const now = current?.systems?.[name];
  const nowMs = validDate(current?.asOf);
  if (!validCount(now) || nowMs === null) return empty;
  const percent = 100 * now.completed / now.total;
  const baseline: ProgressResult = {...empty,percent,remainingPp:100-percent,status:"BASELINE_ONLY"};
  const before = previous?.systems?.[name];
  const beforeMs = validDate(previous?.asOf);
  if (!validCount(before) || beforeMs === null || nowMs - beforeMs !== dayMs || before.total !== now.total || before.scope !== now.scope) return baseline;
  const measured: ProgressResult = {...baseline,changePp:percent-100*before.completed/before.total,status:"MEASURED"};
  if (percent === 100) return {...measured,etaDays:0,etaDate:current!.asOf};
  const recent = history.slice(-8);
  if (recent.length !== 8) return measured;
  let firstCompleted = 0, lastCompleted = -1;
  for (const [i, entry] of recent.entries()) {
    const count = entry?.systems?.[name];
    if (validDate(entry?.asOf) !== nowMs-(7-i)*dayMs || !validCount(count) || count.scope !== now.scope || count.total !== now.total || count.completed < lastCompleted) return measured;
    if (i === 0) firstCompleted = count.completed;
    lastCompleted = count.completed;
  }
  if (lastCompleted !== now.completed || recent[6].systems[name]?.completed !== before.completed || lastCompleted <= firstCompleted) return measured;
  const etaDays = Math.ceil((now.total-now.completed)*7/(lastCompleted-firstCompleted));
  if (!Number.isSafeInteger(etaDays) || etaDays <= 0 || etaDays > 3650) return measured;
  return {...measured,etaDays,etaDate:new Date(nowMs+etaDays*dayMs).toISOString().slice(0,10)};
}
