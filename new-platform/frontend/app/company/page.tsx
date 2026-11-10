import type {Metadata} from "next";
import IntelligenceHub from "../IntelligenceHub";
export const metadata:Metadata={title:"COMPANY — PDUFA Application Intelligence",description:"Source-linked exact drug, indication, FDA application cycle and company records."};
export default function CompanyPage(){return <IntelligenceHub initialView="company"/>;}
