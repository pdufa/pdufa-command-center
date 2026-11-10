import type {Metadata} from "next";
import IntelligenceHub from "../IntelligenceHub";
export const metadata:Metadata={title:"NEWS — PDUFA Intelligence",description:"Official FDA source news and dated sponsor/SEC application evidence, transparently attributed."};
export default function NewsPage(){return <IntelligenceHub initialView="news"/>;}
