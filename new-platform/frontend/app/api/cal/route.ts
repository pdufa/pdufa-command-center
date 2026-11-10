import { NextResponse } from "next/server";
import calendarResearch from "../../../data/calFocusResearchOverlay20261110.json";
import focusRoster from "../../../data/p3PostDataActive.json";
import {APPLICATION_CYCLES} from "../../../lib/medical-intelligence-applications";

/** Public read-only calendar with visibly PROVISIONAL research hypotheses.
 * Research is frozen: it cannot update production FDA predictions, accuracy,
 * probabilities, trial membership, or any Google Sheet.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const SOURCE = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/ios_focus_pdufa_calendar.json";
const noStore = {"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};

function validDate(date: unknown): date is string {
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsed = new Date(date + "T00:00:00Z");
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0,10) === date;
}
type CalendarSourceEvent = {
  id:string; ticker:string; company:string; date:string; drug:string;
  marketCapUsd:number; ncts:string[]; sourceUrl:string|null;
};
type ResearchCycle = (typeof calendarResearch.cycles)[number];

function validateResearch() {
  const p = calendarResearch.policy;
  if (calendarResearch.schemaVersion !== 1 ||
    calendarResearch.kind !== "CAL_FOCUS_LEVEL3_STYLE_RESEARCH_FREEZE_NOT_VALIDATED_FDA_FORECAST" ||
    !validDate(calendarResearch.asOf) || p.preliminarySourceLinkedResearch !== true ||
    p.independentScientificSignoff !== false || p.numericalProbabilities !== null ||
    p.notActivePredictionEngine !== true || p.notForTrading !== true ||
    calendarResearch.summary.exactNcts !== 29 ||
    calendarResearch.summary.applicationCycles !== 23 ||
    calendarResearch.cycles.length !== 23 || focusRoster.records.length < calendarResearch.summary.exactNcts)
    throw new Error("FOCUS research freeze safety gate failed");
  const canonical = new Map(APPLICATION_CYCLES.map(c=>[c.id,c]));
  const rosterByNct = new Map(focusRoster.records.map(r=>[r.nct,r]));
  const seen = new Set<string>();
  for (const c of calendarResearch.cycles) {
    const original = canonical.get(c.cycleId);
    if (seen.has(c.cycleId) || !original || c.ticker !== original.ticker ||
      JSON.stringify([...c.associatedNcts].sort()) !== JSON.stringify([...original.ncts].sort()) ||
      c.associatedNcts.some(n => rosterByNct.get(n)?.ticker !== c.ticker) ||
      c.level !== 3 || c.independentSignoff !== false ||
      c.calibratedProbability !== null ||
      !["APPROVAL_LEAN","CRL_LEAN","ABSTAIN","ALREADY_APPROVED"].includes(c.call)) {
      throw new Error("FOCUS research application-cycle identity or status invalid");
    }
    seen.add(c.cycleId);
  }
  if (seen.size !== calendarResearch.cycles.length) throw new Error("FOCUS cycles are incomplete");
  return rosterByNct;
}
function safeResearch(c:ResearchCycle) {
  return {
    cycleId:c.cycleId, call:c.call, level:c.level,
    provisional:true, asOf:calendarResearch.asOf,
    confidenceDescription:c.confidenceDescription,
    applicationStatusAsRecorded:c.applicationStatusAsRecorded,
    indication:c.indication, drug:c.drug, applicationType:c.applicationType,
    clinicalRationale:c.clinicalRationale,
    benefitRiskRationale:c.benefitRiskRationale,
    fdaCmcRationale:c.fdaCmcRationale,
    evidenceGap:c.evidenceGap, sourceDate:c.sourceDate,
    sourceUrl:c.applicationReferenceUrl, evidenceUrl:c.clinicalEvidenceReferenceUrl,
    independentlyValidated:false, calibratedProbability:null,
    label:c.call === "APPROVAL_LEAN" ? "Approval lean" :
      c.call === "CRL_LEAN" ? "CRL lean" :
      c.call === "ALREADY_APPROVED" ? "Already approved" : "Abstain"
  };
}

export async function GET() {
  try {
    const rosterByNct = validateResearch();
    const upstream = await fetch(SOURCE, {
      cache:"no-store", redirect:"error", headers:{Accept:"application/json"},
      signal:AbortSignal.timeout(12000)
    });
    if (!upstream.ok) throw new Error("Publication unavailable");
    const body = await upstream.text();
    if (body.length > 300000) throw new Error("Publication too large");
    const raw:unknown = JSON.parse(body);
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Invalid root");
    const data = raw as Record<string,unknown>;
    if (data.schemaVersion !== 1 || !Array.isArray(data.events) || data.events.length > 500 ||
      typeof data.generatedAt !== "string" || !Number.isFinite(Date.parse(data.generatedAt)))
      throw new Error("Invalid publication");
    const seen = new Set<string>();
    const sourceEvents:CalendarSourceEvent[] = data.events.map((item:unknown) => {
      if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error("Invalid event");
      const e = item as Record<string,unknown>;
      if (typeof e.id !== "string" || !/^[a-z0-9-]{3,90}$/.test(e.id) || seen.has(e.id) ||
        typeof e.ticker !== "string" || !/^[A-Z0-9.-]{1,10}$/.test(e.ticker) ||
        typeof e.company !== "string" || e.company.length < 1 || e.company.length > 200 ||
        !validDate(e.date) || typeof e.marketCapUsd !== "number" ||
        !Number.isFinite(e.marketCapUsd) || e.marketCapUsd < 300000000 || e.marketCapUsd > 10000000000 ||
        !Array.isArray(e.ncts) || e.ncts.length > 30 ||
        e.ncts.some(n => typeof n !== "string" || !/^NCT\d{8}$/.test(n)) ||
        (e.drug !== undefined && typeof e.drug !== "string") ||
        (e.sourceUrl !== undefined && (typeof e.sourceUrl !== "string" ||
          !/^https:\/\/[^\s]+$/.test(e.sourceUrl))))
        throw new Error("Invalid event fields");
      seen.add(e.id as string);
      return {id:e.id as string,ticker:e.ticker as string,company:e.company as string,
        date:e.date as string,drug:(e.drug as string)||"",
        marketCapUsd:e.marketCapUsd as number,ncts:e.ncts as string[],
        sourceUrl:(e.sourceUrl as string)||null};
    });
    const matchedCycleIds = new Set<string>();
    const events: Array<CalendarSourceEvent & {
      cycleId:string|null; prediction:ReturnType<typeof safeResearch>|null; dateStatus:string
    }> = [];
    for (const e of sourceEvents) {
      // FDA applications, not tickers or registry studies, are the prediction key.
      // One ticker/day can have two independently adjudicated FDA cycles (SRPT).
      const candidates = calendarResearch.cycles.filter(c=>
        c.ticker === e.ticker && c.associatedNcts.some(n=>e.ncts.includes(n)) &&
        (c.reportedPdufaGoal === e.date || c.call === "ALREADY_APPROVED") &&
        (c.call === "ALREADY_APPROVED" ||
         APPLICATION_CYCLES.find(a=>a.id===c.cycleId)?.reportedGoal===e.date));
      if (!candidates.length) {
        events.push({...e,cycleId:null,prediction:null,
          dateStatus:"SOURCE_REPORTED_DATE_WITHOUT_MATCHED_PREDICTION"});
        continue;
      }
      for (const c of candidates) {
        matchedCycleIds.add(c.cycleId);
        events.push({...e,id:e.id+"-"+c.cycleId,cycleId:c.cycleId,
          drug:c.drug || e.drug,ncts:c.associatedNcts,
          prediction:safeResearch(c),
          dateStatus:c.call === "ALREADY_APPROVED" ?
            "ALREADY_APPROVED_NOT_FUTURE_REVIEW" : "SOURCE_REPORTED_NOT_FDA_VERIFIED"});
      }
    }
    // No date is NOT a date prediction: keep pending filings in an undated
    // watchlist rather than inventing a calendar slot for them.
    const unscheduled = calendarResearch.cycles.filter(c=>!matchedCycleIds.has(c.cycleId) &&
      c.call !== "ALREADY_APPROVED").map(c=>{
      const companyRow = rosterByNct.get(c.associatedNcts[0]);
      if (!companyRow) throw new Error("Unscheduled cycle missing canonical FOCUS roster");
      return {id:c.cycleId,ticker:c.ticker,company:companyRow.company,
        marketCapUsd:companyRow.marketCap,ncts:c.associatedNcts,
        date:null, prediction:safeResearch(c),
        dateStatus:c.reportedPdufaGoal ?
          "GOAL_NOT_IN_PUBLISHED_CALENDAR_REQUIRES_VERIFICATION" :
          "FDA_GOAL_DATE_NOT_ASSIGNED"};
    });
    const unique = new Set(events.map(e=>e.id));
    if (unique.size !== events.length || events.length < sourceEvents.length)
      throw new Error("PDUFA application cycle event expansion invalid");
    return NextResponse.json({
      generatedAt:data.generatedAt, events,unscheduled,
      research:{asOf:calendarResearch.asOf,level:3,
        label:"Provisional Level 3-style research — not validated FDA prediction",
        sourceResearchCommit:calendarResearch.sourceResearchCommit,
        independentlyValidated:false,numericalProbabilitiesAvailable:false}
    },{headers:noStore});
  } catch {
    return NextResponse.json({error:"Calendar source unavailable or invalid; no substitute data is displayed."},
      {status:503,headers:noStore});
  }
}
