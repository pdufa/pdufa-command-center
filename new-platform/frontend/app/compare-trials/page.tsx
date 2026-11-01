import type {Metadata} from "next";
import TrialComparison from "../TrialComparison";
export const metadata:Metadata={
  title:"COMPARE TRIALS — Evidence Review | PDUFA",
  description:"Read-only side-by-side research across 20 post-Phase 3 benefit assessments, with source and readiness checks."
};
export default function CompareTrialsPage(){return <TrialComparison/>;}
