import type {Metadata} from "next";
import ChartsWorkspace from "./ChartsWorkspace";

export const metadata:Metadata={
 title:"CHARTS — Alpaca Prices & FDA Overlays | PDUFA",
 description:"Select a saved Watch/Trade program; the app supplies the exact ticker and permanent Program ID for Alpaca price charts and research FDA overlays."
};

export default function ChartsPage(){return <ChartsWorkspace/>;}
