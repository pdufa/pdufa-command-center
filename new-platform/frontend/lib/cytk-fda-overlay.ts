/** Exact-source CYTK event records only. Do not attach to other tickers or programs. */
import type {FdaMilestone} from "../app/AlpacaStockChart";
import fdaAutoEvents from "../app/alpaca-cytk/fda-auto-events.json";

export const cytkEvents: FdaMilestone[] = [
  {
    id: "verified-cytk-2025-approval",
    category: "original-approval",
    date: "2025-12-19",
    label: "Initial FDA approval — MYQORZO (SEQUOIA-HCM)",
    chartLabel: "FDA approval 12/19",
    detail: "Prior initial approval for obstructive HCM. Separate from the MAPLE-HCM supplemental application.",
    source: "https://ir.cytokinetics.com/press-releases/press-release-details/2025/Cytokinetics-Announces-FDA-Approval-of-MYQORZO-aficamten-for-the-Treatment-of-Adults-with-Symptomatic-Obstructive-Hypertrophic-Cardiomyopathy-to-Improve-Functional-Capacity-and-Symptoms/"
  },
  {
    id: "verified-cytk-2026-snda",
    category: "submission",
    date: "2026-05-05",
    label: "MAPLE-HCM supplemental NDA acceptance disclosed",
    chartLabel: "FDA sNDA 5/5",
    detail: "Company's dated quarterly announcement confirmed FDA acceptance and November 14 target; the FDA's actual acceptance date was not stated here.",
    source: "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Reports-First-Quarter-2026-Financial-Results-and-Provides-Business-Update/default.aspx"
  },
  {
    id: "verified-cytk-2026-maple-data",
    date: "2026-08-29",
    label: "MAPLE-HCM additional trial analysis released",
    chartLabel: "MAPLE data 8/29",
    detail: "Company disclosed additional MAPLE-HCM and ACACIA-HCM clinical data. Not a new FDA decision.",
    source: "https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx"
  },
  {
    id: "verified-cytk-2026-pdufa",
    date: "2026-11-14",
    label: "MAPLE-HCM sNDA — scheduled FDA PDUFA target",
    chartLabel: "PDUFA 11/14",
    detail: "Future FDA target action date, not a guaranteed decision date or predicted approval.",
    source: "https://www.sec.gov/Archives/edgar/data/1061983/000119312526206360/cytk-ex99_1.htm",
    planned: true
  },
  ...(fdaAutoEvents.events as FdaMilestone[])
];
export const cytkCategories = fdaAutoEvents.categories;
/** No other program has an integrated official FDA event feed in this module. */
export const unconnectedFdaCategories = fdaAutoEvents.categories.map(c=>({
  id:c.id,title:c.title,mode:"separate_source_required"
}));
