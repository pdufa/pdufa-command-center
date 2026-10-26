export type SystemName = "SCIENCE" | "OUTCOME" | "MAIN";
export type VerifiedCount = { completed: number; total: number; scope: string; evidenceUri: string };
export type DatedSnapshot = { asOf: string; systems: Record<SystemName, VerifiedCount | null> };
export type ProgressResult = { percent: number | null; changePp: number | null; remainingPp: number | null; etaDays: number | null; etaDate: string | null; status: "NOT_VERIFIED" | "BASELINE_ONLY" | "MEASURED" };

function validDate(s: string): number | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const ms = Date.parse(s + "T00:00:00Z");
  return Number.isFinite(ms) && new Date(ms).toISOString().slice(0, 10) === s ? ms : null;
}
function validCount(c: VerifiedCount | null | undefined): c is VerifiedCount {
  return !!c && Number.isSafeInteger(c.completed) && Number.isSafeInteger(c.total)
    && c.total > 0 && c.completed >= 0 && c.completed <= c.total
    && !!c.scope.trim() && /^https:\/\//.test(c.evidenceUri);
}
/** A forecast requires comparable denominators, dated evidence, and positive observed progress. */
export function calculateProgress(name: SystemName, previous: DatedSnapshot | null, current: DatedSnapshot | null): ProgressResult {
  const empty: ProgressResult = {percent:null,changePp:null,remainingPp:null,etaDays:null,etaDate:null,status:"NOT_VERIFIED"};
  const now = current?.systems[name];
  const nowMs = current ? validDate(current.asOf) : null;
  if (!validCount(now) || nowMs === null) return empty;
  const percent = 100 * now.completed / now.total;
  const baseline: ProgressResult = {...empty,percent,remainingPp:100-percent,status:"BASELINE_ONLY"};
  const before = previous?.systems[name];
  const beforeMs = previous ? validDate(previous.asOf) : null;
  if (!validCount(before) || beforeMs === null || beforeMs >= nowMs || before.total !== now.total || before.scope !== now.scope) return baseline;
  const changePp = percent - 100 * before.completed / before.total;
  const days = (nowMs - beforeMs) / 86400000;
  // A single day-over-day change is not a defensible long-range ETA.
  // Require at least 7 calendar days between independent verified snapshots.
  if (changePp <= 0 || days < 7 || percent >= 100) return {...baseline,changePp,status:"MEASURED",etaDays:percent >= 100 ? 0 : null,etaDate:percent >= 100 ? current!.asOf : null};
  const etaDays = Math.ceil((100 - percent) / (changePp / days));
  if (!Number.isFinite(etaDays) || etaDays < 0 || etaDays > 3650) return {...baseline,changePp,status:"MEASURED"};
  return {...baseline,changePp,status:"MEASURED",etaDays,etaDate:new Date(nowMs + etaDays * 86400000).toISOString().slice(0,10)};
}
