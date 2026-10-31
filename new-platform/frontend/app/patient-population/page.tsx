import type { Metadata } from "next";
import PatientPopulationTab from "./PatientPopulationTab";

export const metadata: Metadata = {
  title: "#1 Patient Population | PDUFA Post–Phase 3 Pipeline",
  description: "Read-only patient population research for completed Phase 3 trials in $300M–$10B publicly traded companies.",
};

export default function PatientPopulationPage() {
  return <main><PatientPopulationTab /></main>;
}
