import type {Metadata} from "next";import DailyResultsPanel from "../DailyResultsPanel";
export const metadata:Metadata={title:"RESULTS — Dated PDUFA Research Reports",description:"Saved daily POOL, Pipeline and FDA designation reports; historical counts not silently reclassified."};
export default function ResultsPage(){return <main className="shell"><h1>RESULTS — Daily Research</h1><DailyResultsPanel/></main>;}
