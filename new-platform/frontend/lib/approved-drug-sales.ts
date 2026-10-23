import { parseEvidenceCsv } from "./restriction-evidence";

export const SALES_SOURCE_URL = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/approved_drug_sales_verified.csv";
const COLUMNS = ["company", "ticker", "approved_product", "indication", "period", "individual_sales", "currency", "company_net_sales", "partner_sales", "royalties", "combined_total", "source_url", "verified_on", "disclosure_status"];
const SOURCES = new Set(["sec.gov", "www.sec.gov", "investors.vrtx.com", "ir.biocryst.com", "investors.alnylam.com"]);

export type SalesDisclosure = {
  company: string; ticker: string; product: string; indication: string; period: string;
  individualSales: number; currency: "USD millions"; companyFigure: number | null;
  partnerSales: number | null; royalties: number | null; combinedTotal: number | null;
  sourceUrl: string; verifiedOn: string; note: string;
};
export type SalesPeriod = {
  period: string; products: SalesDisclosure[]; listedProductsSubtotal: number;
  companyFigure: number | null; companyFigureConflict: boolean;
};
export type CompanySales = {
  schemaVersion: 1; ticker: string; company: string; status: "available" | "not-recorded";
  periods: SalesPeriod[]; fetchedAt: string; sourceUrl: string;
};
export type SalesIndex = { fetchedAt: string; byTicker: Record<string, SalesDisclosure[]> };

export function salesTicker(value: string) {
  const ticker = value.trim().toUpperCase();
  return /^[A-Z][A-Z0-9.-]{0,11}$/.test(ticker) ? ticker : "";
}

function canonicalPeriod(value: string) {
  const match = /^(FY|H1|H2|Q[1-4]|9M) ?(20\d{2})$/.exec(value.toUpperCase());
  if (!match) throw new Error("Unsupported sales reporting period");
  return match[1] === "FY" ? match[1] + match[2] : match[1] + " " + match[2];
}

function amount(value: string): number | null {
  if (!value) return null;
  if (!/^\d+(?:\.\d+)?$/.test(value)) throw new Error("Invalid sales amount");
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0 || number >= 1e9) throw new Error("Invalid sales amount");
  return number;
}

export function buildSalesIndex(csv: string, fetchedAt: string): SalesIndex {
  const rows = parseEvidenceCsv(csv);
  if (!rows.length || Object.keys(rows[0]).join(",") !== COLUMNS.join(",")) throw new Error("Sales ledger schema mismatch");
  const index: SalesIndex = { fetchedAt, byTicker: {} };
  const seen = new Set<string>();
  for (const row of rows) {
    const ticker = salesTicker(row.ticker), period = canonicalPeriod(row.period);
    const key = [ticker, row.approved_product.toUpperCase(), period].join("|");
    if (!ticker || !row.company || !row.approved_product || !row.indication || !row.disclosure_status) throw new Error("Sales identity is incomplete");
    if (seen.has(key)) throw new Error("Duplicate sales disclosure");
    seen.add(key);
    const source = new URL(row.source_url);
    if (source.protocol !== "https:" || source.username || source.password || !SOURCES.has(source.hostname)) throw new Error("Invalid sales source");
    if (row.currency !== "USD millions") throw new Error("Unexpected sales units");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(row.verified_on) || new Date(row.verified_on).toISOString().slice(0, 10) !== row.verified_on) throw new Error("Invalid sales verification date");
    const individualSales = amount(row.individual_sales);
    if (individualSales === null) throw new Error("Product sales are missing");
    const records = index.byTicker[ticker] ||= [];
    if (records.some(record => record.company.toLowerCase() !== row.company.toLowerCase())) throw new Error("Ticker has conflicting company names");
    records.push({ company: row.company, ticker, product: row.approved_product, indication: row.indication,
      period, individualSales, currency: "USD millions", companyFigure: amount(row.company_net_sales),
      partnerSales: amount(row.partner_sales), royalties: amount(row.royalties), combinedTotal: amount(row.combined_total),
      sourceUrl: row.source_url, verifiedOn: row.verified_on, note: row.disclosure_status });
  }
  return index;
}

function periodOrder(period: string) {
  const match = /^(FY|H1|H2|Q[1-4]|9M) ?(20\d{2})$/.exec(period)!;
  const months: Record<string, number> = { FY: 12, H1: 6, H2: 12, Q1: 3, Q2: 6, Q3: 9, Q4: 12, "9M": 9 };
  return Number(match[2]) * 100 + months[match[1]];
}

/** Match only the issuer's exact ticker, never a similar name, drug or partner. */
export function companySales(index: SalesIndex, value: string): CompanySales {
  const ticker = salesTicker(value), records = index.byTicker[ticker] || [];
  const groups = new Map<string, SalesDisclosure[]>();
  for (const record of records) groups.set(record.period, [...(groups.get(record.period) || []), record]);
  const periods = [...groups].sort(([a], [b]) => periodOrder(b) - periodOrder(a) || a.localeCompare(b)).map(([period, products]) => {
    const companyFigures = [...new Set(products.map(product => product.companyFigure).filter((n): n is number => n !== null))];
    return { period, products: [...products].sort((a, b) => a.product.localeCompare(b.product)),
      listedProductsSubtotal: Number(products.reduce((sum, product) => sum + product.individualSales, 0).toFixed(6)),
      companyFigure: companyFigures.length === 1 ? companyFigures[0] : null, companyFigureConflict: companyFigures.length > 1 };
  });
  return { schemaVersion: 1, ticker, company: records[0]?.company || "", status: periods.length ? "available" : "not-recorded", periods, fetchedAt: index.fetchedAt, sourceUrl: SALES_SOURCE_URL };
}

export function salesAmount(value: number) {
  return "$" + new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 }).format(value) + " million";
}
