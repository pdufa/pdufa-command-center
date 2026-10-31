import type { NextConfig } from "next";

/**
 * The authenticated POOL → PIPELINE reconciliation reads two dated, pinned
 * public research assets using node:fs. Next.js' serverless output tracing
 * must include those exact files in the /api/scope-funnel function bundle.
 * Public asset hosting alone does not make them available to the function.
 *
 * This changes packaging only; it does not alter source records, eligibility,
 * scientific assessments, archived ledgers, or scan automation.
 */
const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    "/api/scope-funnel": [
      "./public/phase3-census-2026-10-26.csv",
      "./public/phase3-census-sources-2026-10-26.json",
    ],
  },
};

export default nextConfig;
