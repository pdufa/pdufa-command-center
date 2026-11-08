/** Source-anchored independent clinical adjudication workbench.
 * Covers concrete analysis conflicts and clinical benefit-risk tension without
 * medical credential claims, causality overstatement, or FDA outcome forecasts.
 * Current dated research snapshot: November 7, 2026.
 */
import {APPLICATION_CYCLES} from "./medical-intelligence-applications";
import {ADDITIONAL_ADJUDICATION_CASES} from "./medical-intelligence-clinical-adjudication-extra";
import {ADJUDICATION_WAVE_A} from "./medical-intelligence-clinical-adjudication-wave-a";
import {ADJUDICATION_WAVE_B} from "./medical-intelligence-clinical-adjudication-wave-b";
export type ClaimSourceType="FDA_REVIEWER"|"FDA_ACTION_LETTER"|"FDA_DOCUMENTED_APPLICANT_ANALYSIS"|"SEC_SPONSOR_FILING"|"SPONSOR_TRIAL_DATA"|"SPONSOR_REPORT_OF_FDA_COMMUNICATION"|"SPONSOR_STATUS"|"PEER_REVIEWED_TRIAL"|"FDA_PUBLIC_APPROVAL";
export type EvidenceRole="FAVORABLE"|"CHALLENGING"|"CONTEXT";
export type AdjudicationClaim={
 id:string;role:EvidenceRole;type:ClaimSourceType;date:string;title:string;url:string;scope?:"RELATED_EXTERNAL_TRIAL";
 section:string;trial:string;measure:string;result:string;limits:string;
};
export type AdjudicationCase={
 id:string;cycleId:string;nct:string;specialty:string;title:string;
 mode:"ANALYSIS_CONFLICT"|"BENEFIT_RISK_DISCORDANCE"|"REGULATORY_OBJECTION"|"REGULATORY_STATUS_CORRECTION";
 category:"EFFICACY_STATISTICS"|"SAFETY_AND_PATIENT_BENEFIT"|"CMC_AND_FACILITY"|"APPLICATION_IDENTITY";
 researchDate:string;regulatoryQuestion:string;clinicalQuestion:string;
 verdict:"UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION"|"ALREADY_APPROVED_NO_PENDING_FIRST_APPROVAL";
 timing:"NO_NEW_TIMING_EVENT_PROVEN";
 sources:readonly AdjudicationClaim[];
 clinicalSynthesis:string;whyItCouldFail:string;bestCase:string;
 whatWouldResolve:readonly string[];sourceInterpretation:string;
};
const ORIGINAL_ADJUDICATION_CASES:readonly AdjudicationCase[]=[
  {
    "id": "capr-hope3-analysis",
    "cycleId": "capr-deramiocel",
    "nct": "NCT05126758",
    "specialty": "Neuromuscular medicine / Duchenne",
    "title": "HOPE-3: FDA's original PUL model and applicant's modified model disagree on statistical significance",
    "mode": "ANALYSIS_CONFLICT",
    "category": "EFFICACY_STATISTICS",
    "researchDate": "2026-11-07",
    "regulatoryQuestion": "Can the exact proposed upper-limb claim rely on the revised percentage-change model when the older prespecified PUL absolute-change estimand and FDA sensitivity analyses do not establish the same result?",
    "clinicalQuestion": "Would a child with DMD retain a meaningful upper-limb activity long enough to offset treatment burden, based on results reproducible across prespecified analytical choices?",
    "verdict": "UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION",
    "timing": "NO_NEW_TIMING_EVENT_PROVEN",
    "sources": [
      {
        "id": "capr-fda-original",
        "role": "CHALLENGING",
        "type": "FDA_REVIEWER",
        "date": "2026-07-29",
        "title": "FDA deramiocel advisory briefing, Table 7 (SAP 1.1)",
        "url": "https://www.fda.gov/media/193839/download",
        "section": "Printed pp. 39–40, Table 7",
        "trial": "NCT05126758",
        "measure": "PUL 2.0 absolute-change treatment difference",
        "result": "0.66 PUL points (95% CI −0.45 to 1.77), p=0.24",
        "limits": "This is the original SAP 1.1 analysis; it uses an absolute-change estimand and is not on the same scale as later percentage-change models."
      },
      {
        "id": "capr-fda-sensitivity",
        "role": "CHALLENGING",
        "type": "FDA_REVIEWER",
        "date": "2026-07-29",
        "title": "FDA deramiocel advisory briefing, alternative SAP 3.0 (no imputation)",
        "url": "https://www.fda.gov/media/193839/download",
        "section": "Printed pp. 38–40, Table 7",
        "trial": "NCT05126758",
        "measure": "PUL 2.0 percentage-change treatment difference",
        "result": "2.53% (95% CI −1.48% to 6.53%), p=0.21",
        "limits": "FDA retained available observations and used a different handling of two placebo cases; model sensitivity is documented but does not prove the drug has zero effect."
      },
      {
        "id": "capr-modified",
        "role": "FAVORABLE",
        "type": "FDA_DOCUMENTED_APPLICANT_ANALYSIS",
        "date": "2026-07-29",
        "title": "FDA briefing reproducing applicant's modified CSR model",
        "url": "https://www.fda.gov/media/193839/download",
        "section": "Printed pp. 39–40, Table 7",
        "trial": "NCT05126758",
        "measure": "PUL 2.0 percentage-change treatment difference",
        "result": "4.55% (95% CI 0.47% to 8.63%), nominal p=0.029",
        "limits": "Model added a slow-progressor term and revised missing-data handling; FDA discussed robustness concerns. This is not proof the original SAP primary succeeded."
      }
    ],
    "clinicalSynthesis": "All seven tabled analyses have positive point estimates, but their magnitudes, scales and nominal significance vary. Interpretation requires a disease-specialist view of PUL point differences and the consequence of losing meaningful arm function—not a simple p<0.05 vote.",
    "whyItCouldFail": "FDA could find the efficacy claim lacks robust substantial evidence because the original model and plausible missing-data analyses do not establish a reliable primary outcome.",
    "bestCase": "Supportive upper-limb trajectories and the modified CSR effect could still contribute to approval if FDA accepts the revised estimand and the additional evidence in the amended BLA.",
    "whatWouldResolve": [
      "Obtain FDA's current-cycle response to the amended upper-limb indication and sponsor's new statistical package.",
      "Reproduce original and revised SAP models using patient-level data with prespecified missingness and protocol-change chronology.",
      "Quantify the percent-change versus PUL-point interpretation using validated patient-important functional thresholds.",
      "Investigate the BIMO inspection observation and documented response without declaring it closed absent FDA evidence."
    ],
    "sourceInterpretation": "An actual FDA reviewer disagreement is documented, but the July 2026 advisory package does not constitute a final FDA action on the subsequently amended BLA."
  },
  {
    "id": "mltx-vela2-estimand",
    "cycleId": "mltx-sonelokimab",
    "nct": "NCT06411379",
    "specialty": "Dermatology / hidradenitis suppurativa",
    "title": "VELA-2: prespecified primary composite miss versus significant alternative treatment-policy estimand",
    "mode": "ANALYSIS_CONFLICT",
    "category": "EFFICACY_STATISTICS",
    "researchDate": "2026-11-07",
    "regulatoryQuestion": "Is the full VELA-1, VELA-2, MIRA and adolescent evidence sufficient for the intended label despite VELA-2 failing its prespecified primary composite comparison?",
    "clinicalQuestion": "Does an absolute HiSCR75 response improvement of roughly 9–10 points in VELA-2 reliably reduce pain, drainage, tunnels and daily disability in the intended patients?",
    "verdict": "UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION",
    "timing": "NO_NEW_TIMING_EVENT_PROVEN",
    "sources": [
      {
        "id": "mltx-composite",
        "role": "CHALLENGING",
        "type": "SPONSOR_TRIAL_DATA",
        "date": "2026-06-22",
        "title": "MoonLake VELA Phase 3 detailed clinical slides",
        "url": "https://ir.moonlaketx.com/static-files/1509e4c8-1614-4dea-8a72-902ee67b5e36",
        "section": "VELA pivotal slide, Week 16 HiSCR75 composite strategy",
        "trial": "NCT06411379",
        "measure": "VELA-2 HiSCR75 (composite-strategy primary)",
        "result": "34.1% treated vs 24.9% placebo, approximately +9 percentage points; p=0.053",
        "limits": "This is the prespecified primary composite strategy and did not meet nominal p<0.05; efficacy cannot be declared a fully replicated primary success."
      },
      {
        "id": "mltx-treatment-policy",
        "role": "FAVORABLE",
        "type": "SPONSOR_TRIAL_DATA",
        "date": "2026-06-22",
        "title": "MoonLake VELA Phase 3 detailed clinical slides",
        "url": "https://ir.moonlaketx.com/static-files/1509e4c8-1614-4dea-8a72-902ee67b5e36",
        "section": "VELA pivotal slide, Week 16 HiSCR75 treatment-policy strategy",
        "trial": "NCT06411379",
        "measure": "VELA-2 HiSCR75 (alternative prespecified treatment-policy)",
        "result": "35.9% treated vs 25.6% placebo, approximately +10 percentage points; p=0.033",
        "limits": "Different intercurrent-event/missing-data strategy, not a redo of the composite primary. The two analyses are not independent replications."
      },
      {
        "id": "mltx-fda-typeb",
        "role": "CONTEXT",
        "type": "SPONSOR_REPORT_OF_FDA_COMMUNICATION",
        "date": "2026-01-13",
        "title": "MoonLake announcement about FDA Type B meeting",
        "url": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-immunotherapeutics-announces-positive-outcome-type-b",
        "section": "Company report of Type B discussion",
        "trial": "NCT06411379",
        "measure": "Agency's reported position on sufficiency of existing trials",
        "result": "Sponsor reported FDA indicated SEE may be established without additional HS trials using VELA-1, VELA-2 and MIRA.",
        "limits": "A company characterization of meeting feedback is not a filed FDA final review or guarantee of sufficient efficacy."
      },
      {
        "id": "mltx-pending-filing",
        "role": "CONTEXT",
        "type": "SPONSOR_STATUS",
        "date": "2026-11-04",
        "title": "MoonLake Q3 2026 business update",
        "url": "https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-reports-third-quarter-2026-financial-results-and",
        "section": "Hidradenitis suppurativa filing section",
        "trial": "NCT06411379",
        "measure": "BLA acceptance status",
        "result": "BLA submitted September 30, 2026; FDA acceptance and review goal not yet confirmed in the November 4 disclosure.",
        "limits": "The submission date is not a PDUFA target; do not assume future review timing or acceptance."
      }
    ],
    "clinicalSynthesis": "The alternative estimand demonstrates a similar directional effect to the composite analysis, but a narrow primary failure requires scrutiny of responder definitions, intercurrent events, control-arm behavior and clinical relevance. VELA-1's success and MIRA may offer external support, without converting VELA-2's failed composite primary into a success.",
    "whyItCouldFail": "The FDA may judge that the pivotal replication package, prespecified primary testing or proposed 12+ age indication lacks sufficient corroboration.",
    "bestCase": "The broader body of evidence may support substantial effectiveness under a combination of trials as described in sponsor-reported FDA meeting feedback.",
    "whatWouldResolve": [
      "Obtain full VELA-2 locked SAP, treatment-policy/composite estimand definitions, patient-level intercurrent events and site/placebo response investigations.",
      "Review VELA-1, VELA-2 and MIRA joint independence and endpoint family multiplicity, plus pain/tunnel patient benefit.",
      "Verify VELA-TEEN adolescent efficacy/safety and whether the FDA-accepted BLA contains mature data.",
      "Confirm FDA acceptance and PDUFA goal; do not derive it from the September submission date."
    ],
    "sourceInterpretation": "This is a sponsor-reported estimand divergence and FDA meeting account, not a public FDA determination that the application will be approved or rejected."
  },
  {
    "id": "apmd-synairgy-clinical",
    "cycleId": "apmd-ad109",
    "nct": "NCT05813275",
    "specialty": "Sleep medicine / pulmonary medicine",
    "title": "SynAIRgy: physiologic improvement versus nonsignificant fatigue and substantial treatment discontinuation",
    "mode": "BENEFIT_RISK_DISCORDANCE",
    "category": "SAFETY_AND_PATIENT_BENEFIT",
    "researchDate": "2026-11-07",
    "regulatoryQuestion": "Does a consistent AHI improvement provide adequate patient benefit in the presence of non-significant PROMIS-Fatigue and substantial drug-related treatment stopping?",
    "clinicalQuestion": "Would a patient unable to tolerate PAP actually remain on oral AD109 long enough to feel and function better, with a manageable anticholinergic/noradrenergic burden?",
    "verdict": "UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION",
    "timing": "NO_NEW_TIMING_EVENT_PROVEN",
    "sources": [
      {
        "id": "apmd-ahi",
        "role": "FAVORABLE",
        "type": "PEER_REVIEWED_TRIAL",
        "date": "2026-05-18",
        "title": "Strollo et al., randomized phase 3 SynAIRgy trial",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13318230/",
        "section": "Abstract and Week 26 primary efficacy tables",
        "trial": "NCT05813275",
        "measure": "Week 26 mean AHI treatment difference",
        "result": "−4.0 events/hour (95% CI −6.4 to −1.6), p=0.001; model-estimated baseline AHI reductions 44.1% vs 17.6% placebo",
        "limits": "A physiologic primary endpoint does not directly establish improvement in daily function or cardiovascular clinical events."
      },
      {
        "id": "apmd-fatigue",
        "role": "CHALLENGING",
        "type": "PEER_REVIEWED_TRIAL",
        "date": "2026-05-18",
        "title": "Strollo et al., randomized phase 3 SynAIRgy trial",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13318230/",
        "section": "Results and prespecified hierarchical secondary endpoints",
        "trial": "NCT05813275",
        "measure": "Week 26 PROMIS-Fatigue secondary endpoint",
        "result": "No statistically significant treatment difference.",
        "limits": "This failed second hierarchical secondary test limits formal claims for later endpoints even if nominally positive; it does not negate the AHI primary."
      },
      {
        "id": "apmd-discontinuation",
        "role": "CHALLENGING",
        "type": "PEER_REVIEWED_TRIAL",
        "date": "2026-05-18",
        "title": "Strollo et al., randomized phase 3 SynAIRgy trial",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13318230/",
        "section": "Table 6 safety analysis",
        "trial": "NCT05813275",
        "measure": "Adverse-event leading to treatment discontinuation",
        "result": "69/325 (21.2%) AD109 versus 10/319 (3.1%) placebo; absolute excess ~18.1 percentage points.",
        "limits": "These are adverse-event discontinuations, not all serious events. Do not infer every discontinuation represented a serious harm."
      },
      {
        "id": "apmd-serious-safety",
        "role": "CONTEXT",
        "type": "PEER_REVIEWED_TRIAL",
        "date": "2026-05-18",
        "title": "Strollo et al., randomized phase 3 SynAIRgy trial",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13318230/",
        "section": "Table 6 safety analysis",
        "trial": "NCT05813275",
        "measure": "Serious treatment-emergent events",
        "result": "5/325 (1.5%) AD109 vs 8/319 (2.5%) placebo; investigators judged these serious events unrelated to study treatment.",
        "limits": "Serious TEAEs and discontinuation-causing adverse events are distinct categories and should not be conflated."
      }
    ],
    "clinicalSynthesis": "The randomized AHI effect is confirmed in a peer-reviewed report, but fatigue did not achieve statistical significance and the loss of patients from treatment for tolerability is clinically consequential. The patient-level benefit-risk assessment needs on-treatment versus treatment-policy estimands and pragmatic adherence, rather than interpreting percent AHI reduction as guaranteed symptom improvement.",
    "whyItCouldFail": "FDA could question whether sustained real-world benefit outweighs drug tolerability and whether the proposed label implies symptom benefits unsupported by multiplicity-controlled clinical outcomes.",
    "bestCase": "A statistically reliable primary effect on AHI with supportive oxygenation and hypoxic-burden metrics could support treatment for PAP-intolerant patients if FDA accepts benefit-risk and appropriate labeling.",
    "whatWouldResolve": [
      "Review full SAP hierarchical testing: ODI, fatigue, hypoxic burden, sleep impairment and ≥50% AHI responder endpoint.",
      "Reconstruct discontinuation mechanisms, treatment-policy imputation and the effect among all randomized participants versus retained users.",
      "Compare actual patient-day functioning, ESS/PROMIS responder thresholds and baseline severity, and evaluate monitoring in CV/urinary comorbidities.",
      "Verify LunAIRo replication, integrated adverse-event exposure and all commercial CMC/inspection requirements."
    ],
    "sourceInterpretation": "The clinical publication establishes positive respiratory physiological effects and a tolerability tradeoff; it does not establish a current FDA safety objection."
  }
] as const;
export const ADJUDICATION_CASES:readonly AdjudicationCase[]=[...ORIGINAL_ADJUDICATION_CASES,...ADDITIONAL_ADJUDICATION_CASES,...ADJUDICATION_WAVE_A,...ADJUDICATION_WAVE_B];
export function adjudicationForCycle(cycleId:string):AdjudicationCase[]{
 return ADJUDICATION_CASES.filter(x=>x.cycleId===cycleId);
}
export function getAdjudicationCase(caseId:string):AdjudicationCase|null{
 return ADJUDICATION_CASES.find(c=>c.id===caseId)||null;
}
export const ADJUDICATION_AS_OF="2026-11-07";
export const INVESTIGATION_PRIORITIES=APPLICATION_CYCLES
 .filter(a=>a.stage!=="APPROVED_ALREADY")
 .map(a=>{
  const reviews=adjudicationForCycle(a.id);
  return {cycleId:a.id,drug:a.drug,ticker:a.ticker,goal:a.reportedGoal,linkedNcts:a.ncts,
   detailedCaseCount:reviews.length,currentOutcome:"INDETERMINATE" as const,
   deepestReview:reviews.length?"OPEN_EVIDENCE_ADJUDICATION" as const:"NOT_YET_DEEP_ADJUDICATED" as const,
   missingCoreEvidence:[
    "Confirm current-cycle FDA application and label population",
    "Reproduce locked SAP, missing data, multiplicity and subgroup sensitivity",
    "Complete patient-important benefits and integrated safety adjudication",
    "Review commercial CMC, FDA inspections and deficiency closure"
   ]
  };
 }).sort((a,b)=>(a.goal||"9999-12-31").localeCompare(b.goal||"9999-12-31"));
/** Descriptive calculation only: difference in observed trial proportions; no causal certainty or significance implied. */
export function adverseEventAbsoluteDifference(treatedAffected:number,treatedAtRisk:number,controlAffected:number,controlAtRisk:number){
 for(const x of [treatedAffected,treatedAtRisk,controlAffected,controlAtRisk])
  if(!Number.isSafeInteger(x)||x<0)throw Error("Use nonnegative integer counts");
 if(treatedAtRisk===0||controlAtRisk===0||treatedAffected>treatedAtRisk||controlAffected>controlAtRisk)
  throw Error("Invalid denominators or affected count");
 const treatedPercent=treatedAffected/treatedAtRisk*100;
 const controlPercent=controlAffected/controlAtRisk*100;
 return {
  treatedPercent:Number(treatedPercent.toFixed(2)),
  controlPercent:Number(controlPercent.toFixed(2)),
  excessPercentagePoints:Number((treatedPercent-controlPercent).toFixed(2)),
  interpretation:"Observed absolute discontinuation risk difference in the specific published study; no adjusted causal estimate or universal risk extrapolation."
 };
}
