export type ResearchStage = "GEM_JR" | "GEM";

type Identity = { programId: string; exactKey: string };
export type ResearchReadiness = Identity & {
  stage: ResearchStage;
  researchOnly: true;
  ordersEnabled: false;
  fsFaChanges: false;
  marketDataStatus: string | null;
  assessmentEvidence: { status: string; assessment_score: number | null; assessment_coverage: number | null };
  marketEvidenceReview: Identity & { status: string; recommendation: null; assessmentScoreChange: false; qualificationChange: false; fsFaChange: false };
  decisionReadiness: Identity & {
    status: "NOT_READY" | "READY_FOR_HUMAN_RESEARCH_REVIEW";
    missingRequirements: string[];
    ordersEnabled: false;
    assessmentScoreChange: false;
    fsFaChange: false;
    tradeCall: null;
    entryPrice: null;
    targetPrice: null;
    stopLoss: null;
  };
  riskEvidenceReview: Identity & {
    stage: ResearchStage;
    identityStatus: string;
    researchOnly: true;
    ordersEnabled: false;
    assessmentScoreChange: false;
    qualificationChange: false;
    fsFaChange: false;
    catalystVerified: boolean;
    financingRiskReviewed: boolean;
    riskFlags: string[];
    checks: { id: string; label: string; status: string; reason: string; source: string; sourceDate: string; checkedAt: string }[];
  };
};

/** Do not display a different trial/stage or an unsupported readiness claim. */
export function researchReadiness(value: unknown, programId: string, exactKey: string, stage: ResearchStage): ResearchReadiness {
  const r = value as ResearchReadiness | null;
  const decision = r?.decisionReadiness, market = r?.marketEvidenceReview, risk = r?.riskEvidenceReview;
  if (!r || !decision || !market || !risk || r.programId !== programId || r.exactKey !== exactKey
      || r.stage !== stage || risk.stage !== stage
      || [decision, market, risk].some(v => v.programId !== programId || v.exactKey !== exactKey)) {
    throw new Error("Research evidence does not match this trial and assessment stage");
  }
  if (r.researchOnly !== true || r.ordersEnabled !== false || r.fsFaChanges !== false
      || risk.researchOnly !== true || risk.ordersEnabled !== false || decision.ordersEnabled !== false
      || [decision, market, risk].some(v => v.assessmentScoreChange !== false || v.fsFaChange !== false)
      || market.qualificationChange !== false || market.recommendation !== null || risk.qualificationChange !== false
      || [decision.tradeCall, decision.entryPrice, decision.targetPrice, decision.stopLoss].some(v => v !== null)) {
    throw new Error("Research evidence boundary mismatch");
  }
  const checks = risk.checks;
  if (!r.assessmentEvidence || typeof r.assessmentEvidence.status !== "string"
      || !Array.isArray(checks) || checks.length !== 3
      || new Set(checks.map(c => c?.id)).size !== 3
      || checks.some(c => !c || !["catalystTiming", "cashRunway", "dilutionRisk"].includes(c.id)
        || [c.label, c.status, c.reason, c.source, c.sourceDate, c.checkedAt].some(v => typeof v !== "string"))
      || !Array.isArray(risk.riskFlags) || risk.riskFlags.some(v => typeof v !== "string")
      || !Array.isArray(decision.missingRequirements) || decision.missingRequirements.some(v => typeof v !== "string")) {
    throw new Error("Incomplete research evidence response");
  }
  const reviewed = new Set(checks.filter(c => c.status === "REVIEWED").map(c => c.id));
  if (risk.catalystVerified !== reviewed.has("catalystTiming")
      || risk.financingRiskReviewed !== (reviewed.has("cashRunway") && reviewed.has("dilutionRisk"))) {
    throw new Error("Research checks disagree with review status");
  }
  const assessment = r.assessmentEvidence;
  const complete = assessment?.status === "COMPLETE"
    && typeof assessment.assessment_score === "number" && Number.isFinite(assessment.assessment_score)
    && assessment.assessment_score >= 0 && assessment.assessment_score <= 100
    && typeof assessment.assessment_coverage === "number" && Number.isFinite(assessment.assessment_coverage)
    && assessment.assessment_coverage >= 99.99 && assessment.assessment_coverage <= 100;
  if (market.status === "RESEARCH_ONLY" && r.marketDataStatus !== "OK") {
    throw new Error("Market review disagrees with the source status");
  }
  const expected = [
    ...(!complete ? ["complete verified assessment"] : []),
    ...(market.status !== "RESEARCH_ONLY" ? ["exact-program market evidence"] : []),
    ...(!risk.catalystVerified ? ["verified catalyst"] : []),
    ...(!risk.financingRiskReviewed ? ["financing and dilution risk review"] : []),
  ];
  if (decision.missingRequirements.length !== expected.length
      || new Set(decision.missingRequirements).size !== expected.length
      || expected.some(v => !decision.missingRequirements.includes(v))
      || decision.status !== (expected.length ? "NOT_READY" : "READY_FOR_HUMAN_RESEARCH_REVIEW")
      || (!expected.length && risk.identityStatus !== "EXACT_IDENTITY_MATCH")) {
    throw new Error("Readiness does not match the available evidence");
  }
  return r;
}

export function evidenceSource(value: string): string | undefined {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : undefined;
  } catch {
    return undefined;
  }
}
