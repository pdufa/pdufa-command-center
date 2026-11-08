import {permanentRedirect} from "next/navigation";

/** The former numeric score dashboard is retired. Its dated NCT, registry,
 * trial and source-audit records remain unchanged in repository history and
 * research JSON. Open phase-first scientific evidence instead.
 */
export const metadata={
 title:"Alkermes scientific evidence · PDUFA",
 description:"Independent phase-aware scientific review and preserved source evidence."
};
export default function AlkermesHistoricalScoreRedirect(){
 permanentRedirect("/phase-first");
}
