import type {Metadata} from "next";
import IntelligenceHub from "../IntelligenceHub";

export const metadata: Metadata = {
  title: "CAL — PDUFA Calendar | PDUFA Command Center",
  description: "Read-only source-linked PDUFA target date calendar for FOCUS issuers within $300M–$10B market cap."
};
export default function CalPage() {
  return <IntelligenceHub initialView="cal"/>;
}
