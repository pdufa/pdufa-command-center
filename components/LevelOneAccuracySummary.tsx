"use client";

import React from "react";

export type LevelOneAccuracySummaryProps = {
  focusTrialCount: number;
  historicalTargetCount?: number;
  historicalScoredCount: number;
  historicalCorrectCount: number;
  historicalAbstainedCount?: number;
};

/** Place immediately above the ASSESSMENTS table; never count unscored cases as errors. */
export function LevelOneAccuracySummary({
  focusTrialCount,
  historicalTargetCount = 183,
  historicalScoredCount,
  historicalCorrectCount,
  historicalAbstainedCount = 0,
}: LevelOneAccuracySummaryProps) {
  const valid =
    historicalScoredCount >= 0 &&
    historicalCorrectCount >= 0 &&
    historicalCorrectCount <= historicalScoredCount &&
    historicalAbstainedCount >= 0 &&
    historicalScoredCount + historicalAbstainedCount <= historicalTargetCount;
  const accuracy = valid && historicalScoredCount > 0
    ? (100 * historicalCorrectCount / historicalScoredCount).toFixed(1) + "%"
    : "—%";
  const coverage = valid
    ? `${historicalScoredCount}/${historicalTargetCount}`
    : "Unavailable";

  return (
    <section aria-label="Level 1 assessment and historical accuracy summary"
      style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(180px,1fr))",gap:12,marginBottom:20}}>
      <div style={{border:"1px solid #d1d5db",borderRadius:12,padding:16}}>
        <div style={{fontSize:12,fontWeight:700}}>LEVEL 1 ASSESSMENTS</div>
        <div style={{fontSize:28,fontWeight:700}}>{focusTrialCount}</div>
        <div style={{fontSize:12}}>FOCUS trials</div>
      </div>
      <div style={{border:"1px solid #d1d5db",borderRadius:12,padding:16}}>
        <div style={{fontSize:12,fontWeight:700}}>OVERALL L01 ACCURACY</div>
        <div style={{fontSize:28,fontWeight:700}}>{accuracy}</div>
        <div style={{fontSize:12}}>Correct / scored, excluding abstentions</div>
      </div>
      <div style={{border:"1px solid #d1d5db",borderRadius:12,padding:16}}>
        <div style={{fontSize:12,fontWeight:700}}>HISTORICAL COVERAGE</div>
        <div style={{fontSize:28,fontWeight:700}}>{coverage}</div>
        <div style={{fontSize:12}}>2026 FDA decision cohort · abstained: {historicalAbstainedCount}</div>
      </div>
    </section>
  );
}
