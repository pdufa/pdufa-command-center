import HistoricalScientificBacktest from "../HistoricalScientificBacktest";
import historicalPilot from "../../data/historicalScientificPilot2026.json";
import AssessmentLauncher from '../AssessmentLauncher';
import type { Metadata } from "next";
import FunnelWorkspace from "../FunnelWorkspace";
import ScientificStepsReadiness from "../ScientificStepsReadiness";
export const metadata:Metadata={title:"POOL — Master Trial Universe | PDUFA",description:"Preserved master inventory of all tracked source records, independent from post–Phase 3 Pipeline qualification."};
export default function PoolPage(){return <><AssessmentLauncher source="POOL"/><ScientificStepsReadiness cohort="POOL"/><HistoricalScientificBacktest surface="POOL" evaluation={historicalPilot}/><FunnelWorkspace section="pool"/></>;}
